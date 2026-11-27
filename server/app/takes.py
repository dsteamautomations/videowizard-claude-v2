"""design/222 (SK, 19 Nov 2026): step 7, AI video, on the decisions page; design/223 (SK, 22 Nov 2026): the new take process.

Each shot's first take is made once, small (360p), and shown as it is: nobody checks it (not Claude, not a helper, not the server) and nothing
makes it again on its own. The operator answers every take on the page, all together, once every take of the film is made: they accept it, or
say what is wrong in plain words. An accepted 360p take gets its full-size video; words of what is wrong become a correction, whose route the
assistant chooses (`corrections`). Every later video of a shot (a version) is shown beside the one it was made from, and beside its neighbouring
shots. There is no limit on rounds. What is decided before a take is paid for (the still, the word to make the first take) stays a card in
the chat; a layout is put to the operator only when it failed its check three times in a row (A1, 25 Nov 2026).

One flow, two front ends: the page's line and the chat's item are built here from the same words; every answer goes through `answer`. No amount
of money is in any word of the page.

Retired by design/223 and refused by name (design/35 rows 316 to 333): Claude's check of a take from frames and its helpers, the wait for it, the
check line and the scorecard, "Make another" with a cause, "Reject" as a button, the limit of two takes from one camera."""
from . import corrections as C, pictures as P, runlog, visuals_stage as V

OPEN = C.OPEN   # the critic's S9: an unknown submission is recovered or resolved; it is not "could not be made"
GONE = ('failed', 'cancelled', 'rejected')
CONTEXT_CHARS = 60   # the rest of a sentence shown in grey before and after a shot's own words, at most

