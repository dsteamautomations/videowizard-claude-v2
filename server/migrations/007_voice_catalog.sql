-- design/54 A: the catalogue mirror (metadata only; samples play from the provider's links).
create table if not exists vw2_voice_catalog (
  voice_id text primary key, name text not null default '', scope text not null default 'library', public_owner_id text, original_voice_id text,
  language text not null default '', accent text not null default '', gender text not null default '', age text not null default '', use_case text not null default '',
  descriptive text not null default '', description text not null default '', preview_url text not null default '', category text not null default '',
  on_account boolean not null default false, seen_at timestamptz, refreshed_at timestamptz, withdrawn_at timestamptz);
create index if not exists vw2_voice_catalog_labels on vw2_voice_catalog(gender, age, accent);
