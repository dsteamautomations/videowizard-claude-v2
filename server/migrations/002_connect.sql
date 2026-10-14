-- Browser connect flow (ported from v1): the executor generates its token locally and sends only the hash;
-- the browser approves the displayed code; approval creates the executor session. No token ever crosses the wire.
create table vw2_connections (
  id uuid primary key,
  token_hash text not null,
  code text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  approved_by text,
  approved_at timestamptz
);
