"""Release 1 (SK, 20 Nov 2026, "go ahead"): a layout is checked before its card is shown. Seen on the first real step 7 (19 AI video shots): the
operator approved 19 layout drawings one at a time, then the fresh checkers failed 13 of the first 15, and each rebuilt layout came back as a
new card. Now: the fresh checker first, the operator second. The layout drawing's card of a shot is offered only when the check of the current
scene passed; `takes.starts` names the checkers as soon as the check frames are ready, and a shot whose check failed for a rebuilt scene; an
approval already given for a scene that then passes stands; the gates of the still are as before, and a repair needs the approval too; the
checker's verdict is the assistant's line in the run's log. Each test failed first. Without a database."""
import json
from pathlib import Path

from app import chat_flow as CF, guide as G, runlog as L, takes as T, visuals_stage as V
from test_design151_refs_pure import NEW
from test_design222_takes_pure import NOW, RUN, USER as OP, held, plan, session, shot   # noqa: F401 (held: the fixture)
from test_guide_route_pure import OTHER, STILL_WORDS, frames_back, refused, scene, spec10, still_made, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import USER, saved

ROOT = Path(__file__).resolve().parents[2]
START = 'Start now, together in one message: '
CHECK = 'the checkers of the guides of {ids} ({n}) (a fresh `vw-guide-check` helper each: a layout is shown to the operator, and its guide is rendered, only after its check passes)'
# release 2, the critic's point 3: a shot to rebuild is named apart from a shot with no guide yet (until then both read "the writers of the scene descriptions of {ids} ({n})")
SCENES = ("the writers of the scene descriptions of {ids} ({n}), each rebuilt after its check or the operator's correction: read `vw guide status --shot S` first, "
          'it holds what must change')
STILLS = 'the stills of {ids} ({n}), each ordered with `vw guide still --shot S --file still.json`'
AGAIN = 'This drawing replaces an earlier one of this shot: the layout was rebuilt after its check.'


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
    return [i for i in CF._drawing_items(ctx) if i['id'].startswith('shot-drawing:')]


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
    """As the server before this release recorded it: the operator's Yes on a layout drawing whose check had not run."""
    s = saved(store)
    s['guides']['VS1']['drawing'].update(status='approved', verdict={'approved': True, 'quote': 'Yes.'})
    V.save_session(store, NEW, s)


# ---------- the order: the fresh checker first, the operator second ----------

def test_frames_ready_and_no_verdict_the_checker_is_named_and_no_card_is_shown(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    assert said(store) == '' and cards(store, conn) == [] and state(store) == ['being made']       # the check frames are being rendered
    sha = frames_back(store, conn)
    assert said(store) == START + CHECK.format(ids='VS1', n=1) + '.'                              # no approval is waited for
    assert cards(store, conn) == [] and state(store) == ['being checked by Claude']
    no = refused(lambda: G.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'Yes.'))   # the tool's own path: the same rule
    assert 'is not checked yet' in no and 'vw-guide-check' in no and saved(store)['guides']['VS1']['drawing']['status'] == 'proposed'
    nxt = G.status(conn, store, NEW, [], 'VS1')['next']
    assert 'vw-guide-check' in nxt and "waits for the operator's answer" not in nxt


def test_a_failed_check_shows_no_card_and_names_the_shot_for_a_rebuilt_scene_then_the_passed_layout_is_offered(take_film):
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
    assert saved(store)['guides']['VS1']['render']['status'] == 'queued' and 'vw visuals next' in out['next']   # the render follows as before
    got = cards(store, conn)
    assert [i['id'] for i in got] == [f'shot-drawing:VS1:{sha2[:10]}'] and state(store) == ['waiting for you in the chat'] and said(store) == ''
    assert got[0]['text'].startswith(AGAIN)                                                       # an earlier layout of this shot was checked: this one replaces it


