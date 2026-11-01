-- design/130: the drawn route chosen once per run at `vw start --drawn`, immutable. Older runs draw SVG scenes (the older way, kept until phase 6).
alter table vw2_runs add column if not exists drawn_route text not null default 'svg';
alter table vw2_runs drop constraint if exists vw2_runs_drawn_route_check;
alter table vw2_runs add constraint vw2_runs_drawn_route_check check (drawn_route in ('svg', 'motion'));
