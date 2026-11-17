"""design/211, part B: the reference sets of a v2 round. The facts of a thing, the request per kind, the views, the checks' lines,
the two goes of making, the looks at a set, the remake by rewrite.

STEP 0 (17 Nov 2026): this file is the contract's stub. Every name, signature and constant below is fixed by design/211 section 3;
part B fills the bodies. Nothing here is called for a round without `v == 2` (`visuals_stage.round_v2`). Parts A and C read only the
functions and constants named in design/211 section 4.

A refusal is a named constant (a format string): raise it with `visuals_stage.need(False, NAME.format(...))`; a test asserts the message.
"""

RECS = ('footage', 'clean', 'set', 'no_set', 'leave')
REC_VERDICT = {'footage': 'approve', 'clean': 'clean', 'set': 'approve', 'no_set': 'ignore', 'leave': 'ignore'}   # "Accept the proposals": a proposal as a step-1 answer
STEP1_VERDICTS = ('approve', 'clean', 'ignore')
RECOMMENDS = ('use', 'remake', 'doubt')   # the look at a set
REASON_CHARS = 300
FIRST_MAX = 3      # the sets of the first go
MAKES_MAX = 3      # a set is made at most this many times
STATES = (1, 'making', 'looking', 'rewrite', 2, 'complete')   # what visuals_stage._round_pass gives for a v2 round

# ---------- "what next" (design/211 section 3.9): the answer carries one of these as `then`; the tool prints it and adds nothing ----------

ROUND_POSTED = ('The round is posted for {n} things, {d} of them doubtful. Run `vw visuals page`: the operator answers step 1 there, in one visit; in the chat '
                '(`vw visuals next`) only where the page cannot be shown.')
GO1_MAKING = "Step 1 is recorded. The first {k} sets are being made (about ₹{x}); {r} more wait for the operator's word. Wait: `vw visuals status --wait 900`."
ALL_MAKING = '{k} set(s) are being made (about ₹{x}). Wait: `vw visuals status --wait 900`.'
SETS_LOOK = ('The sets are back. Look at them before the operator does: `vw visuals round --looks` lists them and fetches the pictures. Start `vw-set-look` helpers, '
             'about 5 sets each (with 5 sets or fewer, look yourself); each records its looks: `vw visuals round --looks <file>`. No set is shown to the operator '
             'before its look is recorded.')
SETS_PAGE = 'Every set has its look. Run `vw visuals page`: the operator judges the sets there, in one visit.'
REWRITE_DUE = ("{n} set(s) wait for your rewrite. For each, write the request again from the operator's words, the check and your look: out/round-rewrites.json, "
               'rows {{element_id, prompt}}. Send it: `vw visuals round --rewrite out/round-rewrites.json`. The sets are made then, not before.')
REWRITE_MAKING = '{n} set(s) are being made again (about ₹{x}). Wait: `vw visuals status --wait 900`.'
MERGE_ASK = 'The round is past step 1: nothing was made. {n} thing(s) are back with the operator as open lines. Run `vw visuals page`.'

# ---------- refusals ----------

REC_MISSING = '{eid}: give its proposal (`rec`): footage, clean, set, no_set or leave.'
REC_UNKNOWN = '{eid}: {rec!r} is not a proposal: footage, clean, set, no_set or leave.'
REC_NO_FRAME = '{eid}: the proposal {rec} needs a footage picture with a recorded look; it has none.'
REC_PERSON = '{eid} is a person a picture is made of: every such person gets a set, so the proposal is set.'
REASON_MISSING = '{eid}: give the reason of its proposal in one line, at most {max} characters.'
FIRST_TOO_MANY = '{n} rows are marked `first`: at most {max} sets are made in the first go.'
CLEAN_NO_FRAME = '{eid} has no footage picture: a clean set is made from one. Have a set made, or leave it out.'
SET_NO_LOOK = '{eid}: its set has no recorded look yet: it is not shown or answered before (`vw visuals round --looks`).'
LOOK_SET_UNKNOWN = '{eid}: {set} is not its set now (it was made again, or never made): list the sets to look at again (`vw visuals round --looks`).'
LOOK_PICTURES = '{eid}: every picture of the set needs its look; missing: {missing}.'
LOOK_VERDICT = '{eid}: the verdict of a look is pass, weak or fail, and the recommendation is use, remake or doubt.'
LOOK_SEEN = '{eid}: a look says in one line what was seen, at most {max} characters, and the recommendation gives its reason.'
LOOK_GOLDEN = '{eid}: the picture proposed as the starting picture is not a picture of this set.'
REST_NOT_NOW = 'The other sets are ordered once the first sets are back and have their look: not now.'
REST_NONE = 'No set waits to be ordered.'
REST_CAP = ('The other {n} sets need about ₹{x}, and ₹{spent} is spent of the ₹{cap} limit of this film: none was ordered. Leave some things out, or ask the '
            'owner to set another limit for this film.')
REWRITE_NOT_DUE = '{eid}: no rewrite is asked for it now.'
REWRITE_EMPTY = '{eid}: the rewritten request is empty.'
REWRITE_SAME = '{eid}: the request is the same as before: the same words would buy the same picture. Change it from the operator\'s words, the check and your look.'
MAKES_LIMIT = '{eid}: its set was made {max} times. Use one of these, add your own picture, or leave it out.'
MAKE_NO_QUOTE = "{eid}: making a set is paid: give the operator's words (`--quote`)."

# ---------- the facts of a thing (parts A, B and C read this) ----------


