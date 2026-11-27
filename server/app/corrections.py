"""design/223 (SK, 22 Nov 2026): the versions of a take. The first take is made once at 360p and shown as it is. The operator accepts it or says
what is wrong, in plain words; the assistant chooses the route (`RULE`, the one place the rule is written) and sends it here; every version is
720p. An accepted 360p take gets its full-size copy (`copy_text`, `COPY_WAY`: the one place to change how). Nobody checks a video: the frames
the server keeps of each are only for the assistant to choose the route and to place the cut.

One flow, two front ends: the page's answers and the chat's reach this module through `takes.answer`; the assistant's route through `send`.
A correction is one dict on the shot's guide entry (`guides[shot]['corrections']`):
  asked:   {id, job_id (the video the operator answered), words, by, by_name, at}
  routed:  + route, reason, by_route, at_route, source {job_id, key, sha256, seconds, request_key}, jobs [..], and what was sent
  both:    + then (the remake, queued when the edit is back)
  waiting: + waiting (the cost limit's sentence), spec (what to send when the limit is raised)
  dropped: + dropped (withdrawn by the operator)."""
import hashlib
import re
import subprocess
import tempfile
import uuid
from io import BytesIO
from pathlib import Path

from . import generations, guide, video_generators, visuals_stage as VS
from .config import settings
from .errors import Problem
from .visual_contract import need

# ---------- the settings, each in one place ----------
VERSION_SIZE = '720p'               # every version (an edit, a remake, the full-size copy); 1080p on SK's word
CLIP_MIN_S, CLIP_MAX_S = 1.0, 3.0   # a remake's clip: from the video's start to just before the fault
PICTURES_MAX, PICTURE_SIDE = 6, 1536
COPY_WAY = 'edit'                   # how an accepted 360p take gets its full-size video; SK will test another way (the first seconds as a reference)
ROUTES = ('edit', 'remake', 'both', 'first_take', 'none')
OPEN = ('queued', 'running', 'submitted', 'storage_pending', 'submission_unknown')
HOW = guide.HOW

RULE = """The route of a correction. This text is the one place the rule is written (SK's working rule of 22 Nov 2026; it will be looked at again after real runs).
Choose from the operator's words and the video's frames. The frames are only for this choice and for placing a cut: you give no verdict on the video.

- edit: the video is fine, and certain things in it must be corrected, added or removed (an object, a surface, something lying the wrong way, a size). The whole video goes, uncut, with words; no picture. Write each change as one plain, exact line: what, where, and what is there instead. Then what must stay: the people and what they do, the place, the camera, the light, the timing.
- remake: the first seconds are usable and what happens after them must change (the action, the movement, how it ends). Find the second where the fault starts and cut just before it: at least 1 second, at most 3; in doubt, cut earlier (the model copies whatever the clip shows). Give up to 6 approved pictures and a short prompt.
- both: things to correct and an action to change. The edit is made first, then the remake from the edited video, one after the other; give the fields of both.
- first_take: nothing of the video is usable. The first take is made again from the same layout video and still. Only when the still and the layout are right: when the still shows the fault and the rest is fine, the route is edit (it sends no still); when nothing is usable and the still shows the fault, the route is none and the still is repaired first, by its own step.
- none: nothing is made. The operator's words are about the still, the layout or the camera; or they want the shot cut or left out; or the words do not say what should be different (ask once what should change). Say it to the operator in one plain sentence (`say`).

The pictures of a remake: the approved sheets of each person in the shot, the people who act in the changed part first (with more than two people, fewer each: full length before face before hand); then each thing that must appear and is not in the clip; then other things. Only clean pictures: cropped close to the object, and never one that shows the action being removed or other people and things. What the film has no picture of goes in the words; no picture is made for this.

The prompt of a remake, short, in this order: what the shot is for; what stays as in the clip (people, place, camera, light); what happens, in plain terms (the action, the change of posture or movement); the result that must be seen at the end. No second for each move. No box or layout words. Say what is there, not what is missing. Be exact where physics depends on it (which hand, which ends).

Our own words: read the take words and the still's words. When they asked for the fault, say so in `our_words.what` and give the corrected take words in `our_words.take_words`; the still and the plan are not changed."""

