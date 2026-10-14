-- Learned client rules (blueprint v3.2 §4 step 1.3): appended from rejection reasons and explicit operator rules, shown in every later options package for that client.
create table if not exists vw2_client_rules (id bigserial primary key, client_id text not null, rule text not null, source_run text, created_at timestamptz not null default now());
create index if not exists vw2_client_rules_client on vw2_client_rules(client_id, id);
