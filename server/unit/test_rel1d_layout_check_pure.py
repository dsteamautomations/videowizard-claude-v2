"""Release 1 (SK, 20 Nov 2026, "go ahead"): a layout is checked by a fresh checker. Seen on the first real step 7 (19 AI video shots): the
operator approved 19 layout drawings one at a time, then the fresh checkers failed 13 of the first 15, and each rebuilt layout came back as a
new card. `takes.starts` names the checkers as soon as the check frames are ready, and a shot whose check failed for a rebuilt scene; the
checker's verdict is the assistant's line in the run's log. Until 25 Nov 2026 the layout drawing's card was offered to the operator once the
check passed, and the still and a repair waited for their Yes; retired (A1): the check's pass opens the still, no card is made, the old
approval is refused by name (the new way's own tests: test_vw25_layout_card_pure.py). Without a database."""
import json
from pathlib import Path

from app import chat_flow as CF, guide as G, runlog as L, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_design222_takes_pure import NOW, RUN, USER as OP, held, plan, session, shot   # noqa: F401 (held: the fixture)
from test_guide_route_pure import OTHER, STILL_WORDS, frames_back, refused, scene, spec10, still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import USER, saved

ROOT = Path(__file__).resolve().parents[2]
START = 'Start now, together in one message: '
CHECK = 'the checkers of the guides of {ids} ({n}) (a fresh `vw-guide-check` helper each: its guide is rendered, and its still can be ordered, only after its check passes)'
# release 2, the critic's point 3: a shot to rebuild is named apart from a shot with no guide yet (until then both read "the writers of the scene descriptions of {ids} ({n})")
SCENES = ("the writers of the scene descriptions of {ids} ({n}), each rebuilt after its check or the operator's correction: read `vw guide status --shot S` first, "
          'it holds what must change')
STILLS = 'the stills of {ids} ({n}), each ordered with `vw guide still --shot S --file still.json`'
CAN_ORDER = 'first frame ready: the still can be ordered'


def film(take_film):
    store, conn = take_film
    s = saved(store)
    s['round'] = {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}
    V.save_session(store, NEW, s)
    return store, conn


def said(store):
    s = saved(store)
    return T.starts(s, V.current_plan(store, s), [])


def state(store):
    s = saved(store)
    return [i['state'] for i in T.expected(s, V.current_plan(store, s), [])]


def cards(store, conn):
    s = saved(store)
    ctx = {'session': s, 'plan': V.current_plan(store, s), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    return CF._layout_items(ctx)   # VW-25 issue 14: their own function. Until 25 Nov 2026 also a card for a layout that passed ('shot-drawing:'); retired (A1): only a held layout has one


def verdict(store, conn, sha, ok):
    return G.verdict(conn, store, OTHER, NEW, [], 'VS1', sha, ok, [{'look': 'nothing floats', 'pass': ok, 'where': 'the brush, above the board', 'fix': 'lower it by 0.2 m'}])


def changed():
    spec = spec10()
    spec['people'][2]['facing'] = [1, 0]
    return spec


def rendered(store):
    s = saved(store)
    g = s['guides']['VS1']
    G.apply_result(s, {'id': g['render']['job_id'], 'request': {'kind': 'guide-render', 'shot_id': 'VS1', 'sha256': g['sha256']}}, 'ready',
                   {'guide_key': 'g.mp4', 'sha256': 'sha-guide', 'bytes': 9, 'frame1_key': 'f1.png', 'frame1_sha256': 'sha-f1', 'render_seconds': 600}, None)
    V.save_session(store, NEW, s)


def approved_before_the_check(store):
    """As the server before release 1 recorded it: the operator's Yes on a layout drawing whose check had not run."""
    s = saved(store)
    s['guides']['VS1']['drawing'].update(status='approved', verdict={'approved': True, 'quote': 'Yes.'})
    V.save_session(store, NEW, s)


def corrected_the_older_way(store, words):
    """As the server until 25 Nov 2026 recorded "Correct it" on a layout drawing's card (retired, A1)."""
    s = saved(store)
    s['guides']['VS1']['drawing'].update(status='rejected', verdict={'approved': False, 'quote': 'No.', 'notes': words})
    V.save_session(store, NEW, s)


def order(store, conn):
    return G.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])


