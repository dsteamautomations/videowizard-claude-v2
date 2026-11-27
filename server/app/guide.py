"""The new way of making an AI video shot (integration steps B to D, SK 12 Nov 2026): a Blender guide built from a scene description, a GPT image
still made from the guide's first frame, the overlay, the operator's go-ahead, and a Gemini Omni edit of the guide.

Every step is a server function that the page and the chat tool both call. Everything of a shot lives under session['guides'][shot_id]; nothing here
touches the older pictures of a film. Paid steps check the film's cap first; the take is one creation per attempt and the same request is never sent twice.
"""
import hashlib
import re
import uuid
from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from . import draw3d, generations, guide_drawing, guide_spec as G, video_generators
from . import visuals_stage as VS
from .config import settings
from .errors import Problem
from .planning.digest import digest
from .visual_contract import need, route_of

HOW = 'guide'   # the kind of attempt in the record of generations

STILL_OPEN = ('The FIRST image is a rough 3D layout made of plain coloured boxes. Make ONE real photograph with EXACTLY the camera angle, lens, framing, positions, '
              'sizes and light and shadow directions of the first image. Never show the boxes; replace every box with the real thing described. The small black '
              'squares on box people mark the face and chest, and the purple squares the back, so they show which way each person faces. '
              'Every piece of the place stays exactly where its box is, at the same size.')
TAKE_OPEN = ('Edit the video. It is a rough 3D blocking render made of plain coloured boxes. Turn it into real footage of the place, people and light in the image, '
             'in its exact look. The image is exactly the first frame. Keep every movement, path, position and timing of the video exactly, and keep the camera exactly '
             'as in the video (held still, tiny handheld drift). One continuous shot: no cuts, no zoom, real-time speed, no slow motion. The small black squares on box '
             'people mark their face and chest, and the purple squares their back, so they show which way each person faces. Never show the boxes; no 3D-render look, no captions, no subtitles.')
# layout B (SK, 20 Nov 2026): said only when the shot's video was rendered flat (its render records the look); the first frame and the still keep EEVEE's light
FLAT_LINE = ('The video is drawn in flat colours with thin black outlines only to mark the layout; the footage shows neither: '
             'its light, shadows and surfaces are those of the image.')
LIGHT_LINE = 'Light stays exactly as in the image.'
SILENCE_LINE = 'No dialogue. No extra sound effects.'
REPAIR_OPEN = 'Change ONLY the transparent (masked) area: {words} Everything else stays exactly as it is: every person, face, object, position and the light.'
MAX_ROUNDS = 3   # release 2, the critic's point 2: a layout is rebuilt and checked this many times in a row with no word of the operator; then the shot is held (as a drawn graphic after round 3)
TOO_MANY = ("{n} input pictures; GPT image takes at most {max}, the guide's frame and the shot's two drawings included. "
            'Leave out the pictures the shot needs least and ask for the still again (`vw guide still`).')   # release 1, D4: the limit, and the next step
# design/200, Area B: said to GPT image with the shot's drawings (SK, 14 Nov 2026): it copies a reference faithfully, so it is told what not to copy
DIAGRAM_WORDS = ('The drawings are diagrams. Use them only for which way each person faces, which arm works, what each thing is and how it is built. Do not copy how they look: their clean edges, '
                 'even tones and perfect regularity are artificial. Make every surface, every person and the ground as they are in real life, with natural variation, wear and dust.')
RIGHT_HAND_WORDS = ('Right-handed staging: each person works with the right hand, which is on the camera\'s side of the body and fully visible. What that hand uses is in front of the body, '
                    'within easy reach with the elbow bent. No arm reaches backward, across the body or behind the shoulders; the body, the head and the working hand point the same way. '
                    'The left hand does nothing: it rests.')
LOOK_WORDS = ('Image {n} is a look reference. Keep its look in your picture: its real surface textures, its light, its true colours and the way it reads as an ordinary photograph. '
              'Take nothing else from it: not the positions, not the arrangement, not the state of any thing, not the people. Where it differs from Image 1 or from the facts, Image 1 and the facts win.')
# A1 (SK, 25 Nov 2026: "checker decides"): the operator's Yes on each layout drawing before its still is retired; the check's pass is the approval.
# A layout the operator corrected under the older way (its drawing `rejected`) still changes first (`rebuild`).
DRAWING_RETIRED = ("The operator's approval of a layout drawing is retired (25 Nov 2026): the checker decides. "
                   "A fault in the layout is said on the still's card.")
CORRECTED = 'The operator corrected the layout of {shot} ({words}): change the scene and send it again (`vw guide scene --shot {shot} --file …`).'

# what a take prompt never carries (the 48 failed methods; the single-run ones are precautions): (pattern, what to say)
NEVER = [
    (re.compile(r'\b(tripod|dolly|gimbal|crane|steadicam|camera rig)\b', re.I), 'camera gear words are drawn into the picture ("{0}"); the camera phrase is the fixed opening\'s'),
    (re.compile(r'\b(calm|serene|peaceful|misty|dreamy)\b', re.I), 'mood words pull people off their boxes ("{0}"); say what is seen, plainly'),
    (re.compile(r'(?:^|[.!?]\s+)(Do not|Don\'t|Keep|KEEP EXACTLY|Preserve)\b'), 'lock sentences slow the action ("{0} …"); say what happens, not what must not'),
    (re.compile(r'\b(end frame|last frame image|final frame image|Image ?2)\b', re.I), 'an end picture overrides the guide ("{0}"); only the guide and the still are sent'),
    (re.compile(r'\b(VERY FAST|FASTER|QUICKLY|HURRY|RUSH(?:ES|ING)?)\b'), 'push words about speed bring copies of people ("{0}"); the pace is the guide\'s, with plain pace words'),
    (re.compile(r'\b(light(?:ing)? (?:comes|falls|from)|sun(?:light)? from|relight|golden hour)\b', re.I), 'the light is fixed in the still ("{0}"); the take says only "' + LIGHT_LINE + '"'),
]


# release 1 (SK, 20 Nov 2026): a layout is checked by a fresh checker (design/35 row 281). A1: its pass is what the still waits for; nobody else is asked.
NOT_CHECKED = ('The layout of {shot} is not checked yet: a fresh `vw-guide-check` helper passes its check frames first (`vw guide status --shot {shot}`); '
               'the still is ordered after that.')


def now():
    return datetime.now(timezone.utc).isoformat()


def accepted(g):
    """Release 2, the critic's point 2: the operator took this scene's layout as it is, against its check (the held card's first answer)."""
    return bool(g.get('sha256')) and (g.get('accepted') or {}).get('sha256') == g.get('sha256')


def checked(g):
    """The fresh checker passed the check frames of this scene (its verdicts are this scene's: a new scene starts with none). Then, and only
    then, the guide is rendered (`verdict`) and the still can be ordered (A1: the operator is not asked about the layout). A layout the operator
    took as it is, against its check, counts as checked."""
    v = g.get('verdicts') or []
    return (bool(v) and bool(v[-1].get('pass'))) or accepted(g)


def rebuild(g):
    """The scene must change before anything else of the shot: its check failed, or the operator corrected its layout drawing (the older way,
    until 25 Nov 2026: a correction recorded then still holds)."""
    v, d = g.get('verdicts') or [], g.get('drawing') or {}
    return bool(v and not v[-1].get('pass') and not accepted(g)) or (d.get('status') == 'rejected' and d.get('sha256') == g.get('sha256'))


def held(g):
    """Release 2, the critic's point 2: the third check in a row failed with no word of the operator between (`rounds_from`: the round at their
    last word): nothing more is built for the shot; one card asks the operator (`chat_flow._layout_items`, `held_answer`)."""
    v = g.get('verdicts') or []
    return bool(v) and not v[-1].get('pass') and not accepted(g) and int(v[-1].get('round') or 0) - int(g.get('rounds_from') or 0) >= MAX_ROUNDS


def finding(g, n=2):
    """What the checker found on this scene, in a sentence: its failed looks, each with where it is; the first `n`, then how many more."""
    bad = [x for x in ((g.get('verdicts') or [{}])[-1].get('looks') or []) if not x.get('pass')]
    said = [str(x.get('look')) + (f" ({x['where']})" if x.get('where') else '') for x in bad[:n]]
    return '; '.join(said) + (f' (and {len(bad) - n} more)' if len(bad) > n else '')


HELD = ('The layout of {shot} failed its check {n} times in a row: the shot is held and the operator is asked in the chat (`vw visuals next`). '
        'Send no new scene of it until they answer.')
HELD_NOT = 'This layout does not wait for this answer any more (`vw visuals next`).'
JUDGED = 'This scene of {shot} is already judged (round {round}: {how}): a scene gets one verdict. {then}'