W = {
    'step': 'AI video', 'kind': 'An AI video take', 'ask': 'Is this take right for the film?',
    'take_label': 'Take {n}',
    'select': 'Accept', 'again': 'Say what is wrong', 'resend': 'Send it again', 'select_old': 'Use take {n} after all',
    'say_select': 'Take {n} accepted. It goes in the film at {at}.',
    'say_copy': 'Take {n} accepted. Its full-size video is made when you say done; you see it before it goes in the film.',
    'say_again': 'Take {n} is corrected when you say done. Your words: "{words}"',
    'say_resend': 'The same request is sent once more when you say done.',
    'end_select': 'Take {n} accepted, in the film at {at}.', 'end_copy': 'Take {n} accepted; its full-size video is made.', 'end_again': 'Take {n} corrected: "{words}"',
    'end_resend': 'The same request sent once more.',
    'hint_again': ('What is wrong with it? Say what you see, where, and what should be there instead. A correction can change things in the picture and what happens; '
                   'it cannot change the camera (no zoom, no pan, no steadier camera).'), 'go_again': 'Send these words', 'need_words': 'Write what is wrong first. The correction is made from these words.',
    'paid': 'A new video is paid. Its price is said in the chat when you say done; nothing is ordered before that.',
    'log_short': ', shorter than its place in the film',
    'said': 'You said: {words}',
    'short': 'The take is {s} s; its place in the film is {slot} s.',
    'stale': 'This take was made for an earlier plan of the film and cannot be accepted as it is: say what should change.',
    'stale_refuse': 'This take was made for an earlier plan of the film and cannot be accepted.',
    'where': 'In the film at {start} to {end} ({secs} s) · {gap}', 'length': 'The take is {s} s; its place in the film is {slot} s.',
    'before_shot': 'The shot before, {what}.', 'after_shot': 'The shot after, {what}.', 'before_footage': 'Your footage before this shot.', 'after_footage': 'Your footage after this shot.',
    'route_video': 'an AI video take', 'route_still': 'a still picture', 'route_other': 'a made shot',
    'd_where': 'Where it sits in the film', 'd_prompt': 'How the first take was asked for', 'd_how': 'How it was made',
    'how_first': 'The first take: made from the layout video, started from the approved still.', 'how_again': 'The first take, made again.',
    'how_edit': 'An edit of take {m}.', 'how_remake': 'A remake of take {m} from its first seconds.', 'how_copy': 'The full-size copy of take {m}.', 'how_size': 'Its size is {size}.',
    'play_both': 'Play both together',
    'failed_new': 'The new video could not be made. {why}',
    'still': 'The picture the first take started from', 'frame': 'Take {n}',
    # the step's sentences
    'say_need': '{n} takes need your answer:', 'say_need_one': '1 take needs your answer:', 'say_done': 'Then say done here.', 'say_nothing': 'Nothing waits for you on the page now.',
    'say_failed': '{n} could not be made: they are listed apart.', 'say_failed_one': '1 could not be made: it is listed apart.',
    'summary': '{n} to answer.', 'note': 'Answer each take, then say done in the chat.', 'nothing': 'Nothing waits for you now.',
    'failed': 'It could not be made. Claude tells you in the chat what happens to it.',
    'page_later': 'The page opens when every take is made.',
    'count': '{n} of {m} AI video shots are on this page.',   # fix set (f), SK 20 Nov 2026
    'page_now': 'Every take is made: the operator answers them on the page, in one visit: run `vw visuals page` instead; ask here only where the page cannot be shown. ',
    'help': ['Each shot on the left has one take to answer. Play it. Accept it, or say what is wrong with it in plain words. Answer in any order, then say done in the chat.',
             'Nobody has checked these takes: they are shown as they were made. You are the judge.',
             # SK, 27 Nov 2026 (VW-25: two of twelve takes ended at "no route" on a camera complaint): what a correction can change, said before the operator writes
             'A correction can change a thing in the picture (an object, a surface, a colour, a size, something to add or remove) and what happens (the action, the movement, '
             'how it ends). It cannot change the camera: every AI video shot has one camera, held still with a slight handheld movement, with no zoom and no pan. '
             'Say what you see, where, and what should be there instead.',
             'You are never asked for seconds, a cause or a way to correct. Say what you see and what should be there instead; Claude chooses how it is corrected.',
             'A first take is small. When you accept it, its full-size video is made; you see the two side by side before it goes in the film.',
             'A corrected take is shown beside the one it was made from: "Play both together" plays the two at once. Accept it, or say what is still wrong. There is no limit on rounds.',
             'Under the shot\'s name are the words spoken during it; the word being spoken is marked as the take plays. No sound is played.',
             '"See it in the film" shows where the shot before ends and where the shot after begins, only to compare. "Details" has everything else about the take.',
             'A new video is paid; its price is said in the chat when you say done. This page opens when every take of the film is made.'],
    # the older ways, refused by name (design/223)
    'look_retired': ("Claude's check of an AI video take is retired (design/223): no look is recorded for a take. Nobody checks a take; the operator answers it on the page. "
                     'The takes are not in `vw visuals pictures --looks` any more.'),
    'reject_retired': ('"Reject" as an answer to a take is retired (design/223): the operator accepts the take or says what is wrong with it (the answer "again", with their words); '
                       'when their words mean the shot itself must change, the route of the correction is "none" and the plan is revised.'),
    # release 1, D1 (SK, 20 Nov 2026): what can start now in step 7, as step 6 says it (`pictures.starts`)
    'start_guides': 'the checkers of the guides of {ids} ({n}) (a fresh `vw-guide-check` helper each: its guide is rendered, and its still can be ordered, only after its check passes)', 'start_order': 'the stills of {ids} ({n}), each ordered with `vw guide still --shot S --file still.json`',
    'start_words': "the writers of the take's words of {ids} ({n}) (`vw guide prompt --shot S --file take.txt`)",
    'video_wait': ' Everything else for its take is ready: the server orders the take when the video is ready (`vw visuals next`); go on with the other shots.',   # release 4
    'start_scenes': 'the writers of the scene descriptions of {ids} ({n})',
    'start_rebuild': ("the writers of the scene descriptions of {ids} ({n}), each rebuilt after its check or the operator's correction: read `vw guide status --shot S` first, "
                      'it holds what must change'),
    'held_change': ('{name} ({shot}): its layout failed its check {n} times in a row and the operator said what the shot becomes: "{words}". Do that: a plan revision when the shot '
                    'is cut, shortened, left out or becomes another kind of shot; a new scene (`vw guide scene`) when it stays one AI video shot.'),
    'start_stills': 'the checkers of the stills of {ids} ({n})',
    'log_select': 'take {n} accepted', 'log_copy': 'take {n} accepted at 360p; its full-size video ordered', 'log_again': 'take {n}: the operator said what is wrong', 'log_old': 'take {n} used after all',
    'log_resend': 'the same request sent once more after the provider failed',
    'no_guide': '{shot} has no guide: no video can be made for it here. Tell the assistant in the chat what should happen to the shot.',
    'video_none': 'The take cannot be played here: these are its frames, in order.',
    'sheet': 'Take {n}: its frames, four a second',
    'answered': 'Take {n} accepted. It is in the film at {at}.',
}
PAGE = {   # layout.words.takes: the page's chrome (the page holds no words of its own)
    'todo': 'Needs your answer', 'answered_head': 'Answered earlier', 'coming': 'Could not be made', 'nothing': W['nothing'], 'state_open': 'needs your answer',
    'done': {'select': 'Accepted', 'again': 'Correction ordered'}, 'more': 'See all {n}', 'words_label': 'Voiceover',
    'film': 'See it in the film', 'film_head': 'In the film', 'before': 'Where the shot before ends', 'after': 'Where the shot after begins', 'this_take': 'This take',
    'compare_only': 'Shown to compare. Nothing here needs an answer.', 'compare_from': 'The one before', 'compare_new': 'The new one', 'play_both': W['play_both'],
    'details': 'Details', 'd_still': W['still'],
    'undo': 'Undo', 'cancel': 'Cancel', 'close': 'Close', 'change_in_chat': 'To change this answer, say so in the chat.',
    'loading': 'Loading…', 'missing': 'Not available', 'video_bad': 'The take could not be played here. Tell the assistant in the chat.',
    'left_one': '1 answer still needed', 'left_many': '{n} answers still needed', 'left_note': 'Choose one from the list on the left.',
    'end_head': 'All answered', 'end_note': 'Go back to the chat and say done. This is what will happen then:', 'end_foot': 'Nothing is recorded or made before you say done.',
    'end_again': 'New videos made when you say done: {n}. Claude says their price in the chat then.',
    'foot': '{n} of {m} answered.', 'foot_wait': 'When all are answered, say done in the chat. Nothing is recorded before that.', 'foot_done': 'Go back to the chat and say done.',
    'help': 'How this works', 'keys': 'Keys: the left and right arrows move between the shots. Escape closes what is open.'}

