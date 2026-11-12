"""The new way of making an AI video shot (integration steps B to D, SK 12 Nov 2026): a Blender guide built from a scene description, a GPT image
still made from the guide's first frame, the overlay, the operator's go-ahead, and a Gemini Omni edit of the guide.

Every step is a server function that the page and the chat tool both call. Everything of a shot lives under session['guides'][shot_id]; nothing here
touches the older pictures of a film. Paid steps check the film's cap first; the take is one creation per attempt and the same request is never sent twice.
"""
import re
import uuid
from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from . import generations, guide_spec as G, video_generators
from . import visuals_stage as VS
from .errors import Problem
from .planning.digest import digest
from .visual_contract import need, route_of

HOW = 'guide'   # the kind of attempt in the record of generations

STILL_OPEN = ('The FIRST image is a rough 3D layout made of plain coloured boxes. Make ONE real photograph with EXACTLY the camera angle, lens, framing, positions, '
              'sizes and light and shadow directions of the first image. Never show the boxes; replace every box with the real thing described. The small black '
              'squares on box people show which way each person faces. Every piece of the place stays exactly where its box is, at the same size.')
TAKE_OPEN = ('Edit the video. It is a rough 3D blocking render made of plain coloured boxes. Turn it into real footage of the place, people and light in the image, '
             'in its exact look. The image is exactly the first frame. Keep every movement, path, position and timing of the video exactly, and keep the camera exactly '
             'as in the video (held still, tiny handheld drift). One continuous shot: no cuts, no zoom, real-time speed, no slow motion. The small black squares on box '
             'people mark their face and chest, so they show which way each person faces. Never show the boxes; no 3D-render look, no captions, no subtitles.')
LIGHT_LINE = 'Light stays exactly as in the image.'
SILENCE_LINE = 'No dialogue. No extra sound effects.'
REPAIR_OPEN = 'Change ONLY the transparent (masked) area: {words} Everything else stays exactly as it is: every person, face, object, position and the light.'
MAX_ROUNDS_BEFORE_OPERATOR = 2

# what a take prompt never carries (the 48 failed methods; the single-run ones are precautions): (pattern, what to say)
NEVER = [
    (re.compile(r'\b(tripod|dolly|gimbal|crane|steadicam|camera rig)\b', re.I), 'camera gear words are drawn into the picture ("{0}"); the camera phrase is the fixed opening\'s'),
    (re.compile(r'\b(calm|serene|peaceful|misty|dreamy)\b', re.I), 'mood words pull people off their boxes ("{0}"); say what is seen, plainly'),
    (re.compile(r'(?:^|[.!?]\s+)(Do not|Don\'t|Keep|KEEP EXACTLY|Preserve)\b'), 'lock sentences slow the action ("{0} …"); say what happens, not what must not'),
    (re.compile(r'\b(end frame|last frame image|final frame image|Image ?2)\b', re.I), 'an end picture overrides the guide ("{0}"); only the guide and the still are sent'),
    (re.compile(r'\b(VERY FAST|FASTER|QUICKLY|HURRY|RUSH(?:ES|ING)?)\b'), 'push words about speed bring copies of people ("{0}"); the pace is the guide\'s, with plain pace words'),
    (re.compile(r'\b(light(?:ing)? (?:comes|falls|from)|sun(?:light)? from|relight|golden hour)\b', re.I), 'the light is fixed in the still ("{0}"); the take says only "' + LIGHT_LINE + '"'),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def entry_of(session, shot_id):
    g = (session.get('guides') or {}).get(shot_id)
    need(g, f'{shot_id} has no guide yet: `vw guide scene --shot {shot_id} --file work/guide/{shot_id}/scene.json`.')
    return g


def _queue(conn, run, shot_id, provider, request):
    row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'visuals',%s,%s,%s, gen_random_uuid()) returning id",
                       (run['id'], shot_id, provider, Jsonb(request))).fetchone()
    return str(row['id'])


def _slot_seconds(session, shot):
    return (shot['end_frame'] - shot['start_frame']) / float(session['source']['fps'])


def _people_of(plan, shot):
    kinds = {e['id']: e.get('kind') for e in plan.get('elements') or []}
    return [i for i in shot.get('element_ids') or [] if kinds.get(i) == 'person']