# ---------- the order: the fresh checker first; its pass opens the still (until 25 Nov 2026: then the operator's card; retired, A1) ----------

def test_frames_ready_and_no_verdict_the_checker_is_named_and_nobody_is_asked(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    assert said(store) == '' and cards(store, conn) == [] and state(store) == ['being made']       # the check frames are being rendered
    sha = frames_back(store, conn)
    assert said(store) == START + CHECK.format(ids='VS1', n=1) + '.'                              # no approval is waited for
    assert cards(store, conn) == [] and state(store) == ['being checked by Claude']
    no = refused(lambda: G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'Yes.'))   # the tool's own path of the older way: refused by name, before the check too
    assert no == G.DRAWING_RETIRED and saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'
    assert 'first frame of the layout is not rendered yet' in refused(lambda: order(store, conn))   # no pass, no first frame: no still
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert 'vw-guide-check' in nxt and "waits for the operator's answer" not in nxt


def test_a_failed_check_shows_no_card_and_names_the_shot_for_a_rebuilt_scene_then_the_passed_layout_goes_on_with_no_card(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, False)
    assert cards(store, conn) == [] and state(store) == ['being redone'] and saved(store)['guides']['VS1'].get('render') is None
    assert said(store) == START + SCENES.format(ids='VS1', n=1) + '.'                             # never the checker again: this scene has its verdict
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert 'The check of this scene failed (nothing floats): change the scene' in nxt and 'vw-guide-check' not in nxt
    scene(store, conn, changed())
    assert said(store) == '' and cards(store, conn) == []
    sha2 = frames_back(store, conn)
    assert sha2 != sha and said(store) == START + CHECK.format(ids='VS1', n=1) + '.' and cards(store, conn) == []
    out = verdict(store, conn, sha2, True)
    assert saved(store)['guides']['VS1']['render']['status'] == 'queued' and 'vw visuals next' not in out['next']   # the render follows as before; nobody is asked
    assert cards(store, conn) == [] and state(store) == ['being made'] and said(store) == ''      # no card for the layout that replaces an earlier one either
    rendered(store)
    assert cards(store, conn) == [] and state(store) == [CAN_ORDER] and said(store) == START + STILLS.format(ids='VS1', n=1) + '.'


def test_a_passed_check_offers_no_card_and_a_correction_of_the_older_way_goes_back_to_the_check(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, True)
    assert cards(store, conn) == [] and state(store) == ['being made']                            # until 25 Nov 2026: the card with Yes / Correct it; retired (A1)
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert "waits for the operator's answer" not in nxt and 'Yes' not in nxt
    corrected_the_older_way(store, 'the mother faces the wrong way')                              # a "Correct it" recorded before the change still sends the scene back
    assert cards(store, conn) == [] and state(store) == ['being redone']
    assert said(store) == START + SCENES.format(ids='VS1', n=1) + '.'
    scene(store, conn, changed())
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'                       # the new scene's own drawing: the correction was of another one
    frames_back(store, conn)
    assert cards(store, conn) == [] and state(store) == ['being checked by Claude'] and said(store) == START + CHECK.format(ids='VS1', n=1) + '.'


