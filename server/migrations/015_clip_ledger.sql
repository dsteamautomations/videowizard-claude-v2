-- The clip ledger (SK, 23 Nov 2026, after VW-25): per piece of a clip and proposal version, whether it was used and why not. Builder only:
-- written by app/stage2/ledger.py, read with scripts/clip-ledger.py; no page and no `vw` answer reads it. Goes with the run.
create table if not exists vw2_clip_ledger (
  id bigserial primary key,
  run_id uuid not null references vw2_runs(id) on delete cascade,
  version int not null,
  sub_clip_id text not null,
  clip_id text not null default '',
  clip text not null default '',
  result text not null,
  reason text not null default '',
  scene text not null default '',
  decided_by text not null default '',
  at timestamptz not null default now(),
  unique (run_id, version, sub_clip_id, scene, result)
);
create index if not exists vw2_clip_ledger_clip on vw2_clip_ledger(clip_id);
