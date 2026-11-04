"""Reset a run's reference round so the visuals stage can run it again (SK, 4 Nov 2026, VW-18: "reset VW-18 so that i can rerun this reference image stage").
Run on the VM as the service user, from /opt/vw2/app/server:  python ../scripts/reset_run_references.py VW-18 "<SK's words>"
- Removes the round and the picture searches from the visuals session (moved to <run>/archive-<date>/visuals/round.json; nothing is deleted outright).
- Keeps the footage frames (approved and rejected), the plan, the accepted gaps and every other part of the session: the next `vw visuals round` shows the frames again.
- Refuses if the run already has sheets, picks, golden pictures or bindings: that is a later state, not a round to redo (ask the builder).
- Writes one entry in the run's decision log."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402

KEEP = ('frame', 'supplied')


def main(code, words):
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        k = f"{run['id']}/visuals/session.json"
        s = json.loads(store.get(k).decode('utf-8'))
        later = [r['id'] for r in s['references'].values() if r.get('kind') not in KEEP]
        if later or s.get('golden') or s.get('bindings'):
            sys.exit(f"refusing: the run is past the round (references {later[:5]}, golden {s.get('golden')}, bindings {len(s.get('bindings') or {})})")
        archive = f"{run['id']}/archive-{date.today().isoformat()}/visuals/round.json"
        old = {'round': s.pop('round', None), 'searches': s.pop('searches', None), 'refs': s.pop('refs', None)}
        store.put(archive, json.dumps(old, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        store.put(k, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        n = sum(1 for r in s['references'].values() if r.get('kind') == 'frame')
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder reset on SK's request",
                            'entry': f"reference round reset: the round ({len((old['round'] or {}).get('elements') or {})} elements) and {len(old['searches'] or {})} searches moved to {archive}; "
                                     f"{n} footage frames kept; the next round runs the kept way (design/151)", 'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
    print({'elements': len((old['round'] or {}).get('elements') or {}), 'searches': len(old['searches'] or {}), 'frames_kept': n, 'archive': archive})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
