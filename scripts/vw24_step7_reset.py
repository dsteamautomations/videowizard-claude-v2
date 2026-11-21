"""Take VW-24 back to the END of step 6, so step 7 (AI video) starts fresh on the new code: layouts checked first, the flat layout video, the first
frame first (SK, 21 Nov 2026). NOT run by the builder who wrote it. Run on the VM as the service user, from /opt/vw2/app/server, while nobody works on VW-24:
    python ../scripts/vw24_step7_reset.py "<SK's words>"                                       # dry run: prints what it would clear and keep; writes nothing
    python ../scripts/vw24_step7_reset.py "<SK's words>" --apply "Yes, reset VW-24 step 7"     # saves the session beside it, prints the backup's key, then clears
    python ../scripts/vw24_step7_reset.py "<SK's words>" --undo <backup key>                   # puts that saved session back (the current one is saved first)
- Cleared from the session: `guides` (every AI video shot's scene, frames, verdicts, rounds, held answer, accepted layout, drawing, render, first
  frame, stills with their looks, takes, words to shoot), the take preparations of AI video shots, and any selection, hand-in (assets), review,
  take check, chat item or card, page refusal and "not yet" to recording that belongs to an AI video shot, take or gap (none expected on VW-24).
- Kept: everything of step 6 and before: the drawn graphics (motion_*), stills and their selections, the recorded gaps, the plan and its
  versions, the accepted gaps, the specs, the references and drawings, the treatment, the font; the film record lives on the run, untouched.
- Refuses: other confirmation words; a job of VW-24 queued or running; an open defect on the run; a gap with an AI video shot already recorded
  into the film (it cannot be recorded before its takes are selected: the script names it and stops).
- Deletes no stored file (scenes, frames, renders, drawings, stills stay in storage) and no job row (they are history). A finished guide job
  writes nothing once its shot's guide is gone (`guide.apply_result` returns None when the entry is missing or its scene sha differs).
- Under the run's lock (the app's advisory lock `run:<id>`), held to the end. Nothing is written before the whole session was saved beside it
  and read back the same. Writes one line to the run's log (vw2_log, kind override, by SK with his words) each way."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'server'))

from app import runlog   # noqa: E402
from app.db import connect   # noqa: E402
from app.guide import held   # noqa: E402
from app.storage import storage   # noqa: E402

CODE = 'VW-24'
RULE = "builder reset on SK's request"
WORDS = 'Yes, reset VW-24 step 7'
TAG = 'backup-step7'
OPEN = ('queued', 'running', 'submitted', 'submission_unknown', 'storage_pending')   # a job that can still write (guide.shoot's own list)
ITEMS = ('still:', 'shoot:', 'layout-held:', 'shot-drawing:', 'take-done:')   # chat and page item ids of step 7 (chat_flow._guide_items, _drawing_items, takes)


def video_of(plan):
    """{gap id: its AI video shots} over every scene of every gap (over-inclusive on purpose: the refusal must not miss one)."""
    out = {}
    for gap in plan.get('gaps') or []:
        scenes = [sc for c in gap['choices'] for sc in c['scenes']] if gap.get('choices') else gap.get('scenes') or []
        ids = [sh['id'] for sc in scenes for sh in sc.get('shots') or [] if sh.get('visual_type') == 'video']
        if ids:
            out[gap['gap_id']] = ids
    return out


def guide_line(sid, g):
    v, r, d = g.get('verdicts') or [], g.get('render') or {}, g.get('drawing') or {}
    return (f"  {sid}: {len(v) + int(g.get('rounds_before') or 0)} scene round(s), verdicts {' '.join('pass' if x.get('pass') else 'fail' for x in v) or 'none'}; "
            f"first frame {'ready' if r.get('frame1_key') else 'not made'}; video {r.get('status') or 'not queued'}; drawing {d.get('status') or 'none'}"
            f"{' (approved against its check)' if g.get('accepted') else ''}; stills {len(g.get('stills') or [])}; takes {len(g.get('takes') or [])}"
            f"{'; HELD (three failed checks, waits for the operator)' if held(g) else ''}{'; change asked: ' + g['change']['words'][:80] if g.get('change') else ''}")


def step7(item_id, video_jobs):
    i = str(item_id or '')
    i = i[4:] if i.startswith('pic:') else i
    return i.startswith(ITEMS) or (i.startswith('take:') and i.split(':')[1] in video_jobs)


def set_back(s, gaps, video_jobs):
    """The session at the end of step 6. gaps: {gap: AI video shots}; video_jobs: ids of the run's AI video take jobs. Returns what was cleared."""
    shots = {x for ids in gaps.values() for x in ids} | set(s.get('guides') or {})
    out = {}
    if s.get('guides'):
        out['guides'] = sorted(s['guides'])
    s.pop('guides', None)
    for k, gone in (('preparations', lambda x, row: x in shots or (row or {}).get('guide')),
                    ('selections', lambda x, row: x in shots or str((row or {}).get('job_id')) in video_jobs),
                    ('assets', lambda x, row: x in shots),
                    ('reviews', lambda x, row: x in video_jobs),
                    ('take_checks', lambda x, row: x in video_jobs),
                    ('page_refused', lambda x, row: step7(x, video_jobs)),
                    ('chat_record_wait', lambda x, row: x in gaps)):
        rows = s.get(k) or {}
        ids = [x for x in rows if gone(x, rows[x])]
        for x in ids:
            del rows[x]
        if ids:
            out[k] = sorted(ids)
    for k in ('chat_item', 'chat_card'):
        h = s.get(k) or {}
        if h and any(step7(i, video_jobs) for i in [h.get('id')] + list(h.get('group') or []) + list(h.get('items') or [])):
            out[k] = [h.get('id')]
            s.pop(k)
    return out


