"""Set a run's drawings and materials back to "to answer", so the operator approves them again (SK, 16 Nov 2026, VW-24: "I want VW24 to go back … so that
the user will redo or reapprove their answers in the new Claude artifact page"). Run on the VM as the service user, from /opt/vw2/app/server:
    python ../scripts/reset_run_spec_approvals.py VW-24 "<SK's words>"           # set them back
    python ../scripts/reset_run_spec_approvals.py VW-24 "<SK's words>" --undo    # put the earlier approvals back
- Moves the approvals of the drawing specs and the material specs (`spec_approvals` in the visuals session) to
  <run>/archive-spec-approvals/spec_approvals.json. Nothing else changes: the plan, the accepted gaps, the treatment, the specs themselves, the lists of
  wrong forms and any correction already sent all stay.
- Refuses if a picture or a take was already made in this stage: an approval a picture was made under is not taken back here (ask the builder).
- --undo puts the archived approvals back, each only where the spec is still the one that was approved and nothing newer was approved since.
- Writes one entry in the run's decision log each way."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402

MADE = ('assets', 'recorded_gaps', 'preparations')


def log(conn, run, code, entry, words):
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder reset on SK's request", 'entry': entry,
                        'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})


def main(code, words, undo=False):
    assert words.strip(), "SK's words are required"
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        live, kept = f"{run['id']}/visuals/session.json", f"{run['id']}/archive-spec-approvals/spec_approvals.json"
        s = json.loads(store.get(live).decode('utf-8'))
        made = {k: len(s.get(k) or {}) for k in MADE if s.get(k)}
        pictures = [r['id'] for r in (s.get('references') or {}).values() if r.get('kind') not in ('frame', 'supplied')]
        if undo:
            if not store.exists(kept):
                sys.exit('refusing: no archived approvals to put back')
            old, now = json.loads(store.get(kept).decode('utf-8')), s.setdefault('spec_approvals', {})
            back = [k for k in old if k not in now]
            for k in back:
                now[k] = old[k]
            store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
            store.delete([kept])
            log(conn, run, code, f"spec approvals reset undone: {len(back)} earlier approval(s) put back; {len(old) - len(back)} left as approved since", words)
            print({'undone': True, 'put_back': back})
            return
        if made or pictures:
            sys.exit(f'refusing: pictures or takes were made in this stage ({made}, {len(pictures)} made pictures): not a step to redo here')
        if store.exists(kept):
            sys.exit('refusing: approvals are already archived for this run; undo first, or ask the builder')
        old = s.get('spec_approvals') or {}
        if not old:
            sys.exit('nothing to do: no drawing or material is approved on this run')
        store.put(kept, json.dumps(old, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        s['spec_approvals'] = {}
        store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        log(conn, run, code, f"the approvals of {len(old)} drawing and material specs set back to be answered again on the page ({', '.join(sorted(old))}); "
                             'the plan, the accepted gaps and the specs themselves are unchanged', words)
        print({'archived': kept, 'set_back': sorted(old)})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--undo' in sys.argv[3:])