FILE = ('{"route": "edit|remake|both|first_take|none", "reason": "one sentence: why this route", "from": "<a job id, only when the operator said an earlier video was better>", '
        '"changes": ["one exact line for each change"], "keep": "what must stay", "cut_s": 2.0, "pictures": [{"id": "<an approved picture>", "job": "what it is for", '
        '"crop": {"left": 0, "top": 0, "width": 1, "height": 1}}], "prompt": "the short prompt of a remake", '
        '"our_words": {"what": "what our own words asked for", "take_words": "the corrected take words"}, "say": "for none: the one sentence to the operator", "withdrawn": false}')

W = {
    'edit_one': 'Edit the video. Make only this change: {change}', 'edit_many': 'Edit the video. Make only these changes:', 'keep': 'Keep everything else exactly the same: {keep}.',
    # SK's test of 22 Nov 2026 (5 paid calls; vw2-archive/2026-11-22/upscale-test): "make no change: give the same video again" returned the 360p picture made bigger (a 720p
    # file with 360p detail). These words returned a picture as detailed as a true 720p take on three videos, frame for frame on the input. Kept as tested.
    'copy': ('Edit the video. Make only this change: the picture becomes true {to} footage with sharp, fine detail: skin, cloth, surfaces, textures and edges '
             'as a camera records them at {to}. The video given is a small {was} picture; do not simply enlarge it.\n\n'
             'Keep everything else exactly the same, frame for frame: the people and what they do, every object, the place, the camera, the light and the timing.'),
    'remake_open': 'Make a new {s}-second video that begins as the reference video does.', 'remake_close': 'One continuous shot. No cut. No dialogue. No music.',
    'no_correction': 'No correction of {shot} waits for its route: the operator has said nothing is wrong with its video, or its route was already sent (`vw guide corrections`).',
    'being_made': 'A video of this shot is being made: say it again when it is back.',
    'not_a_video': '{job} is not a video of this shot that is ready.',
    'already': 'The full-size video of this take is already ordered.',
    'once': 'This request was sent again once already. Say what should change, or accept an earlier video.',
    'nothing_failed': 'No video of this shot failed at the provider: there is nothing to send again.',
    'need_words': 'Write what is wrong first: the correction is made from these words.',
    'not_sent': 'Not sent: {why}',
    'due': ('{name} ({shot}): the operator said of its video: "{words}". Choose the route and send it: `vw guide corrections` gives the rule, the frames and the pictures; '
            'then `vw guide correct --shot {shot} --file work/guide/{shot}/correction.json`.'),
    'due_cap': '{name} ({shot}): its video waits for the cost limit ({why}) Tell the operator the spend; it is sent when the owner sets another limit, with nothing answered again.',
    'told': 'Ordered: a {s} s video, about ₹{inr}.', 'told_two': 'Ordered: two videos in a row, the edit and then the remake: {s} s, about ₹{inr}.',
    'told_first': 'The first take of {shot} is being made again.',
    'ordered': 'Ordered: {what}: {s} s, about ₹{inr}.', 'copies': '{n} full-size video', 'asked': '{n} correction',
    'ordered_how': 'Say this line to the operator as it is and ask nothing with it.',
    'withdrawn': 'The correction of {shot} is withdrawn: nothing is made; its video waits for the operator\'s answer again.',
    'log_route': 'route {route}: {reason}', 'log_copy': 'the full-size video of the accepted take ordered',
}
TIMED = re.compile(r'\b\d+(?:\.\d+)?\s*(?:–|—|-|to)\s*\d+(?:\.\d+)?\s*s\b|\bat\s+\d+(?:\.\d+)?\s*s\b', re.I)
BOX = re.compile(r'\b(box(?:es)?|layout|blocking)\b', re.I)


# ---------- the sizes ----------

def size_of(job):
    """A video's size: the one its job was asked at; a take made before design/223 names none and is 720p."""
    return str((job.get('request') or {}).get('resolution') or '720p')


