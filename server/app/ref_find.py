"""design/211, part A: finding the footage pictures. The digest of the clip analyses, trial frames, the look record, the search record.

STEP 0 (17 Nov 2026): this file is the contract's stub. Every name, signature and constant below is fixed by design/211 section 3;
part A fills the bodies. Nothing here is called for a round without `v == 2` (`visuals_stage.round_v2`). Parts B and C read only the
functions and constants named in design/211 section 4.

A refusal is a named constant (a format string): raise it with `visuals_stage.need(False, NAME.format(...))`; a test asserts the message.
"""

DIGEST_CONTRACT = 'vw2-refs-digest-v1'
TRIAL_SIDE, TRIAL_QUALITY = 640, 80   # a trial frame: a JPEG, long side at most, quality (page_flow.shrink)
TRIALS_PER_CALL = 8
TRIALS_PER_THING = 8
KEPT_PER_THING = 3
THINGS_PER_HELPER = 5
HELPERS = 6
LIMITS = {'trials_per_thing': TRIALS_PER_THING, 'kept_per_thing': KEPT_PER_THING, 'things_per_helper': THINGS_PER_HELPER, 'helpers': HELPERS}
SEEN_CHARS = 300   # a look's one line
VERDICTS = ('pass', 'weak', 'fail')
WHO = ('helper', 'assistant')
RESULTS = ('found', 'weak', 'none', 'not_searched')

FRAME_RULE = ('A frame is a good reference when the thing is whole, not covered, large enough to read, sharp, and its shape and size can be read. '
              'Weak: one of these fails and the thing is still recognised. Fail: the thing is not in the frame or cannot be recognised.')

# ---------- "what next" (design/211 section 3.9): the answer carries one of these as `then`; the tool prints it and adds nothing ----------

FIND_START = ('The references come next. Run `vw visuals digest`. Then find each thing in the footage: start `vw-reference-finder` helpers, about 5 things each, '
              'up to 6 at a time (with 5 things or fewer, do it yourself). Each takes trial frames (`vw visuals trial`), looks at them and records what it saw '
              '(`vw visuals look`).')
FIND_WORDS = ('This run has no digest of its footage, so the search is by words only: `vw visuals elements` names the likely clips. Every frame still needs a look '
              '(`vw visuals trial`, then `vw visuals look`). Tell the operator the footage was searched by words only.')
TRIAL_NEXT = 'Read each trial frame, then record what you saw: `vw visuals look --file <file>`. A trial frame is not a reference.'
LOOK_MORE = '{n} thing(s) recorded. {left} are not searched yet: {ids}.'
LOOK_ALL = ('Every thing is searched. Write out/reference-round.json, one row per thing (element_id, rec, reason; `prompt` only for what the plan does not say; '
            '`first` on three things of different kinds), and send it: `vw visuals round --file out/reference-round.json`.')

# ---------- refusals ----------

TRIAL_TOO_MANY = 'A call takes at most {max} trial frames; {n} were asked. Nothing was cut.'
TRIAL_LIMIT = '{max} trial frames were already taken for {eid}: choose among them (`vw visuals look`).'
TRIAL_UNKNOWN_CLIP = '{clip} at {at_s} s: not a clip of this run, or the time is outside it.'
LOOK_UNKNOWN_TRIAL = 'No trial frame {trial} was taken for {eid}: a look is recorded only for a frame that was fetched (`vw visuals trial`).'
LOOK_VERDICT = '{eid}: the verdict of a look is pass, weak or fail, not {verdict!r}.'
LOOK_SEEN = '{eid}: a look says in one line what was seen, at most {max} characters.'
LOOK_VIEW = '{eid}: a kept frame names its view.'
KEEP_FAIL = '{eid}: frame {trial} has the verdict fail: it cannot be kept.'
KEEP_LIMIT = '{eid}: at most {max} frames are kept for a thing, one per view.'
LOOK_NOTHING = '{eid}: give its looks, or the clips searched, or why it was not searched (`not_searched`).'
FRAME_NO_LOOK = '{fid} of {eid} has no recorded look: look at it first (`vw visuals trial`, then `vw visuals look`).'
NOT_SEARCHED = '{eid} has no search record: search the footage for it (`vw visuals look`), or record why it was not searched.'


def footage(store, run, outputs):
    """True when the run has at least one analysed clip (an `analysis` output, not excluded, contract clip-log-v1). A film with none
    skips the search: `round_frames` then asks for no search record."""
    raise NotImplementedError('design/211 part A: ref_find.footage')


def digest(store, run, outputs):
    """The digest of every analysed clip (design/211 section 3.1), built from the outputs `visuals_stage.prepare` reads and stored at
    `visuals_stage.key(run, 'digest.json')`; reused while its `stamp` is unchanged. Returns
    {'contract': DIGEST_CONTRACT, 'stamp', 'built_at', 'clips': [{'clip', 'name', 'duration_s', 'overview', 'light', 'entities': [...],
    'parts': [{'id', 'in_s', 'out_s', 'hero_s', 'grade', 'role', 'size', 'angle', 'action', 'uncertain', 'props', 'people', 'defects'}]}],
    'not_searched': [{'clip', 'name', 'reason'}]}."""
    raise NotImplementedError('design/211 part A: ref_find.digest')


