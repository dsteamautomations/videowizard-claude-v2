"""design/222 (SK, 19 Nov 2026): step 7, AI video, on the decisions page.

The finished takes are judged on the page, all together, once every take of the film is made and checked; what is decided before a take is paid
for (the shot's layout drawing, the still, the word to make the first take, "send it again") stays a card in the chat. Claude checks each take
from frames the server takes from it (one every half second, the first and the last, and the sheet at four a second); the server measures the
rest (real footage, the length, the first frame, one continuous shot). "Make another" on the page is the operator's word for one more take.

One flow, two front ends: the page's line and the chat's item are built here from the same words; every answer goes through the functions the
chat already calls (`visuals_stage.review_take`, `select_take`, `guide.shoot`). No amount of money is in any word of the page."""
from datetime import timedelta

from . import pictures as P, runlog, visuals_stage as V

LOOK_MINUTES = P.PICTURE_LOOK_MINUTES   # a take whose check never comes is offered as "not checked" after this long (the number of step 6)
OPEN = ('queued', 'running', 'submitted', 'storage_pending', 'submission_unknown')   # the critic's S9: an unknown submission is recovered or resolved; it is not "could not be made"
CONTEXT_CHARS = 60   # the rest of a sentence shown in grey before and after a shot's own words, at most