def final(job):
    """A video the film can take: one at the version size. A 360p take never goes into the film."""
    return size_of(job) == VERSION_SIZE


def price(seconds, calls=1):
    return float(seconds) * calls * VS.video_price(VERSION_SIZE)


# ---------- the words that are sent ----------

def edit_text(changes, keep):
    changes = [' '.join(str(c).split()) for c in changes]
    head = W['edit_one'].format(change=changes[0]) if len(changes) == 1 else '\n'.join([W['edit_many']] + [f'{n}. {c}' for n, c in enumerate(changes, 1)])
    return head + '\n\n' + W['keep'].format(keep=' '.join(str(keep).split()).rstrip('.'))


def copy_text(was=None, to=None):
    """The words of the full-size copy of an accepted take: `was` is the take's size, `to` the size of a version (both from the settings)."""
    return W['copy'].format(was=was or video_generators.GUIDE['resolution'], to=to or VERSION_SIZE)


def remake_text(seconds, picture_jobs, prompt):
    return '\n\n'.join(x for x in (W['remake_open'].format(s=int(seconds)), '\n'.join(f'Picture {n} = {j}' for n, j in enumerate(picture_jobs, 1)), str(prompt).strip(), W['remake_close']) if x)


def problems(body, seconds):
    """What the server refuses before anything is paid; empty when the route may be sent."""
    route, out = body.get('route'), []
    if route not in ROUTES:
        return [f"The route is one of: {', '.join(ROUTES)}."]
    if len(str(body.get('reason') or '').split()) < 3:
        out.append('Say why this route, in one sentence (`reason`).')
    if route == 'none' and not body.get('withdrawn') and len(str(body.get('say') or '').split()) < 3:
        out.append('Say to the operator, in one plain sentence, why nothing is made or what you need to know (`say`).')
    if route in ('edit', 'both'):
        changes = body.get('changes')
        if not isinstance(changes, list) or not changes or not all(str(c or '').strip() for c in changes):
            out.append('An edit needs at least one change, each as one exact line (`changes`).')
        if not str(body.get('keep') or '').strip():
            out.append('An edit says what must stay (`keep`): the people and what they do, the place, the camera, the light, the timing.')
    if route == 'edit' and body.get('pictures'):
        out.append('An edit sends no picture: only the whole video and the words.')
    if route in ('remake', 'both'):
        cut, pics, words = body.get('cut_s'), body.get('pictures') or [], str(body.get('prompt') or '').split()
        if isinstance(cut, bool) or not isinstance(cut, (int, float)):
            out.append('The cut (`cut_s`) is a number of seconds from the start of the video.')
        elif cut > CLIP_MAX_S:
            out.append(f'The clip is at most {CLIP_MAX_S:g} s: cut earlier.')
        elif cut < CLIP_MIN_S:
            out.append(f'The clip is at least {CLIP_MIN_S:g} s. When the fault starts earlier, this is not a remake: an edit, or the first take again.')
        elif cut > float(seconds) - 1:
            out.append(f'The cut must lie at least 1 s before its end: the video is {float(seconds):g} s.')
        if not isinstance(pics, list) or len(pics) > PICTURES_MAX:
            out.append(f'A remake takes at most {PICTURES_MAX} pictures: what is left out goes in the words.')
        if len(words) < 25:
            out.append('The prompt is too short: what the shot is for, what stays as in the clip, what happens, and the result seen at the end.')
        if len(words) > 300:
            out.append('Keep the prompt short (at most 300 words): the action in plain terms; the moves are the model\'s.')
        if len(TIMED.findall(' '.join(words))) >= 2:
            out.append('The prompt gives a second for every move: say what happens in plain terms and leave the moves to the model.')
        m = BOX.search(' '.join(words))
        if m:
            out.append(f'No box or layout words in a remake ("{m.group(0)}"): say what is there.')
    return out


# ---------- the pictures and the clip ----------