GOES_ON = 'the third failed check in a row: the layout goes on as it is, by the server (the operator never approves a layout)'
HELD_RETIRED = ('The card of a layout that failed its check three times is retired (SK, 27 Nov 2026): the operator never approves a layout. '
                'The layout goes on as it is and the still is ordered. Run `vw visuals next`.')


def go_on(conn, store, run, session, shot_id, g):
    """Release 1 of 27 Nov 2026, phase 4 part A (SK: "the operator never approves a Blender layout, in this step or any other"): after the third
    failed check in a row the server takes the layout as it is, by itself: what the held card's "Use this layout as it is" did. Recorded as the
    server's decision with the checker's finding, in the shot's record and the run's log. The session is changed, not saved.
    Retired: the held-layout card and its three answers (`held_answer`, kept for a layout held before this release)."""
    from . import runlog
    rnd, found = int(g['verdicts'][-1].get('round') or 0), finding(g, 99)
    who = {'quote': GOES_ON, 'by': 'server', 'by_name': 'server', 'at': now()}
    d = _ensure_drawing(store, run, session, g, VS.load_json(store, g['key']))
    g['accepted'] = {'sha256': g['sha256'], 'round': rnd, 'finding': found, **who}
    d.update(status='approved', verdict={'approved': True, 'against_check': True, 'notes': '', **who})
    _render(conn, store, run, shot_id, g)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'held layout: use (the server)', 'round': rnd, 'sha256': g['sha256'], 'finding': found, 'by': 'server', 'by_name': 'server'})
    runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'shot {shot_id}', 'rule': 'release 1 of 27 Nov 2026, phase 4 part A',
                        'entry': f'the layout failed its check {MAX_ROUNDS} times in a row and goes on as it is, against its check: {found}'[:3800],
                        'by_kind': 'server', 'by_name': '', 'quote': '', 'request_id': None})


def held_answer(conn, store, user, run, outputs, shot_id, sha256, choice, quote, notes=''):
    """The operator's answer on a held layout (one flow: the chat's card calls this). `use`: the layout goes on as it is, against its check: it
    counts as checked and approved and its guide is rendered. `again`: three more rounds. `change`: their words on what the shot becomes; the
    next-step line (`takes.held_due`) says what the assistant does with them."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    need(g['sha256'] == sha256 and held(g), HELD_NOT)
    need(choice in ('use', 'again', 'change'), 'A held layout is answered with use, again or change.')
    quote, notes = str(quote or '').strip(), str(notes or '').strip()
    need(quote, "An answer carries the operator's own words.")
    need(choice != 'change' or notes, 'Ask the operator what the shot becomes, in their words.')
    rnd, who = int(g['verdicts'][-1].get('round') or 0), {'quote': quote[:500], 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()}
    if choice == 'use':
        d = _ensure_drawing(store, run, session, g, VS.load_json(store, g['key']))
        g['accepted'] = {'sha256': g['sha256'], 'round': rnd, **who}
        d.update(status='approved', verdict={'approved': True, 'against_check': True, 'notes': '', **who})
        _render(conn, store, run, shot_id, g)
        nxt = f'The layout goes on as it is, against its check. {RENDER_NEXT.format(shot=shot_id)}'
    else:
        g['rounds_from'] = rnd   # their word: the count of rounds in a row starts again
        if choice == 'change':
            g['change'] = {'words': notes[:2000], 'round': rnd, **who}
        nxt = ('Three more rounds are allowed: change the scene and send it again (`vw guide scene`).' if choice == 'again'
               else 'Do what the operator said (the next-step line of `vw visuals next` says it).')
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'held layout: ' + choice, 'round': rnd, 'sha256': sha256, 'quote': who['quote'], 'notes': notes[:2000], 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'answer': choice, 'next': nxt}


def entry_of(session, shot_id):
    g = (session.get('guides') or {}).get(shot_id)
    need(g, f'{shot_id} has no guide yet: `vw guide scene --shot {shot_id} --file work/guide/{shot_id}/scene.json`.')
    return g


def _queue(conn, run, shot_id, provider, request):
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,%s,%s, gen_random_uuid()) returning id",
                       (run['id'], shot_id, provider, Jsonb(request))).fetchone()
    return str(row['id'])


# Release 4 (SK, 20 Nov 2026): the first frame of a layout first, its video behind it. The still needs only frame 1; the video is needed only for
# the take. Both are kept on g['render']: `frame1_key` (the still can be ordered) and `status` 'ready' with `guide_key` (the take can be sent).
# A record of the older code (one job for both) has both and reads as before. (Until then: one job, and the still waited for the video; design/35 row 302.)
FRAME_S = 4   # seconds of rendering one frame of the video on the server (design/181); only for the "about N minutes" of a sentence
RENDER_NEXT = ('The first frame of the layout is being made (free, under a minute); then the still: `vw guide still --shot {shot} --file …`. '
               'The layout video renders behind it (free, several minutes) and is needed only for the take.')
RETRY = 'send the same scene again to render it again (`vw guide scene --shot {shot} --file work/guide/{shot}/scene.json`)'


def _render(conn, store, run, shot_id, g):
    """What a checked scene still lacks is queued: its first frame (a quick job) and then its video (the render lane); a file of this same scene
    still in storage is used again (a scene sent again after another). A job that failed is queued again. Returns what was queued, in words."""
    r, req, out = g.setdefault('render', {}), {'shot_id': shot_id, 'sha256': g['sha256'], 'spec_key': g['key'], 'seconds': g['seconds']}, []
    for key, sha, name in (('frame1_key', 'frame1_sha256', 'frame1.png'), ('guide_key', 'sha256', 'guide.mp4')):
        k = VS.key(run, f"guides/{g['sha256']}/{name}")
        if not r.get(key) and store.exists(k):
            data = store.get(k)
            r.update({key: k, sha: hashlib.sha256(data).hexdigest(), 'reused': True}, **({'status': 'ready', 'bytes': len(data)} if key == 'guide_key' else {}))
    if not r.get('frame1_key') and (not r.get('frame1_job_id') or r.get('frame1_error')):
        r.pop('frame1_error', None)
        r['frame1_job_id'] = _queue(conn, run, shot_id, 'guide', {'kind': 'guide-frame1', **req})
        out.append('first frame')
    if r.get('status') != 'ready' and (not r.get('job_id') or r.get('status') == 'failed'):
        r.pop('error', None)
        r.update(job_id=_queue(conn, run, shot_id, 'guide', {'kind': 'guide-render', **req, 'split': True}), status='queued')   # `split`: its first frame is another job
        out.append('layout video')
    return out


def render_line(shot_id, g):
    """Where the shot's first frame and its video stand, in one sentence for the status, the refused take and the next-step line; '' when both are ready."""
    r, retry = g.get('render') or {}, RETRY.format(shot=shot_id)
    if r.get('status') == 'ready':
        return ''
    if r.get('status') == 'failed':
        return f"The layout video of {shot_id} failed ({r.get('error')}): {retry}."
    if r.get('frame1_key'):
        return (f'The layout video of {shot_id} is still being rendered (needed only for the take; about {max(1, round(g["seconds"] * G.FPS * FRAME_S / 60))} minutes of rendering, '
                'one video at a time).')
    if r.get('frame1_error'):
        return (f"The first frame of {shot_id} failed ({r['frame1_error']}): no still can be ordered yet. It is made again with the layout video, which is rendering; "
                f'to make it at once, {retry}.')
    return f'The first frame of {shot_id} is being made (free, under a minute of rendering); the still can be ordered when it is ready.'


def _slot_seconds(session, shot):
    return (shot['end_frame'] - shot['start_frame']) / float(session['source']['fps'])


def _people_of(plan, shot):
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    return [i for i in shot.get('element_ids') or [] if kinds.get(i) == 'person']


# ---------- step B: the scene, the checks before spend, the check frames ----------

TOO_LONG_PROMPT = ("The still's request would be {n:,} characters; OpenAI takes at most {max:,}. The parts: {parts}, the server's fixed lines {rest:,}. "
                   'Nothing was ordered or paid. Shorten the largest part (your words in the still\'s file, or the scene: fewer, larger background pieces) '
                   'and send it again (`vw guide still --shot {shot} --file …`).')   # hotfix 21 Nov 2026


def _things(store, session):
    """The approved drawing sets of the film's things: {element id: its drawing set}."""
    return {eid: VS.load_json(store, r['key']) for eid, r in (session.get('drawings') or {}).items() if r.get('status') == 'approved'}