STATE = {'none': 'not started', 'chat': 'waiting for you in the chat', 'making': 'being made', 'checking': 'being checked by Claude', 'redo': 'being redone', 'fix': 'being corrected',
         'done': 'made', 'answered': 'answered', 'failed': 'could not be made', 'stale': 'must be made again (the plan changed)', 'cap': 'waiting for the cost limit',
         'video': 'waiting for the layout video', 'still': 'first frame ready: the still can be ordered'}   # release 4: the layout video renders behind the still. "being checked by Claude" is a still's state (its check is unchanged); design/223: a take is never checked
ORDER = ('done', 'answered', 'checking', 'making', 'still', 'video', 'redo', 'fix', 'cap', 'stale', 'chat', 'failed', 'none')   # the order of the counts in the line
COMPLETE = (STATE['done'], STATE['answered'], STATE['failed'], STATE['stale'])   # a take that could not be made never keeps the page closed; the critic's S4: nor one made for an earlier plan


# ---------- the shots, their takes ----------

def video_shots(plan, session):
    """The accepted AI video shots in film order: (gap, shot, its number in the gap, the gap's count of shots)."""
    by_gap = {}
    for g, sh in V._accepted_shots(plan, session):
        by_gap.setdefault(g['gap_id'], []).append((g, sh))
    return [(g, sh, n, len(rows)) for rows in by_gap.values() for n, (g, sh) in enumerate(rows, 1) if V.route_of(sh) == 'video']


name_of = V.name_of   # a shot's name is never its id: the one rule, used by every card since VW-25 issue 7


def jobs_of(take_rows, sid):
    return [j for j in take_rows or [] if j.get('provider') == 'video' and j.get('unit') == sid]


def _rec(session, job):
    """What the server keeps of a take: its frames, one every half second, and its sheet (`take_checks` is the older name of the record)."""
    return (session.get('take_checks') or {}).get(str(job['id'])) or {}


def _reviews(session, job):
    return (session.get('reviews') or {}).get(str(job['id'])) or []


def _rejected(session, job):
    rv = _reviews(session, job)
    return bool(rv) and rv[-1].get('decision') == 'rejected'


def offered(session, job, now=None):
    """design/223: a take is offered to the operator the moment it is made: nothing is awaited. (Until then: with Claude's check, or 30 minutes
    after Claude was asked; design/35 row 318.)"""
    return job.get('status') == 'ready'


def starts(session, plan, take_rows):
    """Release 1, D1 (SK, 20 Nov 2026): the helpers of step 7 that can start now, to be started together in one message, in film order: the writers
    of the scene descriptions (a shot with no guide yet) and the checkers of the stills. '' when none. design/223: a take has no checker.
    The critic's point 4: the line is complete: also the guides whose check frames wait for their fresh checker, the stills that can be ordered
    (the layout's check passed, the guide's first frame rendered, no still yet) and the takes' words that can be written (the still approved); each group is named
    only when the server's own gate takes it (`guide.verdict`, `guide.request_still`, `guide.set_prompt`). Point 10c: a shot that shows a
    person of the footage about whom the operator was never asked is not named for its still: that question is said first, in the same line."""
    if not plan or not V.round_v2(session):
        return ''
    rows = video_shots(plan, session)
    shots, guides, open_ = [sh['id'] for _, sh, _, _ in rows], session.get('guides') or {}, lambda sid: sid not in (session.get('selections') or {}) and not question_open(session, sid)
    from . import guide
    # release 1 (SK, 20 Nov 2026): the fresh checker first, the operator second. A scene whose check failed, or whose layout drawing the operator
    # corrected, is named with the scenes to write (the checker's finding is in the shot's verdict file; the operator's words in `vw guide status`).
    # Release 2, the critic's points 2 and 3: the shots with no guide yet and the shots to rebuild are two groups; a held shot (its third check in a
    # row failed) and one whose change the operator described are not named: the card, and `held_due`, say them. (Until then: one group; design/35 rows 293, 294.)
    none = [sid for sid in shots if sid not in guides and sid not in (session.get('selections') or {}) and not jobs_of(take_rows, sid)]
    again = [sid for sid in shots if sid in guides and open_(sid) and guide.rebuild(guides[sid]) and not guide.held(guides[sid]) and not guides[sid].get('change')]
    mine = lambda g, st: st.get('guide_sha256') == g.get('sha256')
    # A guide's checker is named as soon as its check frames are ready and this scene has no verdict: all together. Never for a scene that has a
    # verdict: passed (its render, then its still) or failed (the scene changes first). (Until release 1: only after the operator approved the
    # layout; design/35 row 281. Until 25 Nov 2026 a passed layout was then shown to the operator on a card; retired, A1.)
    check = [sid for sid in shots if sid in guides and open_(sid) and (guides[sid].get('frames') or {}).get('status') == 'ready' and not guides[sid].get('verdicts') and not guide.rebuild(guides[sid])]
    # release 4: a still is named as soon as the first frame of its layout exists; its video renders behind it (until then: only once the video was rendered too)
    order = [sid for sid in shots if sid in guides and open_(sid) and _still_due(guides[sid]) and not jobs_of(take_rows, sid)]
    hold = P.ask_shots(session, plan) if order else ()   # point 10c: the question is said by `pictures.waits_words` (`faces_to_ask`), first in the same next-step line
    order = [sid for sid in order if sid not in hold]
    words = [sid for sid in shots if sid in guides and open_(sid) and not guides[sid].get('take_prompt') and any(mine(guides[sid], st) and st.get('status') == 'approved' for st in guides[sid].get('stills') or [])]
    stills = {x[1]['id'] for x in P.starts_due(session, plan)}
    what = [W[k].format(ids=', '.join(ids), n=len(ids)) for k, ids in (('start_scenes', none), ('start_rebuild', again), ('start_guides', check), ('start_order', order), ('start_words', words),
                                                                         ('start_stills', [x for x in shots if x in stills])) if ids]
    return P.W['start_now'].format(what='; '.join(what)) if what else ''

