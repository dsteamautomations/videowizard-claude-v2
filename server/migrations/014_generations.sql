-- Integration step A (SK, 12 Nov 2026): one row per attempt of a shot, never overwritten or deleted by the application.
-- `record` is a list of dated entries; each later step of the new AI video process appends its own. Kept with the run, like the decision log.
create table if not exists vw2_generations (
  id bigserial primary key,
  run_id uuid not null references vw2_runs(id) on delete cascade,
  shot_id text not null,
  attempt int not null,
  how text not null,
  verdict text,
  record jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, shot_id, attempt)
);