# ---------- step B: the scene, the checks before spend, the check frames ----------

def set_scene(conn, store, user, run, outputs, shot_id, spec, overrides=None):
    """A helper's scene description for a shot: its shape, then every check that needs no Blender; refused before anything is rendered or paid.
    `overrides`: {'support': '<why>'} is the one refusal that can be overridden, with its reason on the record."""
    session = VS.session_of(store, run, outputs)
    plan, gap, scene, shot = VS.guarded(lambda: VS.locate(store, session, shot_id))
    need(route_of(shot) == 'video', f'{shot_id} is not an AI video shot; a guide is made only for AI video shots.')
    VS._no_question(session, shot_id)
    wrong = G.problems(spec)
    need(not wrong, 'The scene description cannot be built: ' + ' '.join(wrong[:6]) + (f' (and {len(wrong) - 6} more)' if len(wrong) > 6 else ''))
    slot = _slot_seconds(session, shot)
    need(spec['seconds'] >= slot - 1e-6, f"The guide runs {spec['seconds']} s and the shot's slot is {slot:.1f} s: a take is made as long as its guide, a little longer than its slot, and trimmed.")
    rows = G.checks(spec, subjects=_people_of(plan, shot))
    overrides = {k: str(v).strip() for k, v in (overrides or {}).items() if str(v or '').strip()}
    need(set(overrides) <= {'support'}, 'Only the support check can be overridden, with its reason; every other refusal is fixed in the scene.')
    refused = [r for r in G.refusals(rows) if not (r['check'] == 'support' and overrides.get('support'))]
    need(not refused, 'Refused before any spend: ' + ' '.join(r['message'] for r in refused[:5]) + (f' (and {len(refused) - 5} more)' if len(refused) > 5 else ''))
    sha = digest(spec)
    guides = session.setdefault('guides', {})
    old = guides.get(shot_id) or {}
    if old.get('sha256') == sha:
        return {'shot_id': shot_id, 'sha256': sha, 'unchanged': True, 'job_id': (old.get('frames') or {}).get('job_id'), 'next': 'This scene is already stored; nothing was queued.'}
    k = VS.key(run, f'guides/{sha}/scene.json')
    VS.save_json(store, k, spec)
    n = int(round(spec['seconds'] * G.FPS))
    frames = sorted({1, max(1, n // 2), n})
    job_id = _queue(conn, run, shot_id, 'guide', {'kind': 'guide-frames', 'shot_id': shot_id, 'sha256': sha, 'spec_key': k, 'frames': frames})
    guides[shot_id] = {'sha256': sha, 'key': k, 'seconds': spec['seconds'], 'recipe': spec['recipe'], 'process_note': spec['process_note'], 'marks': spec.get('marks') or {},
                       'checks': rows, 'overrides': [{'check': c, 'reason': why, 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()} for c, why in overrides.items()],
                       'frames': {'job_id': job_id, 'status': 'queued'}, 'verdicts': [], 'rounds_before': len(old.get('verdicts') or []) + int(old.get('rounds_before') or 0),
                       'stills': [s for s in old.get('stills') or [] if s.get('status') == 'approved'], 'takes': old.get('takes') or [], 'by': user['id'], 'at': now()}
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'scene', 'sha256': sha, 'key': k, 'recipe': spec['recipe'], 'process_note': spec['process_note'], 'seconds': spec['seconds'],
                                                    'checks': [{'check': r['check'], 'level': r['level'], 'message': r['message']} for r in rows if r['level'] != 'info'],
                                                    'overrides': overrides, 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'sha256': sha, 'job_id': job_id, 'frames': frames,
            'warnings': [r['message'] for r in rows if r['level'] == 'warn'], 'info': [r['message'] for r in rows if r['level'] == 'info'],
            'cannot_see': G.BLIND, 'layout': G.layout_block(spec),
            'next': f'Check frames {frames} are being rendered (free). Then a fresh vw-guide-check helper looks at them: `vw guide frames --shot {shot_id}`, `vw guide verdict --shot {shot_id} --file …`.'}


def verdict(conn, store, user, run, outputs, shot_id, sha256, passed, looks, notes=''):
    """The double check of every guide (SK's requirement B4): a fresh checker's verdict on the check frames. The server counts the rounds; a pass queues the render."""
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    need(g['sha256'] == sha256, 'The scene changed since these frames were made; look at the frames of the current scene (`vw guide frames`).')
    need((g.get('frames') or {}).get('status') == 'ready', 'The check frames are not ready yet (`vw guide status`).')
    need(isinstance(looks, list) and looks and all(isinstance(x, dict) and isinstance(x.get('look'), str) and isinstance(x.get('pass'), bool) for x in looks),
         'A verdict lists every look with "look" and "pass": [{"look": "…", "pass": true, "where": "…"}].')
    failed = [x['look'] for x in looks if not x['pass']]
    need(bool(passed) == (not failed), 'The verdict passes only when every look passes; a failed look names what to change.')
    rnd = len(g['verdicts']) + int(g.get('rounds_before') or 0) + 1
    g['verdicts'].append({'round': rnd, 'sha256': sha256, 'pass': bool(passed), 'looks': [{k: x.get(k) for k in ('look', 'pass', 'where', 'fix')} for x in looks[:60]], 'notes': str(notes or '')[:2000],
                          'by': user['id'], 'by_name': user.get('name') or '', 'at': now()})
    out = {'shot_id': shot_id, 'round': rnd, 'pass': bool(passed), 'failed': failed}
    if passed and not (g.get('render') or {}).get('job_id'):
        job_id = _queue(conn, run, shot_id, 'guide', {'kind': 'guide-render', 'shot_id': shot_id, 'sha256': g['sha256'], 'spec_key': g['key'], 'seconds': g['seconds']})
        g['render'] = {'job_id': job_id, 'status': 'queued'}
        out.update(job_id=job_id, next=f'The guide is being rendered (free, several minutes). Then the still: `vw guide still --shot {shot_id} --file …`.')
    elif not passed:
        out['next'] = (f'Round {rnd} failed. Show the operator what is still open before another round: ' + '; '.join(failed) if rnd >= MAX_ROUNDS_BEFORE_OPERATOR
                       else 'Change the scene (one thing at a time) and upload it again: `vw guide scene`.')
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'guide check', 'round': rnd, 'pass': bool(passed), 'failed': failed, 'notes': str(notes or '')[:2000], 'by': user['id'], 'by_name': user.get('name') or ''})
    return out