# ---------- each shot's state, the line of counts, when the page opens ----------

def _stale(session, plan, job):
    """A take Select would refuse as made for another plan (`visuals_stage.select_gate`, release 1 of 27 Nov 2026, part B: the one gate): its own
    shot is not as it was when the take was ordered, or the take carries no stamp of its shot (made before the release)."""
    return bool(V.select_gate(session, plan, job.get('unit'), job.get('request') or {}, job))


def _ready_to_shoot(g):
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('guide_sha256') == g.get('sha256')), None)
    return bool((g.get('render') or {}).get('status') == 'ready' and still and still.get('overlay_key') and g.get('take_prompt'))


def _still_due(g):
    """Release 4: the still can be ordered: the first frame of the layout exists, this scene's check passed (A1, SK 25 Nov 2026; until then: the
    operator approved this scene's layout drawing), and no still of it is being made, waits or was approved (`guide.request_still` gates the
    same; the video may still be rendering)."""
    from . import guide
    return bool((g.get('render') or {}).get('frame1_key') and guide.checked(g) and not guide.rebuild(g)
                and not any(st.get('status') == 'generating' or (st.get('guide_sha256') == g.get('sha256') and st.get('status') in ('candidate', 'approved')) for st in g.get('stills') or []))


def _video_waits(g):
    """Release 4: everything for the take is there but the layout video (it renders behind the still, or it failed)."""
    return (g.get('render') or {}).get('status') != 'ready' and _ready_to_shoot({**g, 'render': {'status': 'ready'}})


def render_due(session, plan):
    """Release 4: what the next-step line says of the renders: a first frame or a layout video that failed, with how it is made again; and a shot
    that waits only for its video (its word-to-shoot card comes when the video is ready)."""
    from . import guide
    out = []
    for g, sh, n, of in video_shots(plan, session) if plan else []:
        e = (session.get('guides') or {}).get(sh['id']) or {}
        r = e.get('render') or {}
        if not r or sh['id'] in (session.get('selections') or {}) or guide.rebuild(e):
            continue
        state = guide.shoot_state(session, sh['id'])   # phase 4 part B: never silent
        if state and state[0] in ('refused', 'later'):
            out.append((guide.SHOOT_REFUSED if state[0] == 'refused' else guide.SHOOT_WAITS).format(name=name_of(g, sh, n, of), shot=sh['id'], words=state[1]))
        if r.get('status') == 'failed' or (r.get('frame1_error') and not r.get('frame1_key')) or _video_waits(e):
            out.append(f"{name_of(g, sh, n, of)} ({sh['id']}): " + guide.render_line(sh['id'], e) + (W['video_wait'] if r.get('status') != 'failed' and _video_waits(e) else ''))
    return ' '.join(out)


def _card_waits(g):
    """A card of this shot waits in the chat: a still to approve. (Until 25 Nov 2026 also its layout drawing, once the check passed; retired, A1.)"""
    return any(s.get('status') == 'candidate' and s.get('guide_sha256') == g.get('sha256') and s.get('key') for s in g.get('stills') or [])


def _still_checking(session, g, now=None):
    """Release 1, A1: a still of the shot waits for Claude's look (`pictures.start_offered`): its card is not in the chat yet."""
    return any(s.get('status') == 'candidate' and s.get('guide_sha256') == g.get('sha256') and s.get('key') and not P.start_offered(session, s, now) for s in g.get('stills') or [])


def question_open(session, shot_id):
    """E18: an open question on the shot: nothing is made from it, and its take is not selected, until the operator answers it in the chat."""
    return bool((session.get('questions') or {}).get(shot_id))


def _state(session, plan, sh, take_rows, now):
    """(state, the take shown, aside). `aside`: the shot does not keep the page closed for the others: the assistant talks to the operator about it
    in the chat (no route fits, a question is open), or its video waits for the cost limit.
    design/223: a shot whose correction is awaited or being made keeps the page closed: the page opens again when every video of the run is back."""
    sid = sh['id']
    if sid in (session.get('selections') or {}) or sid in (session.get('assets') or {}):   # SK, 23 Nov 2026 (release 3, N1): a shot filled with the operator's own file is done, as step 6 counts it
        return 'answered', None, False
    js, g = jobs_of(take_rows, sid), (session.get('guides') or {}).get(sid) or {}
    if js:
        ready = [j for j in js if j['status'] == 'ready']
        if js[-1]['status'] in OPEN:
            return ('fix' if len(js) > 1 else 'making'), None, False
        mine = C.state(g, js)
        if mine:
            return {'redo': 'fix'}.get(mine, mine), None, mine in ('cap', 'chat')
        if not ready:
            return 'failed', None, False
        if question_open(session, sid):
            return 'chat', None, True
        return ('stale' if _stale(session, plan, ready[-1]) else 'done'), ready[-1], False
    if not g:
        return 'none', None, False
    if _still_checking(session, g, now) or any(P.start_retry_due(session, sid, g, st) for st in g.get('stills') or []):   # phase 4 part A rule 6: made again once by itself
        return 'checking', None, False
    from . import guide
    if guide.held(g):
        return 'chat', None, False   # release 2, the critic's point 2: its third check in a row failed: one card asks the operator
    if guide.rebuild(g):
        return 'redo', None, False  # release 1: its check failed, or the operator corrected its layout: the scene is being rebuilt
    if (g.get('frames') or {}).get('status') == 'ready' and not guide.checked(g):
        return 'checking', None, False   # release 1: the layout is with its fresh checker
    if _card_waits(g) or _ready_to_shoot(g):
        return 'chat', None, False   # a card waits in the chat: the still, or the word to make the take
    if _video_waits(g):
        return 'video', None, False   # release 4: the still is approved and the words are written: only the layout video is awaited
    if _still_due(g):
        return 'still', None, False   # release 4: its first frame is ready, its still can be ordered
    return 'making', None, False