def picture(store, run, session, shot_id, p, people):
    """One picture of a remake: an approved picture of the film (as a still's input is), cropped when asked, made smaller, as a JPEG."""
    from PIL import Image
    entry, job = guide._input(store, run, session, shot_id, p, people)
    with Image.open(BytesIO(store.get(entry['key']))) as im:
        im = im.convert('RGB')
        im.thumbnail((PICTURE_SIDE, PICTURE_SIDE))
        buf = BytesIO()
        im.save(buf, format='JPEG', quality=90)
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    k = VS.key(run, f'takes/pictures/{sha[:16]}.jpg')
    store.put(k, data, 'image/jpeg')
    return {'id': p['id'], 'key': k, 'sha256': sha, 'mime_type': 'image/jpeg', 'job': job}


def clip_args(ffmpeg, src, dst, cut_s):
    """The clip: the video from its start to the cut, re-encoded so the cut is exact, with no sound. No blank is ever sent (the model copies what follows one)."""
    return [str(ffmpeg), '-y', '-v', 'error', '-i', str(src), '-t', f'{float(cut_s):g}', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dst)]


def clip(store, snapshot):
    """Cut in the worker, just before the upload; kept beside the request for the record."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / 'in.mp4', Path(d) / 'clip.mp4'
        src.write_bytes(store.get(snapshot['source']['key']))
        subprocess.run(clip_args(settings().FFMPEG_EXECUTABLE, src, dst, snapshot['cut_s']), check=True, capture_output=True, timeout=120)
        data = dst.read_bytes()
    store.put(snapshot['clip_key'], data, 'video/mp4')
    return data


# ---------- a shot's corrections ----------

def rows(g):
    return [c for c in (g or {}).get('corrections') or [] if not c.get('dropped')]


def last(g):
    r = rows(g)
    return r[-1] if r else None


def pending(g):
    """The correction that waits for its route: asked and not routed, or answered "none" (the operator's answer may give it a route)."""
    c = last(g)
    return c if c and c.get('route') in (None, 'none') else None


def _status(c, take_rows):
    """The status of a correction's newest job, or None."""
    jid = (c.get('jobs') or [None])[-1]
    return next((j['status'] for j in take_rows or [] if str(j['id']) == str(jid)), None)


def state(g, take_rows):
    """What a shot's newest correction makes of the shot: 'cap' (waits for the cost limit), 'redo' (its route is awaited, or the remake of both follows),
    'chat' (no route: the assistant talks to the operator), or None."""
    c = last(g)
    if not c:
        return None
    if c.get('waiting'):
        return 'cap'
    if not c.get('route'):
        return 'redo'
    if c['route'] == 'none':
        return 'chat'
    if c.get('then') and _status(c, take_rows) not in ('failed', 'cancelled', 'rejected'):
        return 'redo'
    return None


def _source(job):
    return {'job_id': str(job['id']), 'key': job['result']['key'], 'sha256': job['result']['sha256'], 'seconds': int(float(job['request'].get('duration_seconds') or 0)),
            'request_key': job['request'].get('request_key')}


def _new(job, user, **more):
    return {'id': uuid.uuid4().hex[:12], 'job_id': str(job['id']), 'by': user['id'], 'by_name': user.get('name') or '', 'at': guide.now(), **more}


def ask(session, shot_id, job, words, user):
    """The operator's words about one video: kept until the assistant sends the route. Nothing is made here."""
    words = ' '.join(str(words or '').split())
    need(words, W['need_words'])
    c = _new(job, user, words=words)
    session['guides'][shot_id].setdefault('corrections', []).append(c)
    return c


def _queue(conn, store, run, session, shot_id, c, spec):
    """One version: its request saved, its job queued, its line in the record of generations."""
    src, gen = c['source'], video_generators.GUIDE
    plan = VS.current_plan(store, session)
    placement = (VS.load_json(store, src['request_key']) or {}).get('placement') if src.get('request_key') else None
    record = {'contract': 'videowizard-version-v1', 'kind': spec['kind'], 'route': c['route'], 'run_id': str(run['id']), 'shot_id': shot_id, 'plan_digest': VS.digest(plan), 'shot_print': VS.shot_print(plan, shot_id),
              'correction_id': c['id'], 'source': {k: src[k] for k in ('job_id', 'key', 'sha256')}, 'pictures': spec.get('pictures') or [], 'effective_prompt': spec['text'],
              'provider': gen['provider'], 'model': gen['model'], 'aspect_ratio': gen['aspect_ratio'], 'resolution': VERSION_SIZE, 'duration_seconds': src['seconds'], 'placement': placement,
              **({'cut_s': float(spec['cut_s'])} if spec['kind'] == 'remake' else {})}
    identity = VS.digest(record)
    if spec['kind'] == 'remake':
        record['clip_key'] = VS.key(run, f'takes/{identity}.clip.mp4')
    k = VS.key(run, f'takes/{identity}.request.json')
    VS.save_json(store, k, record)
    session.setdefault('preparations', {})[shot_id] = {'preparation_id': identity, 'key': k, 'guide': True}
    job_id = guide._queue(conn, run, shot_id, 'video', {'kind': 'take', 'route': c['route'], 'version': spec['kind'], 'preparation_id': identity, 'request_key': k, 'provider': gen['provider'],
                                                        'model': gen['model'], 'duration_seconds': src['seconds'], 'resolution': VERSION_SIZE, 'plan_digest': record['plan_digest'], 'shot_print': record['shot_print'], 'from_job': src['job_id']})
    c.setdefault('jobs', []).append(job_id)
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'version sent', 'job_id': job_id, 'route': c['route'], 'version': spec['kind'], 'reason': c.get('reason') or '', 'words': c.get('words') or '',
                                                    'from_job': src['job_id'], 'answered_job': c['job_id'], 'prompt': spec['text'], 'pictures': [p['id'] for p in spec.get('pictures') or []],
                                                    **({'cut_s': float(spec['cut_s'])} if spec['kind'] == 'remake' else {}), 'model': gen['model'], 'seconds': src['seconds'], 'resolution': VERSION_SIZE,
                                                    'request_key': k, 'asked_by_our_words': bool((c.get('our_words') or {}).get('what')), 'by': c.get('by'), 'by_name': c.get('by_route') or c.get('by_name') or ''})
    return job_id


