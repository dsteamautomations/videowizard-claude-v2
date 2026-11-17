"""Set a run back to the start of its references: the reference drawings to approve again, then the references step from its beginning
(SK, 17 Nov 2026, VW-24: "can we roll back VW24 to the Reference drawing stage" … "yes roll back. i will ask the user to test it"), so the
film goes through the rebuilt step of design/211. Run on the VM as the service user, from /opt/vw2/app/server:
    python ../scripts/reset_run_references_start.py VW-24 "<SK's words>" --dry     # show what would change and what the page would show; writes nothing
    python ../scripts/reset_run_references_start.py VW-24 "<SK's words>"           # set it back
    python ../scripts/reset_run_references_start.py VW-24 "<SK's words>" --undo    # put the earlier state back
- Archives the whole visuals session to <run>/archive-references-start/session.json, then: removes the reference round, the chosen pictures
  (`golden`), the round's kept answers, every made set and every footage frame from the session (the picture files stay in storage), and sets
  each approved reference drawing back to "to approve" (its drawing references are made again when it is approved).
- Unchanged: the treatment, the plan and its accepted gaps, the approvals of the drawings and materials, the drawing sets themselves, the
  cost limit, the money already spent (the jobs stay; the spend is real).
- Refuses if a picture or a take of a shot was already made in this stage.
- --undo puts the archived session back, only while no new round was posted and no thing was searched since.
- Writes one entry in the run's decision log each way."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402

MADE = ('assets', 'recorded_gaps', 'preparations')
DROP = ('round', 'chat_round', 'chat_item', 'round_each', 'page_refused', 'found')


def log(conn, run, code, entry, words):
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder reset on SK's request", 'entry': entry,
                        'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})


def set_back(s):
    """The session at the start of its references; returns what was taken out, in counts."""
    refs = s.get('references') or {}
    sheets = [i for i, r in refs.items() if r.get('kind') == 'sheet']
    frames = [i for i, r in refs.items() if r.get('kind') == 'frame']
    drawn = [i for i, r in refs.items() if r.get('kind') == 'drawing']
    for i in sheets + frames + drawn:
        del refs[i]
    reopened = []
    for eid, d in (s.get('drawings') or {}).items():
        if d.get('status') == 'approved':
            d['status'] = 'proposed'
            d.pop('verdict', None)
            reopened.append(eid)
    for k in DROP:
        s.pop(k, None)
    s['golden'] = {}
    return {'set_pictures': len(sheets), 'footage_frames': len(frames), 'drawing_references': len(drawn), 'drawings_to_approve_again': sorted(reopened)}


def main(code, words, undo=False, dry=False):
    assert words.strip(), "SK's words are required"
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        live, kept = f"{run['id']}/visuals/session.json", f"{run['id']}/archive-references-start/session.json"
        raw = store.get(live)
        s = json.loads(raw.decode('utf-8'))
        if undo:
            if not store.exists(kept):
                sys.exit('refusing: no archived session to put back')
            if s.get('round') or s.get('found'):
                sys.exit('refusing: a new round was posted or things were searched since the reset; not undone here (ask the builder)')
            store.put(live, store.get(kept), 'application/json')
            store.delete([kept])
            log(conn, run, code, 'references reset undone: the earlier round, sets, frames and drawing approvals put back', words)
            print({'undone': True})
            return
        made = {k: len(s.get(k) or {}) for k in MADE if s.get(k)}
        if made:
            sys.exit(f'refusing: pictures or takes of shots were made in this stage ({made}): not a step to redo here')
        if store.exists(kept) and not dry:
            sys.exit('refusing: a session is already archived for this run; undo first, or ask the builder')
        answered = sum(1 for r in ((s.get('round') or {}).get('elements') or {}).values() if r.get('answer'))
        out = set_back(s)
        if dry:
            print({'dry': True, 'sets_judged_that_would_be_lost': answered, **out, 'session_keys_after': sorted(s)})
            return
        store.put(kept, raw, 'application/json')
        store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        log(conn, run, code, f"the references set back to their start for the rebuilt step (design/211): the round, {out['set_pictures']} set pictures and "
                             f"{out['footage_frames']} footage frames taken out of the session (archived; the files stay), the reference drawings of "
                             f"{', '.join(out['drawings_to_approve_again']) or 'no thing'} to approve again; the plan, the accepted gaps, the drawings and materials and the spend are unchanged", words)
        print({'archived': kept, 'sets_judged_lost': answered, **out})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--undo' in sys.argv[3:], '--dry' in sys.argv[3:])