def save_backup(store, live, raw, tag):
    """The whole session saved beside it and read back the same, before anything is written; else nothing is written."""
    key = f"{live[:-len('.json')]}.{tag}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    store.put(key, raw, 'application/json')
    if store.get(key) != raw:
        sys.exit(f'refusing: the backup {key} did not read back the same; nothing changed')
    print(f'Backup of the whole session: {key}')
    return key


def undo(store, live, backup, log):
    beside = live.rsplit('/', 1)[0] + '/'
    if f'.{TAG}-' not in backup or not backup.startswith(beside) or '/' in backup[len(beside):] or not store.exists(backup):
        sys.exit(f'refusing: {backup} is no step-7 backup beside {live}')
    raw = store.get(backup)
    json.loads(raw.decode('utf-8'))
    save_backup(store, live, store.get(live), 'before-undo-step7')
    store.put(live, raw, 'application/json')
    log(f'the step-7 reset of {CODE} undone: the session saved at {backup} put back')
    print(f'Undone: {backup} is the session again.')


def main(argv):
    words = argv[0] if argv and not argv[0].startswith('--') else ''
    if not words.strip():
        sys.exit(f"SK's words are required: python ../scripts/vw24_step7_reset.py \"<SK's words>\" [--apply \"{WORDS}\" | --undo <backup key>]")
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
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'override', 'about': CODE, 'rule': RULE, 'entry': entry,
                                'by_kind': 'operator', 'by_name': 'SK', 'quote': words, 'request_id': None})
        if '--undo' in argv:
            return undo(store, live, argv[argv.index('--undo') + 1], log)
        jobs = conn.execute("select id, unit, provider, status, request->>'kind' as kind from vw2_jobs where run_id=%s and status = any(%s) order by created_at",
                            (run['id'], list(OPEN))).fetchall()
        defects = [r['id'] for r in conn.execute("select id from vw2_defects where run_id=%s and status='open'", (run['id'],)).fetchall()]
        video_jobs = {str(r['id']) for r in conn.execute("select id from vw2_jobs where run_id=%s and provider='video'", (run['id'],)).fetchall()}
        raw = store.get(live)
        s = json.loads(raw.decode('utf-8'))
        try:
            entry = next(v for v in s['versions'] if v['plan_digest'] == s['current'])
            gaps = video_of(json.loads(store.get(entry['file']['key']).decode('utf-8'))['document'])
        except Exception as exc:   # noqa: BLE001
            sys.exit(f'refusing: the current plan could not be read ({exc.__class__.__name__}); nothing changed')
        guides = s.get('guides') or {}
        print(f"Run {CODE} ({run['id']}), session {live}")
        print(f'{len(guides)} guides (step 7, AI video):')
        for sid, g in guides.items():
            print(guide_line(sid, g))
        recorded = sorted(set(s.get('recorded_gaps') or {}) & set(gaps))
        refusals = ([f"job {j['id']} ({j['provider']} {j.get('kind') or ''} of {j['unit']}) is {j['status']}" for j in jobs]
                    + [f'open defect {d} on the run' for d in defects]
                    + [f"gap {g} holds AI video shots ({', '.join(gaps[g])}) and is recorded into the film ({s['recorded_gaps'][g]})" for g in recorded])
        print('No job of VW-24 is queued or running.' if not jobs else 'Jobs of VW-24 queued or running: ' + '; '.join(refusals[:len(jobs)]))
        out = set_back(s, gaps, video_jobs)
        print('Would clear:' if not apply else 'Clearing:')
        for k, ids in out.items():
            print(f"  {k}: {len(ids)} ({', '.join(map(str, ids))})")
        print('AI video selections, hand-ins, reviews and take checks found: ' + (', '.join(f'{k} {len(out[k])}' for k in ('selections', 'assets', 'reviews', 'take_checks') if k in out) or 'none') + '.')
        print('Kept: the drawn graphics (motion_*), the stills and their selections, the recorded gaps ' + str(sorted(s.get('recorded_gaps') or {}))
              + ', the plan and its versions, the accepted gaps, the specs, the references and drawings, the treatment, the font, the film record.')
        print('No stored file (scenes, frames, renders, drawings, stills) and no job row is deleted.')
        if refusals:
            print('This would refuse to apply: ' + '; '.join(refusals) + '.')
        if not apply:
            print(f'Dry run: nothing changed. Apply with: --apply "{WORDS}"')
            return None
        if refusals:
            sys.exit('refusing: ' + '; '.join(refusals) + '; nothing changed')
        backup = save_backup(store, live, raw, TAG)
        s['updated_at'] = datetime.now(timezone.utc).isoformat()
        store.put(live, json.dumps(s, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        log(f"step 7 of {CODE} cleared back to the end of step 6, so it starts fresh on the new code: cleared {len(out.get('guides') or [])} guides"
            + ''.join(f', {k} {len(v)}' for k, v in out.items() if k != 'guides')
            + "; kept step 6 and before (drawn graphics, stills and their selections, recorded gaps, plan, references, film record); no stored file or job row deleted; "
            f'the session before is saved at {backup}')
        print(f'Done. Undo with: --undo {backup}')
        return backup


if __name__ == '__main__':
    main(sys.argv[1:])
