-- Client comes from the shared Active clients directory (v1 flow): name + id on the run; the title is chosen at intake.
alter table vw2_runs add column if not exists client_id text not null default '';