def _draw(store, run, session, spec, sha):
    """design/200: the shot's drawing, from the scene's own numbers: through the camera and from above, both sheets of each stored. Free. It goes
    with the still's request; its record keeps `status` 'proposed' (A1: nobody approves it any more)."""
    import hashlib
    from . import drawings
    d, notes = guide_drawing.description(spec, _things(store, session))
    wrong = draw3d.problems(d)
    need(not wrong, 'The shot cannot be drawn: ' + ' '.join(wrong[:4]))
    views = []
    for s in draw3d.render(d):
        row = {'id': s['view'], 'name': s['name'], 'kind': s['kind'], 'width': s['width'], 'height': s['height']}
        for which, ops in (('labelled', s['labelled_ops']), ('plain', s['plain_ops'])):
            data = drawings.png(ops)
            k = VS.key(run, f"guides/{sha}/drawing-{s['view']}{'-plain' if which == 'plain' else ''}.png")
            store.put(k, data, 'image/png')
            row[f'{which}_key'], row[f'{which}_sha256'] = k, hashlib.sha256(data).hexdigest()
        views.append(row)
    return {'status': 'proposed', 'sha256': sha, 'views': views, 'how': draw3d.how_to_read(d, [v['id'] for v in views], first=2),
            'changes': [str(c).strip() for c in spec.get('changed_from_plan') or []], 'notes': notes, 'at': now()}


def _ensure_drawing(store, run, session, g, spec):
    """A guide made before design/200 has no drawing: it is made now (free)."""
    if (g.get('drawing') or {}).get('sha256') != g['sha256']:
        g['drawing'] = _draw(store, run, session, spec, g['sha256'])
        VS.save_session(store, run, session)
    return g['drawing']


def drawing_verdict(*args, **kw):
    """The operator's Yes or correction on a shot's layout drawing (design/200 Area B; release 1): retired, refused by name. The route stays for
    an older tool (`vw guide drawing-approve`, `drawing-reject`)."""
    need(False, DRAWING_RETIRED)


def layout_lines(g):
    """A1: what the retired layout card showed of the layout, now on the still's card: what the scene changed from the plan, and the drawing's
    notes. [] when it has neither, or when the drawing is of another scene."""
    d = g.get('drawing') or {}
    if d.get('sha256') != g.get('sha256'):
        return []
    return ((['Changed from the plan to make the shot possible:'] + [f'- {c}' for c in d['changes']]) if d.get('changes') else []) \
        + ((['Notes:'] + [f'- {c}' for c in d['notes']]) if d.get('notes') else [])


def _drawn_facts(session, parents):
    """The facts of every drawn thing among a still's parent pictures, one plain line each, under the thing's name."""
    from . import drawings
    out, seen = [], set()
    for p in parents or []:
        eid = ((session.get('references') or {}).get(p.get('id')) or {}).get('element_id')
        if eid and eid not in seen:
            seen.add(eid)
            name = ((session.get('drawings') or {}).get(eid) or {}).get('name') or eid
            out += [f'{name}: {f}' for f in drawings.must_be_true(session, eid)]
    return out


def carried(old):
    """design/222 (the critic's S5): what a new scene keeps of the shot's entry besides its approved stills and its takes: the operator's word for
    one more take given on the page ("Make another"), while it is not used."""
    return {'again': old['again']} if old.get('again') and not old['again'].get('sent') else {}


def set_scene(conn, store, user, run, outputs, shot_id, spec, overrides=None):
    """A helper's scene description for a shot: its shape, then every check that needs no Blender; refused before anything is rendered or paid.
    `overrides`: {'support': '<why>'} is the one refusal that can be overridden, with its reason on the record."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    plan, gap, scene, shot = VS.guarded(lambda: VS.locate(store, session, shot_id))
    need(route_of(shot) == 'video', f'{shot_id} is not an AI video shot; a guide is made only for AI video shots.')
    upright = VS.vertical_video(run, {'gaps': [{'scenes': [{'shots': [shot]}]}]})   # release 1, C5: a plan from before the plan's own refusal: the same sentence, before anything is rendered or paid
    need(not upright, ''.join(upright))
    VS._no_question(session, shot_id)
    wrong = G.problems(spec)
    need(not wrong, 'The scene description cannot be built: ' + ' '.join(wrong[:6]) + (f' (and {len(wrong) - 6} more)' if len(wrong) > 6 else '')
         + f' Correct the scene file and send it again (`vw guide scene --shot {shot_id} --file work/guide/{shot_id}/scene.json`).')   # release 1, D4: a refusal ends with the next step
    slot = _slot_seconds(session, shot)
    need(spec['seconds'] >= slot - 1e-6, f"The guide runs {spec['seconds']} s and the shot's slot is {slot:.1f} s: a take is made as long as its guide, a little longer than its slot, and trimmed.")
    rows = G.checks(spec, subjects=_people_of(plan, shot), flat=settings().GUIDE_VIDEO_LOOK == 'flat')   # layout B: the flat video gives every person stripes
    overrides = {k: str(v).strip() for k, v in (overrides or {}).items() if str(v or '').strip()}
    need(set(overrides) <= {'support'}, 'Only the support check can be overridden, with its reason; every other refusal is fixed in the scene.')
    refused = [r for r in G.refusals(rows) if not (r['check'] == 'support' and overrides.get('support'))]
    need(not refused, 'Refused before any spend: ' + ' '.join(r['message'] for r in refused[:5]) + (f' (and {len(refused) - 5} more)' if len(refused) > 5 else ''))
    sha = digest(spec)
    guides = session.setdefault('guides', {})
    old = guides.get(shot_id) or {}
    need(not held(old), HELD.format(shot=shot_id, n=MAX_ROUNDS))   # release 2, the critic's point 2: the gate: no further scene of a held shot without the operator
    if old.get('sha256') == sha:
        again = _render(conn, store, run, shot_id, old) if old.get('render') and checked(old) and not rebuild(old) else []   # release 4: the retry of a first frame or a video that failed
        if again:
            VS.save_session(store, run, session)
            return {'shot_id': shot_id, 'sha256': sha, 'unchanged': True, 'job_id': (old.get('frames') or {}).get('job_id'),
                    'next': f"This scene is already stored: its {' and its '.join(again)} is queued again (free)."}
        d = old.get('drawing') or {}
        same = ('This scene is already stored; nothing was queued.' if not rebuild(old) else   # the critic's point 3: the scene that failed, sent again, says so
                f"This is the scene whose layout the operator corrected ({(d.get('verdict') or {}).get('notes')}): nothing was queued. The new scene must differ from it: make their correction and send it again."
                if d.get('status') == 'rejected' else
                f'This is the scene whose check failed ({finding(old)}): nothing was queued. The new scene must differ from it: change what the check names and send it again.')
        return {'shot_id': shot_id, 'sha256': sha, 'unchanged': True, 'job_id': (old.get('frames') or {}).get('job_id'), 'next': same}
    k = VS.key(run, f'guides/{sha}/scene.json')
    VS.save_json(store, k, spec)
    n = int(round(spec['seconds'] * G.FPS))
    frames = sorted({1, max(1, n // 2), n})
    job_id = _queue(conn, run, shot_id, 'guide', {'kind': 'guide-frames', 'shot_id': shot_id, 'sha256': sha, 'spec_key': k, 'frames': frames})
    guides[shot_id] = {'sha256': sha, 'key': k, 'seconds': spec['seconds'], 'recipe': spec['recipe'], 'process_note': spec['process_note'], 'marks': spec.get('marks') or {},
                       **({'fronts': G.fronted(spec)} if G.fronted(spec) else {}),   # layout B: the take's words name the things with front panels
                       'checks': rows, 'overrides': [{'check': c, 'reason': why, 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()} for c, why in overrides.items()],
                       'frames': {'job_id': job_id, 'status': 'queued'}, 'verdicts': [], 'rounds_before': len(old.get('verdicts') or []) + int(old.get('rounds_before') or 0),
                       **carried(old), **({'rounds_from': old['rounds_from']} if old.get('rounds_from') else {}), 'stills': [s for s in old.get('stills') or [] if s.get('status') == 'approved'], 'takes': old.get('takes') or [], 'by': user['id'], 'at': now()}
    guides[shot_id]['drawing'] = _draw(store, run, session, spec, sha)   # design/200: free; it goes with the still's request
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'scene', 'sha256': sha, 'key': k, 'recipe': spec['recipe'], 'process_note': spec['process_note'], 'seconds': spec['seconds'],
                                                    'checks': [{'check': r['check'], 'level': r['level'], 'message': r['message']} for r in rows if r['level'] != 'info'],
                                                    'overrides': overrides, 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'sha256': sha, 'job_id': job_id, 'frames': frames,
            'warnings': [r['message'] for r in rows if r['level'] == 'warn'], 'info': [r['message'] for r in rows if r['level'] == 'info'],
            'cannot_see': G.BLIND, 'layout': G.layout_block(spec), 'drawing_notes': guides[shot_id]['drawing']['notes'],
            'next': f'Check frames {frames} are being rendered (free). Then a fresh vw-guide-check helper looks at them: `vw guide frames --shot {shot_id}`, `vw guide verdict --shot {shot_id} --file …`. '
                    'After the check passes the still is ordered: the operator is not asked about the layout.'}


def verdict(conn, store, user, run, outputs, shot_id, sha256, passed, looks, notes=''):
    """The double check of every guide (SK's requirement B4): a fresh checker's verdict on the check frames. The server counts the rounds; a pass queues the render."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    need(g['sha256'] == sha256, 'The scene changed since these frames were made; look at the frames of the current scene (`vw guide frames`).')
    need((g.get('frames') or {}).get('status') == 'ready', 'The check frames are not ready yet (`vw guide status`).')
    need(isinstance(looks, list) and looks and all(isinstance(x, dict) and isinstance(x.get('look'), str) and isinstance(x.get('pass'), bool) for x in looks),
         'A verdict lists every look with "look" and "pass": [{"look": "…", "pass": true, "where": "…"}].')
    failed = [x['look'] for x in looks if not x['pass']]
    need(bool(passed) == (not failed), 'The verdict passes only when every look passes; a failed look names what to change.')
    # release 2, the critic's point 8: one verdict per scene (two checkers on one scene: the later one, failing after a pass, flipped a shot whose render, card or still had moved on)
    last = (g['verdicts'] or [{}])[-1]
    need(not g['verdicts'], JUDGED.format(shot=shot_id, round=last.get('round'), how='passed' if last.get('pass') else 'failed',
                                         then=f'Its first frame is made, then its still is ordered (`vw guide status --shot {shot_id}`).' if last.get('pass')
                                         else f'The operator took the layout as it is (`vw guide status --shot {shot_id}`).' if accepted(g)
                                         else HELD.format(shot=shot_id, n=MAX_ROUNDS) if held(g) else f'Change the scene and send it again (`vw guide scene --shot {shot_id} --file …`).'))
    rnd = len(g['verdicts']) + int(g.get('rounds_before') or 0) + 1
    g['verdicts'].append({'round': rnd, 'sha256': sha256, 'pass': bool(passed), 'looks': [{k: x.get(k) for k in ('look', 'pass', 'where', 'fix')} for x in looks[:60]], 'notes': str(notes or '')[:2000],
                          'by': user['id'], 'by_name': user.get('name') or '', 'at': now()})
    out = {'shot_id': shot_id, 'round': rnd, 'pass': bool(passed), 'failed': failed}
    if passed and not (g.get('render') or {}).get('job_id'):
        _render(conn, store, run, shot_id, g)   # release 4: the first frame, then the video (until then: one `guide-render` job for both)
        r = g['render']
        out.update(job_id=r.get('job_id'), next=('The first frame and the video of this scene were rendered before and are used again: the still can be ordered '
                                                  f'(`vw guide still --shot {shot_id} --file …`).' if r.get('status') == 'ready' else RENDER_NEXT.format(shot=shot_id)))
    elif not passed:
        # release 2, the critic's point 2: the third failure in a row holds the shot (until then: "show the operator what is still open" from round 2, with no card and no gate; design/35 row 293)
        if held(g):   # phase 4 part A: the server goes on by itself; nobody is asked about a layout
            go_on(conn, store, run, session, shot_id, g)
            out['next'] = (f'Round {rnd} failed, the third check in a row: the layout goes on as it is, by the server; the operator is not asked about a layout. '
                           f'{RENDER_NEXT.format(shot=shot_id)} Still open on the layout: ' + '; '.join(failed))
        else:
            out['next'] = 'Change the scene (one thing at a time) and upload it again: `vw guide scene`.'
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'guide check', 'round': rnd, 'pass': bool(passed), 'failed': failed, 'notes': str(notes or '')[:2000], 'by': user['id'], 'by_name': user.get('name') or ''})
    return out


