"""design/147 (design/140, SK 3 Nov 2026): the brand-generic library. After the study, Claude shortlists the clips that would read true in any film of
this client and asks the operator which to mark; every studied clip of the batch is stored (vw2_library), generic or not, keyed by the client. The first
cut of a new film waits for the answer (films started before this release skip it). A later film of the same client gets the generic rows proposed in the
library round (stage2), and its repeats caught before the paid study (L2). Unmark and re-mark by any team member on the client, with their words."""
import json
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from psycopg.types.json import Json

from .errors import Problem

GENERIC_TEST = ('A clip is brand-generic when nothing in it ties it to this one film, so it would read true in another film of the same client: premises, '
                'products, logo shots, staff at work, establishing shots. Not generic: a dated event, a named person speaking about this topic, a one-off site state.')


def asked(run):
    """None for a film started before this release (old ways: no question), else the recorded answer or None when not asked yet."""
    film = (run or {}).get('film')
    if film is None:
        return {'skipped': 'a film started before the library'}
    return film.get('library')


def need_marked(run):
    if (run or {}).get('film') is not None and not (run['film'] or {}).get('library'):
        raise Problem(409, 'LIBRARY_NOT_ASKED', 'The brand-generic question has not been answered for this film: read each clip\'s short description (`vw library`), '
                                                'shortlist the clips that would read true in any film of this client, ask the operator which to mark (none is an answer), '
                                                'and record it: `vw library mark --generic "<names>" --quote "<their words>"`.')


def candidates(conn, run, outputs):
    """Every studied clip of the batch with its short description, for the shortlist; an excluded clip is marked so (it may still be marked, Q5)."""
    media = next((o for o in outputs if o['stage'] == 'media' and o['unit'] is None), None)
    clips = {c['id']: c for c in ((media or {}).get('summary') or {}).get('clips') or []}
    out = []
    for o in outputs:
        if o['stage'] != 'analysis' or o['unit'] is None or o['unit'] not in clips:
            continue
        s = o['summary'] or {}
        if s.get('excluded') and not s.get('descriptive_name'):
            continue   # excluded before a study: nothing describes it
        c = clips[o['unit']]
        out.append({'clip_id': o['unit'], 'name': c['name'], 'sha256': c['sha256'], 'descriptive_name': s.get('descriptive_name'), 'card': s.get('summary_card') or [],
                    'excluded': bool(s.get('excluded')), 'evidence_key': next((f['key'] for f in o.get('files') or [] if str(f.get('name', '')).endswith('.evidence.json')), None),
                    'contract': s.get('contract_version')})
    return out


def _description(store, c):
    """The short description kept with the row: the name, the card, and from the full log the overview and the names it saw (never the whole log)."""
    d = {'descriptive_name': c.get('descriptive_name'), 'card': c.get('card') or []}
    if c.get('evidence_key') and store is not None:
        try:
            log = json.loads(store.get(c['evidence_key']).decode('utf-8')).get('log') or {}
            d['overview'] = log.get('clip_overview')
            d['entities'] = sorted({str(e.get('name')) for e in log.get('entities') or [] if e.get('name')})
        except Exception:   # noqa: BLE001  a missing or unreadable log: the row keeps the card
            pass
    return d


def fingerprint(store, run, clip, ffmpeg='ffmpeg'):
    """Frame fingerprints of the clip (the look-alike tool), for L2's near-repeat check; None when the clip cannot be read."""
    from . import lookalike
    try:
        with tempfile.TemporaryDirectory(prefix='vw2-lib-') as d:
            p = Path(d) / 'clip.mp4'
            p.write_bytes(store.get(f"{run['id']}/media/{clip['name']}"))
            frames = int(float(clip.get('duration_s') or 0) * float(Fraction(str(clip.get('fps') or 25)))) or 1
            return lookalike.video_hashes(p, frames, ffmpeg=ffmpeg)
    except Exception:   # noqa: BLE001
        return None