def answerable(session, plan, take_rows, shot_id, job, now=None):
    """A take the operator can be asked about now: the newest ready video of a shot that waits for their answer."""
    sh = next((sh for _, sh, _, _ in video_shots(plan, session) if sh['id'] == shot_id), None) if plan else None
    if not sh:
        return False
    state, shown, _ = _state(session, plan, sh, take_rows, now)
    return state in ('done', 'stale') and str(shown['id']) == str(job['id'])


def expected(session, plan, take_rows, now=None):
    """Every AI video shot of the accepted plan, in film order, with its state in plain words: [{kind 'take', id, name, state, job?}]."""
    out = []
    for g, sh, n, of in video_shots(plan, session):
        state, job, aside = _state(session, plan, sh, take_rows, now)
        out.append({'kind': 'take', 'id': sh['id'], 'name': name_of(g, sh, n, of), 'state': STATE[state], **({'job': job} if job else {}), **({'aside': True} if aside else {})})
    return out


def complete(items):
    """The page of step 7 opens: every take is made, answered, or could not be made; a shot the assistant talks to the operator about in the chat, or
    one that waits for the cost limit, does not close it for the others."""
    return all(i['state'] in COMPLETE or i.get('aside') for i in items)


def status_line(items):
    """One short line of counts: 'AI video: 11 made, 4 being corrected, 1 waiting for you in the chat.'"""
    mine = [i['state'] for i in items]
    return (f"{W['step']}: " + ', '.join(f'{mine.count(STATE[s])} {STATE[s]}' for s in ORDER if STATE[s] in mine) + '.') if mine else ''


def coming(items, take_rows=()):
    """The shots that could not be made, listed apart: each with what the provider answered (design/223, R3)."""
    why = lambda sid: str((jobs_of(take_rows, sid) or [{}])[-1].get('error') or '')
    return [{'name': i['name'], 'kind_words': W['kind'], 'state': 'failed', 'note': ' '.join(x for x in (W['failed'], why(i['id'])) if x)} for i in items if i['state'] == STATE['failed']]


def say(lines, rows):
    """The one message the assistant posts with the link."""
    open_ = [l for l in lines if l.get('state') == 'open']
    more = (W['say_failed_one'] if len(rows) == 1 else W['say_failed'].format(n=len(rows))) if rows else ''
    if not open_:
        return ' '.join(x for x in (W['say_nothing'], more) if x)
    head = W['say_need_one'] if len(open_) == 1 else W['say_need'].format(n=len(open_))
    return '\n'.join([head] + [f"- {l['name']}" for l in open_] + [' '.join(x for x in (more, W['say_done']) if x)])


def item_id(session, job):
    """The id of a take's item and line: its job. A new video of the shot is a new item: an answer given to an older one is stale."""
    return f"take:{job['id']}"


def chat_text(line):
    """What the chat shows of a take's line: the place, how it was made, a new video that failed, a short take, what the operator said of the ones before."""
    t = line['takes'][-1]
    rows = [line['where'], t['how'], line.get('failed') or '', t['short']] + [x['rejected'] for x in line['takes'][:-1]]
    return '\n'.join('- ' + r for r in rows if r)


# ---------- the words in time ----------

def caption(session, gap, sh):
    """The words spoken during the shot, each with its start and end in seconds from the shot's start (the times `motion_brief` gives a drawn
    graphic: `gap_timing`'s words), and the rest of the sentence before and after them, to show in grey. None when the shot has no words or the
    film has no word times. A word is one unit as the narration's timing gives it; nothing here splits a word."""
    ws = (((session.get('source') or {}).get('gaps') or {}).get(gap['gap_id']) or {}).get('timing', {}).get('words') or []
    mine = [i for i, w in enumerate(ws) if sh['start_frame'] <= w['start_frame'] < sh['end_frame']]
    if not mine:
        return None
    fps, a, b, end = float(V._fps(session) or 25), mine[0], mine[-1], ('.', '?', '!', '।')
    pre, post, i = [], [], a - 1
    while i >= 0 and not ws[i]['text'].endswith(end):
        pre.insert(0, ws[i]['text'])
        i -= 1
    i = b
    while not ws[i]['text'].endswith(end) and i + 1 < len(ws):
        i += 1
        post.append(ws[i]['text'])
    pre, post = ' '.join(pre), ' '.join(post)
    if len(pre) > CONTEXT_CHARS:
        pre = '…' + pre[-CONTEXT_CHARS:].split(' ', 1)[-1]
    if len(post) > CONTEXT_CHARS:
        post = post[:CONTEXT_CHARS].rsplit(' ', 1)[0] + '…'
    return {'pre': pre, 'post': post, 'words': [{'t': w['text'], 's': round((w['start_frame'] - sh['start_frame']) / fps, 2), 'e': round((w['end_frame'] - sh['start_frame']) / fps, 2)} for w in ws[a:b + 1]]}