# ---------- step C: the still, the overlay ----------

def _render_ready(g):
    r = g.get('render') or {}   # release 4: the still needs the first frame only, not the video (until then: `status` ready too)
    need(r.get('frame1_key'), 'The first frame of the layout is not rendered yet: it is rendered, before the video, after a fresh checker passes the check frames (`vw guide status`).')
    return r


def _input(store, run, session, shot_id, p, people):
    """One input picture of a still: an approved reference of the film, or an approved still of this film's guides (a crop of the scene's first still).
    design/207 (D1): a picture of a person goes in only as it would into any other picture (VS.person_picture_refused; people: {person id: name})."""
    pid = p.get('id')
    row = (session.get('references') or {}).get(pid)
    if row is None:
        row = next((s for g in (session.get('guides') or {}).values() for s in g.get('stills') or [] if s['id'] == pid), None)
    need(row is not None, f'{pid} is not a picture of this film.')
    need(row.get('status') == 'approved' and row.get('key'), f'{pid} is not approved; only approved pictures go into a still.')
    need(not VS.person_picture_refused(session, people, row), VS.person_picture_refused(session, people, row))
    need(str(p.get('job') or '').strip(), f'{pid}: say what the picture is for, in a few words (for example "the father: copy his face, hair, build and clothes").')
    return VS.cropped_parent(store, run, row, p.get('crop')), str(p['job']).strip()


PLACE_VIEW = 'Take the camera angle, the framing and every position from Image 1 only, never from this picture.'
PLACE_JOB = 'the place ({name}): keep its walls, floor, surfaces, colours and fixed things. ' + PLACE_VIEW
REFS_WAIT = ('{shot} waits for the approved reference of {names}: the picture that starts an AI video shot is made after the references of what it shows are approved. '
             'Nothing was ordered; the server names it as due when they are.')


def with_places(session, plan, shot, parents):
    """Release 1 of 27 Nov 2026, phase 4 part C (SK): the pictures of a still's request with the approved picture of each place the shot names,
    added by the server with its job in the server's own words: the place's golden picture, else the first approved picture of its set. A picture
    the assistant already named is not added twice: its job gets the sentence about the camera angle. A place the operator left without a
    reference adds nothing. Why: four stills of VW-25 showed a place other than the references.
    Retired: a still of an AI video shot made with no picture of its place."""
    out, refs = [dict(p) for p in parents], session.get('references') or {}
    ok = lambda r: bool(r) and r.get('status') == 'approved' and r.get('key')
    for e in plan.get('elements') or []:
        if e.get('kind') != 'place' or e['id'] not in (shot.get('element_ids') or []):
            continue
        gold = refs.get(VS.golden_of(session, e['id']) or '')
        row = gold if ok(gold) else next((r for r in refs.values() if r.get('element_id') == e['id'] and r.get('kind') in ('sheet', 'frame', 'supplied') and ok(r)), None)
        if not row:
            continue
        named = next((p for p in out if p.get('id') == row['id']), None)
        if named is None:
            out.append({'id': row['id'], 'job': PLACE_JOB.format(name=e.get('name') or e['id'])})
        elif PLACE_VIEW not in str(named.get('job') or ''):
            named['job'] = str(named.get('job') or '').strip().rstrip('.') + '. ' + PLACE_VIEW
    return out


