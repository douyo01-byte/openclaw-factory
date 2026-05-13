#!/usr/bin/env python3
import os
import re
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path.home() / "AI/openclaw-factory/data/openclaw.db")
)
OUTDIR = Path("public_preview/revenue_distribution")
APPROVAL_URL = os.environ.get("REVENUE_APPROVAL_URL", "http://127.0.0.1:8787")

def con():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def has_table(db, name: str) -> bool:
    row = db.execute(
        "select 1 from sqlite_master where type='table' and name=?",
        (name,)
    ).fetchone()
    return row is not None

def cols(db, table: str) -> set[str]:
    if not has_table(db, table):
        return set()
    return {r["name"] for r in db.execute(f"pragma table_info({table})").fetchall()}

def ensure_schema(db):
    db.execute("""
        create table if not exists revenue_distribution_tasks (
          id integer primary key autoincrement,
          group_id integer not null,
          experiment_id integer not null,
          variant_key text not null default '',
          distribution_type text not null,
          traffic_source text not null default '',
          cta_url text not null default '',
          content text not null default '',
          artifact_path text not null default '',
          status text not null default 'planned',
          created_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now')),
          unique(group_id, experiment_id, distribution_type)
        )
    """)
    if "artifact_path" not in cols(db, "revenue_distribution_tasks"):
        db.execute("alter table revenue_distribution_tasks add column artifact_path text not null default ''")
    db.execute("""
        create table if not exists revenue_distribution_publish_queue (
          id integer primary key autoincrement,
          distribution_task_id integer not null unique,
          group_id integer not null,
          experiment_id integer not null,
          variant_key text not null default '',
          distribution_type text not null default '',
          traffic_source text not null default '',
          artifact_path text not null default '',
          candidate_score real not null default 0,
          publish_status text not null default 'queued',
          approval_note text not null default '',
          queued_at text not null default (datetime('now')),
          updated_at text not null default (datetime('now'))
        )
    """)

def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", s or "").strip("_")
    return s[:80] or "distribution"

def render(row) -> str:
    title = f"Revenue LP variant {row['variant_key']}"
    url = row["cta_url"]
    kind = row["distribution_type"]
    if kind == "telegram_post":
        body = f"{title}\n\n短く試せる改善案を公開しました。\n反応を見るため、まずはこちらから確認してください。\n{url}"
    elif kind == "x_thread":
        body = "\n".join([
            f"1/ {title}",
            "2/ 今回はCTA・証拠・導線の違いを小さく分けて検証します。",
            f"3/ 詳細はこちら: {url}",
        ])
    elif kind == "short_blog":
        body = f"# {title}\n\n課題、訴求、CTAを1ページに絞った検証LPです。比較しやすいように流入元を分けて計測します。\n\nCTA: {url}"
    elif kind == "comparison_post":
        body = f"{title}\n\n比較ポイント:\n- 訴求の明確さ\n- CTAの押しやすさ\n- Telegram導線の近さ\n\n検証URL: {url}"
    elif kind == "reddit_style":
        body = f"I tried a small LP experiment for {title}.\n\nWhat changed: clearer CTA, lighter proof, direct Telegram path.\nLink: {url}"
    else:
        body = f"{title}\n\n{row['content']}\n\n{url}"
    return (
        f"distribution_type: {kind}\n"
        f"variant_id: {row['variant_key']}\n"
        f"traffic_source: {row['traffic_source']}\n"
        f"cta_url: {url}\n\n"
        f"{body}\n"
    )

def candidate_score(row) -> float:
    weights = {
        "telegram_post": 100,
        "x_thread": 90,
        "comparison_post": 80,
        "short_blog": 70,
        "reddit_style": 60,
    }
    return float(weights.get(row["distribution_type"], 50))

def enqueue_publish(db, row, artifact_path: str):
    db.execute("""
        insert into revenue_distribution_publish_queue
        (
          distribution_task_id,
          group_id,
          experiment_id,
          variant_key,
          distribution_type,
          traffic_source,
          artifact_path,
          candidate_score,
          publish_status,
          queued_at,
          updated_at
        )
        values
        (?, ?, ?, ?, ?, ?, ?, ?, 'queued', datetime('now'), datetime('now'))
        on conflict(distribution_task_id) do update set
          artifact_path=excluded.artifact_path,
          candidate_score=excluded.candidate_score,
          updated_at=datetime('now')
    """, (
        row["id"],
        row["group_id"],
        row["experiment_id"],
        row["variant_key"],
        row["distribution_type"],
        row["traffic_source"],
        artifact_path,
        candidate_score(row),
    ))

def write_index(db):
    rows = db.execute("""
        select *
        from revenue_distribution_publish_queue
        where publish_status in ('queued', 'approved')
        order by candidate_score desc, id asc
        limit 100
    """).fetchall()
    lines = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Revenue Distribution Publish Queue</title></head><body>",
        "<h1>Revenue Distribution Publish Queue</h1>",
        "<p>Human approval required before real posting.</p>",
        "<ol>",
    ]
    for r in rows:
        lines.append(
            "<li>"
            f"<strong>{r['publish_status']}</strong> score={r['candidate_score']:.1f} "
            f"variant={r['variant_key']} source={r['traffic_source']} type={r['distribution_type']} "
            f"<a href=\"{Path(r['artifact_path']).name}\">{Path(r['artifact_path']).name}</a>"
            f" <a href=\"{APPROVAL_URL}/\">approval ui</a>"
            "</li>"
        )
    lines.extend(["</ol>", "</body></html>"])
    (OUTDIR / "index.html").write_text("\n".join(lines), encoding="utf-8")

def main():
    db = con()
    ensure_schema(db)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    rows = db.execute("""
        select *
        from revenue_distribution_tasks
        where coalesce(status,'') in ('planned', 'new')
          and coalesce(artifact_path,'') = ''
        order by id asc
        limit 50
    """).fetchall()

    done = 0
    for row in rows:
        out = OUTDIR / f"dist_{row['id']}_{slug(row['distribution_type'])}_{slug(row['variant_key'])}.txt"
        out.write_text(render(row), encoding="utf-8")
        db.execute("""
            update revenue_distribution_tasks
            set artifact_path=?,
                status='generated',
                updated_at=datetime('now')
            where id=?
        """, (str(out), row["id"]))
        enqueue_publish(db, row, str(out))
        done += 1

    write_index(db)
    db.commit()
    print(f"[revenue_distribution_executor_v1] generated={done}", flush=True)

if __name__ == "__main__":
    main()