def mark(conn, store, user, run, outputs, generic_names, quote, ffmpeg='ffmpeg'):
    """Store every studied clip of the batch; the named ones generic. Recorded on the run with the operator's words; re-callable (an upsert)."""
    quote = str(quote or '').strip()
    if not quote:
        raise Problem(422, 'LIBRARY', "Pass the operator's own words with --quote.")
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    if run.get('film') is None:
        raise Problem(409, 'LIBRARY', 'This film was started before the library; its clips are not stored (a backfill is a task of its own).')
    rows = candidates(conn, run, outputs)
    if not rows:
        raise Problem(409, 'LIBRARY', 'No studied clips yet: the library question comes after the analysis.')
    by_name = {r['name']: r for r in rows}
    wanted = [n.strip() for n in (generic_names or []) if str(n).strip()]
    unknown = [n for n in wanted if n not in by_name]
    if unknown:
        raise Problem(422, 'LIBRARY', f"Not clips of this batch: {', '.join(unknown)}. The names are: {', '.join(sorted(by_name))}.")
    answer = {'asked': True, 'generic': wanted, 'quote': quote, 'by': user.get('name') or user.get('id'), 'at': datetime.now(timezone.utc).isoformat()}
    stored = 0
    if run.get('client_id'):
        media = next(o for o in outputs if o['stage'] == 'media' and o['unit'] is None)
        clips = {c['id']: c for c in media['summary']['clips']}
        for r in rows:
            c = clips[r['clip_id']]
            prior = conn.execute('select fingerprint from vw2_library where client_id=%s and sha256=%s', (run['client_id'], c['sha256'])).fetchone()
            fp = prior['fingerprint'] if prior and prior['fingerprint'] else fingerprint(store, run, c, ffmpeg)
            conn.execute('''insert into vw2_library(client_id, sha256, name, generic, films, description, media_key, evidence_key, contract, clip, fingerprint, marked)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            on conflict (client_id, sha256) do update set generic = vw2_library.generic or excluded.generic, name = excluded.name,
                              films = (select jsonb_agg(distinct x) from jsonb_array_elements(vw2_library.films || excluded.films) x),
                              description = excluded.description, evidence_key = coalesce(excluded.evidence_key, vw2_library.evidence_key), contract = excluded.contract,
                              fingerprint = coalesce(vw2_library.fingerprint, excluded.fingerprint), marked = case when excluded.generic then excluded.marked else vw2_library.marked end,
                              updated_at = now()''',
                         (run['client_id'], c['sha256'], c['name'], r['name'] in wanted, Json([run.get('code') or str(run['id'])]), Json(_description(store, r)),
                          f"{run['id']}/media/{c['name']}", r.get('evidence_key'), r.get('contract'),
                          Json({k: c.get(k) for k in ('duration_s', 'width', 'height', 'fps', 'rotation_deg', 'has_audio', 'bytes', 'color_transfer', 'codec', 'pix_fmt', 'bit_rate')}),
                          Json(fp) if fp else None, Json({'by': answer['by'], 'quote': quote, 'at': answer['at']}) if r['name'] in wanted else None))
            stored += 1
    else:
        answer['skipped'] = 'no client on this run: nothing stored'
    conn.execute("update vw2_runs set film = coalesce(film, '{}'::jsonb) || jsonb_build_object('library', %s::jsonb) where id=%s", (Json(answer), run['id']))
    return {'stored': stored, 'generic': wanted, 'skipped': answer.get('skipped')}


def unmark(conn, user, run, name, quote, generic=False):
    """Any team member on the client may unmark (or mark again) one file, with their words; a film that already placed it keeps it."""
    quote = str(quote or '').strip()
    if not quote or not str(name or '').strip():
        raise Problem(422, 'LIBRARY', "Name the clip and pass the operator's own words with --quote.")
    if not run.get('client_id'):
        raise Problem(409, 'LIBRARY', 'This run has no client, so it has no library.')
    row = conn.execute('update vw2_library set generic=%s, marked=%s, updated_at=now() where client_id=%s and (name=%s or sha256=%s) returning id, name, generic',
                       (generic, Json({'by': user.get('name') or user.get('id'), 'quote': quote, 'at': datetime.now(timezone.utc).isoformat(), 'unmarked': not generic}),
                        run['client_id'], name, name)).fetchone()
    if not row:
        raise Problem(404, 'NOT_FOUND', f'{name} is not in the library of this client.')
    return {'name': row['name'], 'generic': row['generic']}