def request_still(conn, store, user, run, outputs, shot_id, prompt, parents, repair_of=None, region=None, look=None):
    """The still of a shot: GPT image 2.6 whatever the film's picture AI (SK, 10 Nov); Image 1 is the guide's first frame; then the given approved pictures,
    each with its job; the layout numbers are written by the server from the scene. With `repair_of` and `region`: a masked repair of one wrong part."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    VS._no_question(session, shot_id)
    render = _render_ready(g)
    words = str(prompt or '').strip()
    need(len(words.split()) >= (4 if repair_of else 25), 'Say in words what is wrong and what it becomes.' if repair_of else
         'The still needs its words: the view, the place, each box and who or what it is, the moment, the light.')
    need(not any(s.get('status') == 'generating' for s in g.get('stills') or []), 'A still of this shot is being made; wait for it (`vw guide status`).')
    spec = VS.load_json(store, g['key'])
    still = video_generators.STILL
    sheets = []
    d = _ensure_drawing(store, run, session, g, spec)   # design/200, Area B
    # A1: the scene's check passed, or the operator took a held layout as it is; a masked repair too (a still kept from an earlier scene is not
    # repaired under a layout nobody checked). (Until 25 Nov 2026: the operator's Yes on this scene's layout drawing; retired.)
    need(checked(g), NOT_CHECKED.format(shot=shot_id))
    need(not rebuild(g), CORRECTED.format(shot=shot_id, words=(d.get('verdict') or {}).get('notes')))
    if repair_of:
        base = next((s for s in g['stills'] if s['id'] == repair_of and s.get('key') and s.get('status') in ('candidate', 'approved')), None)
        need(base, f'{repair_of} is not a finished still of this shot.')
        need(isinstance(region, dict) and all(isinstance(region.get(k), (int, float)) for k in ('left', 'top', 'width', 'height')),
             'A repair names its region: {"left", "top", "width", "height"} as fractions of the picture.')
        inputs, jobs_ = [{'id': base['id'], 'key': base['key'], 'sha256': base['sha256']}], []
        effective = REPAIR_OPEN.format(words=words)
        parts = {'your words': len(words)}
    else:
        need(isinstance(parents, list), 'parents: a list of {"id", "job", "crop"?}.')
        plan_, _, _, shot_ = VS.guarded(lambda: VS.locate(store, session, shot_id))
        held_ = VS.refs_waited(session, plan_, shot_)   # phase 4 part C rule 4 (SK: everything the shot shows): as a still picture's (phase 2 part C)
        need(not held_, REFS_WAIT.format(shot=shot_id, names=', '.join(e.get('name') or e['id'] for e in held_)))
        parents = with_places(session, plan_, shot_, parents)
        people = VS.people_of(VS.guarded(lambda: VS.current_plan(store, session)))
        pairs = [_input(store, run, session, shot_id, p, people) for p in parents]
        sheets = [{'id': f"shot-drawing-{v['id']}-{g['sha256'][:12]}", 'key': v['plain_key'], 'sha256': v['plain_sha256']} for v in d['views']]
        looks = [_input(store, run, session, shot_id, {'id': look, 'job': 'a look reference'}, people)[0]] if look else []
        inputs = [{'id': 'guide-frame-' + g['sha256'][:12], 'key': render['frame1_key'], 'sha256': render['frame1_sha256']}] + sheets + [a for a, _ in pairs] + looks
        jobs_ = [j for _, j in pairs]
        need(len(inputs) <= still['max_inputs'], TOO_MANY.format(n=len(inputs), max=still['max_inputs']))
        roles = ['Image 1 is the layout: take from it positions and framing only.'] + [f'Image {n} is {j}' + ('' if j.endswith('.') else '.') for n, j in enumerate(jobs_, 2 + len(sheets))]
        facts = _drawn_facts(session, parents)
        size = VS.size_line(*VS.guarded(lambda: VS.locate(store, session, shot_id))[::3])   # design/207: (plan, shot): the size sentence, when size is the message

        def build(how, block):
            return '\n'.join(x for x in [STILL_OPEN, marks_line(spec.get('marks'), 'image', fronts=G.fronted(spec)), how, DIAGRAM_WORDS, words, block, ' '.join(roles), size,
                                         RIGHT_HAND_WORDS if any(p.get('hands') for p in spec.get('people') or []) else '',
                                         ('What must be true:\n' + '\n'.join(f'- {f}' for f in facts)) if facts else '',
                                         LOOK_WORDS.format(n=len(inputs)) if looks else ''] if x)
        how, block = d['how'], G.layout_block(spec)
        effective = build(how, block)
        if len(effective) > still['max_prompt']:   # hotfix (SK, 21 Nov 2026, "B1 shorten"): the least seen background pieces are summed up, five at a time
            desc = guide_drawing.description(spec, _things(store, session))[0]
            far = G.background(spec)
            for n in range(5, len(far) + 5, 5):
                how, block = draw3d.how_to_read(desc, [v['id'] for v in d['views']], first=2, drop=far[:n]), G.layout_block(spec, drop=far[:n])
                effective = build(how, block)
                if len(effective) <= still['max_prompt']:
                    break
        parts = {'the colour key': len(how), 'the layout block': len(block), 'your words': len(words)}
    need(len(effective) <= still['max_prompt'], TOO_LONG_PROMPT.format(n=len(effective), max=still['max_prompt'], shot=shot_id,
                                                                    parts=', '.join(f'{k} {v:,}' for k, v in parts.items()), rest=len(effective) - sum(parts.values())))
    from . import pictures as P   # release 1 of 27 Nov 2026, phase 4 part A rule 6: this order is the one remake of a start still whose check failed
    retried = next((s for s in g.get('stills') or [] if P.start_retry_due(session, shot_id, g, s)), None)
    try:
        VS.check_cap(conn, run, session, VS.image_price_inr(run, provider='openai'), 'this still')
    except Problem as e:
        if retried:   # at the cost limit there is no remake: the first picture goes to the operator with the check's finding
            session.setdefault('still_retries', {})[shot_id] = {'of': retried['id'], 'gave_up': str(getattr(e, 'message', None) or e)}
            VS.save_session(store, run, session)
        raise
    still_id = uuid.uuid4().hex
    request = {'kind': 'guide-still', 'op': 'edit', 'provider': 'openai', 'model': still['model'], 'prompt': effective, 'size': still['size'], 'quality': still['quality'],
               'parents': inputs, 'reference': {'id': still_id}, 'shot_id': shot_id, 'sha256': g['sha256'], **({'region': region} if repair_of else {})}
    job_id = _queue(conn, run, shot_id, 'guide-still', request)
    g.setdefault('stills', []).append({'id': still_id, 'job_id': job_id, 'status': 'generating', 'guide_sha256': g['sha256'], 'prompt': words, 'effective_prompt': effective,
                                       'inputs': [{'id': i['id'], 'job': j} for i, j in zip(inputs[1 + len(sheets):], jobs_)], **({'look': look} if look and not repair_of else {}), **({'repair_of': repair_of, 'region': region} if repair_of else {}),
                                       'model': still['model'], 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()})
    if retried:   # counted once for the shot; the first picture stays in the record as the earlier try
        lines_ = ' '.join(P._failed_lines(retried))
        session.setdefault('still_retries', {})[shot_id] = {'of': retried['id'], 'by': still_id, 'lines': lines_, 'at': now()}
        retried.update(status='rejected', rejection={'notes': f"Made again once by itself: Claude's check failed: {lines_}", 'quote': '', 'by': 'server', 'at': now()})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'still repair asked' if repair_of else 'still asked', 'still_id': still_id, 'model': still['model'], 'prompt': effective,
                                                    'inputs': [i['id'] for i in inputs], **({'repair_of': repair_of, 'region': region} if repair_of else {}), 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'still_id': still_id, 'job_id': job_id, 'model': still['model'],
            'next': 'The still is being made. Claude checks it first; then the server puts it to the operator on a card (`vw visuals next`).'}


def _still(g, still_id):
    s = next((s for s in g.get('stills') or [] if s['id'] == still_id), None)
    need(s, f'{still_id} is not a still of this shot.')
    return s


SHOOT_ON_APPROVAL = ("The picture is approved and its take is paid for on this answer: the server orders it as soon as the take's words and the shot's video of "
                     "positions are both there. Write the take's words now (`vw guide prompt --shot {shot} --file …`), then run `vw visuals next`.")
SHOOT_LATER = ("The picture is approved. No take is ordered: the operator said not yet. Write the take's words meanwhile (`vw guide prompt --shot {shot} --file …`); "
               'when the operator says so, order the take with their words: `vw guide shoot --shot {shot} --quote "…"`.')
SHOOT_REFUSED = '{name} ({shot}): its take was not ordered: {words} When that is settled, order it with the operator\'s words: `vw guide shoot --shot {shot} --quote "…"`.'
SHOOT_WAITS = '{name} ({shot}): its picture is approved and everything for its take is ready, but the operator said not yet. On their word: `vw guide shoot --shot {shot} --quote "…"`.'


def approve_still(conn, store, user, run, outputs, shot_id, still_id, sha256, quote, shoot=False):
    """The operator approves the exact file. One approved still per guide. Release 1 of 27 Nov 2026, phase 4 part B (SK: one approving button):
    with `shoot` the approval is also the operator's word for the paid first take (the price is on the card they answered): `order_due` orders it
    when the take's words and the layout video both exist. Without it (a typed "not yet", the page, the tool) the still alone is approved.
    Part A: nobody approves on the overlay any more; it stays required, as the input of Claude's check.
    Retired: the separate Shoot card of a first take, and "it is approved on its overlay"."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    s = _still(g, still_id)
    need(s.get('status') in ('candidate', 'approved') and s.get('key'), 'Approve a finished still.')
    if s.get('sha256') != sha256:
        raise Problem(409, 'REFERENCE_MISMATCH', 'The still changed since it was looked at; look at the current file and approve that.')
    need(s.get('overlay_key'), 'This still is not ready yet: its check has not got its files. Run `vw guide status` and try again.')
    need(s.get('guide_sha256') == g['sha256'], 'The scene changed since this still was made; make the still again from the current guide.')
    for other in g['stills']:
        if other is not s and other.get('status') == 'approved':
            other['status'] = 'superseded'
    s.update(status='approved', approval={'by': user['id'], 'by_name': user.get('name') or '', 'at': now(), 'sha256': sha256, 'quote': VS.said(quote, 'Approved', user), **({'shoot': True} if shoot else {})})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'still approved', 'still_id': still_id, 'sha256': sha256, 'quote': s['approval']['quote'], 'by': user['id'], 'by_name': user.get('name') or '',
                                                    **({'take': 'paid for on this answer'} if shoot else {})})
    return {'shot_id': shot_id, 'still_id': still_id, 'status': 'approved', 'next': (SHOOT_ON_APPROVAL if shoot else SHOOT_LATER).format(shot=shot_id)}


