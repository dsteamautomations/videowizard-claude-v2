"""Release VW-24's takes that were set aside by the older first-frame limits (3 % of the width, 3 % of zoom) and are within today's (30 %, SK,
21 Nov 2026), so they go to Claude's check and the review page instead of being made again. NOT run by the builder without SK's words. Run on
the VM as the service user, from /opt/vw2/app/server:
    python ../scripts/vw24_release_first_frame.py "<SK's words>"                                          # dry run: prints each take; writes nothing
    python ../scripts/vw24_release_first_frame.py "<SK's words>" --apply "Yes, release the VW-24 takes"   # saves the session beside it, then releases
    python ../scripts/vw24_release_first_frame.py "<SK's words>" --undo <backup key>                      # puts that saved session back
- Released: a take set aside for its first frame only, measured within today's limits (`guide_worker.released`), of a shot whose one still is
  its approved still (the take was made from it). Its line passes, its block is gone, its scorecard is rebuilt; nothing else changes.
- Left as it is, and named: a take above the limits or set aside for another reason; every take of a shot whose still was made again since
  (a new take from the new still follows; say `--all-shots` to release those too).
- Deletes nothing. Under the run's lock. The whole session is saved beside it and read back before anything is written. One line in the
  run's log (kind override, by SK with his words) each way."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import guide_worker as W, runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.storage import storage   # noqa: E402
from vw24_step7_reset import save_backup   # noqa: E402

CODE = 'VW-24'
WORDS = 'Yes, release the VW-24 takes'
TAG = 'backup-release'


def plan(s, all_shots=False):
    """[(shot, job, what, release?)] for every take of the session that is set aside; the records are changed in place where release is True."""
    out, checks = [], s.get('take_checks') or {}
    for sid, g in sorted((s.get('guides') or {}).items()):
        stills = [x for x in g.get('stills') or [] if x.get('status') not in ('rejected', 'failed')]
        one_still = len(stills) == 1 and stills[0].get('status') == 'approved'
        for t in g.get('takes') or []:
            rec = checks.get(t.get('job_id') or '') or {}
            if not rec.get('blocked'):
                continue
            was = str(rec['blocked'])
            if not (one_still or all_shots):
                out.append((sid, t['job_id'], was + ': left, its still was made again since', False))
            elif W.released(rec):
                out.append((sid, t['job_id'], was + ': RELEASED', True))
            else:
                out.append((sid, t['job_id'], was + ': left, not within the limits or set aside for another reason', False))
    return out


def main(argv):
    words = argv[0] if argv and not argv[0].startswith('--') else ''
    if not words.strip():
        sys.exit(f"SK's words are required: python ../scripts/vw24_release_first_frame.py \"<SK's words>\" [--apply \"{WORDS}\" | --undo <backup key>]")
    apply = '--apply' in argv
    if apply and (argv.index('--apply') + 1 >= len(argv) or argv[argv.index('--apply') + 1] != WORDS):
        sys.exit(f'refusing: the confirmation words differ; apply with exactly --apply "{WORDS}"; nothing changed')
    store = storage()
    with connect() as conn:   # one transaction: the run's lock is held until the end
        run = conn.execute('select * from vw2_runs where code=%s', (CODE,)).fetchone()
        if not run:
            sys.exit(f'refusing: no run {CODE}')
        conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(run['id']),))
        live = f"{run['id']}/visuals/session.json"

        def log(entry):
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': CODE, 'rule': "builder release on SK's request", 'entry': entry,
                                'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
        raw = store.get(live)
        if '--undo' in argv:
            backup, beside = argv[argv.index('--undo') + 1], live.rsplit('/', 1)[0] + '/'
            if f'.{TAG}-' not in backup or not backup.startswith(beside) or not store.exists(backup):
                sys.exit(f'refusing: {backup} is no release backup beside {live}')
            save_backup(store, live, raw, 'before-undo-release')
            store.put(live, store.get(backup), 'application/json')
            log(f'the release of set-aside takes of {CODE} undone: the session saved at {backup} put back')
            return print(f'Undone: {backup} is the session again.')
        s = json.loads(raw.decode('utf-8'))
        rows = plan(s, '--all-shots' in argv)
        print(f"Run {CODE} ({run['id']}); limits now: {W.FIRST_FRAME_SHIFT * 100:.0f} % of the width, {W.FIRST_FRAME_ZOOM * 100:.0f} % of zoom")
        for sid, job, what, _ in rows:
            print(f'  {sid} take {job[:8]}: {what}')
        n = sum(1 for r in rows if r[3])
        print(f'{n} take(s) would be released, {len(rows) - n} left as they are.' if not apply else f'Releasing {n} take(s).')
        if not apply:
            return print(f'Dry run: nothing changed. Apply with: --apply "{WORDS}"')
        if not n:
            sys.exit('nothing to release; nothing changed')
        backup = save_backup(store, live, raw, TAG)
        s['updated_at'] = datetime.now(timezone.utc).isoformat()
        store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        log(f"{n} take(s) of {CODE} set aside by the older first-frame limits released to Claude's check and the page: "
            + ', '.join(f'{r[0]} {r[1][:8]}' for r in rows if r[3]) + f'; the session before is saved at {backup}')
        print(f'Done. Undo with: --undo {backup}')


if __name__ == '__main__':
    main(sys.argv[1:])
