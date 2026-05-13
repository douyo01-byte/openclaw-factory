-- OpenClaw Codex review loop v1
-- Deterministic review queue for Codex task results. This only queues next prompts for human approval.

create table if not exists codex_run_transcripts (
  id integer primary key autoincrement,
  task_id integer not null default 0,
  run_id integer not null,
  transcript_text text not null default '',
  result_summary text not null default '',
  diff_summary text not null default '',
  test_summary text not null default '',
  risk_summary text not null default '',
  created_at text not null default (datetime('now')),
  unique(run_id)
);

create table if not exists codex_review_queue (
  id integer primary key autoincrement,
  source_task_id integer not null default 0,
  source_run_id integer not null default 0,
  review_status text not null default 'queued',
  candidate_score real not null default 0,
  review_summary text not null default '',
  next_prompt text not null default '',
  approval_note text not null default '',
  created_at text not null default (datetime('now')),
  updated_at text not null default (datetime('now')),
  unique(source_run_id)
);

create index if not exists idx_codex_review_queue_status
  on codex_review_queue(review_status, candidate_score, id);

