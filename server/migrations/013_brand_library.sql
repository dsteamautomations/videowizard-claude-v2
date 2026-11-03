-- design/147 (the brand-generic library, SK 3 Nov 2026): one row per file per client. Every studied clip of a batch is stored, generic or not;
-- only generic rows are proposed to later films of the same client. Keyed by client_id, never by the run's owner.
create table if not exists vw2_library (
  id bigserial primary key,
  client_id text not null,
  sha256 text not null,
  name text not null,
  generic boolean not null default false,
  films jsonb not null default '[]'::jsonb,
  description jsonb not null default '{}'::jsonb,
  media_key text not null,
  evidence_key text,
  contract text,
  clip jsonb not null default '{}'::jsonb,
  fingerprint jsonb,
  marked jsonb,
  missing boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, sha256)
);
create index if not exists vw2_library_client_generic on vw2_library (client_id, generic);