W = {
    'step': 'AI video', 'kind': 'An AI video take', 'ask': 'Is this take right for the film?',
    'take_label': 'Take {n}', 'tab_rejected': 'Take {n}, rejected',
    'select': 'Select', 'again': 'Make another', 'reject': 'Reject', 'select_old': 'Use take {n} after all',
    'say_select': 'Take {n} selected. It goes in the film at {at}.', 'say_select_why': 'Take {n} selected. It goes in the film at {at}. Your reason: "{words}"',
    'say_reject': 'Take {n} rejected. No new take is ordered; Claude asks you in the chat what happens to the shot. Your words: "{words}"',
    'say_again': 'Take {n} rejected. Another take is ordered when you say done; Claude says its price in the chat then. Your words: "{words}"',
    'end_select': 'Take {n} selected, in the film at {at}.', 'end_reject': 'Take {n} rejected: "{words}"', 'end_again': 'Take {n} rejected, another take ordered: "{words}"',   # the end card's short rows
    'hint_reject': 'What is wrong with it?', 'go_reject': 'Reject with these words', 'need_words': 'Write what is wrong first.',
    'hint_again': 'What should change in the next take?', 'go_again': 'Make another with these words', 'need_again': 'Write what should change first. The next take is made from these words.',
    'again_paid': 'A new take is paid. Its price is said in the chat when you say done; nothing is ordered before that.',
    'no_more': 'No further take is made from this camera: two were made. After this rejection Claude asks you in the chat: cut the shot, another angle, or leave it out.',
    'no_more_cap': 'No further take can be ordered: the cost limit of this film is reached. Only the owner can change it.',
    'hint_why': 'The check did not pass it. Why is it right for the film all the same?', 'hint_why_none': 'It was not checked. Why is it right for the film?',
    'hint_why_short': 'It is shorter than its place in the film. Why is it right for the film all the same?',
    'hint_why_old': 'You rejected take {n} earlier, and its check did not pass. Why use it after all?', 'old_ask': 'You rejected take {n} earlier. Use it in the film after all?',
    'go_why': 'Select it with this reason', 'need_why': 'Write your reason first. It is kept with the film.', 'back': 'Go back',
    'rejected': 'Rejected. You said: {words}', 'rejected_bare': 'Rejected. You said no, with no words.',
    'short': 'The take is {s} s; its place in the film is {slot} s.',
    'stale': 'This take was made for an earlier plan of the film and cannot be used: make another, or reject it.',
    'stale_refuse': 'This take was made for an earlier plan of the film and cannot be selected: make another, or reject it.',
    'where': 'In the film at {start} to {end} ({secs} s) · {gap}', 'length': 'The take is {s} s; its place in the film is {slot} s.',
    'before_shot': 'The shot before, {what}.', 'after_shot': 'The shot after, {what}.', 'before_footage': 'Your footage before this shot.', 'after_footage': 'Your footage after this shot.',
    'route_video': 'an AI video take', 'route_still': 'a still picture', 'route_other': 'a made shot',
    # the check
    'check_pass': 'Check passed', 'check_fail': 'Check:', 'measured': '{line}: {seen}. Measured by the server.',
    'late': "Not checked: Claude's check did not come within {m} minutes. Judge it by eye.", 'unopened': 'Not checked: Claude could not open its frames. Judge it by eye.',
    'no_frames': 'Not checked: its frames could not be made. Judge it by eye.', 'none': 'Not checked. Judge it by eye.',
    'by': 'Claude looked at {n} frames of this take (one every half second, the first and the last), the sheet at four a second and the start picture, against {k} lines. '
          'The server measured the rest: real footage, the length, the first frame, one continuous shot.',
    'not_judged': 'Not judged: how things move between the frames. Play the take.',
    'd_where': 'Where it sits in the film', 'd_prompt': 'How the take was asked for', 'd_how': 'How it was made',
    'how': 'The video AI made it as an edit of the guide, started from the approved still.', 'how_n': 'Take {n} of this shot.',
    'still': 'The picture the take started from', 'frame': 'Take {n}',
    # the step's sentences
    'say_need': '{n} takes need your answer:', 'say_need_one': '1 take needs your answer:', 'say_done': 'Then say done here.', 'say_nothing': 'Nothing waits for you on the page now.',
    'say_failed': '{n} could not be made: they are listed apart.', 'say_failed_one': '1 could not be made: it is listed apart.',
    'summary': '{n} to answer.', 'note': 'Answer each take, then say done in the chat.', 'nothing': 'Nothing waits for you now.',
    'failed': 'It could not be made. Claude tells you in the chat what happens to it.',
    'page_later': 'The page opens when every take is made and checked.',
    'count': '{n} of {m} AI video shots are on this page.',   # fix set (f), SK 20 Nov 2026
    'page_now': ('Every take is made and checked: the operator answers them on the page, in one visit: run `vw visuals page` instead; ask here only where the page '
                 'cannot be shown. '),
    'help': ['Each shot on the left has one take to judge. Play it, then select it for the film, ask for another with your words, or reject it. Answer in any order, then say done in the chat.',
             'Claude checked each take first, from frames of it. "Check passed", or the first thing it found; "Go to 5 s" jumps the player to that second. The check marks problems; it never decides.',
             'Under the shot\'s name are the words spoken during it; the word being spoken is marked as the take plays. No sound is played.',
             '"See it in the film" shows what comes before and after the shot, only to compare. "Details" has everything else about the take.',
             'A shot that has two takes shows them as two tabs. A take answered earlier stays in the list; to change its answer, say so in the chat.',
             '"Make another" orders one more take, made from your words. It is paid; its price is said in the chat when you say done.',
             'This page opens when every take of the film is made and checked.'],
    # Claude's check: the refusals and the duty
    'look_gone': '{name}: it is not a take waiting for its check now (made again, answered, or set aside): list them again (`vw visuals pictures --looks`).',
    'looks_due': '{n} take(s) wait for Claude\'s check: run `vw visuals pictures --looks`; a `vw-take-look` helper judges about three takes.',
    'looks_then': 'The rows of kind `take` are video takes: give them to `vw-take-look` helpers, about three takes each (`how_take` says how a take is judged from its frames); they send their own files.',
    'rejected_do': ('{name} ({shot}): its take was rejected ("{words}") and no new take is ordered{why}: ask the operator what happens to the shot: '
                    'cut it into shorter shots, another angle, or leave it out; a new take after that is asked with its card.'),
    'rejected_cap': ' (the cost limit refused the take ordered on the page: tell the operator the spend; only the owner can change the limit)',
    'order_log': 'another take ordered on the page: {secs} s, about ₹{inr}',
    'log_select': 'take {n} selected', 'log_reject': 'take {n} rejected, no new take ordered', 'log_old': 'take {n} selected after all', 'log_cancel': 'the take ordered on the page withdrawn',
    'no_guide': '{shot} has no guide: another take cannot be ordered here. Reject it, and Claude asks you in the chat what happens to the shot.',
    'video_none': 'The take cannot be played here: these are its frames, in order.',
    'sheet': 'Take {n}: its frames, four a second',
    # "Make another": what the assistant does after done, and the one line it says
    'again_do': ('{name} ({shot}): the operator ordered another take on the page with these words: "{words}". Say what caused the fault, in the server\'s order '
                 '(`vw guide cause --shot {shot} --cause still|guide|words|model --notes "…" --fix "…"`), change that one thing, then `vw guide shoot --shot {shot}`: '
                 'the operator\'s word is given, ask nothing more. If the cause is the still or the layout, its card comes first; if it is the model\'s own limit, no take is made.'),
    'ordered': '{n} new take{s} {are} ordered: {secs} s, about ₹{inr}.', 'ordered_how': 'Say this line to the operator as it is and ask nothing with it.',
    'again_word': 'Make another: {words}',
    'answered': 'Take {n} selected. It is in the film at {at}.',
}
PAGE = {   # layout.words.takes: the page's chrome (the page holds no words of its own)
    'todo': 'Needs your answer', 'answered_head': 'Answered earlier', 'coming': 'Could not be made', 'nothing': W['nothing'], 'state_open': 'needs your answer',
    'against': 'Against the check', 'done': {'select': 'Selected', 'reject': 'Rejected', 'again': 'Another ordered'},
    'check_pass': W['check_pass'], 'more': 'See all {n}', 'seek': 'Go to {s} s', 'words_label': 'The words spoken during this shot',
    'film': 'See it in the film', 'film_head': 'In the film', 'before': 'Before this shot', 'after': 'After this shot', 'this_take': 'This take',
    'compare_only': 'Shown to compare. Nothing here needs an answer.',
    'details': 'Details', 'd_check': 'The check', 'd_passed': 'The {n} lines it passed', 'd_still': W['still'],
    'undo': 'Undo', 'cancel': 'Cancel', 'close': 'Close', 'change_in_chat': 'To change this answer, say so in the chat.',
    'loading': 'Loading…', 'missing': 'Not available', 'video_bad': 'The take could not be played here. Tell the assistant in the chat.',
    'left_one': '1 answer still needed', 'left_many': '{n} answers still needed', 'left_note': 'Choose one from the list on the left.',
    'end_head': 'All answered', 'end_note': 'Go back to the chat and say done. This is what will happen then:', 'end_foot': 'Nothing is recorded or made before you say done.',
    'end_again': 'New takes ordered when you say done: {n}. Claude says their price in the chat then.',
    'end_reject': 'For a take rejected with no new one ordered, Claude asks you in the chat what happens to the shot.',
    'foot': '{n} of {m} answered.', 'foot_wait': 'When all are answered, say done in the chat. Nothing is recorded before that.', 'foot_done': 'Go back to the chat and say done.',
    'help': 'How this works', 'keys': 'Keys: the left and right arrows move between the shots. Escape closes what is open.'}

