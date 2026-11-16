"""Take a run's visuals stage back to its start, so the treatment and the plan are made again (SK, 16 Nov 2026, VW-24: "redo the treatment and plan again to see the
revised changes"). Run on the VM as the service user, from /opt/vw2/app/server:
    python ../scripts/reset_run_visuals_start.py VW-24 "<SK's words>"           # take it back
    python ../scripts/reset_run_visuals_start.py VW-24 "<SK's words>" --undo    # put the earlier treatment and plan back
- Moves the visuals session (<run>/visuals/session.json: the treatment, the plan versions and the answers) to <run>/archive-visuals-start/session.json. Nothing is
  deleted outright; the plan files stay where they are. The next `vw visuals prepare` starts a new session: the cost limit by the film's length, the Direction alone first.
- Keeps the film record (category, motion style, shape): it is on the run, not in the session.
- Refuses if the run has made anything in this stage (references, pictures, takes, recorded gaps, visuals jobs): that is a later state, not a start to redo.
- --undo moves the archived session back and sets the session made since aside (<run>/archive-visuals-start/session.redo.json). Refused when nothing is archived.
- Writes one entry in the run's decision log each way."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402

LATER = ('references', 'bindings', 'assets', 'recorded_gaps', 'preparations', 'reviews')


def made(session):
    return {k: len(session.get(k) or {}) for k in LATER if session.get(k)}


def log(conn, run, code, entry, words):
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder reset on SK's request", 'entry': entry,
                        'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})


def main(code, words, undo=False):
    assert words.strip(), "SK's words are required"
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        live, kept, redo = f"{run['id']}/visuals/session.json", f"{run['id']}/archive-visuals-start/session.json", f"{run['id']}/archive-visuals-start/session.redo.json"
        jobs = conn.execute("select count(*) n from vw2_jobs where run_id=%s and stage='visuals'", (run['id'],)).fetchone()['n']
        now = json.loads(store.get(live).decode('utf-8')) if store.exists(live) else None
        if now is not None and (made(now) or jobs):
            sys.exit(f'refusing: the run has made things in the visuals stage ({made(now)}, {jobs} jobs): not a start to redo')
        if undo:
            if not store.exists(kept):
                sys.exit('refusing: no archived session to put back')
            if now is not None:
                store.put(redo, json.dumps(now, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
            store.put(live, store.get(kept), 'application/json')
            store.delete([kept])
            log(conn, run, code, 'visuals start reset undone: the earlier treatment and plan are back; the session made since is set aside in the archive', words)
            print({'undone': True, 'set_aside': redo if now is not None else None})
            return
        if now is None:
            sys.exit('nothing to do: the run has no visuals session')
        if store.exists(kept):
            sys.exit('refusing: a session is already archived for this run; undo first, or ask the builder')
        store.put(kept, json.dumps(now, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        store.delete([live])
        log(conn, run, code, f"visuals stage taken back to its start: the treatment ({len((now.get('treatment') or {}).get('gaps') or [])} gaps), "
                             f"{len(now.get('versions') or [])} plan version(s) and {len(now.get('accepted') or {})} accepted gap(s) moved to the archive; the film record is kept", words)
        print({'archived': kept, 'treatment_gaps': len((now.get('treatment') or {}).get('gaps') or []), 'plan_versions': len(now.get('versions') or []), 'accepted': len(now.get('accepted') or {})})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--undo' in sys.argv[3:])
