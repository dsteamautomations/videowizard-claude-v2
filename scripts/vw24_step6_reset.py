"""Set VW-24 back to the start of step 6 (the pictures and the drawn graphics), so the film goes through the redo of step 6 of design/221
(SK, 19 Nov 2026). NOT run by the builder who wrote it. Run on the VM as the service user, from /opt/vw2/app/server, while nobody works on VW-24:
    python ../scripts/vw24_step6_reset.py "<SK's words>"                     # dry run: prints what it would clear and keep; writes nothing
    python ../scripts/vw24_step6_reset.py "<SK's words>" --apply             # saves the session beside it, prints the backup's key, then clears
    python ../scripts/vw24_step6_reset.py "<SK's words>" --undo <backup key> # puts that saved session back (the current one is saved first)
Without a database, on a session file (the test of the logic; backups are written beside the file):
    python scripts/vw24_step6_reset.py --check <session.json> [--apply | --undo <backup file>]
- Cleared from the session: every drawn-graphic build trace (the keys of CLEARED below, each with what it holds), the render preparations of
  drawn shots, and the selections, reviews and take checks of drawn takes of this run (listed first; on VW-24 there were none on 19 Nov).
- Kept: the plan and its versions, the accepted gaps, the approved specs (spec_approvals), the references and everything of steps 4 and 5
  (the round, the sets, the golden pictures), the treatment, the session's font; the film record with the font lives on the run, untouched.
- Deletes no stored file (project zips, parts, stills, renders stay in storage) and no job row (the spend is real).
- Nothing is written before the whole session was saved beside it and read back the same.
- Writes one line to the run's log (vw2_log, kind override, rule "builder reset on SK's request", by SK) each way."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

CODE = 'VW-24'
RULE = "builder reset on SK's request"
CLEARED = {   # every session key the drawn graphics of step 6 write (grep `session['motion_` and design/218, 221)
    'motion_projects': 'the uploaded HyperFrames projects of each drawn shot, their rules and brief lines (design/130, 221)',
    'motion_checks': "the checkers' verdicts by round (design/130, 221 phase 2)",
    'motion_bound': 'the project bound to its shot at its clean verdict or when held (design/221, the critic\'s A1)',
    'motion_stills': 'the still end-frames and their approval (design/221 row 3)',
    'motion_parts': 'the shared parts upload and a rejection (design/221 row 1)',
    'motion_parts_approved': 'the approved shared parts (design/221 row 1)',
    'motion_held': "the operator's answer on a held drawing's card (design/221 row 18)",
    'motion_more': '"One more round" used (design/221 row 18)',
    'motion_finish_off': 'a finish taken away by the operator (design/186)',
    'drawings_shown': 'the finished drawings already shown once in the chat (design/221 row 18)',
    'drawing_notes': "Claude's notes on a drawing's view and the shared look (design/218b, 221 row 7)",
    'added_colours': 'the colours added for drawings (design/218 A)',
}
KEPT = ('versions', 'current', 'accepted', 'spec_approvals', 'references', 'round', 'golden', 'treatment', 'font')
CARDS = ('parts:', 'still-end:', 'held:')   # a chat item handed out for one of the drawn graphics' cards


def drawn_shots(s):
    """The shots with a drawn-graphic trace in the session."""
    return ({sid for sid, p in (s.get('preparations') or {}).items() if p.get('drawn')} | {p.get('shot_id') for p in (s.get('motion_projects') or {}).values()}
            | set(s.get('motion_checks') or {}) | set(s.get('motion_bound') or {}) | set(s.get('motion_stills') or {})) - {None}


def set_back(s, drawn_jobs=None):
    """The session at the start of step 6. drawn_jobs: {job id: shot} of the run's drawn renders (from the database), else read from the
    selections of drawn shots. Returns what was cleared and what is kept, in words and counts."""
    shots = drawn_shots(s)
    jobs = dict(drawn_jobs or {})
    jobs.update({str(sel.get('job_id')): sid for sid, sel in (s.get('selections') or {}).items() if sid in shots and sel.get('job_id')})
    out = {'cleared': {}, 'drawn_takes': {}, 'kept': {}}
    for k, what in CLEARED.items():
        if s.get(k):
            out['cleared'][k] = f'{len(s[k])} ({what})'
        s.pop(k, None)
    preps = [sid for sid, p in (s.get('preparations') or {}).items() if p.get('drawn')]
    for sid in preps:
        del s['preparations'][sid]
    if preps:
        out['cleared']['preparations'] = f"{len(preps)} drawn render preparations ({', '.join(sorted(preps))})"
    for k in ('selections', 'reviews', 'take_checks'):
        rows = s.get(k) or {}
        gone = [x for x in rows if (x in jobs if k != 'selections' else str((rows[x] or {}).get('job_id')) in jobs)]
        for x in gone:
            del rows[x]
        out['drawn_takes'][k] = sorted(gone)
    if str((s.get('chat_item') or {}).get('id') or '').startswith(CARDS):
        s.pop('chat_item')
        out['cleared']['chat_item'] = 'the chat item handed out for a drawn card'
    out['kept'] = {k: (len(s[k]) if isinstance(s[k], (dict, list)) else s[k]) for k in KEPT if s.get(k)}
    return out


def summary(out):
    takes = sum(len(v) for v in out['drawn_takes'].values())
    return (', '.join(f'{k} {v.split(" (")[0]}' for k, v in out['cleared'].items()) or 'nothing') + f"; drawn takes' selections, reviews and checks: {takes}"


def reset(store, live, drawn_jobs, apply, log):
    raw = store.get(live)
    s = json.loads(raw.decode('utf-8'))
    out = set_back(s, drawn_jobs)
    print(json.dumps({'session': live, **out}, indent=1, ensure_ascii=False))
    takes = out['drawn_takes']
    print('Drawn takes of this run: ' + ('none found.' if not any(takes.values()) else
                                         '; '.join(f'{k}: {", ".join(v)}' for k, v in takes.items() if v) + ' (cleared).'))
    print('No stored project zip, picture, render or job row is deleted.')
    if not apply:
        print('Dry run: nothing changed. Run again with --apply to clear.')
        return None
    backup = save_backup(store, live, raw, 'backup-step6')
    store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
    log(f"step 6 of {CODE} set back to its start (pictures and drawn graphics) for the redo of design/221: cleared {summary(out)}; kept the plan, "
        f"the accepted gaps, the approved specs, the references and steps 4 and 5, the treatment and the film record; no stored file or job row deleted; "
        f"the session before is saved at {backup}")
    print(f'Done. Undo with: --undo {backup}')
    return backup


def save_backup(store, live, raw, tag):
    """The whole session saved beside it and read back the same, before anything is written; else nothing is written."""
    key = f"{live[:-len('.json')]}.{tag}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    store.put(key, raw, 'application/json')
    if store.get(key) != raw:
        sys.exit(f'refusing: the backup {key} did not read back the same; nothing changed')
    print(f'Backup of the whole session: {key}')
    return key


def undo(store, live, backup, log):
    beside = live.rsplit('/', 1)[0] + '/' if '/' in live else ''
    if '.backup-step6-' not in backup or not backup.startswith(beside) or '/' in backup[len(beside):] or not store.exists(backup):
        sys.exit(f'refusing: {backup} is no step-6 backup beside {live}')
    raw = store.get(backup)
    json.loads(raw.decode('utf-8'))
    save_backup(store, live, store.get(live), 'before-undo')
    store.put(live, raw, 'application/json')
    log(f'the step-6 reset of {CODE} undone: the session saved at {backup} put back')
    print(f'Undone: {backup} is the session again.')


def main(argv):
    if argv[:1] == ['--check']:   # a session file, no database: the logic, for the test and a look before the real run
        from app.storage import LocalStorage
        path = Path(argv[1]).resolve()
        store, live = LocalStorage(path.parent), path.name
        log = lambda entry: print(f'Log line (not written: no database): {entry}')
        if '--undo' in argv:
            return undo(store, live, Path(argv[argv.index('--undo') + 1]).name, log)
        return reset(store, live, None, '--apply' in argv, log)
    words = argv[0] if argv and not argv[0].startswith('--') else ''
    if not words.strip():
        sys.exit("SK's words are required: python ../scripts/vw24_step6_reset.py \"<SK's words>\" [--apply | --undo <backup key>]")
    from app import runlog
    from app.db import connect
    from app.storage import storage
    store = storage()
    with connect() as conn:
        run = conn.execute('select * from vw2_runs where code=%s', (CODE,)).fetchone()
        if not run:
            sys.exit(f'refusing: no run {CODE}')
        live = f"{run['id']}/visuals/session.json"

        def log(entry):
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': CODE, 'rule': RULE, 'entry': entry,
                                'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
        if '--undo' in argv:
            return undo(store, live, argv[argv.index('--undo') + 1], log)
        jobs = {str(r['id']): r['unit'] for r in conn.execute("select id, unit from vw2_jobs where run_id=%s and provider='drawn'", (run['id'],)).fetchall()}
        return reset(store, live, jobs, '--apply' in argv, log)


if __name__ == '__main__':
    main(sys.argv[1:])