def test_an_approval_of_the_older_way_does_not_replace_the_check_and_the_scene_goes_on_when_it_passes(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    approved_before_the_check(store)                                                              # the live film at the deploy
    assert cards(store, conn) == [] and said(store) == START + CHECK.format(ids='VS1', n=1) + '.' and state(store) == ['being checked by Claude']
    verdict(store, conn, sha, True)
    assert cards(store, conn) == [] and saved(store)['guides']['VS1']['drawing']['status'] == 'approved' and state(store) == ['being made']   # not asked again
    rendered(store)
    assert said(store) == START + STILLS.format(ids='VS1', n=1) + '.'
    still_made(store, conn)                                                                       # both gates are open: the first frame and the check's pass


def test_a_scene_rebuilt_after_an_earlier_approval_is_checked_and_goes_on_with_no_card(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    approved_before_the_check(store)
    verdict(store, conn, sha, False)
    assert cards(store, conn) == [] and state(store) == ['being redone'] and said(store) == START + SCENES.format(ids='VS1', n=1) + '.'
    scene(store, conn, changed())
    sha2 = frames_back(store, conn)
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'proposed' and cards(store, conn) == []   # the approval was of another drawing
    verdict(store, conn, sha2, True)
    assert cards(store, conn) == [] and saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'   # nobody is asked about the new drawing
    rendered(store)
    assert said(store) == START + STILLS.format(ids='VS1', n=1) + '.' and state(store) == [CAN_ORDER]
    still_made(store, conn)                                                                       # until 25 Nov 2026 the still waited for the new drawing's Yes; retired (A1)


# ---------- the gates stay; the one hole is closed ----------

def test_a_repair_is_not_ordered_under_a_layout_that_is_not_checked_and_is_ordered_after_its_pass_with_no_word_of_the_operator(take_film):
    """A masked repair of a still kept from an earlier scene waits for the new scene's check like a new still. (Until 25 Nov 2026 it waited for
    the operator's Yes on the new scene's layout drawing; retired, A1.)"""
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, True)
    rendered(store)
    sid = still_made(store, conn)
    G.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes.')
    scene(store, conn, changed())                                                                 # the scene changes: the approved still is kept
    sha2 = frames_back(store, conn)
    repair = lambda: G.request_still(conn, store, USER, NEW, [], 'VS1', 'the left arm becomes whole', None, repair_of=sid, region={'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2})
    assert 'The first frame of the layout is not rendered yet' in refused(repair)                 # the new scene has no pass and no first frame
    s = saved(store)
    s['guides']['VS1']['render'] = {'frame1_key': 'f1.png', 'frame1_sha256': 'sha-f1'}             # a first frame kept from somewhere, and still no pass
    V.save_session(store, NEW, s)
    assert 'The layout of VS1 is not checked yet' in refused(repair)
    s['guides']['VS1'].pop('render')
    V.save_session(store, NEW, s)
    verdict(store, conn, sha2, True)
    rendered(store)
    assert cards(store, conn) == [] and repair()['still_id']


# ---------- several shots at once; the film in mid-step at the deploy ----------

def live(drawing='approved', verdicts=(), frames='ready', before=0, render=None):
    sha = 'g' * 64
    return {'sha256': sha, 'key': 'k', 'seconds': 6, 'frames': {'job_id': 'f', 'status': frames, 'frames': [], 'strip_key': 'strip'}, 'verdicts': [{'sha256': sha, 'pass': ok} for ok in verdicts],
            'rounds_before': before, 'drawing': {'status': drawing, 'sha256': sha, 'views': []}, 'stills': [], 'takes': [], 'checks': [], **({'render': render} if render else {})}


def layout_cards(s, p):
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None}
    return [i['id'].split(':')[:2] for i in CF._layout_items(ctx)]


def test_the_layouts_that_passed_get_no_card_and_the_held_ones_come_in_film_order(held):
    ids = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
    s, p = session(), plan(*[shot(sid, start=100 * n, end=100 * n + 100) for n, sid in enumerate(ids)])
    s['guides'] = {'S6': live('proposed', [False]), 'S4': live('proposed', [True], render={'job_id': 'r', 'status': 'queued'}), 'S2': live('proposed'), 'S3': live('proposed', [False]),
                   'S1': live('proposed', [True], render={'job_id': 'r', 'status': 'queued'}), 'S5': live('proposed', [False])}   # written in another order
    for sid in ('S5', 'S6'):
        s['guides'][sid]['verdicts'][-1]['round'] = G.MAX_ROUNDS                                  # the third failed check in a row: held
    held(s, p)
    assert layout_cards(s, p) == [['layout-held', 'S5'], ['layout-held', 'S6']]                   # S1 and S4 passed: no card (until 25 Nov 2026: theirs, in film order; retired, A1); S2 is with its checker, S3 is rebuilt
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 1 being checked by Claude, 2 being made, 1 being redone, 2 waiting for you in the chat.'
    assert T.starts(s, p, []) == START + SCENES.format(ids='S3', n=1) + '; ' + CHECK.format(ids='S2', n=1) + '.'


def test_the_film_in_mid_step_at_the_deploy_shaped_like_the_live_one(held):
    """19 guides, the operator's approval on all 19 (given before any check), then: 2 checks passed, 13 failed of which 3 scenes are already
    rebuilt (a new drawing, its check frames ready, no verdict), 4 with no verdict."""
    ids = [f'S{n:02d}' for n in range(1, 20)]
    s, p = session(), plan(*[shot(sid, start=100 * n, end=100 * n + 100) for n, sid in enumerate(ids)])
    s['guides'] = {sid: live() for sid in ids}
    for sid in ids[:2]:                                                                           # passed: rendered (the older approval changes nothing)
        s['guides'][sid] = live(verdicts=[True], render={'job_id': 'r', 'status': 'ready', 'frame1_key': 'f1.png'})
    for sid in ids[2:12]:                                                                         # failed, not rebuilt yet
        s['guides'][sid] = live(verdicts=[False])
    for sid in ids[12:15]:                                                                        # failed and rebuilt: the new scene's drawing was never approved
        s['guides'][sid] = live('proposed', before=1)
    held(s, p)
    assert layout_cards(s, p) == []                                                               # nobody is asked anything now
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 7 being checked by Claude, 2 first frame ready: the still can be ordered, 10 being redone.'   # release 4 (until then: "2 being made")
    assert T.starts(s, p, []) == (START + SCENES.format(ids=', '.join(ids[2:12]), n=10) + '; ' + CHECK.format(ids=', '.join(ids[12:]), n=7) + '; '
                                  + STILLS.format(ids='S01, S02', n=2) + '.')
    for sid in ids[12:]:                                                                          # the seven checks pass
        s['guides'][sid].update(verdicts=[{'sha256': 'g' * 64, 'pass': True}], render={'job_id': 'r', 'status': 'queued'})
    assert layout_cards(s, p) == []                                                               # nobody is asked (until 25 Nov 2026: the three new drawings; retired, A1)
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 7 being made, 2 first frame ready: the still can be ordered, 10 being redone.'   # the three new drawings and the four approved ones alike


# ---------- the run's log: the checker's verdict is the assistant's line ----------

def test_the_checkers_verdict_is_logged_as_the_assistants_and_the_layout_approval_as_the_operators():
    run = '11111111-2222-3333-4444-555555555555'
    e = L.entry_from(f'/api/runs/{run}/visuals/guide/verdict', {'request_id': 'r1', 'shot_id': 'VS1', 'sha256': 'a' * 64, 'passed': False, 'looks': [], 'notes': 'The brush floats above the board.'}, 200, {})
    assert e['by_kind'] == 'assistant' and e['entry'].startswith('visuals/guide/verdict') and 'shot_id VS1' in e['about'] and e['quote'] == 'The brush floats above the board.'
    m = L.entry_from(f'/api/runs/{run}/visuals/motion/verdict', {'request_id': 'r2', 'shot_id': 'D1', 'sha256': 'a' * 64, 'rules': []}, 200, {})
    assert m['by_kind'] == 'assistant'                                                            # as the drawn graphics' checker is logged
    d = L.entry_from(f'/api/runs/{run}/visuals/guide/drawing', {'request_id': 'r3', 'shot_id': 'VS1', 'sha256': 'a' * 64, 'approved': True, 'quote': 'Yes, that is the shot.'}, 200, {})
    assert d['by_kind'] == 'operator' and d['quote'] == 'Yes, that is the shot.'


# ---------- the words: served text, the helpers, the server's own next steps ----------

def test_the_served_text_and_the_helpers_say_the_checker_decides():
    """Until 25 Nov 2026: release 1's sentences (`rel1d_wording.ASK_NEW`, `ROW_NEW`, `PARA_NEW`, `CHECK_NEW`: the check first, then the operator's
    card); retired (A1), replaced through scripts/a1_wording.py."""
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    import a1_wording as A1
    import rel1d_wording as W
    stage = next(st for st in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if st['name'] == 'visuals')
    later = next(pt for pt in stage['parts'] if pt['name'] == 'later')['text']
    assert later.count(A1.ASK_NEW) == 1 and W.ASK_NEW not in later and W.ASK not in later
    assert 'a fresh checker checks that layout' in A1.ASK_NEW and 'the checkers of the layouts are started together, in one message' in A1.ASK_NEW
    assert A1.ASK_NEW.endswith('after the check passes, order the still: the operator is not asked about the layout drawing;')
    # release 1's own step is still found under A1's: the text before A1 holds release 1's sentence once, and before release 1 the sentence of design/200 once
    rel1 = json.loads(json.dumps(stage))
    for where, old, new in A1.PAIRS:
        part = next(pt for pt in rel1['parts'] if pt['name'] == where)
        part['text'] = part['text'].replace(new, old)
    assert next(pt for pt in rel1['parts'] if pt['name'] == 'later')['text'].count(W.ASK_NEW) == 1
    was = next(pt for pt in W.before(rel1)['parts'] if pt['name'] == 'later')['text']
    assert was.count(W.ASK) == 1 and W.ASK_NEW not in was and A1.ASK_NEW not in was
    again = json.loads(json.dumps(stage))
    assert A1.apply(again['prompt'], again['parts']) == stage['prompt'] and again['parts'] == stage['parts']   # applying twice changes nothing
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    files = {f: (ROOT / 'plugin' / f).read_text(encoding='utf-8') for f, _, _ in A1.HELPERS}
    for file, old, new in A1.HELPERS:
        assert files[file].count(new) == 1 and old not in files[file], (file, new[:40])
    for file, old, new in W.HELPERS:                                                              # release 1's sentences are gone from the helpers
        assert new not in files[file], (file, new[:40])
    served = json.dumps(stage, ensure_ascii=False)
    for gone in W.RETIRED + A1.RETIRED:
        assert gone in retired and gone not in served and all(gone not in text for text in files.values()), gone
    skill = files['skills/guide/SKILL.md']
    assert 'before any layout card is shown' not in skill and 'checked and approved again' not in skill and 'No still before their Yes' not in skill
    assert 'after the check passes, order the still' in skill and 'Nobody approves the drawing' in skill and 'drawing-approve' not in skill
    check = files['agents/vw-guide-check.md']
    assert 'Your check decides' in check and 'only after it passes' not in check
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from rel1d_wording import') < split.index('from vw25_wording import apply as vw25') < split.index('from a1_wording import apply as a1') < split.index('from d132_wording_v3 import')


def test_the_scenes_next_step_says_the_check_then_the_still(take_film):
    store, conn = film(take_film)
    nxt = scene(store, conn)['next']
    assert nxt.index('vw-guide-check') < nxt.index('After the check passes the still is ordered') and nxt.endswith('the operator is not asked about the layout.')
    assert 'shown to the operator' not in nxt and 'the operator approves it in the chat before the still' not in nxt   # until 25 Nov 2026: "shown to the operator only after that check passes"; retired (A1)
