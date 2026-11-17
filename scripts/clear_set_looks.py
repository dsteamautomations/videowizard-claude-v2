"""Clear the recorded look of named sets of a run's reference round, so Claude looks at them again (SK, 17 Nov 2026, VW-24, defect 55: the
looks of the mason's and the roof deck's sets were made on the pictures of an earlier round, served under the same file names).
Run on the VM as the service user, from /opt/vw2/app/server:
    python ../scripts/clear_set_looks.py VW-24 "<SK's words>" MASON SITE_DECK --dry    # show what would change; writes nothing
    python ../scripts/clear_set_looks.py VW-24 "<SK's words>" MASON SITE_DECK          # clear them
- Removes, for each named thing, the row's `set_look` and the `look` of each picture of the set it holds now. Nothing else changes: the
  pictures, the checks, the operator's answers of step 1, the other things.
- Refuses a thing whose set already has the operator's answer (an answer given on a look is not taken back here).
- The removed looks are written to <run>/archive-set-looks/<time>.json.
- Writes one entry in the run's decision log."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app import visuals_stage as V   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402


def main(code, words, things, dry=False):
    assert words.strip() and things, "SK's words and at least one thing are required"
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        live = f"{run['id']}/visuals/session.json"
        s = json.loads(store.get(live).decode('utf-8'))
        rd = s.get('round') or {}
        if not V.round_v2(s):
            sys.exit('refusing: this run has no reference round of the rebuilt step')
        removed = {}
        for eid in things:
            row = (rd.get('elements') or {}).get(eid)
            if not row or not row.get('set'):
                sys.exit(f'refusing: {eid} holds no set')
            if row.get('answer'):
                sys.exit(f'refusing: {eid} already has the operator\'s answer on its set')
            pics = [r for r in s['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == eid and r.get('set') == row['set']]
            removed[eid] = {'set_look': row.pop('set_look', None), 'looks': {p['id']: p.pop('look', None) for p in pics}}
        print({'dry': dry, 'pass_before': rd.get('pass'), 'pass_after': V._round_pass(s, rd),
               'cleared': {eid: {'set_look': bool(v['set_look']), 'picture_looks': sum(1 for x in v['looks'].values() if x)} for eid, v in removed.items()}})
        if dry:
            return
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        store.put(f"{run['id']}/archive-set-looks/{stamp}.json", json.dumps(removed, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder reset on SK's request",
                            'entry': f"the recorded looks of the sets of {', '.join(things)} cleared, to be looked at again: they were made on the pictures of an earlier round "
                                     'served under the same file names (defect 55); the pictures, the checks and every answer are unchanged',
                            'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})


if __name__ == '__main__':
    args = [a for a in sys.argv[3:] if a != '--dry']
    main(sys.argv[1], sys.argv[2], args, '--dry' in sys.argv[3:])