def generic_rows(conn, client_id, contract=None):
    """The client's generic clips that can be proposed: not missing, and of the current clip-log contract (an older contract is retired, old ways)."""
    if not client_id:
        return []
    rows = conn.execute('select * from vw2_library where client_id=%s and generic and not missing order by updated_at desc', (client_id,)).fetchall()
    return [dict(r) for r in rows if not contract or r['contract'] == contract]


BITS_CLIP = 8   # ponytail: of 64, a frame of a moving clip against a library clip's sampled frames; tune on real footage (design/140 C4)


def repeats(conn, store, run, clips, ffmpeg='ffmpeg'):
    """design/147 L2 (SK: before the study): the batch's clips that the client's library already holds, exactly (sha256) or by look (frame fingerprints),
    each with the library file and the film it came with. Nothing for a film started before the library, or a run with no client."""
    if (run or {}).get('film') is None or not run.get('client_id'):
        return []
    found = []
    exact = known(conn, run['client_id'], [c['sha256'] for c in clips])
    rows = [dict(r) for r in conn.execute('select name, films, fingerprint, sha256 from vw2_library where client_id=%s and fingerprint is not null', (run['client_id'],)).fetchall()]
    from . import lookalike
    for c in clips:
        if c['sha256'] in exact:
            e = exact[c['sha256']]
            found.append({'clip_id': c['id'], 'name': c['name'], 'library_name': e['name'], 'films': e['films'], 'kind': 'the same file'})
            continue
        if not rows:
            continue
        fp = fingerprint(store, run, c, ffmpeg) or []
        for r in rows:
            if r['sha256'] != c['sha256'] and any(lookalike.distance(a, b) <= BITS_CLIP for a in fp for b in r['fingerprint'] or []):
                found.append({'clip_id': c['id'], 'name': c['name'], 'library_name': r['name'], 'films': r['films'], 'kind': 'looks the same'})
                break
    return found


def duplicates_decision(found, choice):
    """The operator decides once for the list: keep (analyse anyway) or skip (left out of this film's batch, offered from the library instead)."""
    if not found:
        return []
    if choice not in ('keep', 'skip'):
        lines = '; '.join(f"{f['name']} is {f['kind']} as {f['library_name']} (from {', '.join(map(str, f['films'] or []))})" for f in found)
        raise Problem(409, 'LIBRARY_REPEATS', f'The client\'s library already holds {len(found)} of these clips: {lines}. Ask the operator once: analyse them anyway, '
                                              'or skip them (left out of this film, offered from the library in the library round)? Then `vw analysis start --duplicates keep|skip`.',
                      repeats=found)
    return [f['clip_id'] for f in found] if choice == 'skip' else []


PROPOSE_RULE = ('Propose only where it serves the words: a gap proposal is a footage shot with match "library", evidence from the description, and a note '
                '{kind: "library", question: why it fits}; a swap puts the library clip as the shot with the current clip as its alternative and preferred_because '
                'the reason it serves the words better. Every server rule applies unchanged; nothing is placed without the operator\'s yes on the review page.')