def test_a_passed_check_offers_the_card_and_a_no_on_it_goes_back_to_the_check(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, True)
    got = cards(store, conn)
    assert len(got) == 1 and AGAIN not in got[0]['text'] and [b['label'] for b in got[0]['buttons']] == ['Yes', 'Correct it']
    assert "waits for the operator's answer" in G.status(conn, store, NEW, [], 'VS1')['next']
    got[0]['_run']('correct', 'No.', 'the mother faces the wrong way')
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'rejected' and cards(store, conn) == [] and state(store) == ['being redone']
    assert said(store) == START + SCENES.format(ids='VS1', n=1) + '.'
    scene(store, conn, changed())
    frames_back(store, conn)
    assert cards(store, conn) == [] and state(store) == ['being checked by Claude'] and said(store) == START + CHECK.format(ids='VS1', n=1) + '.'


def test_an_approval_given_before_the_check_stands_when_the_same_scene_passes(take_film):
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    approved_before_the_check(store)                                                              # the live film at the deploy
    assert cards(store, conn) == [] and said(store) == START + CHECK.format(ids='VS1', n=1) + '.' and state(store) == ['being checked by Claude']
    verdict(store, conn, sha, True)
    assert cards(store, conn) == [] and saved(store)['guides']['VS1']['drawing']['status'] == 'approved' and state(store) == ['being made']   # not asked again
    rendered(store)
    assert said(store) == START + STILLS.format(ids='VS1', n=1) + '.'
    still_made(store, conn)                                                                       # both gates are open: the rendered guide and the operator's approval


def test_a_scene_rebuilt_after_an_earlier_approval_is_checked_and_then_asked_again_with_the_sentence(take_film):
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
    got = cards(store, conn)
    assert len(got) == 1 and got[0]['text'].startswith(AGAIN)
    rendered(store)
    assert "has not approved this shot's drawing yet" in refused(lambda: still_made(store, conn)) and said(store) == ''   # the still waits for the new drawing's Yes
    got[0]['_run']('yes', 'Yes.', '')
    assert said(store) == START + STILLS.format(ids='VS1', n=1) + '.'


# ---------- the gates stay; the one hole is closed ----------