def _shoot_stamp(g, still):
    """The state of a shot a take is ordered for: its approved still, its words and its layout video. An order is tried once for each."""
    return '|'.join(str(x) for x in (still.get('sha256'), (g.get('take_prompt') or {}).get('at') or (g.get('take_prompt') or {}).get('prompt'), (g.get('render') or {}).get('sha256')))


def shoot_state(session, shot_id):
    """Part B: where a shot's first take stands once everything for it exists: None (not ready, a take was already sent, or a take is selected),
    else ('order', stamp): to be ordered now on the operator's approval; ('refused', words): the order was refused, in the refusal's words;
    ('later', ''): the operator approved the picture and said not yet."""
    g = (session.get('guides') or {}).get(shot_id) or {}
    if not g or g.get('takes') or shot_id in (session.get('selections') or {}) or not ready_card(session, shot_id, 0)['ready']:
        return None
    still = next(s for s in g['stills'] if s.get('status') == 'approved' and s.get('guide_sha256') == g['sha256'])
    if not (still.get('approval') or {}).get('shoot'):
        return 'later', ''
    stamp, tried = _shoot_stamp(g, still), g.get('auto_shoot') or {}
    return ('refused', tried.get('refused') or '') if tried.get('stamp') == stamp else ('order', stamp)


def order_due(conn, store, user, run, outputs):
    """Part B, rule 2: the first take of every shot whose picture the operator approved with "Approve and shoot", ordered by the server once the
    take's words and the layout video both exist, whichever came last, with the operator's words on the still as the word for the paid call
    (`shoot`: its cost limit and every other gate as before). A refusal keeps the approval and is never silent: its words are kept on the shot and
    said in the next-step line (`takes.render_due`); the order is tried once for each state of the shot. Called where the chat fetches its next
    step. Returns the shots it ordered."""
    session, sent = VS.session_of(store, run, outputs), []
    for shot_id in list(session.get('guides') or {}):
        state = shoot_state(session, shot_id)
        if not state or state[0] != 'order':
            continue
        still = next(s for s in session['guides'][shot_id]['stills'] if s.get('status') == 'approved' and s.get('guide_sha256') == session['guides'][shot_id]['sha256'])
        refused = None
        try:
            shoot(conn, store, user, run, outputs, shot_id, still['approval']['quote'])
            sent.append(shot_id)
        except (Problem, ValueError) as e:
            refused = str(getattr(e, 'message', None) or e)
        session = VS.session_of(store, run, outputs)   # `shoot` saved its own
        session['guides'][shot_id]['auto_shoot'] = {'stamp': state[1], 'at': now(), **({'refused': refused} if refused else {})}
        VS.save_session(store, run, session)
    return sent


def reject_still(conn, store, user, run, outputs, shot_id, still_id, notes, quote):
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    s = _still(g, still_id)
    need(s.get('status') in ('candidate', 'approved'), 'Reject a finished still.')
    need(str(notes or '').strip(), 'Say what is wrong with the still; the words go on the record.')
    s.update(status='rejected', rejection={'notes': str(notes).strip(), 'quote': VS.said(quote, 'Rejected', user), 'by': user['id'], 'at': now()})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'still rejected', 'still_id': still_id, 'notes': str(notes).strip(), 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'still_id': still_id, 'status': 'rejected',
            'next': 'A wrong part: a masked repair (`vw guide repair`). A still off the guide: a new still. A fault in the guide itself: change the scene.'}


# ---------- step D: the take ----------

def prompt_problems(text):
    """What a take prompt must not carry, each with the reason; empty when it may be sent."""
    out = []
    for pattern, why in NEVER:
        m = pattern.search(text)
        if m:
            out.append(why.format(m.group(1) if m.groups() else m.group(0)))
    return out


def marks_line(marks, of, flat=False, fronts=()):
    """The line that explains the band, the stripes and the front panels of a guide, for the video or for the image made from its first frame; '' without them.
    flat: the video is rendered flat, where every person has stripes (layout B); fronts: the names of the things with a front panel."""
    marks, fronts = marks or {}, list(fronts or [])
    stripes = flat or marks.get('stripes')
    if not (marks.get('band') or stripes or fronts):
        return ''
    return f'How to read the {of}: ' + ' '.join((['the coloured band on the ground only marks where the walking line runs; it is not a thing in the place and is never shown.'] if marks.get('band') else [])
                                               + (["the thin yellow stripe down the side of each box person marks that person's side."] if stripes else [])
                                               + ([f"the black panel marks the front of {' and '.join([', '.join(fronts[:-1])] + fronts[-1:]) if len(fronts) > 1 else fronts[0]}, "
                                                   f"the purple panel {'their' if len(fronts) > 1 else 'its'} back; the panels are never shown."] if fronts else []))


def effective_prompt(g, words):
    """The prompt as sent: the fixed opening, the flat look explained when the video has it, the line that explains the marks when the guide has them,
    the writer's blocks, the two fixed closing lines."""
    flat = (g.get('render') or {}).get('look') == 'flat'
    lines = [TAKE_OPEN] + ([FLAT_LINE] if flat else []) + [x for x in [marks_line(g.get('marks'), 'video', flat, g.get('fronts'))] if x]
    lines.append(words.strip())
    lines += [l for l in (LIGHT_LINE, SILENCE_LINE) if l.lower() not in words.lower()]
    return '\n'.join(lines)


def set_prompt(conn, store, user, run, outputs, shot_id, prompt):
    """The writer's words for the take, kept until the take is ordered. Refused when it carries what the tests showed to fail."""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    words = str(prompt or '').strip()
    need(len(words.split()) >= 20, 'The take needs its words: which box is who, the ONE action with its seconds (the guide\'s own times), who stays in place, the exact count of people.')
    need(len(words) <= 6000, 'The take\'s words are too long; keep to the shot\'s one action.')
    wrong = prompt_problems(words)
    need(not wrong, 'Not sent as written: ' + '; '.join(wrong) + '.')
    need('ONE action only' in words, 'Open the action paragraph with "ONE action only:" and give a second on every move, repeating the guide\'s own times.')
    g['take_prompt'] = {'prompt': words, 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()}
    VS.save_session(store, run, session)
    return {'shot_id': shot_id, 'words': len(words.split()), 'prompt': effective_prompt(g, words),
            'next': 'Run `vw visuals next`: the server orders the take itself when the operator approved the picture with "Approve and shoot"; no card asks for it.'}


def ready_card(session, shot_id, price_per_s):
    """What the operator sees before any video is paid for, and what is still missing. design/207: the scene's warnings that matter before a paid
    take (an untried kind, a run, people whose paths overlap, nothing moving) are repeated here, in the line both front ends already show."""
    g = entry_of(session, shot_id)
    warnings = [r['message'] for r in g.get('checks') or [] if r.get('before_take')]
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('guide_sha256') == g['sha256']), None)
    missing = [what for ok, what in (((g.get('render') or {}).get('status') == 'ready', 'the rendered guide'), (still is not None, 'an approved still made from this guide'),
                                     (bool(still and still.get('overlay_key')), 'the overlay'), (bool(g.get('take_prompt')), "the take's words")) if not ok]
    return {'shot_id': shot_id, 'ready': not missing, 'missing': missing, 'seconds': g['seconds'], 'cost_inr': round(g['seconds'] * price_per_s, 2),
            'guide_key': (g.get('render') or {}).get('guide_key'), 'strip_key': (g.get('frames') or {}).get('strip_key'), 'still': still,
            'prompt': effective_prompt(g, g['take_prompt']['prompt']) if g.get('take_prompt') else None, 'warnings': warnings,
            'look_for': 'Before you pay: ' + ' '.join(warnings) if warnings else ''}   # phase 4 part A: no word about the overlay or its outlines


def take_price():
    """design/223: what one second of the first take is counted at: the price of its size (360p)."""
    return VS.video_price(video_generators.GUIDE['resolution'])


def same_of(render_sha, still_sha, prompt, shot_print):
    """The request's identity: the same guide, still and words for the same shot is never sent twice. Release 1 of 27 Nov 2026, part I row 2:
    the shot's own fingerprint (until then the whole plan's, the critic's S4: after a change to another shot the same take could be paid again)."""
    return digest({'guide': render_sha, 'still': still_sha, 'prompt': prompt, 'shot': shot_print})


