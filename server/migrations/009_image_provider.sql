-- design/120: the image model chosen once per run, immutable. Old runs are OpenAI.
alter table vw2_runs add column if not exists image_provider text not null default 'openai';
alter table vw2_runs drop constraint if exists vw2_runs_image_provider_check;
alter table vw2_runs add constraint vw2_runs_image_provider_check check (image_provider in ('openai', 'gemini'));