def digest_answer(store, run, outputs):
    """What `GET /api/runs/{run_id}/visuals/digest` answers: {'digest', 'things': [ref_sets.thing_facts(...) + {'found': result or None}],
    'rule': FRAME_RULE, 'limits': LIMITS, 'then': FIND_START or FIND_WORDS}. The things are the elements the round takes (no graphic, no animal)."""
    raise NotImplementedError('design/211 part A: ref_find.digest_answer')


def trial_id(clip, at_s):
    """The id of a trial frame: 't' + sha1('<clip>:<at_s rounded to 0.1>')[:12]. The same moment is the same frame, for any thing."""
    raise NotImplementedError('design/211 part A: ref_find.trial_id')


def cut_trials(store, run, outputs, frames):
    """Before the run's lock: the frames [{element_id, clip, at_s}] cut as small JPEGs, one download per clip. Returns a list, one entry per
    frame in order: {'clip', 'at_s', 'jpg': bytes} or {'clip', 'at_s', 'error': str}. Writes nothing."""
    raise NotImplementedError('design/211 part A: ref_find.cut_trials')


def trial_record(store, user, run, outputs, frames, cut):
    """Under the run's lock: the cut frames stored (`<run id>/visuals/trials/<trial id>.jpg`) and recorded in
    `visuals_stage.key(run, 'trials.json')`: {'trials': {id: {'id', 'clip', 'at_s', 'key', 'sha256', 'elements': [eid], 'looks': {eid: look},
    'at', 'by'}}}. Returns {'trials': [{'id', 'clip', 'at_s', 'key', 'elements'}], 'failed': [{'clip', 'at_s', 'reason'}], 'left': {eid: n},
    'then': TRIAL_NEXT}. Refuses TRIAL_TOO_MANY, TRIAL_LIMIT, TRIAL_UNKNOWN_CLIP. A trial frame is never a reference."""
    raise NotImplementedError('design/211 part A: ref_find.trial_record')


def look_record(conn, store, user, run, outputs, things, by):
    """The looks of `vw visuals look` (design/211 section 3.3): things = [{'element', 'clips', 'note', 'not_searched'?, 'looks': [{'trial',
    'view', 'verdict', 'seen', 'keep'?, 'closest'?}]}]. Each look is stored on its trial frame; a `keep` row becomes a `frame` reference
    through `visuals_stage.add_reference`, with `view`, `look`, `weak`, `trial` on it; the search record goes to `session['found'][eid]`
    with the result the server decides. Returns {'recorded': [eid], 'refused': {eid: message}, 'results': {eid: result},
    'kept': {eid: [reference ids]}, 'left': [eid], 'then': LOOK_MORE or LOOK_ALL}. A refused thing does not stop the others."""
    raise NotImplementedError('design/211 part A: ref_find.look_record')


def round_frames(session, plan, eid, named):
    """Called by `visuals_stage.round_start` for every row of a v2 round: the thing's frames that have a look, in view order (`named`: the
    ids the row gives, or empty for all). Refuses FRAME_NO_LOOK and, when the run has footage, NOT_SEARCHED. Returns [reference ids]."""
    raise NotImplementedError('design/211 part A: ref_find.round_frames')


def frames_of(session, eid):
    """The thing's looked footage frames that are candidate or approved, in view order: [{'ref', 'view', 'verdict', 'seen', 'weak'}]."""
    raise NotImplementedError('design/211 part A: ref_find.frames_of')


def found_all(store, run, session, plan):
    """The search record of every thing, for the page and the chat: {eid: {'result', 'by', 'at', 'clips': count, 'clip_names': [first five],
    'not_searched': [clip names], 'note', 'closest': {'trial', 'key', 'view', 'seen'} or None, 'stale': bool}}. A thing with no record is absent."""
    raise NotImplementedError('design/211 part A: ref_find.found_all')


def fingerprint(element):
    """sha256 of the plan fields a search and a set rest on: name, kind, identity, description, requirements, required_views, size."""
    raise NotImplementedError('design/211 part A: ref_find.fingerprint')


def not_this(conn, store, user, run, outputs, eid, ref_id, quote):
    """The operator's "Not this picture": the frame is rejected with their words; the best other looked trial frame of the same view (pass
    before weak, never fail) is kept in its place, without a new search. Returns {'next': reference id or None}."""
    raise NotImplementedError('design/211 part A: ref_find.not_this')


def that_is_it(conn, store, user, run, outputs, eid, trial, quote):
    """The operator's "That is it" on the closest picture of a thing that was not found: the trial frame becomes a kept frame, weak.
    Returns {'ref': reference id}."""
    raise NotImplementedError('design/211 part A: ref_find.that_is_it')