def shoot(conn, store, user, run, outputs, shot_id, quote, again=False, same=False):
    """The operator's go-ahead: one Gemini edit of the guide: the first take, made once, at `video_generators.GUIDE`'s size (design/223: 360p), and shown
    as it is. Refused while anything of the card is missing, while a take is open, and when nothing changed since the last take: the same request is
    never sent twice, except `again`, once, after a call that failed at the provider (design/223, E9), and `same`, the third route of a correction
    (nothing of the take is usable: `corrections.send`), each time on the operator's words.
    (Until design/223: 720p; a cause had to be named for a rejected take; at most two takes from one camera; design/35 rows 316, 321, 322.)"""
    VS.need_free(conn, store, run, [shot_id])   # the critic's point 1 on release 3: an open defect on this shot, or on the drawing it continues from, holds it on every path
    session = VS.session_of(store, run, outputs)
    plan, gap, scene, shot = VS.guarded(lambda: VS.locate(store, session, shot_id))
    VS._no_question(session, shot_id)
    g = entry_of(session, shot_id)
    need(shot_id not in (session.get('selections') or {}), f'{shot_id} has a take selected: no new take is made while it stands. To make another, the operator rejects the selected take first.')   # design/222, the second critic's point 3
    card = ready_card(session, shot_id, take_price())
    need(card['missing'] != ['the rendered guide'],   # release 4: only the video is awaited: said plainly; no take is ever sent without the whole video
         render_line(shot_id, g) + f' No take is sent without it: send this again when `vw guide status --shot {shot_id}` says it is ready.')
    need(card['ready'], 'Not ready to shoot; still missing: ' + ', '.join(card['missing']) + '.')
    need(str(quote or '').strip(), "A take is paid for on the operator's word: give their words (--quote).")
    render, still = g['render'], card['still']
    camera = digest(VS.load_json(store, g['key'])['camera'])
    open_job = conn.execute("select id from vw2_jobs where run_id=%s and stage='visuals' and unit=%s and provider='video' and status in ('queued','running','submitted','submission_unknown','storage_pending')",
                            (run['id'], shot_id)).fetchone()
    if open_job:
        raise Problem(409, 'JOB_OPEN', 'A take for this shot is still open; wait, recover or resolve it first.', job_id=str(open_job['id']))
    prompt = card['prompt']
    same_id = same_of(render['sha256'], still['sha256'], prompt, VS.shot_print(plan, shot_id))
    before = [t for t in g.get('takes') or [] if t.get('same') == same_id]
    if before and not same:
        was = next((j for j in VS.take_jobs(conn, run, shot_id) if str(j['id']) == str(before[-1].get('job_id'))), None)
        failed = bool(was and was['status'] in ('failed', 'cancelled'))
        need(again and failed, 'Nothing changed since the last take of this shot: the same request is never sent twice. Change the guide, the still or the words (one thing), or cut the shot.'
             if not failed else 'The last take could not be made at the provider. To send the same request once more, the operator says so: `vw guide shoot --again --quote "…"`.')
        need(len(before) < 2, 'This request was already sent twice; change the guide, the still or the words.')
    seconds = int(g['seconds'])
    VS.check_cap(conn, run, session, seconds * take_price(), f'a {seconds} s take')
    gen = video_generators.GUIDE
    fps = float(session['source']['fps'])
    record = {'contract': 'videowizard-guide-take-v1', 'kind': 'guide', 'run_id': str(run['id']), 'shot_id': shot_id, 'plan_digest': digest(plan), 'shot_print': VS.shot_print(plan, shot_id), 'attempt': len(g.get('takes') or []) + 1,
              'guide': {'key': render['guide_key'], 'sha256': render['sha256'], 'seconds': seconds, 'scene_sha256': g['sha256']},
              'start_image': {'reference_id': still['id'], 'sha256': still['sha256'], 'key': still['key'], 'mime_type': 'image/png', 'width': still.get('width'), 'height': still.get('height')},
              'prompt': g['take_prompt']['prompt'], 'effective_prompt': prompt, 'provider': gen['provider'], 'model': gen['model'], 'aspect_ratio': gen['aspect_ratio'], 'resolution': gen['resolution'],
              'duration_seconds': seconds, 'recipe': g.get('recipe'),
              'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': session['source']['fps'],
                            'duration_seconds': str((shot['end_frame'] - shot['start_frame']) / fps), 'exact_seconds': (shot['end_frame'] - shot['start_frame']) / fps}}
    identity = VS.own_identity(record)
    k = VS.key(run, f'takes/{identity}.request.json')
    VS.save_json(store, k, record)
    session['preparations'][shot_id] = {'preparation_id': identity, 'key': k, 'guide': True}
    job_id = _queue(conn, run, shot_id, 'video', {'kind': 'take', 'preparation_id': identity, 'request_key': k, 'provider': gen['provider'], 'model': gen['model'], 'duration_seconds': seconds,
                                                  'resolution': gen['resolution'], 'plan_digest': record['plan_digest'], 'shot_print': record['shot_print']})   # release 1 of 27 Nov 2026, part B: its own shot's fingerprint; design/222: the page counts a take shot for another plan as "must be made again"
    g.setdefault('takes', []).append({'job_id': job_id, 'same': same_id, 'camera': camera, 'preparation_id': identity, 'quote': str(quote).strip(), 'by': user['id'], 'at': now()})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'take sent', 'job_id': job_id, 'model': gen['model'], 'seconds': seconds, 'prompt': prompt, 'guide_sha256': render['sha256'], 'still_sha256': still['sha256'],
                                                    'request_key': k, 'quote': str(quote).strip(), 'again': bool(before), 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'job_id': job_id, 'seconds': seconds, 'model': gen['model'], 'next': 'The take is being made (one to three minutes). It is shown to the operator as it is, on the page, when every take is made: `vw visuals status`.'}


# ---------- what the worker writes back (under the run's lock) ----------

def apply_result(session, job, status, result, error):
    """A finished guide job's result on the shot's entry; ignored when the scene changed meanwhile. Returns the entry for the record of generations, or None."""
    req = job['request']
    g = (session.get('guides') or {}).get(req.get('shot_id'))
    if not g or g.get('sha256') != req.get('sha256'):
        return None
    g['moved_at'] = now()   # phase 4 part D: a result that came back is the shot's newest mark (`pictures.stuck_of`)
    ok = status in ('ready', 'retained')
    if req['kind'] == 'guide-frames':
        g['frames'] = {'job_id': str(job['id']), 'status': 'ready' if ok else 'failed', **({'frames': result['frames'], 'strip_key': result['strip_key']} if ok else {'error': error})}
        return {'kind': 'check frames', 'ok': ok, **({'strip_key': result['strip_key']} if ok else {'error': error})}
    if req['kind'] == 'guide-frame1':   # release 4: the first frame alone: the still can be ordered; the video's own record is untouched
        r = g.setdefault('render', {})
        r.pop('frame1_error', None)
        r.update({k: result[k] for k in ('frame1_key', 'frame1_sha256')} if ok else {'frame1_error': error})
        return {'kind': 'first frame made', 'ok': ok, **({'frame1_key': result['frame1_key']} if ok else {'error': error})}
    if req['kind'] == 'guide-render':
        kept = {k: v for k, v in (g.get('render') or {}).items() if k in ('frame1_key', 'frame1_sha256', 'frame1_job_id')}   # a video that failed does not take the first frame with it
        g['render'] = {**kept, 'job_id': str(job['id']), 'status': 'ready' if ok else 'failed', **({k: result[k] for k in ('guide_key', 'sha256', 'bytes', 'frame1_key', 'frame1_sha256', 'render_seconds')} if ok else {'error': error}),
                       **({'look': result['look']} if ok and result.get('look') else {})}   # layout B: the take's words say how the video looks
        return {'kind': 'guide rendered', 'ok': ok, **({'guide_key': result['guide_key'], 'sha256': result['sha256'], 'render_seconds': result['render_seconds']} if ok else {'error': error})}
    if req['kind'] == 'guide-still':
        s = next((s for s in g.get('stills') or [] if s['id'] == req['reference']['id']), None)
        if s is None:
            return None
        if ok:
            s.update(status='candidate', **{k: result.get(k) for k in ('key', 'sha256', 'bytes', 'width', 'height', 'overlay_key')}, cost=result.get('cost'))
        else:
            s.update(status='failed', error=error)
        return {'kind': 'still made', 'still_id': s['id'], 'ok': ok, **({'key': result.get('key'), 'sha256': result.get('sha256'), 'overlay_key': result.get('overlay_key')} if ok else {'error': error})}
    return None