STATE = {'none': 'not started', 'chat': 'waiting for you in the chat', 'making': 'being made', 'checking': 'being checked by Claude', 'redo': 'being redone',
         'done': 'made and checked', 'answered': 'answered', 'failed': 'could not be made', 'stale': 'must be made again (the plan changed)'}
ORDER = ('done', 'answered', 'checking', 'making', 'redo', 'stale', 'chat', 'failed', 'none')   # the order of the counts in the line
COMPLETE = (STATE['done'], STATE['answered'], STATE['failed'], STATE['stale'])   # a take that could not be made never keeps the page closed; the critic's S4: nor one made for an earlier plan (it is on the page with Make another and Reject)


# ---------- the shots, their takes ----------

def video_shots(plan, session):
    """The accepted AI video shots in film order: (gap, shot, its number in the gap, the gap's count of shots)."""
    by_gap = {}
    for g, sh in V._accepted_shots(plan, session):
        by_gap.setdefault(g['gap_id'], []).append((g, sh))
    return [(g, sh, n, len(rows)) for rows in by_gap.values() for n, (g, sh) in enumerate(rows, 1) if V.route_of(sh) == 'video']


def name_of(gap, sh, n, of):
    """A shot's name is never its id: its title, else its gap's title and its number in the gap."""
    return str(sh.get('title') or (str(gap.get('title') or f"Gap {gap.get('gap_id')}") + (f', shot {n}' if of > 1 else '')))


def jobs_of(take_rows, sid):
    return [j for j in take_rows or [] if j.get('provider') == 'video' and j.get('unit') == sid]


def _rec(session, job):
    return (session.get('take_checks') or {}).get(str(job['id'])) or {}


def _reviews(session, job):
    return (session.get('reviews') or {}).get(str(job['id'])) or []


def _rejected(session, job):
    rv = _reviews(session, job)
    return bool(rv) and rv[-1].get('decision') == 'rejected'


def again_pending(g):
    """The operator's word for one more take, given on the page ("Make another") and not yet used by a take."""
    a = (g or {}).get('again')
    return a if a and not a.get('sent') else None


# ---------- Claude's check: which takes, when a take is offered ----------

def look_lines():
    """The lines Claude judges from frames: the five reading lines of a take made from a guide, each with an id from its words."""
    from .image_check import GUIDE_TAKE_LINES
    return [P._line(l['check'], l['pass_when']) for l in GUIDE_TAKE_LINES]


def looked(session, job):
    """Claude's look of this take as it is now (the same file), or None."""
    look = _rec(session, job).get('look') or {}
    return look if look and look.get('sha256') == (job.get('result') or {}).get('sha256') else None


def checkable(rec):
    """A take Claude can check: made from a guide, not set aside, with its frames and its sheet at four a second (the sheet is required)."""
    return bool(rec.get('guide') and not rec.get('blocked') and rec.get('frames') and rec.get('sheet_key'))


def offered(session, job, now=None):
    """A take is offered to the operator with its check recorded; or LOOK_MINUTES after Claude was first asked, as not checked; at once when it
    cannot be checked (its frames could not be made). Before the worker has written its record it is not offered (the gap of a take shown with no
    check lines), but never held for ever: LOOK_MINUTES after the take was made."""
    rec, now = _rec(session, job), now or P._now()
    if not rec:
        at = P._ts(job.get('updated_at'))
        return bool(at) and now - at >= timedelta(minutes=LOOK_MINUTES)
    if rec.get('blocked'):
        return False
    if not checkable(rec) or looked(session, job):
        return True
    at = P._ts(rec.get('asked_at'))
    return bool(at) and now - at >= timedelta(minutes=LOOK_MINUTES)


def _open_takes(session, plan, take_rows):
    """Each AI video shot's newest take when it is ready and waits for an answer: [(gap, shot, n, of, job)]."""
    out = []
    for g, sh, n, of in video_shots(plan, session):
        js = jobs_of(take_rows, sh['id'])
        if js and js[-1].get('status') == 'ready' and sh['id'] not in (session.get('selections') or {}) and not _rejected(session, js[-1]):
            out.append((g, sh, n, of, js[-1]))
    return out


def due(session, plan, take_rows):
    """The takes that wait for Claude's check: checkable, no look of their file yet. One past the time-out stays due: a look that comes before
    the operator's answer replaces "not checked"."""
    return [row for row in _open_takes(session, plan, take_rows) if checkable(_rec(session, row[4])) and not looked(session, row[4])]


def asked(session, plan, take_rows, now=None):
    """The first time Claude is asked to check a take it gets `asked_at`: the time-out counts from then, never from when the take was made.
    True when the session changed (the caller saves it)."""
    changed = False
    for *_, j in due(session, plan, take_rows):
        rec = session['take_checks'][str(j['id'])]
        if not rec.get('asked_at'):
            rec['asked_at'] = (now or P._now()).isoformat()
            changed = True
    return changed


def waits_words(session, plan, take_rows):
    n = len(due(session, plan, take_rows))
    return W['looks_due'].format(n=n) if n else ''


