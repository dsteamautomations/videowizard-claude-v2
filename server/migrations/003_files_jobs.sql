-- Retained files in storage (verified by size + sha256 on receipt) and background jobs' claim lease.
create table vw2_files (
  key text primary key,
  run_id uuid not null references vw2_runs(id),
  stage text not null,
  name text not null,
  sha256 text not null,
  bytes bigint not null,
  mime text,
  verified_at timestamptz not null default now()
);
create index vw2_files_run on vw2_files(run_id, stage);

alter table vw2_jobs add column lease_until timestamptz;
alter table vw2_jobs add column cost jsonb;