# ---------- the page's line of a shot ----------

def _frame(session, job_id, at):
    """The stored frame of a video nearest before `at` seconds (the last one when `at` is None), as a key; None when it has none."""
    frames = ((session.get('take_checks') or {}).get(str(job_id)) or {}).get('frames') or []
    if not frames:
        return None
    before = [f for f in frames if at is None or f['at_s'] <= at + 0.01]
    return (before[-1] if before else frames[0])['key']


def _beside(session, plan, gap, sh, take_rows):
    """What sits directly before and after the shot in the film, where the film holds a picture of it: inside the gap the neighbouring shot's own
    picture (a placed still; for an accepted take the frame the cut leaves from, before, and the frame it arrives at, after); at the gap's edges a
    footage picture of the clip there. Only ever shown to compare. design/223 (A3, SK: "pictures"): the shot before is shown by its last picture in
    the film, not its first (until then: its first frame; design/35 row 331).
    ponytail: a drawn graphic beside the shot has no single picture here; its frame sheet if SK wants one."""
    row = [s for g, s in V._accepted_shots(plan, session) if g['gap_id'] == gap['gap_id']]
    i = next(k for k, s in enumerate(row) if s['id'] == sh['id'])
    fps = float(V._fps(session) or 25)
    foot_before, foot_after = P.footage(session, gap)

    def shot_pic(other, words, end):
        sel, asset = (session.get('selections') or {}).get(other['id']) or {}, (session.get('assets') or {}).get(other['id']) or {}
        in_s = float(sel.get('in_s') or 0)
        frame = _frame(session, sel.get('job_id'), in_s + (other['end_frame'] - other['start_frame']) / fps if end else in_s) if sel.get('job_id') else None
        ref = (session.get('references') or {}).get(asset.get('reference_id') or '') or {}
        what = W['route_video'] if V.route_of(other) == 'video' else W['route_still'] if V.route_of(other) == 'still' else W['route_other']
        key, mark = (frame, str((sel.get('take') or {}).get('sha256') or '')) if frame else (ref.get('key'), str(ref.get('sha256') or ''))
        return {'_key': key, '_mark': mark, 'label': words.format(what=what)} if key else None
    far_before, far_after = V.across(plan, session, sh)   # SK, 23 Nov 2026 (release 4, V4): at the gap's edge, the shot of the touching gap
    before = shot_pic(row[i - 1], W['before_shot'], True) if i > 0 else shot_pic(far_before, W['before_shot'], True) if far_before else ({'_key': foot_before['key'], '_mark': str(foot_before.get('sha256') or ''), 'label': W['before_footage']} if foot_before else None)
    after = shot_pic(row[i + 1], W['after_shot'], False) if i + 1 < len(row) else shot_pic(far_after, W['after_shot'], False) if far_after else ({'_key': foot_after['key'], '_mark': str(foot_after.get('sha256') or ''), 'label': W['after_footage']} if foot_after else None)
    return ([{**before, 'role': 'before'}] if before else []), ([{**after, 'role': 'after'}] if after else [])


def _how(job, n, num):
    """How a video was made, in one line: the first take, or the version of which take."""
    req = job.get('request') or {}
    m = num.get(str(req.get('from_job') or ''))
    if not m:
        return W['how_first'] if n == 1 else W['how_again']
    return (W['how_copy'] if req.get('route') == 'copy' else W['how_remake'] if req.get('version') == 'remake' else W['how_edit']).format(m=m)


def _take(store, session, plan, sh, job, n, slot, num):
    """One take of a shot, for the page: its video (the page copy is made from `_key`), its length, where its place starts in it, its size and how
    it was made, and the operator's words about it. design/223: it has no check."""
    res = job.get('result') or {}
    secs = float((res.get('evidence') or {}).get('duration_seconds') or 0)
    try:
        in_s = float(V.take_in_point(V.load_json(store, job['request']['request_key']), job, None).get('in_s') or 0)   # the same figure the film uses
    except Exception:
        in_s = 0.0
    rv = _reviews(session, job)
    notes = str(rv[-1].get('notes') or '').strip() if _rejected(session, job) else ''
    return {'n': n, 'job': str(job['id']), 'label': W['take_label'].format(n=n), 'tab': W['take_label'].format(n=n), 'size': C.size_of(job), 'how': _how(job, n, num),
            'video': {'_key': res.get('key') or '', '_mark': str(res.get('sha256') or ''), 'code': '', 'label': W['take_label'].format(n=n), 'none': ''},
            'secs': f'{secs:.1f}', 'in_s': round(in_s, 2),
            'short': W['stale'] if _stale(session, plan, job) else W['short'].format(s=f'{secs:.1f}', slot=f'{slot:.1f}') if secs and secs < slot - 0.001 else '',
            'rejected': W['said'].format(words=notes) if notes else ''}