def listed(session, plan, take_rows):
    """The takes due, for `vw visuals pictures --looks`: each as a picture row of that list: `key` is the sheet at four a second, `inputs` the
    frames in order (each with its second) and the approved still the take started from; `request` is how the take was asked for."""
    out = []
    for g, sh, n, of, j in due(session, plan, take_rows):
        rec, guide_ = _rec(session, j), (session.get('guides') or {}).get(sh['id']) or {}
        still = next((s for s in guide_.get('stills') or [] if s.get('status') == 'approved' and s.get('key')), None)
        out.append({'ref': str(j['id']), 'sha10': str(j['result']['sha256'])[:10], 'kind': 'take', 'name': name_of(g, sh, n, of), 'shot_id': sh['id'], 'key': rec['sheet_key'],
                    'inputs': [{'ref': f"{f['at_s']:g} s", 'role': 'frame', 'at_s': f['at_s'], 'key': f['key']} for f in rec['frames']]
                              + ([{'ref': still['id'], 'role': 'still', 'key': still['key']}] if still else []),
                    'request': str((guide_.get('take_prompt') or {}).get('prompt') or ''), 'seconds': float(((j.get('result') or {}).get('evidence') or {}).get('duration_seconds') or 0),
                    'lines': look_lines()})
    return out


def record(session, plan, take_rows, sent, who, at=None):
    """One take's look, line by line. None when recorded; else the refusal (nothing recorded). The scorecard `select_take` reads is rebuilt from
    the server's measured lines and Claude's."""
    from . import guide_worker
    jid = str(sent.get('ref') or '')
    row = next((r for r in due(session, plan, take_rows) if str(r[4]['id']) == jid), None)
    name = name_of(*row[:4]) if row else jid
    if not row or not sent.get('sha10') or str(row[4]['result']['sha256'])[:10] != str(sent.get('sha10'))[:10]:
        return W['look_gone'].format(name=name)
    want = look_lines()
    fault = P._fault(name, want, sent)
    if fault:
        return fault
    rec = session['take_checks'][jid]
    why = ' '.join(str(sent.get('not_checked') or '').split())
    got = {a.get('id'): a for a in sent.get('lines') or [] if isinstance(a, dict)}
    num = lambda v: round(float(v), 1) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    rec['look'] = {'who': who, 'at': at or P._now().isoformat(), 'sha256': row[4]['result']['sha256'],
                   **({'not_checked': why} if why else {'lines': [{'id': w['id'], 'check': w['check'], 'pass': got[w['id']]['pass'], 'seen': ' '.join(str(got[w['id']].get('seen') or '').split()),
                                                                **({'at_s': num(got[w['id']].get('at_s'))} if num(got[w['id']].get('at_s')) is not None else {})} for w in want]})}
    rec['scorecard'], rec['watch'] = guide_worker.scorecard(rec.get('code_lines') or [], None if why else {'lines': rec['look']['lines']})
    rec['not_read'] = bool(why)
    return None


# ---------- each shot's state, the line of counts, when the page opens ----------

def _stale(plan, job):
    """A take shot for another plan than the film has now: `select_take` refuses it. A take queued before design/222 names no plan and is read as before."""
    req = job.get('request') or {}
    return bool(req.get('plan_digest')) and req['plan_digest'] != V.digest(plan)


def _ready_to_shoot(g):
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('guide_sha256') == g.get('sha256')), None)
    return bool((g.get('render') or {}).get('status') == 'ready' and still and still.get('overlay_key') and g.get('take_prompt'))


def _card_waits(g):
    """A card of this shot waits in the chat: its layout drawing, or a still to approve."""
    d = g.get('drawing') or {}
    return (d.get('status') == 'proposed' and d.get('sha256') == g.get('sha256')) \
        or any(s.get('status') == 'candidate' and s.get('guide_sha256') == g.get('sha256') and s.get('key') for s in g.get('stills') or [])


def question_open(session, shot_id):
    """E18: an open question on the shot: nothing is made from it, and its take is not selected, until the operator answers it in the chat."""
    return bool((session.get('questions') or {}).get(shot_id))


def answerable(session, shot_id, job, now=None):
    """A take the operator can be asked about now: offered (its check is there, or timed out) and no question open on its shot."""
    return offered(session, job, now) and not question_open(session, shot_id)


def _state(session, plan, sh, take_rows, now):
    """(state, the take shown, aside). `aside`: the shot does not keep the page closed for the others: one of its takes was already answered by the
    operator (a rejection: its remake, its cards and what happens to it go on beside the page), or a question on it waits in the chat."""
    sid = sh['id']
    if sid in (session.get('selections') or {}):
        return 'answered', None, False
    js, g = jobs_of(take_rows, sid), (session.get('guides') or {}).get(sid) or {}
    if js:
        j, seen = js[-1], any(_rejected(session, x) for x in js)
        if j['status'] in OPEN:
            return ('redo' if seen else 'making'), None, seen
        if j['status'] != 'ready':
            return 'failed', None, seen
        if _rec(session, j).get('blocked'):
            return 'chat', None, seen   # "send the same request once more?" is asked in the chat
        if _rejected(session, j):
            return ('redo' if again_pending(g) and not _card_waits(g) else 'chat'), None, True   # E30: a remake whose still or layout card waits reads "waiting for you in the chat"
        if question_open(session, sid):
            return 'chat', None, True
        if _stale(plan, j):
            return 'stale', j, seen
        return ('done' if offered(session, j, now) else 'checking'), j, seen
    if not g:
        return 'none', None, False
    if _card_waits(g) or _ready_to_shoot(g):
        return 'chat', None, False   # a card waits in the chat: the layout drawing, the still, or the word to make the take
    return 'making', None, False


