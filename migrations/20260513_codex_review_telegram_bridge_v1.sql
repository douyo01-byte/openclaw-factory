-- OpenClaw Codex review Telegram bridge v1
-- Tracks low-noise Telegram notifications for queued Codex review items.

create table if not exists codex_review_telegram_notifications (
  id integer primary key autoincrement,
  queue_id integer not null,
  source_task_id integer not null default 0,
  source_run_id integer not null default 0,
  candidate_score real not null default 0,
  message_id text not null default '',
  sent_at text not null default (datetime('now')),
  unique(queue_id)
);

create index if not exists idx_codex_review_telegram_notifications_sent
  on codex_review_telegram_notifications(sent_at, queue_id);