def line(store, session, plan, gap, sh, n, of, take_rows, now=None):
    """The page's line of an AI video shot (kind `take`): every video of the shot (the newest is the one to answer), the words in time, what sits
    before and after it, the picture the first take started from, and the answers: accept, or say what is wrong. A version is compared with the
    video the operator answered (`compare`: the two takes shown side by side, "Play both together"). No amount reaches the page."""
    fps, g = float(V._fps(session) or 25), (session.get('guides') or {}).get(sh['id']) or {}
    slot = (sh['end_frame'] - sh['start_frame']) / fps
    every = jobs_of(take_rows, sh['id'])
    js = [j for j in every if j.get('status') == 'ready']
    num = {str(j['id']): k for k, j in enumerate(js, 1)}
    takes = [_take(store, session, plan, sh, j, k, slot, num) for k, j in enumerate(js, 1)]
    cur, cur_job = takes[-1], js[-1]
    at = P._t(sh['start_frame'], fps)
    where = W['where'].format(start=at, end=P._t(sh['end_frame'], fps), secs=f'{slot:.1f}', gap=str(gap.get('title') or f"Gap {gap.get('gap_id')}"))
    prompt = str((g.get('take_prompt') or {}).get('prompt') or '')
    for t in takes:
        t['details'] = [[W['d_where'], [where, W['length'].format(s=t['secs'], slot=f'{slot:.1f}')]], [W['d_how'], [t['how'], W['how_size'].format(size=t['size'])]]] + ([[W['d_prompt'], [prompt[:1500]]]] if prompt else [])
    made = next((c for c in C.rows(g) if cur['job'] in [str(x) for x in c.get('jobs') or []]), None)   # the correction this video answers: it is compared with the video the operator answered
    was = num.get(str((made or {}).get('job_id') or (cur_job.get('request') or {}).get('from_job') or ''))
    failed = every[-1]['status'] in GONE and every[-1] is not cur_job

    def accept(t, j, choice, label):
        final = C.final(j)
        return {'label': label, 'choice': choice, 'act': 'select', 'take': t['n'] if choice == 'select' else cur['n'], 'needs_words': False, 'hint': '', 'go': '', 'prefill': '', 'need': '',
                'note': '' if final else W['paid'], 'say': (W['say_select'].format(n=t['n'], at=at) if final else W['say_copy'].format(n=t['n'])),
                'end': (W['end_select'].format(n=t['n'], at=at) if final else W['end_copy'].format(n=t['n'])), **({} if final else {'paid': True})}
    buttons, old_plan = [], _stale(session, plan, cur_job)   # a take made for an earlier plan cannot be accepted: the operator says what should change (a version stands on today's plan)
    if not old_plan:
        buttons.append(accept(cur, cur_job, 'select', W['select']))
    if True:
        buttons.append({'label': W['again'], 'choice': 'again', 'act': 'again', 'take': cur['n'], 'needs_words': True, 'hint': W['hint_again'], 'go': W['go_again'], 'prefill': '',
                        'need': W['need_words'], 'note': W['paid'], 'paid': True, 'say': W['say_again'].format(n=cur['n'], words='{words}'), 'end': W['end_again'].format(n=cur['n'], words='{words}')})
        if not old_plan and failed and C.can_resend(g, every):   # E9: the same request once more, on the operator's word, once
            buttons.append({'label': W['resend'], 'choice': 'resend', 'act': 'again', 'take': cur['n'], 'needs_words': False, 'hint': '', 'go': '', 'prefill': '', 'need': '', 'note': W['paid'],
                            'paid': True, 'say': W['say_resend'], 'end': W['end_resend']})
        for t, j in list(zip(takes, js))[:-1]:   # an earlier video may be used after all. SK, 22 Nov 2026: one click: the second question under the button asked the
            # same thing again, and the answer can be undone on the page (until then: asked once, D7; design/35 row 334)
            if not _stale(session, plan, j):
                buttons.append(accept(t, j, f"old:{t['n']}", W['select_old'].format(n=t['n'])))
    before, after = _beside(session, plan, gap, sh, take_rows)
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('key')), None)
    pics = before + [{'_key': (_rec(session, j).get('frames') or [{}])[0].get('key'), '_mark': str((j.get('result') or {}).get('sha256') or ''), 'label': W['frame'].format(n=k), 'role': 'frame', 'take': k}
                     for k, j in enumerate(js, 1)] + after \
        + [{'_key': _rec(session, j).get('sheet_key'), '_mark': str((j.get('result') or {}).get('sha256') or ''), 'label': W['sheet'].format(n=k), 'role': 'sheet', 'take': k} for k, j in enumerate(js, 1)] + ([{'_key': still['key'], '_mark': str(still.get('sha256') or ''), 'label': W['still'], 'role': 'still'}] if still else [])
    return {'kind': 'take', 'name': name_of(gap, sh, n, of), 'kind_words': W['kind'], 'ask': W['ask'], 'where': where, 'film_at': at, 'words': str(sh.get('narration') or ''),
            'caption': caption(session, gap, sh), 'takes': takes, 'pics': [p for p in pics if p.get('_key')], 'buttons': buttons, 'details': [],
            **({'compare': {'from': was, 'new': cur['n'], 'play': W['play_both']}} if was and was != cur['n'] else {}),
            **({'failed': W['failed_new'].format(why=str(every[-1].get('error') or '')).strip()} if failed else {})}