def view(session, shot_id, url):
    """The guide of a shot for the page and the chat tool: where it stands and every picture to look at."""
    g = (session.get('guides') or {}).get(shot_id)
    if not g:
        return None
    frames, render = g.get('frames') or {}, g.get('render') or {}
    return {'sha256': g['sha256'], 'recipe': g.get('recipe'), 'seconds': g['seconds'], 'process_note': g.get('process_note'),
            'warnings': [r['message'] for r in g.get('checks') or [] if r['level'] == 'warn'], 'overrides': g.get('overrides') or [], 'cannot_see': G.BLIND,
            'frames': {'status': frames.get('status'), 'error': frames.get('error'), 'strip_url': url(frames.get('strip_key')) if frames.get('strip_key') else None,
                       'urls': [url(f['key']) for f in frames.get('frames') or []]},
            'verdicts': [{k: v.get(k) for k in ('round', 'pass', 'looks', 'notes', 'by_name')} for v in g.get('verdicts') or []],
            'render': {'status': render.get('status'), 'error': render.get('error'), 'guide_url': url(render.get('guide_key')) if render.get('guide_key') else None,
                       'frame1_url': url(render.get('frame1_key')) if render.get('frame1_key') else None},
            'stills': [{'id': s['id'], 'status': s['status'], 'sha256': s.get('sha256'), 'error': s.get('error'), 'repair_of': s.get('repair_of'), 'prompt': s.get('prompt'),
                        'url': url(s['key']) if s.get('key') else None, 'overlay_url': url(s['overlay_key']) if s.get('overlay_key') else None,
                        'current': s.get('guide_sha256') == g['sha256']} for s in g.get('stills') or [] if s.get('status') != 'superseded'],
            'drawing': {k: (g.get('drawing') or {}).get(k) for k in ('status', 'sha256', 'changes', 'notes')},
            'take_prompt': (g.get('take_prompt') or {}).get('prompt'), 'card': {k: v for k, v in ready_card(session, shot_id, take_price()).items() if k in ('ready', 'missing', 'seconds', 'cost_inr', 'prompt', 'look_for')}}


def status(conn, store, run, outputs, shot_id):
    """Where a shot's guide stands, for the chat tool: the same view the page shows (keys in place of links), the files it can fetch, and what comes next."""
    session = VS.session_of(store, run, outputs)
    VS.guarded(lambda: VS.locate(store, session, shot_id))
    v = view(session, shot_id, lambda k: k)
    if v is None:
        return {'shot_id': shot_id, 'guide': None, 'next': f'No guide yet: write the scene description and send it, `vw guide scene --shot {shot_id} --file work/guide/{shot_id}/scene.json`.'}
    g = session['guides'][shot_id]
    names = (['strip'] + [f"check-{f['n']:04d}" for f in (g.get('frames') or {}).get('frames') or []] if (g.get('frames') or {}).get('status') == 'ready' else []) \
        + (['frame1'] if (g.get('render') or {}).get('frame1_key') else []) + (['guide'] if (g.get('render') or {}).get('status') == 'ready' else []) \
        + [n for s in g.get('stills') or [] if s.get('key') for n in (['still-' + s['id']] + (['overlay-' + s['id']] if s.get('overlay_key') else []))]
    names += ['drawing-' + x['id'] for x in (g.get('drawing') or {}).get('views') or []]
    f, r, card = v['frames'], v['render'], v['card']
    if f['status'] != 'ready':
        nxt = 'The check frames failed: ' + str(f['error']) if f['status'] == 'failed' else 'The check frames are being rendered; ask again in a minute.'
    elif held(g):   # release 2, the critic's point 2: the same as the next-step line: held, the operator is asked
        nxt = (f"The check of this scene failed for the third time in a row ({'; '.join(x['look'] for x in v['verdicts'][-1]['looks'] or [] if not x.get('pass'))}): the shot is held and the operator "
               'is asked in the chat (`vw visuals next`); send no new scene of it until they answer.')
    elif v['verdicts'] and not v['verdicts'][-1]['pass'] and not accepted(g):   # release 1: a scene that has its verdict is not checked again: it changes first
        nxt = f"The check of this scene failed ({'; '.join(x['look'] for x in v['verdicts'][-1]['looks'] or [] if not x.get('pass'))}): change the scene (one thing at a time) and send it again (`vw guide scene --shot {shot_id} --file …`)."
    elif not v['verdicts']:
        nxt = f'A fresh vw-guide-check helper looks at the check frames (`vw guide frames --shot {shot_id}`) and gives its verdict (`vw guide verdict`).'
    elif not r['frame1_url']:   # release 4: the first frame is what the still waits for (until then: the whole render)
        nxt = render_line(shot_id, g)
    elif card['ready']:
        nxt = (f"Everything for the take is ready ({card['seconds']} s, about {card['cost_inr']:.0f} rupees). The server orders it on the operator's approval of the picture: "   # phase 4 part B
               f"run `vw visuals next`. When they approved the picture and said not yet, on their word: `vw guide shoot --shot {shot_id} --quote \"…\"`.")
    else:   # release 4: the first frame is ready: the still goes on while the video renders; the two are said apart
        rest = [m for m in card['missing'] if m != 'the rendered guide']
        ordered = any(s.get('guide_sha256') == g['sha256'] and s.get('status') in ('generating', 'candidate', 'approved') for s in g.get('stills') or [])
        nxt = ' '.join(x for x in ((f'First frame ready: the still can be ordered (`vw guide still --shot {shot_id} --file …`).' if not ordered
                                    else 'Still missing before the take: ' + ', '.join(rest) + '.' if rest
                                    else 'Everything else for the take is ready: the server orders the take when the layout video is ready (`vw visuals next`).'), render_line(shot_id, g)) if x)
    d = g.get('drawing') or {}
    if d.get('status') == 'rejected' and d.get('sha256') == g.get('sha256'):   # a correction of the older way (until 25 Nov 2026): the scene changes first, whatever else is ready
        nxt = CORRECTED.format(shot=shot_id, words=(d.get('verdict') or {}).get('notes'))
    return {'shot_id': shot_id, 'guide': v, 'files': names, 'next': nxt}


def file(store, run, outputs, shot_id, name):
    """One picture (or the guide video) of a shot's guide, for the chat tool to save and look at."""
    import base64
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    frames, render = g.get('frames') or {}, g.get('render') or {}
    keys = {'strip': (frames.get('strip_key'), 'image/jpeg', 'jpg'), 'frame1': (render.get('frame1_key'), 'image/png', 'png'), 'guide': (render.get('guide_key'), 'video/mp4', 'mp4')}
    keys.update({f"check-{f['n']:04d}": (f['key'], 'image/png', 'png') for f in frames.get('frames') or []})
    keys.update({'drawing-' + v['id']: (v['labelled_key'], 'image/png', 'png') for v in (g.get('drawing') or {}).get('views') or []})   # design/200: the operator's sheets of the shot's drawing
    for s in g.get('stills') or []:
        keys['still-' + s['id']] = (s.get('key'), 'image/png', 'png')
        keys['overlay-' + s['id']] = (s.get('overlay_key'), 'image/jpeg', 'jpg')
    k, mime, ext = keys.get(name) or (None, None, None)
    need(k, f'{name} is not a file of this guide yet (`vw guide status --shot {shot_id}` lists them).')
    return {'name': name, 'file': f'{name}.{ext}', 'mime': mime, 'base64': base64.b64encode(store.get(k)).decode()}


# ---------- the older way, retired by name (SK, 12 Nov 2026: no switch; each step deletes the part it replaces) ----------

TAKE_RETIRED = ('The picture-to-video take (a start picture, an end picture and a motion text) is retired. An AI video shot is made from a guide: load the vw:guide skill, '
                'then `vw guide scene --shot S --file work/guide/S/scene.json`.')
START_PICTURE_RETIRED = ('A start picture composed from words is retired for an AI video shot. Its still is made from the guide\'s first frame: '
                         '`vw guide still --shot S --file …` as soon as that first frame is rendered (the vw:guide skill).')   # release 4 (until then: "after the guide is rendered")


def older_take_retired(*_):
    raise Problem(410, 'RETIRED', TAKE_RETIRED)


def older_start_picture_retired(store, run, outputs, body):
    """A keyframe asked for an AI video shot is the older way's start (or end) picture: refused by name. Every other picture is untouched."""
    if body.get('kind') != 'keyframe' or not body.get('shot_id'):
        return
    session = VS.session_of(store, run, outputs)
    try:
        shot = VS.locate(store, session, body['shot_id'])[3]
    except ValueError:
        return   # the picture's own gates answer an unknown shot
    if route_of(shot) == 'video':
        raise Problem(410, 'RETIRED', START_PICTURE_RETIRED)


# ---------- when a take is wrong (design/223, SK 22 Nov 2026) ----------
# The operator says what is wrong, in plain words; the assistant chooses the route of the correction (`corrections.RULE`, `corrections.send`); there is
# no limit on rounds. The older way is retired by name: a cause named for a rejected take (still, guide, words, model), "change one thing", at most two
# takes from one camera and the ladder after them (design/35 rows 321, 322).

CAUSE_RETIRED = ('Naming a cause for a rejected take is retired (design/223). The operator says what is wrong with a take, and you choose the route of its '
                 'correction: `vw guide corrections` gives the rule, the frames and the pictures; then `vw guide correct --shot S --file work/guide/S/correction.json`.')
ORDER_RETIRED = ('"Make another" and its withdrawal are retired (design/223). To withdraw a correction the operator asked for: '
                 '`vw guide correct --shot S --withdraw --reason "<their words>"`.')


def cause_retired(*_):
    raise Problem(410, 'RETIRED', CAUSE_RETIRED)


def order_retired(*_):
    raise Problem(410, 'RETIRED', ORDER_RETIRED)