# ---------- step C: the still, the overlay ----------

def _render_ready(g):
    r = g.get('render') or {}
    need(r.get('status') == 'ready' and r.get('frame1_key'), 'The guide is not rendered yet: it is rendered after a fresh checker passes its check frames (`vw guide status`).')
    return r


def _input(store, run, session, shot_id, p):
    """One input picture of a still: an approved reference of the film, or an approved still of this film's guides (a crop of the scene's first still)."""
    pid = p.get('id')
    row = (session.get('references') or {}).get(pid)
    if row is None:
        row = next((s for g in (session.get('guides') or {}).values() for s in g.get('stills') or [] if s['id'] == pid), None)
    need(row is not None, f'{pid} is not a picture of this film.')
    need(row.get('status') == 'approved' and row.get('key'), f'{pid} is not approved; only approved pictures go into a still.')
    need(str(p.get('job') or '').strip(), f'{pid}: say what the picture is for, in a few words (for example "the father: copy his face, hair, build and clothes").')
    return VS.cropped_parent(store, run, row, p.get('crop')), str(p['job']).strip()


def request_still(conn, store, user, run, outputs, shot_id, prompt, parents, repair_of=None, region=None):
    """The still of a shot: GPT image 2.6 whatever the film's picture AI (SK, 10 Nov); Image 1 is the guide's first frame; then the given approved pictures,
    each with its job; the layout numbers are written by the server from the scene. With `repair_of` and `region`: a masked repair of one wrong part."""
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
    if repair_of:
        base = next((s for s in g['stills'] if s['id'] == repair_of and s.get('key') and s.get('status') in ('candidate', 'approved')), None)
        need(base, f'{repair_of} is not a finished still of this shot.')
        need(isinstance(region, dict) and all(isinstance(region.get(k), (int, float)) for k in ('left', 'top', 'width', 'height')),
             'A repair names its region: {"left", "top", "width", "height"} as fractions of the picture.')
        inputs, jobs_ = [{'id': base['id'], 'key': base['key'], 'sha256': base['sha256']}], []
        effective = REPAIR_OPEN.format(words=words)
    else:
        need(isinstance(parents, list), 'parents: a list of {"id", "job", "crop"?}.')
        pairs = [_input(store, run, session, shot_id, p) for p in parents]
        inputs = [{'id': 'guide-frame-' + g['sha256'][:12], 'key': render['frame1_key'], 'sha256': render['frame1_sha256']}] + [a for a, _ in pairs]
        jobs_ = [j for _, j in pairs]
        need(len(inputs) <= still['max_inputs'], f"{len(inputs)} input pictures; GPT image takes at most {still['max_inputs']}, the guide's frame included.")
        roles = ['Image 1 is the layout: take from it positions and framing only.'] + [f'Image {n} is {j}' + ('' if j.endswith('.') else '.') for n, j in enumerate(jobs_, 2)]
        effective = '\n'.join([STILL_OPEN, words, G.layout_block(spec), ' '.join(roles)])
    VS.check_cap(conn, run, session, VS.image_price_inr(run, provider='openai'), 'this still')
    still_id = uuid.uuid4().hex
    request = {'kind': 'guide-still', 'op': 'edit', 'provider': 'openai', 'model': still['model'], 'prompt': effective, 'size': still['size'], 'quality': still['quality'],
               'parents': inputs, 'reference': {'id': still_id}, 'shot_id': shot_id, 'sha256': g['sha256'], **({'region': region} if repair_of else {})}
    job_id = _queue(conn, run, shot_id, 'guide-still', request)
    g.setdefault('stills', []).append({'id': still_id, 'job_id': job_id, 'status': 'generating', 'guide_sha256': g['sha256'], 'prompt': words, 'effective_prompt': effective,
                                       'inputs': [{'id': i['id'], 'job': j} for i, j in zip(inputs[1:], jobs_)], **({'repair_of': repair_of, 'region': region} if repair_of else {}),
                                       'model': still['model'], 'by': user['id'], 'by_name': user.get('name') or '', 'at': now()})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'still repair asked' if repair_of else 'still asked', 'still_id': still_id, 'model': still['model'], 'prompt': effective,
                                                    'inputs': [i['id'] for i in inputs], **({'repair_of': repair_of, 'region': region} if repair_of else {}), 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'still_id': still_id, 'job_id': job_id, 'model': still['model'],
            'next': f'The still is being made. Then look at the overlay (`vw guide status --shot {shot_id}`) and approve or repair it.'}