def recorded(ctx):
    """The takes answered earlier, for the page: each shot whose take is accepted into the film stays in the list with its decision and can be
    opened again; it has no buttons (its answer is changed in the chat)."""
    session, plan, out = ctx['session'], ctx['plan'], []
    rows = V.take_jobs(ctx['conn'], ctx['run'])
    for g, sh, n, of in video_shots(plan, session):
        sel = (session.get('selections') or {}).get(sh['id'])
        js = [j for j in jobs_of(rows, sh['id']) if j.get('status') == 'ready']
        if not sel or not any(str(j['id']) == str(sel.get('job_id')) for j in js):
            continue
        ln = line(ctx['store'], session, plan, g, sh, n, of, js)
        chosen = next(t for t in ln['takes'] if t['job'] == str(sel['job_id']))
        ln.update(buttons=[], takes=[chosen], pics=[p for p in ln['pics'] if p.get('take') in (None, chosen['n'])],
                  answer={'say': W['answered'].format(n=chosen['n'], at=ln['film_at']), 'against': False, 'act': 'select'})
        ln.pop('compare', None), ln.pop('failed', None)
        out.append({'key': f"pic:take-done:{sh['id']}", 'item': f"take-done:{sh['id']}", 'state': 'recorded', **ln})
    return out


# ---------- the answers ----------

def answer(conn, store, user, run, outputs, shot_id, take_rows, choice, quote, words):
    """One answer to a shot's video, from the page or the chat (design/223):
    `select`: accept. A video at the version size goes into the film; a 360p take is accepted and its full-size video ordered (it is shown before it
    goes in the film). `again`: the operator's words of what is wrong: kept as a correction; the assistant chooses its route (`corrections.send`).
    `old:n`: an earlier video after all. `resend`: the same request once more, after the provider failed, once.
    Nothing is made twice: a second accept of the same take, or an answer while a video of the shot is being made, is refused."""
    session = V.session_of(store, run, outputs)
    every = jobs_of(take_rows, shot_id)
    js = [j for j in every if j.get('status') == 'ready']
    V.need(js, f'{shot_id} has no take to answer now.')
    V.need(choice != 'reject', W['reject_retired'])
    V.need(not any(j['status'] in OPEN for j in every), C.W['being_made'])
    plan = V.current_plan(store, session)
    g = (session.get('guides') or {}).get(shot_id) or {}
    said = ' '.join(str(words or '').split())

    def decided(entry, quoted=''):   # requirement 4.13: each answer to a take is a decision of the operator in the run's log
        if conn is not None:
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'shot {shot_id}', 'rule': 'design/223 (step 7, a take answered)',
                                'entry': entry, 'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': quoted or quote, 'request_id': None})

    def accept(j, n, log):
        V.need(not _stale(session, plan, j), W['stale_refuse'])
        jid = str(j['id'])
        short = ((j.get('result') or {}).get('evidence') or {}).get('timing_matches_placement') is False
        note = P.W['against_note'] if short else ''   # a take shorter than its place: one click, a fixed note, and the log says so
        if C.final(j):
            if not note:
                V.review_take(conn, store, user, run, outputs, jid, 'accepted', '', '', quote)
            out = V.select_take(conn, store, user, run, outputs, jid, quote, note, note, None)
            decided(W[log].format(n=n) + (W['log_short'] if short else ''))
            return out
        V.need(g, W['no_guide'].format(shot=shot_id))
        V.need(not C.copied(g, j), C.W['already'])
        V.review_take(conn, store, user, run, outputs, jid, 'accepted', '', note, quote)
        s = V.session_of(store, run, outputs)
        c = C.copy(conn, store, user, run, s, shot_id, j, quote)
        V.save_session(store, run, s)
        decided(W['log_copy'].format(n=n))
        return {'shot_id': shot_id, 'ordered': 'copy', **({'waiting': c['waiting']} if c.get('waiting') else {})}
    if choice == 'select':
        return accept(js[-1], len(js), 'log_select')
    if choice == 'again':
        V.need(said, C.W['need_words'])
        V.need(g, W['no_guide'].format(shot=shot_id))
        out = V.review_take(conn, store, user, run, outputs, str(js[-1]['id']), 'rejected', said, '', quote)
        s = V.session_of(store, run, outputs)
        C.ask(s, shot_id, js[-1], said, user)
        V.save_session(store, run, s)
        decided(W['log_again'].format(n=len(js)), said)
        return out
    if choice == 'resend':
        C.resend(conn, store, user, run, session, shot_id, every)
        V.save_session(store, run, session)
        decided(W['log_resend'])
        return {'shot_id': shot_id, 'ordered': 'resend'}
    if choice.startswith('old:'):
        k = int(choice[4:]) if choice[4:].isdigit() else 0
        V.need(1 <= k < len(js), f'{shot_id}: there is no earlier take {choice[4:]}.')
        return accept(js[k - 1], k, 'log_old')
    raise ValueError(f'Not an answer to a take: {choice!r}.')


def held_due(session, plan):
    """Release 2, the critic's point 2: a held layout the operator answered with "Change the shot": their words, and what the assistant does with
    them, until a new scene of the shot is sent or the plan no longer makes it an AI video shot."""
    from . import guide
    out = []
    for g, sh, n, of in video_shots(plan, session) if plan else []:
        e = (session.get('guides') or {}).get(sh['id']) or {}
        if e.get('change') and sh['id'] not in (session.get('selections') or {}):
            out.append(W['held_change'].format(name=name_of(g, sh, n, of), shot=sh['id'], n=guide.MAX_ROUNDS, words=e['change']['words']))
    return ' '.join(out)
