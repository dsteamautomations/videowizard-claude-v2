-- design/142 R1: one decision log per run, for every stage: what was decided, about what, by which rule (or "no rule"), who, and the operator's words.
-- The server writes every write step and every refusal; the assistant adds its judgement calls with `vw log`. Kept with the run (the files' retention does not touch it).
create table if not exists vw2_log (
  id bigserial primary key,
  run_id uuid not null references vw2_runs(id) on delete cascade,
  at timestamptz not null default now(),
  stage text not null default '',
  kind text not null,
  about text not null default '',
  rule text not null default '',
  entry text not null,
  by_kind text not null,
  by_name text not null default '',
  quote text not null default '',
  request_id text
);
create index if not exists vw2_log_run_at on vw2_log (run_id, at);
create unique index if not exists vw2_log_once on vw2_log (run_id, request_id, kind) where request_id is not null;
