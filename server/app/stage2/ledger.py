"""The clip ledger (SK, 23 Nov 2026, after VW-25): for every piece of every clip of a film, whether a proposal used it and, if not, why. Built from
what the server already holds at a proposal (the package and the proposed cut); no model call. Builder only: the application writes the table and
never reads it back, so no page, no route and no answer to the `vw` tool carries it. Read it with scripts/clip-ledger.py on the server."""
import logging
from difflib import get_close_matches

log = logging.getLogger('vw2.ledger')


def _row(r, names, result, reason='', scene='', by='server'):
    return {'sub_clip_id': r['sub_clip_id'], 'clip_id': r.get('clip_id') or '', 'clip': names.get(r.get('clip_id')) or r.get('clip_name') or '',
            'result': result, 'reason': str(reason or '')[:600], 'scene': scene or '', 'decided_by': by}


def _names(pk):
    return {c.get('clip_id'): c.get('descriptive_name') for c in pk.get('cards') or []}


def rows(pk, doc, rejected=None):
    """One row per piece and reason. `rejected`: {(option_number, event index): the operator's note} for the shots answered Reject on the review page."""
    pieces = {r['sub_clip_id']: r for r in pk.get('sub_clips') or []}
    names, out, seen = _names(pk), [], set()

    def add(sub, *a, **k):
        if sub in pieces:
            seen.add(sub)
            out.append(_row(pieces[sub], names, *a, **k))

    for o in doc.get('options') or []:
        scene = o.get('beat_id') or ''
        for i, ev in enumerate(o.get('events') or []):
            if ev.get('sub_clip_id'):
                add(ev['sub_clip_id'], 'used', scene=scene, by='assistant')
                if (o.get('option_number'), i) in (rejected or {}):
                    add(ev['sub_clip_id'], 'rejected by the operator', rejected[(o.get('option_number'), i)], scene, 'operator')
            for alt in ev.get('alternatives') or []:
                add(alt.get('sub_clip_id'), 'alternative', scene=scene, by='assistant')
            for c in ev.get('considered') or []:
                if isinstance(c, dict):
                    add(c.get('sub_clip_id'), 'turned down', ': '.join(x for x in (str(c.get('why') or ''), str(c.get('words') or '')) if x), scene, 'assistant')
        best = o.get('best_unchosen') or {}
        if best.get('sub_clip_id'):
            add(best['sub_clip_id'], 'turned down', f"best not chosen: {best.get('rule') or ''}", scene, 'assistant')
    ruled = {x['sub_clip_id']: x.get('reason') for x in pk.get('ruled_out') or []}
    ranks = {b: [x['sub_clip_id'] for x in order] for b, order in (pk.get('ranked') or {}).items()}
    used = {o.get('beat_id'): sum(1 for ev in o.get('events') or [] if ev.get('sub_clip_id')) for o in doc.get('options') or []}
    chapters = (pk.get('project') or {}).get('process_stages') or []
    for sub, r in pieces.items():
        if sub in seen:
            continue
        if sub in ruled:
            out.append(_row(r, names, 'refused by analysis', ruled[sub] or r.get('eligibility'), by='analysis'))
        elif not r.get('fit_kinds'):
            own = r.get('process_stage')
            near = get_close_matches(own, chapters, 1, 0.5) if own else []
            why = (f"its chapter '{own}' is not a chapter of this film" + (f"; nearest: '{near[0]}'" if near else '')) if own and own not in chapters else 'no chapter and no line fit'
            if r.get('process_stage_study') and not own:   # 23 Nov 2026: the scenes file's chapter_map said none
                why = f"its chapter '{r['process_stage_study']}' (from the film it was studied for) was mapped to no chapter of this film"
            out.append(_row(r, names, 'no fit', why))
        else:
            fits = ', '.join(f'{b} ({k})' for b, k in r['fit_kinds'].items())
            place = min(((order.index(sub), b) for b, order in ranks.items() if sub in order), default=None)   # its best place in the server's ranking (23 Nov 2026)
            rank = f"; ranked {place[0] + 1} of {len(ranks[place[1]])} for {place[1]}, where the proposal used {used.get(place[1], 0)}" if place else ''
            out.append(_row(r, names, 'never considered', f'fits {fits}{rank}; the proposal did not name it', by='assistant'))
    return out


def refusal_rows(pk, refusals):
    """A refused proposal: one row per piece a refusal names, with the refusal's words."""
    names = _names(pk)
    return [_row(r, names, 'named in a server refusal', msg) for msg in refusals for r in pk.get('sub_clips') or [] if r['sub_clip_id'] in msg]


def write(conn, run, version, rows_):
    """Never fails its caller: an error is logged and that version's ledger is missing or partial. The same rows sent twice are written once."""
    if not rows_:
        return 0
    try:
        if conn is None:   # a refused proposal: the request's transaction is rolled back, so the rows go in their own
            from ..db import connect
            with connect() as own:
                return write(own, run, version, rows_)
        with (conn.transaction() if hasattr(conn, 'transaction') else conn):   # a savepoint: a failed insert must not spoil the proposal's own writes
            with conn.cursor() as cur:
                cur.executemany('insert into vw2_clip_ledger(run_id, version, sub_clip_id, clip_id, clip, result, reason, scene, decided_by) values (%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                                'on conflict (run_id, version, sub_clip_id, scene, result) do update set reason = excluded.reason, at = now()',
                                [(run['id'], version, r['sub_clip_id'], r['clip_id'], r['clip'], r['result'], r['reason'], r['scene'], r['decided_by']) for r in rows_])
        return len(rows_)
    except Exception:
        log.exception('clip ledger not written for run %s version %s', run.get('id'), version)
        return 0