def _still(g, still_id):
    s = next((s for s in g.get('stills') or [] if s['id'] == still_id), None)
    need(s, f'{still_id} is not a still of this shot.')
    return s


def approve_still(conn, store, user, run, outputs, shot_id, still_id, sha256, quote):
    """The operator approves the exact file, on the overlay. One approved still per guide."""
    session = VS.session_of(store, run, outputs)
    g = entry_of(session, shot_id)
    s = _still(g, still_id)
    need(s.get('status') in ('candidate', 'approved') and s.get('key'), 'Approve a finished still.')
    if s.get('sha256') != sha256:
        raise Problem(409, 'REFERENCE_MISMATCH', 'The still changed since it was looked at; look at the current file and approve that.')
    need(s.get('overlay_key'), 'This still has no overlay yet; it is approved on its overlay.')
    need(s.get('guide_sha256') == g['sha256'], 'The scene changed since this still was made; make the still again from the current guide.')
    for other in g['stills']:
        if other is not s and other.get('status') == 'approved':
            other['status'] = 'superseded'
    s.update(status='approved', approval={'by': user['id'], 'by_name': user.get('name') or '', 'at': now(), 'sha256': sha256, 'quote': VS.said(quote, 'Approved', user)})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'still approved', 'still_id': still_id, 'sha256': sha256, 'quote': s['approval']['quote'], 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'still_id': still_id, 'status': 'approved', 'next': f'Write the take\'s words (`vw guide prompt --shot {shot_id} --file …`), then the operator says Shoot.'}


