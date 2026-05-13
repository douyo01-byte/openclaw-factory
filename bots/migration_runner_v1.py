#!/usr/bin/env python3
import argparse
import getpass
import hashlib
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = os.environ.get("DB_PATH", str(Path.home() / "AI/openclaw-factory/data/openclaw.db"))

LEDGER_SQL = """
create table if not exists openclaw_migration_ledger (
  id integer primary key autoincrement,
  migration_name text not null unique,
  file_path text not null default '',
  sha256 text not null default '',
  status text not null default 'applied',
  applied_at text not null default (datetime('now')),
  applied_by text not null default '',
  db_path text not null default '',
  error_text text not null default ''
);

create index if not exists idx_openclaw_migration_ledger_status
  on openclaw_migration_ledger(status, applied_at);
"""


def connect():
    db = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("pragma busy_timeout=30000")
    return db


def ensure_ledger(db):
    db.executescript(LEDGER_SQL)


def migration_path(path_arg: str) -> Path:
    path = Path(path_arg)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def migration_name(path: Path) -> str:
    return path.name


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sql_literal(value: str) -> str:
    return "'" + (value or "").replace("'", "''") + "'"


def reject_transaction_control(sql: str, name: str):
    lowered = sql.lower()
    blocked = ["begin", "commit", "rollback"]
    for token in blocked:
        if token in lowered.replace(";", " ").split():
            raise RuntimeError(f"migration {name} must not contain transaction control: {token}")


def current_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return ""


def ledger_row(db, name: str):
    return db.execute(
        "select * from openclaw_migration_ledger where migration_name=?",
        (name,),
    ).fetchone()


def fail_if_blocked(row, sha: str, name: str):
    if not row:
        return
    if row["status"] == "failed":
        raise RuntimeError(f"migration {name} has failed ledger status; inspect before retry")
    if row["status"] == "applied":
        if row["sha256"] != sha:
            raise RuntimeError(f"migration {name} hash mismatch; refusing schema drift")
        return
    raise RuntimeError(f"migration {name} has unsupported ledger status: {row['status']}")


def record_failed(db, name: str, path: Path, sha: str, error: str):
    db.execute("begin immediate")
    try:
        db.execute("""
            insert into openclaw_migration_ledger
            (migration_name, file_path, sha256, status, applied_by, db_path, error_text, applied_at)
            values (?, ?, ?, 'failed', ?, ?, ?, datetime('now'))
            on conflict(migration_name) do update set
              file_path=excluded.file_path,
              sha256=excluded.sha256,
              status='failed',
              applied_by=excluded.applied_by,
              db_path=excluded.db_path,
              error_text=excluded.error_text,
              applied_at=datetime('now')
        """, (name, str(path), sha, current_user(), DB_PATH, error[:1200]))
        db.execute("commit")
    except Exception:
        try:
            db.execute("rollback")
        except sqlite3.OperationalError:
            pass
        raise


def mark_applied(db, path_arg: str) -> str:
    path = migration_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"migration file not found: {path}")
    name = migration_name(path)
    sha = file_sha256(path)
    row = ledger_row(db, name)
    fail_if_blocked(row, sha, name)
    if row and row["status"] == "applied":
        return f"skip mark-applied {name}"
    db.execute("begin immediate")
    try:
        db.execute("""
            insert into openclaw_migration_ledger
            (migration_name, file_path, sha256, status, applied_by, db_path, error_text, applied_at)
            values (?, ?, ?, 'applied', ?, ?, '', datetime('now'))
        """, (name, str(path), sha, current_user(), DB_PATH))
        db.execute("commit")
        return f"marked applied {name}"
    except Exception:
        db.execute("rollback")
        raise


def apply_migration(db, path_arg: str) -> str:
    path = migration_path(path_arg)
    if not path.is_file():
        raise RuntimeError(f"migration file not found: {path}")
    name = migration_name(path)
    sha = file_sha256(path)
    row = ledger_row(db, name)
    fail_if_blocked(row, sha, name)
    if row and row["status"] == "applied":
        return f"skip applied {name}"

    sql = read_sql(path)
    reject_transaction_control(sql, name)
    migration_sql = sql.rstrip()
    if not migration_sql.endswith(";"):
        migration_sql += ";"
    script = "\n".join([
        "begin immediate;",
        migration_sql,
        """
        insert into openclaw_migration_ledger
        (migration_name, file_path, sha256, status, applied_by, db_path, error_text, applied_at)
        values
        ({name}, {path}, {sha}, 'applied', {user}, {db_path}, '', datetime('now'));
        """.format(
            name=sql_literal(name),
            path=sql_literal(str(path)),
            sha=sql_literal(sha),
            user=sql_literal(current_user()),
            db_path=sql_literal(DB_PATH),
        ),
        "commit;",
    ])
    try:
        db.executescript(script)
        return f"applied {name}"
    except Exception as exc:
        try:
            db.execute("rollback")
        except sqlite3.OperationalError:
            pass
        record_failed(db, name, path, sha, repr(exc))
        raise


def status(db) -> str:
    rows = db.execute("""
        select migration_name, status, substr(sha256, 1, 12) as sha, applied_at, error_text
        from openclaw_migration_ledger
        order by id asc
    """).fetchall()
    if not rows:
        return "no migrations recorded"
    lines = []
    for row in rows:
        suffix = f" error={row['error_text'][:80]}" if row["error_text"] else ""
        lines.append(f"{row['status']}\t{row['sha']}\t{row['applied_at']}\t{row['migration_name']}{suffix}")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Apply SQLite migrations with OpenClaw ledger checks.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("file")
    mark_p = sub.add_parser("mark-applied")
    mark_p.add_argument("file")
    return parser.parse_args()


def main():
    args = parse_args()
    db = connect()
    try:
        ensure_ledger(db)
        if args.cmd == "status":
            print(status(db))
        elif args.cmd == "apply":
            print(apply_migration(db, args.file))
        elif args.cmd == "mark-applied":
            print(mark_applied(db, args.file))
        else:
            raise RuntimeError(f"unsupported command: {args.cmd}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