def thing_facts(plan, session, element):
    """What the plan says of one thing and where the film uses it (design/211 section 3.5): {'id', 'name', 'kind', 'identity', 'real_person',
    'description', 'requirements', 'sizes': [{'part', 'measure', 'value', 'unit', 'status'}], 'views': [three view names], 'signs': [str],
    'shots': [{'gap', 'shot', 'size', 'way'}] (every shot of all_scenes(gap) naming it, film order), 'shots_made' (those not footage),
    'closest' (the tightest size among them, '' when none), 'scene': {'gap', 'scene', 'place'} of its first shot, or None}."""
    raise NotImplementedError('design/211 part B: ref_sets.thing_facts')


def views_for(element, plan):
    """The three views of a thing's set, always three: [{'name': short label, 'ask': the sentence of that turn}]. The plan's required_views
    first (two that read the same are one), then the kind's own, never one already present. A person's pictures 1 (full length, front)
    and 3 (the face) are fixed."""
    raise NotImplementedError('design/211 part B: ref_sets.views_for')


def view_names(element):
    """The three view names of a thing, as `views_for` names them: for the helpers' brief and the labels of footage frames."""
    raise NotImplementedError('design/211 part B: ref_sets.view_names')


# ---------- the request and the checks ----------

def set_request(plan, run, session, element, row):
    """The whole request of one set of a v2 round (design/211 section 3.6), by kind: {'prompt', 'views': [{'name', 'ask'}], 'inputs':
    [{'ref', 'role': 'footage'|'drawing'|'photo', 'view'}], 'search': bool, 'lines': [{'check', 'weight', 'pass_when'}], 'parts': {'kind',
    'subject', 'description', 'requirements', 'sizes', 'material', 'signs', 'place', 'look', 'category', 'added', 'operator', 'views',
    'inputs', 'source': 'footage'|'web'}}. The server places the plan's words; `added` is the row's `prompt`; `operator` the latest of
    its `operator_words`."""
    raise NotImplementedError('design/211 part B: ref_sets.set_request')


def check_summary(session, ref):
    """One picture's check for the page: {'state': 'pass'|'fail'|'none', 'failed': [{'check', 'seen'}], 'error': str or None}."""
    raise NotImplementedError('design/211 part B: ref_sets.check_summary')


def set_facts(session, plan, eid, row):
    """What the page and the chat show of one made (or failed) set (design/211 section 3.7): {'pictures': [{'ref', 'n', 'view', 'check':
    check_summary, 'look': look or None}], 'inputs': [{'ref', 'role', 'view'}], 'from': 'footage'|'web', 'notes', 'sources': [{'url',
    'title'}], 'partial': {'made', 'asked', 'missing'} or None, 'rec': {'do', 'golden', 'reason'} or None, 'makes', 'makes_left',
    'asked': the operator's words of the last remake or None, 'history': [{'n', 'set', 'added', 'operator'}], 'changed': bool,
    'fail': {'cause', 'model', 'text'} or None}."""
    raise NotImplementedError('design/211 part B: ref_sets.set_facts')


# ---------- the passes of a v2 round ----------

def looks_due(store, run, outputs):
    """`GET /api/runs/{run_id}/visuals/round/looks`: the made sets with no complete look: {'sets': [{'element_id', 'name', 'set', 'facts':
    thing_facts, 'request', 'inputs': [{'ref', 'role', 'view', 'key'}], 'pictures': [{'ref', 'n', 'view', 'key', 'check'}], 'notes'}], 'then'}.
    The picture keys are the 1600 px copies (page_flow.sized)."""
    raise NotImplementedError('design/211 part B: ref_sets.looks_due')


def round_looks(store, user, run, outputs, sets, by):
    """`POST /api/runs/{run_id}/visuals/round/looks`: sets = [{'element_id', 'set', 'recommend', 'golden', 'reason', 'pictures': [{'ref',
    'view', 'verdict', 'seen'}]}]. Each picture gets its `look`; the row its `set_look`. Refuses LOOK_SET_UNKNOWN, LOOK_PICTURES,
    LOOK_VERDICT, LOOK_SEEN, LOOK_GOLDEN. Returns {'recorded': [eid], 'refused': {eid: message}, 'left': [eid], 'then'}."""
    raise NotImplementedError('design/211 part B: ref_sets.round_looks')


def round_rest(conn, store, user, run, outputs, quote):
    """The second go, on the operator's word: every set of `round['rest']` ordered, or none (REST_CAP). Refuses REST_NOT_NOW, REST_NONE.
    Returns {'pass', 'queued': [eid], 'errors': {eid: message}, 'cost_inr', 'then': ALL_MAKING}."""
    raise NotImplementedError('design/211 part B: ref_sets.round_rest')


def round_rewrite(conn, store, user, run, outputs, rows):
    """Claude's rewrite of the requests the operator sent back: rows = [{'element_id', 'prompt'}]. The earlier request goes to the row's
    `history`, the new one is stored, `rewrite_due` is cleared and the set is ordered. Refuses REWRITE_NOT_DUE, REWRITE_EMPTY,
    REWRITE_SAME. Returns {'pass', 'queued': [eid], 'errors': {eid: message}, 'cost_inr', 'then': REWRITE_MAKING}."""
    raise NotImplementedError('design/211 part B: ref_sets.round_rewrite')


def round_reopen(conn, store, user, run, outputs, eid, verdict, words, quote):
    """The operator's answer to a thing that came back after a second send of the round file (`reopened`): 'approve' orders its set
    (paid, their word), 'ignore' leaves it out. Returns {'element_id', 'queued': bool, 'pass', 'cost_inr', 'then'}."""
    raise NotImplementedError('design/211 part B: ref_sets.round_reopen')