def reject_still(conn, store, user, run, outputs, shot_id, still_id, notes, quote):
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


def effective_prompt(g, words):
    """The prompt as sent: the fixed opening, the line that explains the marks when the guide has them, the writer's blocks, the two fixed closing lines."""
    marks = g.get('marks') or {}
    lines = [TAKE_OPEN]
    if marks.get('band') or marks.get('stripes'):
        lines.append('How to read the video: ' + ' '.join(([f'the coloured band on the ground only marks where the walking line runs; it is not a thing in the place and is never shown.'] if marks.get('band') else [])
                                                         + (["the thin stripe down the side of each box person marks that person's side."] if marks.get('stripes') else [])))
    lines.append(words.strip())
    lines += [l for l in (LIGHT_LINE, SILENCE_LINE) if l.lower() not in words.lower()]
    return '\n'.join(lines)


def set_prompt(conn, store, user, run, outputs, shot_id, prompt):
    """The writer's words for the take, kept until the operator says Shoot. Refused when it carries what the tests showed to fail."""
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
    return {'shot_id': shot_id, 'words': len(words.split()), 'prompt': effective_prompt(g, words), 'next': 'Show the operator the ready-to-shoot card; the take is paid for only on their word (`vw guide shoot`).'}


def ready_card(session, shot_id, price_per_s):
    """What the operator sees before any video is paid for, and what is still missing."""
    g = entry_of(session, shot_id)
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('guide_sha256') == g['sha256']), None)
    missing = [what for ok, what in (((g.get('render') or {}).get('status') == 'ready', 'the rendered guide'), (still is not None, 'an approved still made from this guide'),
                                     (bool(still and still.get('overlay_key')), 'the overlay'), (bool(g.get('take_prompt')), "the take's words")) if not ok]
    return {'shot_id': shot_id, 'ready': not missing, 'missing': missing, 'seconds': g['seconds'], 'cost_inr': round(g['seconds'] * price_per_s, 2),
            'guide_key': (g.get('render') or {}).get('guide_key'), 'strip_key': (g.get('frames') or {}).get('strip_key'), 'still': still,
            'prompt': effective_prompt(g, g['take_prompt']['prompt']) if g.get('take_prompt') else None, 'look_for': 'On the overlay: every person and thing of the still sits on the red outlines of the guide.'}