def expected(session, plan, take_rows, now=None):
    """Every AI video shot of the accepted plan, in film order, with its state in plain words: [{kind 'take', id, name, state, job?}]."""
    out = []
    for g, sh, n, of in video_shots(plan, session):
        state, job, aside = _state(session, plan, sh, take_rows, now)
        out.append({'kind': 'take', 'id': sh['id'], 'name': name_of(g, sh, n, of), 'state': STATE[state], **({'job': job} if job else {}), **({'aside': True} if aside else {})})
    return out


def complete(items):
    """The page of step 7 opens: every take is made and checked, answered, or could not be made. The second critic's point 1: a shot one of whose
    takes the operator already answered (a rejection, its remake under way) does not close the page for the takes still unanswered."""
    return all(i['state'] in COMPLETE or i.get('aside') for i in items)


def status_line(items):
    """One short line of counts: 'AI video: 11 made and checked, 4 being made, 1 waiting for you in the chat.'"""
    mine = [i['state'] for i in items]
    return (f"{W['step']}: " + ', '.join(f'{mine.count(STATE[s])} {STATE[s]}' for s in ORDER if STATE[s] in mine) + '.') if mine else ''


def coming(items):
    return [{'name': i['name'], 'kind_words': W['kind'], 'state': 'failed', 'note': W['failed']} for i in items if i['state'] == STATE['failed']]


def say(lines, rows):
    """The one message the assistant posts with the link."""
    open_ = [l for l in lines if l.get('state') == 'open']
    more = (W['say_failed_one'] if len(rows) == 1 else W['say_failed'].format(n=len(rows))) if rows else ''
    if not open_:
        return ' '.join(x for x in (W['say_nothing'], more) if x)
    head = W['say_need_one'] if len(open_) == 1 else W['say_need'].format(n=len(open_))
    return '\n'.join([head] + [f"- {l['name']}" for l in open_] + [' '.join(x for x in (more, W['say_done']) if x)])


# ---------- the check as the page and the chat say it ----------

def check_view(session, job, now=None):
    """One short line: "Check passed", or "Check:" and the faults in full (the server's measured lines first, then Claude's), each with the second
    it was seen; or why it was not checked. Who checked, what frames cannot show and the lines that passed are for Details."""
    rec, look = _rec(session, job), looked(session, job)
    cap = lambda t: str(t)[:1].upper() + str(t)[1:]
    code = [l for l in rec.get('code_lines') or [] if isinstance(l.get('pass'), bool)] if rec.get('guide') else []
    read = [] if not look or look.get('not_checked') else look['lines']
    older = [l for l in rec.get('lines') or [] if isinstance(l.get('pass'), bool)] if not rec.get('guide') else []   # a take checked before this design keeps the lines it has
    faults = [{'text': W['measured'].format(line=cap(l['check']), seen=l.get('seen') or ''), 'at_s': l.get('at_s')} for l in code if not l['pass']] \
        + [{'text': f"{cap(l['check'])}: {l.get('seen') or ''}", 'at_s': l.get('at_s')} for l in read + older if not l['pass']]
    passed = [cap(l['check']) + (f": {l['seen']}" if l.get('seen') else '') for l in code + read + older if l['pass']]
    state = 'fail' if faults else 'pass' if (read or older) else 'not_checked'
    late = not look and checkable(rec) and bool(rec.get('asked_at'))
    head = (W['check_fail'] if state == 'fail' else W['check_pass'] if state == 'pass' else W['unopened'] if look and look.get('not_checked')
            else W['no_frames'] if rec and not checkable(rec) else W['late'].format(m=LOOK_MINUTES) if late else W['none'])
    return {'state': state, 'head': head, 'faults': faults, 'by': W['by'].format(n=len(rec.get('frames') or []), k=len(read)) if read else '',
            'not_judged': W['not_judged'] if rec.get('guide') else '', 'passed': passed}


def item_id(session, job):
    """The id of a take's item and line: the job and a mark of its check as it is shown (its state, its faults). The second critic's point 2: an answer
    given to the take as it was shown before its check arrived, or changed, is stale."""
    import hashlib
    v = check_view(session, job)
    return f"take:{job['id']}:" + hashlib.sha1('|'.join([v['state'], v['head']] + [f['text'] for f in v['faults']]).encode('utf-8')).hexdigest()[:8]


def chat_text(line):
    """What the chat shows of a take's line: the place, the check's line and its faults, a short take, why no further take."""
    t = line['takes'][-1]
    c = t['check']
    rows = [line['where'], c['head'] if c['state'] != 'fail' else ''] + [(c['head'] + ' ' if i == 0 else '') + f['text'] + (f" (at {f['at_s']:g} s)" if f.get('at_s') is not None else '') for i, f in enumerate(c['faults'][:6])] \
        + [t['short']] + [x['rejected'] for x in line['takes'][:-1]]
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