def _go(conn, store, run, session, shot_id, c, spec, calls=1):
    """Send a correction's first call when the film's cost limit allows all its calls; else it waits, with what to send, and nothing is lost.
    Returns the job, or None when it waits."""
    try:
        VS.check_cap(conn, run, session, price(c['source']['seconds'], calls), f"a {c['source']['seconds']} s video" if calls == 1 else f"two {c['source']['seconds']} s videos")
    except Problem as exc:
        if exc.code != 'VISUALS_CAP':
            raise
        c.update(waiting=str(getattr(exc, 'message', '') or exc), spec=spec, calls=calls)
        return None
    c.pop('waiting', None), c.pop('spec', None), c.pop('calls', None)
    return _queue(conn, store, run, session, shot_id, c, spec)


def _log(conn, run, shot_id, entry, user, quote, by_kind):
    if conn is not None:
        from . import runlog
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'shot {shot_id}', 'rule': 'design/223 (the take process)', 'entry': entry,
                            'by_kind': by_kind, 'by_name': user.get('name') or '', 'quote': quote or '', 'request_id': None})


def copied(g, job):
    return any(c.get('route') == 'copy' and c['job_id'] == str(job['id']) for c in rows(g))


def copy(conn, store, user, run, session, shot_id, job, quote=''):
    """The full-size video of an accepted 360p take: the whole take sent as an edit that asks for the same video at the version's size, with its detail
    (`copy_text`). The caller saves the session."""
    g = session['guides'][shot_id]
    need(not copied(g, job), W['already'])
    c = _new(job, user, route='copy', source=_source(job))
    g.setdefault('corrections', []).append(c)
    _go(conn, store, run, session, shot_id, c, {'kind': COPY_WAY, 'text': copy_text(size_of(job)), 'pictures': []})
    _log(conn, run, shot_id, W['log_copy'], user, quote, 'operator')
    return c


