"""design/221 phase 3c (SK, 19 Nov 2026): row 1, the shared parts drawn once and approved in the chat; row 3, the still end-frame approved in the
chat before the motion. And the small fix of the labels gate: a shot's message is its point, not text on screen. Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import chat_flow as C, font_sample, motion as M, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_batch89b_pure import SPEC
from test_design130_p1_pure import INDEX, WALL, FakeConn, motion_shot, motion_store, project, worker_fakes, zipped
from test_design221_p1_pure import NEW, edit_plan, edit_session, visuals
from test_design221_p2_pure import EVEN, LEAVES, RULES, SOLID, Jobs, answer, selectable, two_drawn
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
PARTS = '''<svg xmlns="http://www.w3.org/2000/svg">
<symbol id="part-wall" viewBox="0 0 200 100" data-element="E1"><title>Wall section</title><rect width="200" height="100" fill="#B5543A"/></symbol>
<symbol id="part-arrow" viewBox="0 0 100 20"><title>Load arrow</title><path d="M0 10 H90" stroke="#2B2B2B"/></symbol>
</svg>'''
USES = WALL.replace('</svg>', '<use href="#part-wall" x="10" y="10" width="400" height="200"/></svg>')
ALL = {SOLID: True, EVEN: True, LEAVES: True}


@pytest.fixture(autouse=True)
def drawn_picture(monkeypatch):
    """The parts picture is drawn by Chromium on the server; here it is faked."""
    seen = {}
    monkeypatch.setattr(font_sample, 'render', lambda html: seen.setdefault('html', html) and b'\x89PNGparts')
    return seen


def two(store=None):
    store = store or motion_store()
    two_drawn(store)
    edit_session(store, lambda s: s['spec_approvals'].update(MO2={'digest': VS.spec_digest(SPEC)}))
    return store


def parts(store, text=PARTS, ok=True):
    out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', text.encode('utf-8')))
    if ok:
        VS.parts_answer(store, USER, NEW, [], out['sha256'], True, 'Approve')
    return out


def upload(store, files=None, shot='MO1', still=False, rules=RULES):
    return g(lambda: VS.set_motion(store, USER, NEW, [], shot, 'shot.zip', zipped(files or project()), rules, **({'still': True} if still else {})))['sha256']


def chat(store, kind):
    return [i for i in C._waiting_items(C._ctx(FakeConn([]), store, USER, NEW, [])) if i['kind'] == kind]


def build(store, shot='MO1'):
    return g(lambda: VS.motion_brief(store, NEW, [], shot, build=True, conn=FakeConn([])))


# ---------- the small fix: the labels gate does not count a shot's message ----------

def test_a_message_alone_is_not_text_on_screen_for_the_labels_gate():
    quiet = motion_store(sh=motion_shot(scene_motion={'labels': [], 'cues': []}, message='The course spreads the load.'))
    assert 'Text on screen, word for word, and only these: none.' in build(quiet)['brief']
    for over in ({'carries_text': True}, {'drawing_spec': {**SPEC, 'illustrative': False, 'label': 'Sill course'}}):
        with pytest.raises(Problem, match='carries text and has no scene_motion.labels'):
            build(motion_store(sh=motion_shot(scene_motion={'labels': [], 'cues': []}, message='The point.', **over)))


# ---------- row 1: the shared parts ----------

def test_one_drawn_graphic_has_no_shared_parts_and_nothing_is_asked():
    store = motion_store()
    assert 'Use these parts' not in build(store)['brief'] and chat(store, 'parts') == []
    with pytest.raises(Problem, match='This film has one drawn graphic: it has no shared parts'):
        g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', PARTS.encode('utf-8')))


def test_two_drawn_graphics_need_their_shared_parts_before_any_brief():
    store = two()
    with pytest.raises(Problem) as e:
        build(store)
    assert ('This film has 2 drawn graphics: their shared parts are drawn once, before any brief. Run `vw motion parts`, start one `vw-motion-parts` '
            'helper, and upload its file with `vw motion parts --file work/motion/parts/parts.svg`; the operator approves its picture in the chat '
            '(`vw visuals next`). Then brief each drawing.') in str(e.value)
    VS.motion_brief(store, NEW, [], 'MO1')   # the brief's lines for a check or a page are not gated
    parts(store, ok=False)
    with pytest.raises(Problem, match="The shared parts wait for the operator's approval in the chat"):
        build(store)


def test_the_parts_brief_holds_every_drawn_brief_and_the_things_shown_twice():
    store = two()
    out = g(lambda: VS.parts_brief(store, NEW, []))
    assert '## MO1' in out['brief'] and '## MO2' in out['brief'] and 'Things shown by two or more drawings (each is a part to draw once): E1 Wall section (MO1, MO2).' in out['brief']
    assert 'comp-1' in out['refs']
    edit_session(store, lambda s: s['spec_approvals'].pop('MO2'))
    with pytest.raises(Problem, match='The shared parts are drawn from the approved specs: approve the drawing spec of MO2 first'):
        g(lambda: VS.parts_brief(store, NEW, []))


@pytest.mark.parametrize('text, match', [
    (PARTS.replace('<title>Load arrow</title>', ''), 'part-arrow has no <title>'),
    (PARTS.replace('id="part-arrow"', 'id="arrow"'), 'arrow: a part\'s id is part-<name>'),
    (PARTS.replace('data-element="E1"', 'data-element="E7"'), 'part-wall draws E7, which is no thing of the plan'),
    (PARTS.replace('<path', '<script>x()</script><path'), 'no script'),
    (PARTS.replace('<path', '<image href="https://example.com/a.png"/><path'), 'loads from the network'),
    (PARTS.replace('<path', '<image href="assets/ref/comp-1.png"/><path'), 'places no picture or file'),
    ('<!DOCTYPE svg [<!ENTITY a "x">]>' + PARTS, 'no DOCTYPE'),
    (PARTS.replace('id="part-arrow"', 'id="part-wall"'), 'part-wall is defined twice'),
    (PARTS.replace(' viewBox="0 0 100 20"', ''), 'part-arrow has no viewBox'),
    ('<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>', 'holds symbols only'),
    ('<svg xmlns="http://www.w3.org/2000/svg"><defs/></svg>', 'no <symbol id="part-'),   # fix set A1.1: an <svg> with nothing in it now says that no shape repeats (test_fixset2_pure)
    ('<svg', 'not an SVG file'),
])
def test_the_parts_file_is_checked_like_a_project(text, match):
    with pytest.raises(Problem, match=match):
        parts(two(), text, ok=False)


def test_the_parts_are_one_card_in_the_chat_with_their_picture_before_any_drawn_shot(drawn_picture):
    store = two()
    out = parts(store, ok=False)
    assert out['parts'] == ['part-wall', 'part-arrow'] and 'in the chat' in out['next']
    s = saved(store)
    assert s['motion_parts']['picture_key'] == f"run-1/visuals/motion/parts/{out['sha256']}.png" and store.files[s['motion_parts']['picture_key']] == b'\x89PNGparts'
    html = drawn_picture['html']
    assert '<use href="#part-wall"' in html and 'Wall section' in html and 'Load arrow' in html and '#F4EDE1' in html   # each part large with its name, on the film's ground
    rows = VS.waiting(s, VS.current_plan(store, s), 'VW-9', [])
    assert rows[0]['kind'] == 'shared parts to approve' and rows[0]['label'] == 'Shared parts · 2 parts'
    item = chat(store, 'parts')[0]
    assert item['question'] == 'The shared parts of the drawn graphics (2): each is drawn once and every drawing uses it. Are they right?'
    assert [b['label'] for b in item['buttons']] == ['Approve', 'Reject'] and item['buttons'][1]['needs_words']
    assert item['show'] == [{'key': s['motion_parts']['picture_key'], 'name': 'shared-parts.png'}]
    assert '- part-wall: Wall section (Wall section)' in item['text'] and '- part-arrow: Load arrow' in item['text']
    item['_run']('approve', 'Approve', '')
    assert chat(store, 'parts') == [] and saved(store)['motion_parts_approved']['sha256'] == out['sha256']


def test_a_picture_the_server_cannot_draw_shows_the_parts_drawing_itself(monkeypatch):
    def broken(html):
        raise RuntimeError('no chromium')
    monkeypatch.setattr(font_sample, 'render', broken)
    store = two()
    out = parts(store, ok=False)
    key = saved(store)['motion_parts']['picture_key']
    assert key.endswith('-preview.svg') and b'<use href="#part-wall"' in store.files[key] and 'drawn by the server' in out['next']
    assert chat(store, 'parts')[0]['show'] == [{'key': key, 'name': 'shared-parts.svg'}]


def test_a_rejected_parts_file_goes_back_with_the_operators_words_and_the_next_upload_asks_again():
    store = two()
    out = parts(store, ok=False)
    said = chat(store, 'parts')[0]['_run']('reject', 'Reject', 'The wall is too tall.')
    assert said['for_the_assistant'] == ('The operator rejected the shared parts: "The wall is too tall.". Give these words to a `vw-motion-parts` helper to redraw them, '
                                         'then upload again (`vw motion parts --file work/motion/parts/parts.svg`).')
    assert chat(store, 'parts') == []
    with pytest.raises(Problem, match='The operator rejected the shared parts: "The wall is too tall."'):
        build(store)
    assert g(lambda: VS.parts_brief(store, NEW, []))['rejected'] == 'The wall is too tall.'
    again = parts(store, PARTS.replace('height="100" fill', 'height="80" fill'), ok=False)
    assert again['sha256'] != out['sha256'] and len(chat(store, 'parts')) == 1


def test_once_approved_the_brief_lists_the_parts_and_vw_saves_the_file_beside_it():
    store = two()
    out = parts(store)
    b = build(store)
    assert ('Use these parts (drawn once for the whole film; do not redraw them): part-wall: Wall section; part-arrow: Load arrow. Place the view this '   # fix set A3.2: was "Place each with"
            'drawing shows with <use href="#part-<name>"> (one view of a thing is enough): the server puts them in the page, and parts.svg beside this brief '
            'shows them.') in b['brief']
    assert b['brief'].index('Drawing spec') < b['brief'].index('Use these parts') < b['brief'].index('Text on screen')
    assert b['parts_key'] == f"run-1/visuals/motion/parts/{out['sha256']}.svg"
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('parts_key')" in vw and "f'work/motion/{a.shot}/parts.svg'" in vw and "'parts'" in vw and "base + '/motion/parts'" in vw


def test_a_new_parts_upload_after_the_approval_is_asked_again_before_the_next_brief():
    store = two()
    parts(store)
    parts(store, PARTS.replace('height="100" fill', 'height="80" fill'), ok=False)
    assert len(chat(store, 'parts')) == 1
    with pytest.raises(Problem, match="wait for the operator's approval"):
        build(store)


def test_the_parts_are_pasted_hidden_at_the_start_of_every_drawn_page(monkeypatch, tmp_path):
    (tmp_path / 'index.html').write_text('<html><body class="x"><div id="root"></div></body></html>', encoding='utf-8')
    M.apply_parts(tmp_path, PARTS)
    M.apply_parts(tmp_path, PARTS)
    html = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert html.count('id="vw-parts"') == 1 and html.index('<body class="x">') < html.index('id="vw-parts"') < html.index('id="root"')
    assert 'width="0" height="0"' in html and '<symbol id="part-wall"' in html
    store = two()
    parts(store)
    sha = upload(store, project(**{'compositions/wall.html': USES}))
    worker_fakes(monkeypatch, store, tmp_path)
    request = VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1', sha)[3]
    folder = VW._motion_folder(store, request, tmp_path / 'render', note=False)
    assert 'id="vw-parts"' in (folder / 'index.html').read_text(encoding='utf-8')   # the HyperFrames check sees them too


def test_an_upload_that_redraws_a_shared_part_is_refused_and_names_it():
    store = two()
    parts(store)
    with pytest.raises(Problem) as e:
        upload(store)
    assert ('MO1 shows Wall section but does not use its shared part: place part-wall with <use href="#part-wall"> (drawn once for the whole film; '
            'do not redraw it).') in str(e.value)
    with pytest.raises(Problem, match='MO1 defines part-wall, the id of a shared part'):
        upload(store, project(**{'compositions/wall.html': USES.replace('<div id="label"', '<g id="part-wall"></g><div id="label"')}))
    assert upload(store, project(**{'compositions/wall.html': USES.replace('href=', 'xlink:href=')}))


def test_defect56_a_thing_with_several_views_among_the_parts_needs_one_of_them_not_every_one():
    store = two()
    views = PARTS.replace('</svg>', '<symbol id="part-wall-plan" viewBox="0 0 200 100" data-element="E1"><title>Wall from above</title><rect width="200" height="30"/></symbol></svg>')
    parts(store, views)
    assert upload(store, project(**{'compositions/wall.html': USES}))   # the cut view alone: the drawing shows the wall cut across, not from above
    assert upload(store, project(**{'compositions/wall.html': USES.replace('#part-wall"', '#part-wall-plan"')}))   # or the other view alone
    with pytest.raises(Problem) as e:
        upload(store)   # neither view placed
    assert ('MO1 shows Wall section but uses none of its shared parts: place the view this drawing shows, one of part-wall, part-wall-plan, '
            'with <use href="#part-…">') in str(e.value)


def test_a_changed_part_changes_the_render_request_of_the_drawings_that_use_it():
    store = two()
    parts(store)
    sha = upload(store, project(**{'compositions/wall.html': USES}))
    req = lambda: VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1', sha)[3].get('parts')
    first = req()
    assert set(first['used']) == {'part-wall'} and first['key'] == saved(store)['motion_parts_approved']['key']
    parts(store, PARTS.replace('M0 10 H90', 'M0 10 H80'))   # only the arrow changed: MO1 does not use it
    assert req()['used'] == first['used']
    out = parts(store, PARTS.replace('height="100" fill', 'height="80" fill'))
    assert req()['used'] != first['used'] and 'used' in json.dumps(req())
    plain = two()
    plain_sha = upload(plain)
    assert 'parts' not in VS._motion_request(plain, VS.session_of(plain, NEW, []), NEW, 'MO1', plain_sha)[3]   # no parts: the request is as before
    assert out['sha256']


def test_a_take_rendered_with_older_parts_is_rendered_again_not_rebuilt():
    store = two()
    parts(store)
    sha = upload(store, project(**{'compositions/wall.html': USES}))
    conn = selectable(store, sha)
    said = VS.parts_answer(store, USER, NEW, [], parts(store, PARTS.replace('height="100" fill', 'height="80" fill'), ok=False)['sha256'], True, 'Approve')
    assert 'Its parts changed for MO1: render each again (`vw motion render --shot S`)' in said['for_the_assistant']
    with pytest.raises(Problem, match=r'Its parts changed since this drawing was rendered: render it again \(`vw motion render --shot MO1`\); nothing is rebuilt.'):
        g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))


def test_the_parts_line_is_part_of_the_brief_fingerprint():
    store = two()
    parts(store)
    was = build(store)['lines']['Use these parts']
    parts(store, PARTS.replace('height="100" fill', 'height="80" fill'))   # the same names, another drawing
    assert build(store)['lines']['Use these parts'] != was


def test_the_parts_helper_and_the_texts():
    agent = (ROOT / 'plugin' / 'agents' / 'vw-motion-parts.md').read_text(encoding='utf-8')
    assert 'name: vw-motion-parts' in agent and 'work/motion/parts/parts.svg' in agent and 'id="part-<name>"' in agent and '<title>' in agent and 'data-element' in agent
    assert 'Look at these before you draw' in agent and 'operator\'s words' in agent
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221e_wording_v3 as W
    import fixset2_wording as FIX2   # fix set phase 2: sentences added inside this script's sentences, and one replaced
    stage = FIX2.before(visuals())
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and olds[where].count(old) == 1, old[:50]
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(FIX2.now(file, new)) == 1, file   # c4: "place each with" is now "place the view this drawing shows with"
    later = texts['later']
    assert '`vw motion parts --file work/motion/parts/parts.svg`' in later and 'one `vw-motion-parts` helper' in later and 'rendered again, not rebuilt' in later
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'never redraw one' in skill and 'say so in REVIEW.md and give it back to the main assistant' in skill
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'Write no rule about how a shared part' in rules and 'where it sits and how many there are still apply' in rules
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'never fail how a shared part is drawn' in check
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d221d(prompt, parts)') < split.index('d221e(prompt, parts)')
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert all(s in retired for s in W.RETIRED)


# ---------- row 3: the still end-frame ----------

END = 'run-1/visuals/motion/tools/s1/0.png'
STILL_FIRST = ("MO1: the still end-frame comes first: build the picture as it stands at the end of the shot, with no motion, upload it with "
               "`vw motion upload --shot MO1 --still`, snapshot its last frame, check it and send the checker's verdict; the operator approves it in the "
               "chat. Then the animated project.")


def no_still(store):
    edit_session(store, lambda s: s.pop('motion_stills', None))   # motion_store holds an approved still for MO1, so the older tests upload as before
    return store


def end_jobs(sha, shot='MO1', at=3.96, key=END, snap=True):
    rows = [{'id': f'c-{sha[:6]}', 'run_id': 'run-1', 'unit': shot, 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-check', 'sha256': sha},
             'result': {'ok': True, 'warnings': []}}]
    rows += [{'id': f's-{sha[:6]}', 'run_id': 'run-1', 'unit': shot, 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-snapshot', 'sha256': sha},
              'result': {'snapshots': [{'at': at, 'key': key}]}}] if snap else []
    return Jobs(rows)


def still_verdict(store, sha, answers, shot='MO1', key=END, png=b'\x89PNGend', at=3.96, rnd=1):
    store.files[key] = png
    return g(lambda: VS.motion_verdict(store, USER, NEW, [], {'shot_id': shot, 'sha256': sha, 'round': rnd, 'rules': [answer(r, s) for r, s in answers.items()]},
                                       conn=end_jobs(sha, shot, at=at, key=key)))


def test_the_animated_project_waits_for_its_still_and_a_film_with_one_drawn_graphic_takes_it_too():
    store = no_still(motion_store())
    with pytest.raises(Problem) as e:
        upload(store)
    assert STILL_FIRST in str(e.value)
    sha = upload(store, still=True)
    assert saved(store)['motion_projects'][sha]['still'] is True and chat(store, 'parts') == []
    out = VS.set_motion(store, USER, NEW, [], 'MO1', 'shot.zip', zipped(project()), RULES, still=True)
    assert '`vw motion snapshot --shot MO1 --sha ' + sha + ' --at 3.96`' in out['next'] and 'must rules a still can show' in out['next']


def test_the_still_is_checked_on_its_must_rules_alone_and_comes_to_the_chat_as_a_card():
    store = no_still(motion_store())
    sha = upload(store, still=True)
    out = still_verdict(store, sha, {SOLID: True})   # the rules about motion and the shoulds are not answered on a still
    assert out['next'].startswith('The still end-frame passed') and 'build the motion only after the approval' in out['next']
    s = saved(store)
    assert 'MO1' not in (s.get('motion_bound') or {}) and s['motion_checks']['MO1'][-1]['still'] is True   # a still is never the shot's drawing
    assert s['motion_stills']['MO1']['frame_key'] == END
    assert [w['label'] for w in VS.waiting(s, VS.current_plan(store, s), 'VW-9', []) if w['kind'] == 'still end-frame to approve'] == ['Still end-frame · MO1']
    item = chat(store, 'still end-frame')[0]
    assert item['question'] == 'Gap G1, shot 1 (MO1): this is the drawing as it stands at the end of the shot, before any motion is added. Is it right?'
    assert item['show'] == [{'key': END, 'name': 'MO1-still-end.png'}] and [b['label'] for b in item['buttons']] == ['Approve', 'Reject'] and item['buttons'][1]['needs_words']


def test_hotfix_a_rule_a_still_cannot_show_answered_not_seen_does_not_hold_the_still():
    store = no_still(motion_store())
    sha = upload(store, still=True)
    out = still_verdict(store, sha, {SOLID: True, LEAVES: 'not seen'})   # a checker answers a rule about motion "not seen" on the still
    assert out['next'].startswith('The still end-frame passed')
    assert chat(store, 'still end-frame')   # the card comes; no frame is asked for and nothing is "not seen twice"


def test_hotfix_a_still_held_as_not_seen_twice_passes_when_it_is_judged_again():
    store = no_still(motion_store())
    sha = upload(store, still=True)
    edit_session(store, lambda s: s.setdefault('motion_checks', {}).setdefault('MO1', []).append(
        {'sha256': sha, 'round': 1, 'still': True, 'rules': [{'rule': SOLID, 'pass': True, 'class': 'must'},
                                                             {'rule': LEAVES, 'pass': False, 'class': 'must', 'where': 'not seen twice in round 1 (a crop of the sill)'}]}))
    out = still_verdict(store, sha, {SOLID: True}, rnd=2)   # the state two stills of VW-24 were in: the rule a still cannot show is left out now
    assert out['next'].startswith('The still end-frame passed')


def test_the_still_verdict_needs_the_last_frame_of_the_still():
    store = no_still(motion_store())
    sha = upload(store, still=True)
    for conn in (end_jobs(sha, snap=False), end_jobs(sha, at=1.0)):
        with pytest.raises(Problem) as e:
            g(lambda: VS.motion_verdict(store, USER, NEW, [], {'shot_id': 'MO1', 'sha256': sha, 'round': 1, 'rules': [answer(SOLID, True)]}, conn=conn))
        assert f"MO1: the still's last frame is not taken yet: run `vw motion snapshot --shot MO1 --sha {sha} --at 3.96`, give it to the checker, then send the verdict." in str(e.value)


def test_a_failed_must_on_the_still_sends_it_back_and_its_rounds_are_its_own():
    store = no_still(motion_store())
    sha = upload(store, still=True)
    out = still_verdict(store, sha, {SOLID: False})
    assert out['next'] == ("1 rules failed on the still: give them to a vw-motion-shot helper for MO1 to redo the still (the still's rounds do not count against "
                           "the animation's three).")
    assert chat(store, 'still end-frame') == [] and 'motion_stills' not in saved(store)


def test_an_approved_still_lets_the_motion_be_uploaded_and_checked_as_before():
    store = no_still(motion_store())
    still_verdict(store, upload(store, still=True), {SOLID: True})
    said = chat(store, 'still end-frame')[0]['_run']('approve', 'Approve', '')
    assert said['for_the_assistant'] == 'The still end-frame of MO1 is approved: build its motion now without changing what the still shows, and upload it without --still.'
    assert chat(store, 'still end-frame') == []
    sha = upload(store, project(**{'style.css': 'body { margin: 0; }'}))
    out = VS.motion_verdict(store, USER, NEW, [], {'shot_id': 'MO1', 'sha256': sha, 'round': 1, 'rules': [answer(r, True) for r in ALL]})
    assert out['next'].startswith('Passed') and saved(store)['motion_bound'] == {'MO1': sha}


def test_a_rejected_still_is_redone_with_the_words_and_its_card_comes_again():
    store = no_still(motion_store())
    still_verdict(store, upload(store, still=True), {SOLID: True})
    said = chat(store, 'still end-frame')[0]['_run']('reject', 'Reject', 'The slab is missing.')
    words = ('MO1: the operator rejected the still end-frame: "The slab is missing.". Give these words to a `vw-motion-shot` helper to redo the still, then '
             'upload it again with --still.')
    assert said['for_the_assistant'] == words and chat(store, 'still end-frame') == []
    with pytest.raises(Problem) as e:
        upload(store)
    assert words in str(e.value)
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}), still=True)
    still_verdict(store, sha2, {SOLID: True}, key='run-1/visuals/motion/tools/s2/0.png', png=b'\x89PNGend2')
    assert chat(store, 'still end-frame')[0]['show'] == [{'key': 'run-1/visuals/motion/tools/s2/0.png', 'name': 'MO1-still-end.png'}]


def test_the_stills_of_one_diagram_are_one_card_when_ready_together_else_one_each():
    store = two()
    entry = lambda n: {'sha256': str(n) * 64, 'frame_key': f'k{n}', 'png': f'p{n}', 'parts': {}}
    edit_session(store, lambda s: s.update(motion_stills={'MO1': entry(1)}))
    one = chat(store, 'still end-frame')
    assert len(one) == 1 and one[0]['show'] == [{'key': 'k1', 'name': 'MO1-still-end.png'}]
    edit_session(store, lambda s: s.update(motion_stills={'MO2': entry(2), 'MO1': entry(1)}))
    both = chat(store, 'still end-frame')
    assert len(both) == 1 and both[0]['question'] == ('Gap G1, shot 1 (MO1), Gap G1, shot 2 (MO2): the drawing as it stands at the end of each of these shots, in order, before any motion is added. '
                                                     'Are they right?')
    assert both[0]['show'] == [{'key': 'k1', 'name': 'MO1-still-end.png'}, {'key': 'k2', 'name': 'MO2-still-end.png'}]
    both[0]['_run']('approve', 'Approve', '')
    assert chat(store, 'still end-frame') == [] and all(st['approved']['png'] == st['png'] for st in saved(store)['motion_stills'].values())


def test_a_parts_change_makes_an_approved_still_stale_and_the_same_picture_keeps_its_approval():
    store = no_still(two())
    parts(store)
    still = upload(store, project(**{'compositions/wall.html': USES}), still=True)
    still_verdict(store, still, {SOLID: True})
    chat(store, 'still end-frame')[0]['_run']('approve', 'Approve', '')
    assert upload(store, project(**{'compositions/wall.html': USES, 'style.css': 'b {}'}))
    parts(store, PARTS.replace('height="100" fill', 'height="80" fill'))
    with pytest.raises(Problem) as e:
        upload(store, project(**{'compositions/wall.html': USES, 'style.css': 'b {}'}))
    assert ("MO1: its parts changed since the still end-frame was approved: upload the still again (`vw motion upload --shot MO1 --still`), snapshot its last "
            "frame and send the checker's verdict; the approval stays when the picture is the same.") in str(e.value)
    assert upload(store, project(**{'compositions/wall.html': USES}), still=True) == still   # the same still, uploaded again with the new parts
    still_verdict(store, still, {SOLID: True}, key='run-1/visuals/motion/tools/s3/0.png')   # the same picture: no new approval
    assert chat(store, 'still end-frame') == [] and upload(store, project(**{'compositions/wall.html': USES, 'style.css': 'b {}'}))
    parts(store, PARTS.replace('height="100" fill', 'height="60" fill'))
    upload(store, project(**{'compositions/wall.html': USES}), still=True)
    still_verdict(store, still, {SOLID: True}, key='run-1/visuals/motion/tools/s4/0.png', png=b'\x89PNGshorter')   # the picture changed: asked again
    assert len(chat(store, 'still end-frame')) == 1


def test_the_texts_say_the_still_first_and_the_motion_after():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221e_wording_v3 as W
    later = next(p['text'] for p in visuals()['parts'] if p['name'] == 'later')
    assert '`vw motion upload --shot S --still`' in later and 'only the must rules a still can show' in later and 'the end framing' in later
    assert 'with no pictures it stops at a still key frame first' not in later and "The still's rounds do not count against the animation's three" in later
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert '`vw motion upload --shot <shot> --still`' in skill and 'without changing what the still shows' in skill and 'the end framing' in skill
    assert 'answer "key frame ready"' not in skill
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'a rule about motion or timing is not answered on the still' in check
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "s.add_argument('--still', action='store_true'" in vw and "'still': True" in vw
    assert 'still: bool = False' in (ROOT / 'server' / 'app' / 'main.py').read_text(encoding='utf-8')
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert W.RETIRED and all(s in retired for s in W.RETIRED)
