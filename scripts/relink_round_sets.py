"""Relink a kept reference round to the sets already made (VW-18, 4 Nov 2026: a re-post after Done wiped the round's rows while the 46 finished sets stayed
in the session as orphans; server 0.90.5 refuses that re-post, this repairs the one that happened).
Run on the VM as the service user, from /opt/vw2/app/server:  PYTHONPATH=/opt/vw2/app/server python /tmp/relink_round_sets.py VW-18 "<SK's words>"
- For every round row without a set: the element's newest set (its picture 1, named set-<element>-r<n>) is linked back (set, round, verdict approve, no error).
- The round goes to 'making', which reads as step 2 once no set is still being made; rows that have no set stay as they are (the assistant posts them again).
- Nothing is deleted; one entry in the run's decision log."""
import json
import sys

from app import runlog
from app.db import connect
from app.storage import storage


def main(code, words):
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (code,)).fetchone()
        k = f"{run['id']}/visuals/session.json"
        s = json.loads(store.get(k).decode('utf-8'))
        rd = s.get('round') or {}
        if not rd.get('kept'):
            sys.exit('refusing: no kept round on this run')
        plan_key = next((v['file']['key'] for v in s.get('versions') or [] if v.get('plan_digest') == s.get('current')), None)
        plan = json.loads(store.get(plan_key).decode('utf-8')) if plan_key else {}
        kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
        linked, missing, footage = [], [], []
        for eid, row in rd['elements'].items():
            if row.get('ignored'):
                continue
            approved = [fid for fid in row.get('frames') or [] if (s['references'].get(fid) or {}).get('status') == 'approved']
            if approved and kinds.get(eid) != 'person':   # SK, 5 Nov 2026: the footage picture is the reference; the AI set made for it is set aside
                for r in s['references'].values():
                    if r.get('kind') == 'sheet' and r.get('element_id') == eid and r.get('status') in ('candidate', 'generating'):
                        r.update(status='rejected', rejection={'by': 'SK', 'notes': 'the approved footage picture is the reference; no AI set is needed'})
                row.update(from_footage=True, verdict='approve', set=None, error=None)
                s.setdefault('golden', {})[eid] = approved[0]
                footage.append(eid)
                continue
            if row.get('set'):
                continue
            firsts = [r for r in s['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == eid and (r.get('set_n') or 1) == 1
                      and str(r.get('name') or '').startswith(f'set-{eid}-r') and r.get('status') in ('generating', 'candidate', 'approved')]
            if not firsts:
                missing.append(eid)
                continue
            first = max(firsts, key=lambda r: str(r.get('name')))
            n = int(str(first['name']).rsplit('-r', 1)[-1] or 1)
            row.update(set=first.get('set') or first['id'], round=n, verdict='approve', ignored=False, error=None)
            linked.append(eid)
        rd['pass'] = 'making'
        store.put(k, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': code, 'rule': "builder repair on SK's request",
                            'entry': f"reference round relinked to its sets: {len(linked)} elements linked, {len(footage)} referenced by their approved footage picture (their AI sets set aside), "
                                     f"{len(missing)} without a set ({', '.join(missing)}); the round is at step 2 once no set is being made",
                            'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
    print({'linked': len(linked), 'from_footage': len(footage), 'missing': missing})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