def test_a_repair_is_not_ordered_under_a_layout_the_operator_has_not_approved(take_film):
    """Until this release a masked repair of a still kept from an earlier scene was taken with the new scene's check passed and its guide
    rendered, but its layout drawing not approved (`guide.request_still` asked for the approval only of a new still)."""
    store, conn = film(take_film)
    scene(store, conn)
    sha = frames_back(store, conn)
    verdict(store, conn, sha, True)
    rendered(store)
    cards(store, conn)[0]['_run']('yes', 'Yes.', '')
    sid = still_made(store, conn)
    G.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes.')
    scene(store, conn, changed())                                                                 # the scene changes: the approved still is kept
    verdict(store, conn, frames_back(store, conn), True)
    rendered(store)
    repair = lambda: G.request_still(conn, store, USER, NEW, [], 'VS1', 'the left arm becomes whole', None, repair_of=sid, region={'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2})
    assert "has not approved this shot's drawing yet" in refused(repair)
    cards(store, conn)[0]['_run']('yes', 'Yes.', '')
    assert repair()['still_id']


# ---------- several shots at once; the film in mid-step at the deploy ----------

def live(drawing='approved', verdicts=(), frames='ready', before=0, render=None):
    sha = 'g' * 64
    return {'sha256': sha, 'key': 'k', 'seconds': 6, 'frames': {'job_id': 'f', 'status': frames, 'frames': [], 'strip_key': 'strip'}, 'verdicts': [{'sha256': sha, 'pass': ok} for ok in verdicts],
            'rounds_before': before, 'drawing': {'status': drawing, 'sha256': sha, 'views': []}, 'stills': [], 'takes': [], 'checks': [], **({'render': render} if render else {})}


def layout_cards(s, p):
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None}
    return [i['id'].split(':')[1] for i in CF._drawing_items(ctx) if i['id'].startswith('shot-drawing:')]


def test_the_cards_of_the_layouts_that_passed_come_in_film_order(held):
    ids = ['S1', 'S2', 'S3', 'S4']
    s, p = session(), plan(*[shot(sid, start=100 * n, end=100 * n + 100) for n, sid in enumerate(ids)])
    s['guides'] = {'S4': live('proposed', [True], render={'job_id': 'r', 'status': 'queued'}), 'S2': live('proposed'), 'S3': live('proposed', [False]),
                   'S1': live('proposed', [True], render={'job_id': 'r', 'status': 'queued'})}   # written in another order
    held(s, p)
    assert layout_cards(s, p) == ['S1', 'S4']                                                     # S2 is with its checker, S3 is rebuilt: no card
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 1 being checked by Claude, 1 being redone, 2 waiting for you in the chat.'
    assert T.starts(s, p, []) == START + SCENES.format(ids='S3', n=1) + '; ' + CHECK.format(ids='S2', n=1) + '.'


def test_the_film_in_mid_step_at_the_deploy_shaped_like_the_live_one(held):
    """19 guides, the operator's approval on all 19 (given before any check), then: 2 checks passed, 13 failed of which 3 scenes are already
    rebuilt (a new drawing, its check frames ready, no verdict), 4 with no verdict."""
    ids = [f'S{n:02d}' for n in range(1, 20)]
    s, p = session(), plan(*[shot(sid, start=100 * n, end=100 * n + 100) for n, sid in enumerate(ids)])
    s['guides'] = {sid: live() for sid in ids}
    for sid in ids[:2]:                                                                           # passed: rendered, the approval stands
        s['guides'][sid] = live(verdicts=[True], render={'job_id': 'r', 'status': 'ready', 'frame1_key': 'f1.png'})
    for sid in ids[2:12]:                                                                         # failed, not rebuilt yet
        s['guides'][sid] = live(verdicts=[False])
    for sid in ids[12:15]:                                                                        # failed and rebuilt: the new scene's drawing was never approved
        s['guides'][sid] = live('proposed', before=1)
    held(s, p)
    assert layout_cards(s, p) == []                                                               # nobody is asked anything now
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 7 being checked by Claude, 2 being made, 10 being redone.'
    assert T.starts(s, p, []) == (START + SCENES.format(ids=', '.join(ids[2:12]), n=10) + '; ' + CHECK.format(ids=', '.join(ids[12:]), n=7) + '; '
                                  + STILLS.format(ids='S01, S02', n=2) + '.')
    for sid in ids[12:]:                                                                          # the seven checks pass
        s['guides'][sid].update(verdicts=[{'sha256': 'g' * 64, 'pass': True}], render={'job_id': 'r', 'status': 'queued'})
    assert layout_cards(s, p) == ids[12:15]                                                       # only the three new drawings are asked; the four approved ones stand
    assert T.status_line(T.expected(s, p, [], NOW)) == 'AI video: 6 being made, 10 being redone, 3 waiting for you in the chat.'


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

def test_the_served_text_and_the_helpers_say_the_check_comes_first():
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    import rel1d_wording as W
    stage = next(st for st in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if st['name'] == 'visuals')
    later = next(pt for pt in stage['parts'] if pt['name'] == 'later')['text']
    assert later.count(W.ASK_NEW) == 1 and 'only after a fresh checker passed that layout' in W.ASK_NEW and 'before any layout card is shown' in W.ASK_NEW
    assert 'the operator sees only layouts that passed' in W.ASK_NEW and W.ASK_NEW.endswith('no still before their Yes;')
    was = next(pt for pt in W.before(stage)['parts'] if pt['name'] == 'later')['text']
    assert was.count(W.ASK) == 1 and W.ASK_NEW not in was
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    for file, old, new in W.HELPERS:
        text = (ROOT / 'plugin' / file).read_text(encoding='utf-8')
        assert text.count(new) == 1, file
    for gone in W.RETIRED:
        assert gone in retired and gone not in later and all(gone not in (ROOT / 'plugin' / f).read_text(encoding='utf-8') for f, _, _ in W.HELPERS), gone
    skill = (ROOT / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'before any layout card is shown' in skill and 'checked and approved again' in skill
    assert 'only after it passes' in (ROOT / 'plugin' / 'agents' / 'vw-guide-check.md').read_text(encoding='utf-8')


def test_the_scenes_next_step_says_the_check_first(take_film):
    store, conn = film(take_film)
    nxt = scene(store, conn)['next']
    assert nxt.index('vw-guide-check') < nxt.index('shown to the operator') and 'only after that check passes' in nxt
    assert 'the operator approves it in the chat before the still' not in nxt