def library_round(conn, store, run, outputs, session, save_package):
    """design/147 L4 (Q3, Q4, Q6): after the second look, the client's generic clips this film can use: each re-checked for eligibility and crops under this
    film's policy and shape (the solver, no paid call), this batch's own files and the proposals the operator rejected left out, added to the package as
    rows marked library so the check, the stills, the render and the package read them. Returns the candidates with their descriptions."""
    from .clip_log import solver
    from .stage2 import package as P
    if (run or {}).get('film') is None:
        return {'candidates': [], 'note': 'a film started before the library: no library round'}
    if not run.get('client_id'):
        return {'candidates': [], 'note': 'no client on this run: no library'}
    pk = session_package(store, session)
    own = {c.get('sha256') for c in (session['package'].get('clips') or {}).values()}
    skipped = {f.get('name') for f in (run['film'] or {}).get('library_skipped') or []}
    rejected = set(session.get('library_rejected') or [])
    rows = [r for r in generic_rows(conn, run['client_id'], 'clip-log-v1')] + [dict(r) for r in conn.execute(
        'select * from vw2_library where client_id=%s and not generic and not missing and name = any(%s)', (run['client_id'], sorted(skipped))).fetchall()] if skipped else \
        generic_rows(conn, run['client_id'], 'clip-log-v1')
    policy, timeline = session['package'].get('policy') or {}, session['package'].get('timeline') or {}
    fps = timeline.get('fps') or 25
    pk['sub_clips'] = [r for r in pk['sub_clips'] if not r.get('library')]
    pk['cards'] = [c for c in pk.get('cards') or [] if not c.get('library')]
    candidates, seen = [], set()
    for r in rows:
        if r['sha256'] in own or r['sha256'] in seen or not r.get('evidence_key'):
            continue
        seen.add(r['sha256'])
        if not store.exists(r['media_key']):
            conn.execute('update vw2_library set missing=true, updated_at=now() where id=%s', (r['id'],))
            continue
        try:
            log = json.loads(store.get(r['evidence_key']).decode('utf-8')).get('log') or {}
        except Exception:   # noqa: BLE001
            continue
        film_from = (r.get('films') or ['?'])[0]
        clip = {'id': r['sha256'][:16], 'name': r['name'], 'sha256': r['sha256'], **(r.get('clip') or {}), 'key': r['media_key'], 'library_from': film_from}
        solver.solve(log, policy, clip, timeline)
        d = r.get('description') or {}
        for sub in log.get('sub_clips') or []:
            if not str(sub['stage15']['visual_eligibility']).startswith('ELIGIBLE'):
                continue
            row = P.sub_clip_row(clip, log, sub, fps)
            if row['sub_clip_id'] in rejected:
                continue
            row.update(primary_fits=[], secondary_fits=[], fit_kinds={}, library=True, library_from=film_from)   # its beat fits named another film
            pk['sub_clips'].append(row)
            candidates.append({k: row.get(k) for k in ('sub_clip_id', 'clip_name', 'duration_s', 'in_frame', 'out_frame', 'in_s', 'out_s', 'native_shot_size', 'eligibility', 'landmarks')}
                              | {'library_from': film_from, 'descriptive_name': d.get('descriptive_name'), 'overview': d.get('overview'), 'entities': d.get('entities') or [],
                                 'card': d.get('card') or [], 'generic': bool(r.get('generic'))})
        pk['cards'].append({'clip_id': clip['id'], 'clip_name': clip['name'], 'descriptive_name': d.get('descriptive_name'), 'lines': d.get('card') or [], 'library': True})
        session['package'].setdefault('clips', {})[clip['id']] = clip
    save_package(pk)   # the package digest is left as prepare set it: the library adds rows, it is not a re-prepare
    return {'candidates': candidates, 'rejected_before': sorted(rejected), 'rule': PROPOSE_RULE,
            'note': '' if candidates else 'the client\'s library has nothing this film can use yet'}


def session_package(store, session):
    return json.loads(store.get(session['package']['key']).decode('utf-8'))


def known(conn, client_id, shas):
    """L2: the client's library rows whose file is exactly one of these (sha256), with the film it came with."""
    if not client_id or not shas:
        return {}
    rows = conn.execute('select sha256, name, films, generic from vw2_library where client_id=%s and sha256 = any(%s)', (client_id, list(shas))).fetchall()
    return {r['sha256']: {'name': r['name'], 'films': r['films'], 'generic': r['generic']} for r in rows}