def send(conn, store, user, run, outputs, shot_id, body):
    """The assistant's route for the correction that waits on this shot. Refused, with nothing paid, when the route's own rules are broken."""
    VS.need_free(conn, store, run, [shot_id])
    session = VS.session_of(store, run, outputs)
    VS.guarded(lambda: VS.locate(store, session, shot_id))
    c = pending(guide.entry_of(session, shot_id))
    need(c, W['no_correction'].format(shot=shot_id))
    take_rows = VS.take_jobs(conn, run, shot_id)
    need(not any(j['status'] in OPEN for j in take_rows), W['being_made'])
    body = body if isinstance(body, dict) else {}
    src = next((j for j in take_rows if str(j['id']) == str(body.get('from') or c['job_id']) and j['status'] == 'ready'), None)
    need(src, W['not_a_video'].format(job=body.get('from') or c['job_id']))
    wrong = problems(body, _source(src)['seconds'])
    need(not wrong, W['not_sent'].format(why=' '.join(wrong)))
    route, ours = body['route'], body.get('our_words') if isinstance(body.get('our_words'), dict) else {}
    mark = {'route': route, 'reason': ' '.join(str(body['reason']).split()), 'by_route': user.get('name') or '', 'at_route': guide.now(), 'source': _source(src),
            **({'our_words': {'what': ' '.join(str(ours['what']).split()), 'take_words': bool(str(ours.get('take_words') or '').strip())}} if str(ours.get('what') or '').strip() else {})}
    if route == 'none':
        c.update(mark, **({'dropped': {'by': user['id'], 'at': guide.now()}} if body.get('withdrawn') else {'say': ' '.join(str(body.get('say') or '').split())}))
        VS.save_session(store, run, session)
        _log(conn, run, shot_id, W['log_route'].format(route='none', reason=mark['reason']), user, c.get('words'), 'assistant')
        return {'shot_id': shot_id, 'route': 'none', 'tell': W['withdrawn'].format(shot=shot_id) if body.get('withdrawn') else c['say']}
    spec = then = None
    if route in ('remake', 'both'):
        people = VS.people_of(VS.guarded(lambda: VS.current_plan(store, session)))
        pics = [picture(store, run, session, shot_id, p, people) for p in body.get('pictures') or []]
        spec = {'kind': 'remake', 'text': remake_text(mark['source']['seconds'], [p['job'] for p in pics], body['prompt']), 'pictures': pics, 'cut_s': float(body['cut_s'])}
        mark.update(cut_s=float(body['cut_s']), pictures=[p['id'] for p in pics], prompt=str(body['prompt']).strip())
    if route in ('edit', 'both'):
        spec, then = {'kind': 'edit', 'text': edit_text(body['changes'], body['keep']), 'pictures': []}, spec
        mark.update(changes=[' '.join(str(x).split()) for x in body['changes']], keep=' '.join(str(body['keep']).split()))
    if str(ours.get('take_words') or '').strip():   # R11: our own words asked for the fault: the stored take words are corrected (the still and the plan are not)
        guide.set_prompt(conn, store, user, run, outputs, shot_id, ours['take_words'])
        session = VS.session_of(store, run, outputs)
        c = pending(guide.entry_of(session, shot_id))
    if route == 'first_take':   # nothing of the video is usable: the first take again, on the operator's words
        out = guide.shoot(conn, store, user, run, outputs, shot_id, c['words'], same=True)
        session = VS.session_of(store, run, outputs)
        c = pending(guide.entry_of(session, shot_id))
        c.update(mark, jobs=[out['job_id']])
        tell = W['told_first'].format(shot=shot_id)
    else:
        c.update(mark, **({'then': then} if then else {}))
        calls = 2 if then else 1
        sent = _go(conn, store, run, session, shot_id, c, spec, calls)
        tell = (W['told_two'] if then else W['told']).format(s=mark['source']['seconds'] * calls, inr=f"{price(mark['source']['seconds'], calls):,.0f}") if sent else c['waiting']
    c['told'] = True
    VS.save_session(store, run, session)
    _log(conn, run, shot_id, W['log_route'].format(route=route, reason=mark['reason']), user, c.get('words'), 'assistant')
    return {'shot_id': shot_id, 'route': route, 'jobs': c.get('jobs') or [], 'tell': tell, 'tell_how': W['ordered_how']}


