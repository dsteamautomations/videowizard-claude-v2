"""The clip ledger of a film, for the builder (SK, 23 Nov 2026). Run on the server, as user vw2, from /opt/vw2/app/server:
    PYTHONPATH=. /opt/vw2/venv/bin/python ../scripts/clip-ledger.py VW-25            the count per result, then every piece not used
    PYTHONPATH=. /opt/vw2/venv/bin/python ../scripts/clip-ledger.py VW-25 C0051      only the clips whose name or id holds this text
Reads only. The newest proposal version is shown; add --all for every version."""
import sys

from app.db import connect

args = [a for a in sys.argv[1:] if a != '--all']
if not args:
    sys.exit(__doc__)
with connect() as conn:
    run = conn.execute('select id from vw2_runs where code = %s', (args[0],)).fetchone()
    if not run:
        sys.exit(f'no run {args[0]}')
    rows = conn.execute('select * from vw2_clip_ledger where run_id = %s order by version, clip, sub_clip_id, at', (run['id'],)).fetchall()
if not rows:
    sys.exit(f'no ledger for {args[0]} (proposed before the ledger existed, or the write failed: see the server log for "clip ledger not written")')
if '--all' not in sys.argv:
    rows = [r for r in rows if r['version'] == rows[-1]['version']]
if len(args) > 1:
    rows = [r for r in rows if args[1].lower() in (r['clip'] + r['clip_id'] + r['sub_clip_id']).lower()]
counts = {}
for r in rows:
    counts[r['result']] = counts.get(r['result'], 0) + 1
print(f"{args[0]} version {rows[-1]['version'] if rows else '-'}: " + ', '.join(f'{k} {n}' for k, n in sorted(counts.items(), key=lambda x: -x[1])))
for r in rows:
    if r['result'] != 'used':
        print(f"v{r['version']} | {r['clip'][:40]} | {r['sub_clip_id']} | {r['result']} | {r['scene']} | {r['decided_by']} | {r['reason']}")
