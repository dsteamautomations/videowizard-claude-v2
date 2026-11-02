-- design/137, design/139: what the operator chose for the film (category, shape, colours, font), each with their words.
-- Runs made before this have film NULL and keep what they were made with (the older way, design/35, kept until they close); new runs start empty and are asked.
alter table vw2_runs add column if not exists film jsonb;
alter table vw2_runs alter column film set default '{}'::jsonb;