def reopen(conn, store, user, run, outputs, shot_id, words, quote):
    """E13: the operator corrects a shot whose video they had accepted, while the film is in this step: the acceptance is taken back and the
    correction starts from the accepted video."""
    session = VS.session_of(store, run, outputs)
    sel = (session.get('selections') or {}).get(shot_id)
    need(sel, f'{shot_id} has no accepted video: answer its video on the page.')
    need(' '.join(str(words or '').split()), W['need_words'])
    job = next((j for j in VS.take_jobs(conn, run, shot_id) if str(j['id']) == str(sel['job_id'])), None)
    need(job and job['status'] == 'ready', W['not_a_video'].format(job=sel['job_id']))
    VS.review_take(conn, store, user, run, outputs, str(job['id']), 'rejected', words, '', quote)   # takes the selection back
    session = VS.session_of(store, run, outputs)
    c = ask(session, shot_id, job, words, user)
    VS.save_session(store, run, session)
    return {'shot_id': shot_id, 'correction': c['id'], 'next': W['due'].format(name=shot_id, shot=shot_id, words=c['words'])}


def resend(conn, store, user, run, session, shot_id, take_rows):
    """E9: a call that failed at the provider is sent again, once, on the operator's word: the same request. The caller saves the session."""
    g = session['guides'][shot_id]
    c = last(g)
    failed = next((j for j in take_rows if c and str(j['id']) == str((c.get('jobs') or [None])[-1]) and j['status'] in ('failed', 'cancelled')), None)
    need(failed, W['nothing_failed'])
    need(not c.get('resent'), W['once'])
    VS.check_cap(conn, run, session, price(failed['request'].get('duration_seconds') or 0), 'the same video once more')
    job_id = guide._queue(conn, run, shot_id, 'video', dict(failed['request']))
    c['jobs'].append(job_id)
    c['resent'] = True
    generations.add(conn, run['id'], shot_id, HOW, {'kind': 'version sent again', 'job_id': job_id, 'after': str(failed['id']), 'route': c.get('route'), 'request_key': failed['request'].get('request_key'),
                                                    'by': user['id'], 'by_name': user.get('name') or ''})
    return job_id


def can_resend(g, take_rows):
    c = last(g)
    return bool(c and c.get('jobs') and not c.get('resent') and c.get('route') != 'first_take' and _status(c, take_rows) in ('failed', 'cancelled'))


