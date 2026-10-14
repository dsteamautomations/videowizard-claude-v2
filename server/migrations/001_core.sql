-- VideoWizard v2 core ledger. All tables prefixed vw2_; v1 videowizard_* tables are untouched.
create table vw2_procedures (
  version text primary key,
  document jsonb not null,
  published_at timestamptz not null default now()
);

create sequence vw2_run_code;

create table vw2_runs (
  id uuid primary key default gen_random_uuid(),
  code text not null unique default ('VW-' || nextval('vw2_run_code')),
  title text not null default '',
  client text,
  owner_id text not null,
  owner_name text not null,
  procedure_version text not null references vw2_procedures(version),
  status text not null default 'open' check (status in ('open','closed')),
  active_machine text,
  created_at timestamptz not null default now(),
  closed_at timestamptz
);
create index vw2_runs_owner on vw2_runs(owner_id, created_at desc);

create table vw2_stage_outputs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references vw2_runs(id),
  stage text not null,
  unit text,
  version text not null,
  files jsonb not null default '[]'::jsonb,
  summary jsonb not null default '{}'::jsonb,
  cost_cents integer,
  accepted_by text,
  accepted_at timestamptz,
  accepted_quote text,
  stale boolean not null default false,
  created_at timestamptz not null default now()
);
create index vw2_stage_outputs_current on vw2_stage_outputs(run_id, stage, unit) where not stale;

create table vw2_attempts (
  run_id uuid not null references vw2_runs(id),
  stage text not null,
  unit text not null default '',
  count integer not null default 0,
  blocked boolean not null default false,
  primary key (run_id, stage, unit)
);

create table vw2_revises (
  id bigserial primary key,
  run_id uuid not null references vw2_runs(id),
  stage text not null,
  unit text,
  confirm_quote text,
  by_user text not null,
  at timestamptz not null default now()
);

create table vw2_jobs (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references vw2_runs(id),
  stage text not null,
  unit text,
  provider text not null,
  request jsonb not null,
  request_id uuid not null,
  status text not null default 'queued',
  result jsonb,
  error text,
  attempt integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index vw2_jobs_open on vw2_jobs(provider, status) where status in ('queued','running');

create table vw2_defects (
  id bigserial primary key,
  run_id uuid not null references vw2_runs(id),
  stage text,
  error text not null,
  log_excerpt text,
  status text not null default 'open' check (status in ('open','fixed')),
  by_user text not null,
  created_at timestamptz not null default now()
);

create table vw2_sessions (
  token_hash text primary key,
  user_id text not null,
  user_name text not null,
  role text not null,
  kind text not null check (kind in ('browser','executor')),
  expires_at timestamptz not null,
  revoked boolean not null default false,
  created_at timestamptz not null default now()
);

create table vw2_receipts (
  user_id text not null,
  request_id uuid not null,
  fingerprint text not null,
  status integer not null,
  response jsonb not null,
  created_at timestamptz not null default now(),
  primary key (user_id, request_id)
);