def _beside(session, plan, gap, sh, take_rows):
    """What sits directly before and after the shot in the film, where the film holds a picture of it: the neighbouring shot's own picture inside
    the gap (a selected take's first frame, a placed still); at the gap's edges a footage picture of the clip there. Only ever shown to compare.
    ponytail: a drawn graphic beside the shot has no single picture here; its frame sheet if SK wants one."""
    row = [s for g, s in V._accepted_shots(plan, session) if g['gap_id'] == gap['gap_id']]
    i = next(k for k, s in enumerate(row) if s['id'] == sh['id'])
    foot_before, foot_after = P.footage(session, gap)

    def shot_pic(other, words):
        sel, asset = (session.get('selections') or {}).get(other['id']) or {}, (session.get('assets') or {}).get(other['id']) or {}
        frames = ((session.get('take_checks') or {}).get(str(sel.get('job_id'))) or {}).get('frames') or []
        ref = (session.get('references') or {}).get(asset.get('reference_id') or '') or {}
        what = W['route_video'] if V.route_of(other) == 'video' else W['route_still'] if V.route_of(other) == 'still' else W['route_other']
        key, mark = (frames[0]['key'], str((sel.get('take') or {}).get('sha256') or '')) if frames else (ref.get('key'), str(ref.get('sha256') or ''))
        return {'_key': key, '_mark': mark, 'label': words.format(what=what)} if key else None
    before = shot_pic(row[i - 1], W['before_shot']) if i > 0 else ({'_key': foot_before['key'], '_mark': str(foot_before.get('sha256') or ''), 'label': W['before_footage']} if foot_before else None)
    after = shot_pic(row[i + 1], W['after_shot']) if i + 1 < len(row) else ({'_key': foot_after['key'], '_mark': str(foot_after.get('sha256') or ''), 'label': W['after_footage']} if foot_after else None)
    return ([{**before, 'role': 'before'}] if before else []), ([{**after, 'role': 'after'}] if after else [])


def _take(store, session, plan, sh, job, n, slot, now):
    """One take of a shot, for the page: its video (the page copy is made from `_key`), its length, where its place starts in it, its check."""
    res = job.get('result') or {}
    secs = float((res.get('evidence') or {}).get('duration_seconds') or 0)
    try:
        in_s = float(V.take_in_point(V.load_json(store, job['request']['request_key']), job, None).get('in_s') or 0)   # the same figure the film uses
    except Exception:
        in_s = 0.0
    rv = _reviews(session, job)
    notes = str(rv[-1].get('notes') or '').strip() if _rejected(session, job) else ''
    return {'n': n, 'job': str(job['id']), 'label': W['take_label'].format(n=n), 'tab': (W['tab_rejected'] if _rejected(session, job) else W['take_label']).format(n=n),
            'video': {'_key': res.get('key') or '', '_mark': str(res.get('sha256') or ''), 'code': '', 'label': W['take_label'].format(n=n), 'none': ''},
            'secs': f'{secs:.1f}', 'in_s': round(in_s, 2),
            'short': W['stale'] if _stale(plan, job) else W['short'].format(s=f'{secs:.1f}', slot=f'{slot:.1f}') if secs and secs < slot - 0.001 else '',
            'rejected': (W['rejected'].format(words=notes) if notes else W['rejected_bare']) if _rejected(session, job) else '',
            'check': check_view(session, job, now)}


def _can_again(session, g, job):
    """One more take may be ordered from this camera: none of its takes was rejected before this one (the server makes at most two)."""
    from . import guide
    cam = next((t.get('camera') for t in g.get('takes') or [] if t.get('job_id') == str(job['id'])), None)
    return not [t for t in guide._rejected(session, g) if t.get('camera') == cam and t.get('job_id') != str(job['id'])]


