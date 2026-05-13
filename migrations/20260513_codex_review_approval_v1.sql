-- OpenClaw Codex review approval v1
-- Human approval metadata for converting queued review items back into codex_tasks.

alter table codex_review_queue
  add column created_codex_task_id integer not null default 0;

create index if not exists idx_codex_review_queue_approval
  on codex_review_queue(review_status, created_codex_task_id, id);
