# VideoWizard v2

Agent-operated video builder. Design and plan: [design/](design/) (start with `02-videowizard-v2-build-plan.md`).

## Layout

- `server/` — FastAPI ledger + gatekeeper (slice 1). Tables are prefixed `vw2_` in the existing VideoBuilder Supabase project.
- `design/` — architecture pattern, build plan, slice requirement lists, traceability matrix.
- `plugin/`, `web/` — arrive in slices 2 and 3.

## Server: run the tests

Docker Desktop must be running (the tests start a throwaway `postgres:17` container).

```bash
cd server && python -m pip install -r requirements.txt && python -m pytest -q
```

## Server: run locally

Copy `server/.env.example` to `server/.env`, fill in the values, then:

```bash
cd server && python -m uvicorn app.main:app --port 8002
```

Migrations in `server/migrations/*.sql` and procedure bundles in `server/procedures/*.json` are applied at startup (`app.db.migrate`).

## Plugin (operator side)

`plugin/` is a Claude Code plugin named `vw`. Install it in the operator's Claude Code profile, copy `plugin/operator-CLAUDE.md` to that profile's `CLAUDE.md`, and set `VW2_SERVER_URL` to the server origin. Then say `/vw start a new video` in chat; the first run shows a connect link to approve in the browser.