def line(store, session, plan, gap, sh, n, of, take_rows, now=None, left_inr=None, price_inr_per_s=0.0):
    """The page's line of an AI video shot (kind `take`): every take of the shot (the newest is the one to answer), the words in time, what sits
    before and after it, the picture it started from, and the answers. `left_inr`: what the film's cost limit still allows; it only decides
    whether "Make another" is offered, and no amount reaches the page."""
    fps, g = float(V._fps(session) or 25), (session.get('guides') or {}).get(sh['id']) or {}
    slot = (sh['end_frame'] - sh['start_frame']) / fps
    js = [j for j in jobs_of(take_rows, sh['id']) if j.get('status') == 'ready' and not _rec(session, j).get('blocked')]
    takes = [_take(store, session, plan, sh, j, k, slot, now) for k, j in enumerate(js, 1)]
    cur, cur_job = takes[-1], js[-1]
    at = P._t(sh['start_frame'], fps)
    where = W['where'].format(start=at, end=P._t(sh['end_frame'], fps), secs=f'{slot:.1f}', gap=str(gap.get('title') or f"Gap {gap.get('gap_id')}"))
    prompt = str((g.get('take_prompt') or {}).get('prompt') or '')
    for t in takes:
        t['details'] = [[W['d_where'], [where, W['length'].format(s=t['secs'], slot=f'{slot:.1f}')]]] + ([[W['d_prompt'], [prompt[:1500]]]] if prompt else []) + [[W['d_how'], [W['how'], W['how_n'].format(n=t['n'])]]]
    faults = ' '.join(f['text'] for f in cur['check']['faults'])
    why = W['hint_why'] if cur['check']['state'] == 'fail' else W['hint_why_none'] if cur['check']['state'] != 'pass' else W['hint_why_short'] if cur['short'] else ''
    cap = left_inr is not None and float(g.get('seconds') or 0) * price_inr_per_s > left_inr + 1e-9
    more = bool(g) and _can_again(session, g, cur_job) and not cap   # no guide entry: no take can be ordered
    buttons = [] if _stale(plan, cur_job) else [   # a take made for an earlier plan cannot be selected
        {'label': W['select'], 'choice': 'select', 'act': 'select', 'take': cur['n'], 'needs_words': bool(why), 'hint': why, 'go': W['go_why'] if why else '', 'prefill': '',
         'need': W['need_why'], 'note': '', 'say': W['say_select_why' if why else 'say_select'].format(n=cur['n'], at=at, words='{words}'), 'end': W['end_select'].format(n=cur['n'], at=at)}]
    if more:
        buttons.append({'label': W['again'], 'choice': 'again', 'act': 'again', 'take': cur['n'], 'needs_words': True, 'hint': W['hint_again'], 'go': W['go_again'], 'prefill': faults,
                        'need': W['need_again'], 'note': W['again_paid'], 'say': W['say_again'].format(n=cur['n'], words='{words}'), 'end': W['end_again'].format(n=cur['n'], words='{words}')})
    buttons.append({'label': W['reject'], 'choice': 'reject', 'act': 'reject', 'take': cur['n'], 'needs_words': True, 'hint': W['hint_reject'], 'go': W['go_reject'], 'prefill': faults,
                    'need': W['need_words'], 'note': '' if more or not g else W['no_more_cap'] if cap and _can_again(session, g, cur_job) else W['no_more'], 'say': W['say_reject'].format(n=cur['n'], words='{words}'), 'end': W['end_reject'].format(n=cur['n'], words='{words}')})
    for t in takes[:-1]:   # an earlier, rejected take may be used after all: asked once when its check passed, with a typed reason when it did not
        ok = t['check']['state'] == 'pass' and not t['short']
        label = W['select_old'].format(n=t['n'])
        buttons.append({'label': label, 'choice': f"old:{t['n']}", 'act': 'select', 'take': t['n'], 'needs_words': not ok, 'hint': '' if ok else W['hint_why_old'].format(n=t['n']),
                        'go': '' if ok else W['go_why'], 'prefill': '', 'need': W['need_why'], 'note': '',
                        'say': W['say_select' if ok else 'say_select_why'].format(n=t['n'], at=at, words='{words}'), 'end': W['end_select'].format(n=t['n'], at=at), **({'sure': {'ask': W['old_ask'].format(n=t['n']), 'go': label, 'back': W['back']}} if ok else {})})
    before, after = _beside(session, plan, gap, sh, take_rows)
    still = next((s for s in g.get('stills') or [] if s.get('status') == 'approved' and s.get('key')), None)
    pics = before + [{'_key': (_rec(session, j).get('frames') or [{}])[0].get('key'), '_mark': str((j.get('result') or {}).get('sha256') or ''), 'label': W['frame'].format(n=k), 'role': 'frame', 'take': k}
                     for k, j in enumerate(js, 1)] + after \
        + [{'_key': _rec(session, j).get('sheet_key'), '_mark': str((j.get('result') or {}).get('sha256') or ''), 'label': W['sheet'].format(n=k), 'role': 'sheet', 'take': k} for k, j in enumerate(js, 1)] + ([{'_key': still['key'], '_mark': str(still.get('sha256') or ''), 'label': W['still'], 'role': 'still'}] if still else [])
    return {'kind': 'take', 'name': name_of(gap, sh, n, of), 'kind_words': W['kind'], 'ask': W['ask'], 'where': where, 'film_at': at, 'words': str(sh.get('narration') or ''),
            'caption': caption(session, gap, sh), 'takes': takes, 'pics': [p for p in pics if p.get('_key')], 'buttons': buttons, 'details': []}


def recorded(ctx):
    """The takes answered earlier, for the page: each shot whose take is selected stays in the list with its decision and can be opened again;
    it has no buttons (its answer is changed in the chat)."""
    session, plan, out = ctx['session'], ctx['plan'], []
    rows = V.take_jobs(ctx['conn'], ctx['run'])
    for g, sh, n, of in video_shots(plan, session):
        sel = (session.get('selections') or {}).get(sh['id'])
        js = [j for j in jobs_of(rows, sh['id']) if j.get('status') == 'ready']
        if not sel or not any(str(j['id']) == str(sel.get('job_id')) for j in js):
            continue
        ln = line(ctx['store'], session, plan, g, sh, n, of, [j for j in js if not _rejected(session, j) or str(j['id']) == str(sel.get('job_id'))])
        chosen = next(t for t in ln['takes'] if t['job'] == str(sel['job_id']))
        ln.update(buttons=[], takes=[chosen], pics=[p for p in ln['pics'] if p.get('take') in (None, chosen['n'])],
                  answer={'say': W['answered'].format(n=chosen['n'], at=ln['film_at']), 'against': chosen['check']['state'] == 'fail', 'act': 'select'})
        out.append({'key': f"pic:take-done:{sh['id']}", 'item': f"take-done:{sh['id']}", 'state': 'recorded', **ln})
    return out


# ---------- the answers ----------

