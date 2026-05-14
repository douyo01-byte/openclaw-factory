from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BOT_DIR = ROOT / "bots"
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

from bots import openclaw_goal_reader_v1 as goal_reader
from bots import telegram_digest_v1 as telegram_digest
from bots import unified_runtime_digest_v1 as unified_digest


def make_row(
    row_id: int,
    task_text: str,
    status: str = "new",
    result_text: str = "",
    reply_text: str = "",
    parent_task_id: int = 0,
    target_bot: str = "kaikun04",
    mode: str = "THINK",
) -> sqlite3.Row:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        """
        create table rows (
          id integer,
          parent_task_id integer,
          task_role text,
          target_bot text,
          mode text,
          status text,
          task_text text,
          clean_prompt text,
          reply_text text,
          result_text text,
          validation_reason text,
          exec_bridge_reason text,
          ts text
        )
        """
    )
    db.execute(
        "insert into rows values (?, ?, '', ?, ?, ?, ?, '', ?, ?, '', '', datetime('now'))",
        (row_id, parent_task_id, target_bot, mode, status, task_text, reply_text, result_text),
    )
    row = db.execute("select * from rows").fetchone()
    db.close()
    return row


def digest_fixture_rows() -> list[sqlite3.Row]:
    winner = "[WINNER_ONLY] 勝ち案件だけ進める。テーマ: 今ある商品の売上改善を1件に絞る"
    goal_impl = "[ROLE:CTO] [GOAL_IMPL] n8n/OpenClaw mainline fixation"
    return [
        make_row(1, goal_impl, status="failed", result_text="llm_error:ConnectionError"),
        make_row(2, goal_impl, status="failed", result_text="llm_error:ConnectionError"),
        make_row(3, winner, status="new"),
        make_row(4, winner, status="new"),
        make_row(5, "[EXEC]\nscript=status_core.sh", status="done", result_text="ok"),
    ]


def create_digest_db(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript(
        """
        create table router_tasks (
          id integer primary key,
          parent_task_id integer default 0,
          task_role text default '',
          target_bot text default '',
          mode text default '',
          status text default '',
          task_text text default '',
          clean_prompt text default '',
          reply_text text default '',
          result_text text default '',
          validation_reason text default '',
          exec_bridge_reason text default '',
          created_at text default (datetime('now')),
          updated_at text default (datetime('now'))
        );
        create table telegram_digest_state (
          key text primary key,
          value text,
          updated_at text default (datetime('now'))
        );
        insert into telegram_digest_state(key, value) values('last_router_task_id', '7');
        """
    )
    for row in digest_fixture_rows():
        db.execute(
            """
            insert into router_tasks(
              id, parent_task_id, task_role, target_bot, mode, status, task_text,
              clean_prompt, reply_text, result_text, validation_reason, exec_bridge_reason,
              created_at, updated_at
            )
            values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                row["id"],
                row["parent_task_id"],
                row["task_role"],
                row["target_bot"],
                row["mode"],
                row["status"],
                row["task_text"],
                row["clean_prompt"],
                row["reply_text"],
                row["result_text"],
                row["validation_reason"],
                row["exec_bridge_reason"],
            ),
        )
    db.commit()
    db.close()


class GoalReaderTests(unittest.TestCase):
    def test_parses_long_horizon_goal_doc(self) -> None:
        goal = goal_reader.read_active_goal()

        self.assertTrue(goal["ok"])
        self.assertTrue(goal["active_goal"])
        self.assertIn("Phase 1", goal["current_phase"])
        phases = [item["phase"] for item in goal["roadmap"]]
        for number in range(1, 8):
            self.assertTrue(
                any(f"Phase {number}" in phase for phase in phases),
                f"missing Phase {number}: {phases}",
            )

    def test_missing_goal_doc_is_safe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            goal = goal_reader.read_active_goal(Path(td) / "missing_goal_doc.md")

        self.assertFalse(goal["ok"])
        self.assertIn("goal document not found", goal["blocked_by"])


class TelegramDigestTests(unittest.TestCase):
    def test_scoring_groups_connection_errors_and_winner_only_rows(self) -> None:
        rows = digest_fixture_rows()
        items = telegram_digest.scored_digest_items(rows)
        by_key = {item["key"]: item for item in items}

        self.assertIn("error:ConnectionError", by_key)
        self.assertEqual(by_key["error:ConnectionError"]["count"], 2)
        self.assertEqual(by_key["error:ConnectionError"]["score"]["compressed_count"], 1)
        winner_keys = [key for key in by_key if key.startswith("winner_only:")]
        self.assertEqual(len(winner_keys), 1)
        self.assertEqual(by_key[winner_keys[0]]["count"], 2)
        self.assertEqual(by_key[winner_keys[0]]["score"]["compressed_count"], 1)

    def test_readable_digest_contains_operator_sections_and_scoring_metadata(self) -> None:
        with mock.patch.object(
            telegram_digest,
            "_goal_summary",
            return_value={"ok": True, "current_focus": "n8n/OpenClaw mainline fixation"},
        ):
            text = telegram_digest.build_digest(digest_fixture_rows())

        for marker in (
            "OpenClaw digest 10m",
            "Status:",
            "Top issue:",
            "Operator next:",
            "Risks:",
            "Top scored items:",
            "duplicate_group_key",
            "compressed_count",
        ):
            self.assertIn(marker, text)

    def test_readable_digest_generation_does_not_open_db(self) -> None:
        rows = digest_fixture_rows()
        with mock.patch.object(
            telegram_digest,
            "_goal_summary",
            return_value={"ok": True, "current_focus": "test"},
        ), mock.patch.object(telegram_digest.sqlite3, "connect", side_effect=AssertionError("db write")):
            text = telegram_digest.build_digest(rows)

        self.assertIn("OpenClaw digest 10m", text)

    def test_sample_mode_does_not_update_last_router_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "digest.db"
            create_digest_db(db_path)
            old_argv = sys.argv[:]
            sys.argv = ["telegram_digest_v1.py", "--sample-recent", "--limit", "5"]
            try:
                with mock.patch.object(telegram_digest, "DB", str(db_path)), mock.patch.object(
                    telegram_digest, "DRY_RUN", True
                ), contextlib.redirect_stdout(io.StringIO()):
                    telegram_digest.main()
            finally:
                sys.argv = old_argv

            db = sqlite3.connect(db_path)
            value = db.execute(
                "select value from telegram_digest_state where key='last_router_task_id'"
            ).fetchone()[0]
            db.close()
        self.assertEqual(value, "7")


class UnifiedDigestTests(unittest.TestCase):
    def test_execution_section_uses_readable_digest_and_stays_compact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "unified.db"
            create_digest_db(db_path)
            db = sqlite3.connect(db_path)
            db.row_factory = sqlite3.Row
            with mock.patch.object(
                telegram_digest,
                "_goal_summary",
                return_value={"ok": True, "current_focus": "n8n/OpenClaw mainline fixation"},
            ):
                section = unified_digest.execution_section(db)
            db.close()

        self.assertIn("Execution:\nOpenClaw digest 10m", section)
        self.assertIn("Top scored items:", section)
        self.assertLessEqual(len(section), 1500)


class OpenClawUiApiTests(unittest.TestCase):
    def test_active_goal_endpoint_function_returns_goal_payload_without_server(self) -> None:
        from bots import openclaw_ui_api

        payload = openclaw_ui_api.active_goal()
        if not isinstance(payload, dict):
            payload = json.loads(getattr(payload, "body", b"{}").decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("Phase 1", payload["current_phase"])


if __name__ == "__main__":
    unittest.main()