def shoot(conn, store, user, run, outputs, shot_id, quote, again=False):
    """The operator's go-ahead: one Gemini edit of the guide. Refused while anything of the card is missing, while a take is open, and when nothing
    changed since the last take (the same request is never sent twice; `again` only after a take that came back as the guide itself or at the wrong length)."""
    session = VS.session_of(store, run, outputs)
    plan, gap, scene, shot = VS.guarded(lambda: VS.locate(store, session, shot_id))
    VS._no_question(session, shot_id)
    g = entry_of(session, shot_id)
    card = ready_card(session, shot_id, VS.prices()['video_inr_per_s'])
    need(card['ready'], 'Not ready to shoot; still missing: ' + ', '.join(card['missing']) + '.')
    need(str(quote or '').strip(), "A take is paid for on the operator's word: give their words (--quote).")
    render, still = g['render'], card['still']
    open_job = conn.execute("select id from vw2_jobs where run_id=%s and stage='visuals' and unit=%s and provider='video' and status in ('queued','running','submitted','submission_unknown','storage_pending')",
                            (run['id'], shot_id)).fetchone()
    if open_job:
        raise Problem(409, 'JOB_OPEN', 'A take for this shot is still open; wait, recover or resolve it first.', job_id=str(open_job['id']))
    prompt = card['prompt']
    same = digest({'guide': render['sha256'], 'still': still['sha256'], 'prompt': prompt})
    before = [t for t in g.get('takes') or [] if t.get('same') == same]
    if before:
        blocked = (session.get('take_checks') or {}).get(before[-1].get('job_id') or '', {}).get('blocked')
        need(again and blocked, 'Nothing changed since the last take of this shot: the same request is never sent twice. Change the guide, the still or the words (one thing), or cut the shot.'
             if not blocked else 'The last take came back unusable (' + str(blocked) + '). To send the same request once more, the operator says so: `vw guide shoot --again --quote "…"`.')
        need(sum(1 for t in before) < 2, 'This request was already sent twice; change the guide, the still or the words.')
    seconds = int(g['seconds'])
    VS.check_cap(conn, run, session, seconds * VS.prices()['video_inr_per_s'], f'a {seconds} s take')
    gen = video_generators.GUIDE
    fps = float(session['source']['fps'])
    record = {'contract': 'videowizard-guide-take-v1', 'kind': 'guide', 'run_id': str(run['id']), 'shot_id': shot_id, 'plan_digest': digest(plan), 'attempt': len(g.get('takes') or []) + 1,
              'guide': {'key': render['guide_key'], 'sha256': render['sha256'], 'seconds': seconds, 'scene_sha256': g['sha256']},
              'start_image': {'reference_id': still['id'], 'sha256': still['sha256'], 'key': still['key'], 'mime_type': 'image/png', 'width': still.get('width'), 'height': still.get('height')},
              'prompt': g['take_prompt']['prompt'], 'effective_prompt': prompt, 'provider': gen['provider'], 'model': gen['model'], 'aspect_ratio': gen['aspect_ratio'], 'resolution': gen['resolution'],
              'duration_seconds': seconds, 'recipe': g.get('recipe'),
              'placement': {'start_frame': shot['start_frame'], 'end_frame': shot['end_frame'], 'film_fps': session['source']['fps'],
                            'duration_seconds': str((shot['end_frame'] - shot['start_frame']) / fps), 'exact_seconds': (shot['end_frame'] - shot['start_frame']) / fps}}
    identity = digest(record)
    k = VS.key(run, f'takes/{identity}.request.json')
    VS.save_json(store, k, record)
    session['preparations'][shot_id] = {'preparation_id': identity, 'key': k, 'guide': True}
    job_id = _queue(conn, run, shot_id, 'video', {'kind': 'take', 'preparation_id': identity, 'request_key': k, 'provider': gen['provider'], 'model': gen['model'], 'duration_seconds': seconds})
    g.setdefault('takes', []).append({'job_id': job_id, 'same': same, 'preparation_id': identity, 'quote': str(quote).strip(), 'by': user['id'], 'at': now()})
    VS.save_session(store, run, session)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'take sent', 'job_id': job_id, 'model': gen['model'], 'seconds': seconds, 'prompt': prompt, 'guide_sha256': render['sha256'], 'still_sha256': still['sha256'],
                                                    'request_key': k, 'quote': str(quote).strip(), 'again': bool(before), 'by': user['id'], 'by_name': user.get('name') or ''})
    return {'shot_id': shot_id, 'job_id': job_id, 'seconds': seconds, 'model': gen['model'], 'next': 'The take is being made (one to three minutes). Then it is checked and shown with its scorecard: `vw visuals status`.'}


# ---------- what the worker writes back (under the run's lock) ----------

def apply_result(session, job, status, result, error):
    """A finished guide job's result on the shot's entry; ignored when the scene changed meanwhile. Returns the entry for the record of generations, or None."""
    req = job['request']
    g = (session.get('guides') or {}).get(req.get('shot_id'))
    if not g or g.get('sha256') != req.get('sha256'):
        return None
    ok = status in ('ready', 'retained')
    if req['kind'] == 'guide-frames':
        g['frames'] = {'job_id': str(job['id']), 'status': 'ready' if ok else 'failed', **({'frames': result['frames'], 'strip_key': result['strip_key']} if ok else {'error': error})}
        return {'kind': 'check frames', 'ok': ok, **({'strip_key': result['strip_key']} if ok else {'error': error})}
    if req['kind'] == 'guide-render':
        g['render'] = {'job_id': str(job['id']), 'status': 'ready' if ok else 'failed', **({k: result[k] for k in ('guide_key', 'sha256', 'bytes', 'frame1_key', 'frame1_sha256', 'render_seconds')} if ok else {'error': error})}
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
            'take_prompt': (g.get('take_prompt') or {}).get('prompt'), 'card': {k: v for k, v in ready_card(session, shot_id, VS.prices()['video_inr_per_s']).items() if k in ('ready', 'missing', 'seconds', 'cost_inr', 'prompt', 'look_for')}}