def answer(conn, store, user, run, outputs, shot_id, take_rows, choice, quote, words):
    """One answer to a shot's take, from the page or the chat, through the functions the chat calls: Select (with the operator's reason when the
    check did not pass it, it was not checked or it is short); Reject (with their words; nothing is ordered); Make another (the rejection, and
    their word for one more take, kept on the shot until `guide.shoot` uses it); Use take n after all (an earlier, rejected take)."""
    session = V.session_of(store, run, outputs)
    js = [j for j in jobs_of(take_rows, shot_id) if j.get('status') == 'ready' and not _rec(session, j).get('blocked')]
    V.need(js, f'{shot_id} has no take to answer now.')
    job, jid = js[-1], str(js[-1]['id'])
    ev = (job.get('result') or {}).get('evidence') or {}
    short = ev.get('timing_matches_placement') is False
    plan = V.current_plan(store, session)
    def decided(entry, said):   # requirement 4.13: each answer to a take is a decision of the operator in the run's log
        if conn is not None:
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'shot {shot_id}', 'rule': 'design/222 (step 7, a take answered)',
                                'entry': entry, 'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': said or quote, 'request_id': None})
    if choice == 'select':
        V.need(not _stale(plan, job), W['stale_refuse'])
        held = check_view(session, job)['state'] != 'pass' or short
        if not held:   # nothing holds it: the accepted review carries the operator's click, no words
            V.review_take(conn, store, user, run, outputs, jid, 'accepted', '', '', quote)
        out = V.select_take(conn, store, user, run, outputs, jid, quote, words if held else '', words if held and short else '', None)
        decided(W['log_select'].format(n=len(js)), words)
        return out
    if choice == 'reject':
        out = V.review_take(conn, store, user, run, outputs, jid, 'rejected', words, '', quote)
        decided(W['log_reject'].format(n=len(js)), words)
        return out
    if choice == 'again':
        g = (session.get('guides') or {}).get(shot_id) or {}
        V.need(g, W['no_guide'].format(shot=shot_id))   # the second critic's point 10: before anything is saved
        V.need(_can_again(session, g, job), W['no_more'])
        out = V.review_take(conn, store, user, run, outputs, jid, 'rejected', words, '', quote)
        s = V.session_of(store, run, outputs)
        from . import guide
        s['guides'][shot_id]['again'] = {'job_id': jid, 'words': words, 'by': user['id'], 'by_name': user.get('name') or '', 'at': guide.now()}
        s['guides'][shot_id].pop('again_refused', None)
        V.save_session(store, run, s)
        if conn is not None:   # the order is a decision of the operator in the run's log, with its price (the amount is never on the page)
            secs = int(float(s['guides'][shot_id].get('seconds') or 0))
            runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f'shot {shot_id}', 'rule': 'design/222 (Make another, on the page)',
                                'entry': W['order_log'].format(secs=secs, inr=f"{secs * V.prices()['video_inr_per_s']:,.0f}"), 'by_kind': 'operator', 'by_name': user.get('name') or '',
                                'quote': words, 'request_id': None})
        return out
    if choice.startswith('old:'):
        k = int(choice[4:]) if choice[4:].isdigit() else 0
        V.need(1 <= k < len(js), f'{shot_id}: there is no earlier take {choice[4:]}.')
        old = js[k - 1]
        V.need(not _stale(plan, old), W['stale_refuse'])
        old_short = ((old.get('result') or {}).get('evidence') or {}).get('timing_matches_placement') is False
        oid, was = str(old['id']), list(_reviews(session, old))
        try:   # the second critic's points 4 and 5: the earlier take is selected and nothing else is written: the newer take gets no review (a shot with a
            # selection is not asked about again), and a refusal leaves the earlier take's reviews as they were
            if not words:
                V.review_take(conn, store, user, run, outputs, oid, 'accepted', '', '', quote)
            out = V.select_take(conn, store, user, run, outputs, oid, quote, words, words if old_short else '', None)
        except Exception:
            s = V.session_of(store, run, outputs)
            if (s.get('reviews') or {}).get(oid) != was:
                s['reviews'][oid] = was
                V.save_session(store, run, s)
            raise
        decided(W['log_old'].format(n=k), words)
        return out
    raise ValueError(f'Not an answer to a take: {choice!r}.')


def again_due(session, plan, take_rows):
    """What the assistant does for each take ordered on the page ("Make another") and not yet sent: the cause, the one change, then the take."""
    out = []
    for g, sh, n, of in video_shots(plan, session):
        a = again_pending((session.get('guides') or {}).get(sh['id']))
        if a and sh['id'] not in (session.get('selections') or {}) and not any(j['status'] in OPEN for j in jobs_of(take_rows, sh['id'])):
            out.append(W['again_do'].format(name=name_of(g, sh, n, of), shot=sh['id'], words=a['words']))
    return ' '.join(out)


def rejected_due(session, plan, take_rows):
    """The critic's S3: a shot whose newest take is rejected with no new one ordered: what the assistant asks the operator (the server says it, in
    the chat tool's next step and after the page's done)."""
    out = []
    for g, sh, n, of in video_shots(plan, session):
        js, guide_ = jobs_of(take_rows, sh['id']), (session.get('guides') or {}).get(sh['id']) or {}
        if not js or sh['id'] in (session.get('selections') or {}) or any(j['status'] in OPEN for j in js) or js[-1]['status'] != 'ready':
            continue
        if _rejected(session, js[-1]) and not again_pending(guide_) and not _rec(session, js[-1]).get('blocked'):
            words = str(_reviews(session, js[-1])[-1].get('notes') or '').strip()
            out.append(W['rejected_do'].format(name=name_of(g, sh, n, of), shot=sh['id'], words=words, why=W['rejected_cap'] if guide_.get('again_refused') else ''))
    return ' '.join(out)


def ordered(session, plan, price_inr_per_s):
    """The one line the chat says after done: how many new takes were ordered on the page, their length and the amount. Said, not asked (SK, D4a).
    The critic's S7: each order is counted once: it is marked `told` here (the caller saves the session)."""
    mine = [a for g, sh, n, of in video_shots(plan, session) for a in [again_pending((session.get('guides') or {}).get(sh['id']))] if a and not a.get('told')]
    secs = [int(float((session['guides'][sh['id']]).get('seconds') or 0)) for g, sh, n, of in video_shots(plan, session)
            if again_pending((session.get('guides') or {}).get(sh['id'])) and not session['guides'][sh['id']]['again'].get('told')]
    for a in mine:
        a['told'] = True
    return W['ordered'].format(n=len(secs), s='' if len(secs) == 1 else 's', are='is' if len(secs) == 1 else 'are', secs=sum(secs), inr=f'{sum(secs) * price_inr_per_s:,.0f}') if secs else ''
