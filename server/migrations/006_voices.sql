-- design/52 A: the voice register (favourites, library identity) and its events. Starts empty; nothing is read from earlier runs.
create table if not exists vw2_voices (
  voice_id text primary key, name text not null default '', source text not null default 'custom',
  public_owner_id text, original_voice_id text,
  favourite boolean not null default false, favourite_by text, favourite_at timestamptz, note text not null default '',
  updated_at timestamptz not null default now());
create table if not exists vw2_voice_events (
  id bigserial primary key, voice_id text not null, event text not null, by_id text not null, by_name text not null default '',
  note text not null default '', at timestamptz not null default now());
create index if not exists vw2_voice_events_voice on vw2_voice_events(voice_id, id);