def landed(conn, store, run, session, job, ok):
    """In the worker, when a version's call ends: for both kinds of fault the remake is sent now, from the edited video; never when the edit failed.
    True when the session changed (the caller saves it)."""
    g = (session.get('guides') or {}).get(job.get('unit')) or {}
    c = next((c for c in rows(g) if c.get('then') and str((c.get('jobs') or [None])[-1]) == str(job['id'])), None)
    if not c or not ok:
        return False
    then = c.pop('then')
    c['source'] = {**c['source'], 'job_id': str(job['id']), 'key': job['result']['key'], 'sha256': job['result']['sha256']}
    try:
        _queue(conn, store, run, session, job['unit'], c, then)   # the cost limit was asked for both calls when the route was sent
    except Exception as exc:   # the shot is never left "being corrected" for ever: the edited video is shown, and the operator says what is still wrong
        c['then_failed'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    return True


def go_waiting(conn, store, run, session):
    """E12: after the owner set another cost limit: the videos that waited for it are sent, with nothing answered again. Returns how many went."""
    n = 0
    for shot_id, g in (session.get('guides') or {}).items():
        for c in rows(g):
            if c.get('waiting') and c.get('spec') and _go(conn, store, run, session, shot_id, c, c['spec'], c.get('calls') or 1):
                n += 1
    return n


# ---------- what the assistant is told ----------

def _shots(session, plan):
    from . import takes
    return [(takes.name_of(g, sh, n, of), sh) for g, sh, n, of in takes.video_shots(plan, session)] if plan else []


def due(session, plan, take_rows):
    """For the next-step line: each correction that waits for its route, and each video that waits for the cost limit."""
    from . import takes
    out = []
    for name, sh in _shots(session, plan):
        g = (session.get('guides') or {}).get(sh['id']) or {}
        c = last(g)
        if not c or sh['id'] in (session.get('selections') or {}) or any(j['status'] in OPEN for j in takes.jobs_of(take_rows, sh['id'])):
            continue
        if c.get('waiting'):
            out.append(W['due_cap'].format(name=name, shot=sh['id'], why=c['waiting']))
        elif not c.get('route'):
            out.append(W['due'].format(name=name, shot=sh['id'], words=c['words']))
    return ' '.join(out)


def listed(store, session, plan, take_rows):
    """`vw guide corrections`: every correction that waits for its route, with what the assistant chooses from: the operator's words, the video's
    frames (one every half second) and its sheet, our own words for the shot, the approved pictures of the shot's people and things, and the rule."""
    from . import takes
    out = []
    for name, sh in _shots(session, plan):
        g = (session.get('guides') or {}).get(sh['id']) or {}
        c = pending(g)
        if not c or c.get('route'):
            continue
        job = next((j for j in takes.jobs_of(take_rows, sh['id']) if str(j['id']) == c['job_id']), None)
        rec = (session.get('take_checks') or {}).get(c['job_id']) or {}
        still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('key')), None) or {}
        mine = set(sh.get('element_ids') or [])
        out.append({'shot_id': sh['id'], 'name': name, 'words': c['words'], 'job': c['job_id'], 'seconds': int(float(((job or {}).get('request') or {}).get('duration_seconds') or g.get('seconds') or 0)),
                    'size': size_of(job or {}), 'frames': rec.get('frames') or [], 'sheet': rec.get('sheet_key'), 'take_words': str((g.get('take_prompt') or {}).get('prompt') or ''),
                    'still_words': str(still.get('prompt') or ''), 'plan_line': str(sh.get('description') or sh.get('title') or ''),
                    'pictures': [{'id': r['id'], 'kind': r.get('kind'), 'element_id': r.get('element_id'), 'key': r['key']} for r in (session.get('references') or {}).values()
                                 if r.get('status') == 'approved' and r.get('key') and r.get('element_id') in mine],
                    'videos': [{'job': str(j['id']), 'size': size_of(j), 'route': (j.get('request') or {}).get('route') or 'first take'} for j in takes.jobs_of(take_rows, sh['id']) if j['status'] == 'ready'],
                    'earlier': [{k: x.get(k) for k in ('route', 'reason', 'words', 'cut_s') if x.get(k) is not None} for x in rows(g) if x is not c and x.get('route') not in (None, 'copy')]})
    return {'corrections': out, 'rule': RULE, 'file': FILE,
            'film_pictures': [{'id': r['id'], 'kind': r.get('kind'), 'element_id': r.get('element_id')} for r in (session.get('references') or {}).values() if r.get('status') == 'approved' and r.get('key')],
            'then': ('For each: choose the route by the rule, write `work/guide/<shot>/correction.json` in the shape of `file`, and send it: `vw guide correct --shot S --file …`.'
                     if out else 'No correction waits for its route.')}


def ordered(session, plan):
    """The one line the chat says after done: the full-size videos and the corrections the operator's answers ordered, with the seconds and the
    amount (a correction at one 720p video; two, when it needs both routes, is said when its route is sent). Said once: each is marked `told`."""
    copies = asked = secs = 0
    for _, sh in _shots(session, plan):
        g = (session.get('guides') or {}).get(sh['id']) or {}
        for c in rows(g):
            if c.get('told') or c.get('route') not in (None, 'copy'):
                continue
            c['told'] = True
            copies, asked, secs = copies + (c.get('route') == 'copy'), asked + (c.get('route') is None), secs + int(float(g.get('seconds') or 0))
    plural = lambda t, n: t.format(n=n) + ('' if n == 1 else 's')
    what = ' and '.join(x for x in (plural(W['copies'], copies) if copies else '', plural(W['asked'], asked) if asked else '') if x)
    return W['ordered'].format(what=what, s=secs, inr=f'{price(secs):,.0f}') if what else ''
