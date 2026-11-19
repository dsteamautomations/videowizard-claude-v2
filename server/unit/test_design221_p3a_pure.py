"""design/221 phase 3a (SK, 19 Nov 2026): rows 5, 7, 8 and 10, and section 10 (the camera in a drawing that explains, with SK's ruling).
Row 8 and 10 (design/221a F1-F6): the fixed paragraph "In every style" under every style; each style file with its new text, its energy, its camera
flows and its family of motions, printed in the brief; the skill's order of who wins and the five extra motions; no rule from any of it. Section 10:
one camera flow per drawn shot (`camera_flow`, none is Fixed), printed in the brief, warned when the style does not allow it, changed without
reopening an accepted gap; the rule writer's one must for a Fixed camera. Row 7: the shared look, `vw motion note --shot all`, printed under
"Shared look". Row 5: the pictures to look at before drawing, apart from those to place. The corner note's box in the brief and the checker's look.
Without a database."""
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from app import film, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import motion_shot, motion_store
from test_design221_p1_pure import NEW, edit_plan, edit_session, run_with, visuals
from test_visuals_stage_pure import USER, g, ref

ROOT = Path(__file__).resolve().parents[2]
STYLES = ['restrained', 'lively', 'bold', 'technical', 'editorial', 'playful', 'data-led', 'product']
ENERGY = {'restrained': 3, 'editorial': 3, 'data-led': 3, 'technical': 3, 'lively': 4, 'product': 4, 'bold': 5, 'playful': 5}
CAMERA = {'technical': ['Fixed', 'Step closer', 'Pull back', 'Pan along'], 'restrained': ['Fixed', 'Step closer', 'Slow push-in'], 'data-led': ['Fixed'],
          'lively': ['Fixed', 'Step closer', 'Pull back', 'Pan along', 'Follow'], 'editorial': ['Fixed', 'Slow push-in'], 'bold': ['Fixed'], 'playful': ['Fixed'], 'product': ['Fixed']}
GONE = ['Avoid stillness', 'pans and gentle zooms', 'camera bobs', 'camera orbits', 'whole frame drifts', 'letters easing', 'push-in of a few percent across the whole shot',
        'panning along the object', 'camera snaps']


def brief(store, run=NEW):
    return VS.motion_brief(store, run, [], 'MO1')


# ---------- rows 8 and 10: the styles, their motions and the fixed paragraph ----------

def test_each_style_file_has_its_energy_its_camera_flows_and_a_family_of_four_or_five_motions():
    st = film.styles()
    assert sorted(st) == sorted(STYLES)
    for name, s in st.items():
        assert s['energy'] == ENERGY[name] and s['camera'] == CAMERA[name], name
        assert 4 <= len(s['motions']) <= 5 and all(re.match(r'^- [A-Z][^()]+ \([^)]+\): ', m) for m in s['motions']), name
        assert 120 <= len(re.findall(r'\w+', s['text'])) <= 260 and 'motions:' not in s['text'] and 'energy' not in s['text'], name
        assert not [w for w in GONE if w in s['text']], name
        assert 'letter by letter' not in ' '.join(s['motions']).lower() and 'letter-by-letter' not in ' '.join(s['motions']).lower(), name
    assert st['data-led']['text'].startswith('The numbers are the subject.') and 'The camera is fixed' in st['data-led']['text']   # unchanged


def test_a_style_file_without_a_motions_section_prints_no_motions_line(tmp_path, monkeypatch):
    (tmp_path / 'plain.md').write_text('title: Plain\nfor: tests\n\n' + 'Word ' * 130 + '\n', encoding='utf-8')
    monkeypatch.setattr(film, 'STYLE_DIR', tmp_path)
    film.styles.cache_clear()
    try:
        assert film.styles()['plain']['motions'] == [] and film.styles()['plain']['camera'] == ['Fixed'] and film.styles()['plain']['energy'] is None
        part = film.style_part(run_with(motion='plain'))
        assert 'The motions of this film' not in part and part.endswith(film.EVERY_STYLE)
    finally:
        film.styles.cache_clear()


def test_the_brief_prints_the_style_its_camera_flows_its_motions_and_the_fixed_paragraph_last_once():
    b = brief(motion_store())['brief']
    s = film.styles()['lively']
    assert s['text'].split('.')[0] in b and 'Camera flows this style allows on a shot that explains: Fixed, Step closer, Pull back, Pan along, Follow.' in b
    assert 'The motions of this film, by name. Use these for these jobs and no others:' in b
    for name in ('Label slide', 'Build in order', 'Dim the rest', 'Wipe between states', 'Quiet leave'):
        assert f'- {name} (' in b
    assert b.count(film.EVERY_STYLE) == 1 and b.rstrip().endswith(film.EVERY_STYLE)
    assert 'never letter by letter' in film.EVERY_STYLE and 'about 0.5 s plus 0.3 s for each word' in film.EVERY_STYLE
    older = VS.motion_brief(motion_store(), {**NEW, 'film': None}, [], 'MO1')['brief']   # a film from before keeps its older style, no paragraph
    assert 'In every style' not in older and 'older fixed style' in older


# ---------- section 10: the camera flow ----------

def test_the_camera_flows_are_the_six_for_explaining_and_the_plan_takes_them():
    assert list(film.CAMERA) == ['fixed', 'step_closer', 'pull_back', 'pan_along', 'follow', 'slow_push_in']
    assert set(VC.Shot.model_fields['camera_flow'].annotation.__args__) == {''} | set(film.CAMERA)
    assert VC.Shot.model_validate(motion_shot(camera_flow='pan_along')).camera_flow == 'pan_along'
    with pytest.raises(Exception):
        VC.Shot.model_validate(motion_shot(camera_flow='orbit'))   # not offered for a film that explains


def test_absent_stays_absent_and_a_camera_flow_never_reopens_an_accepted_gap():
    from test_visuals_pure import GAPS, plan, shot as pshot
    rest = [pshot('VS1', 100, 250, 'video'), pshot('VS2', 250, 500, 'video'), pshot('VS3', 500, 750, 'video'), pshot('VS4', 750, 1000, 'video')]
    out, _ = VC.validate_plan(plan([pshot('DG1', 0, 100, 'diagram'), *rest]), GAPS, Fraction(25))
    assert 'camera_flow' not in out['gaps'][0]['scenes'][0]['shots'][0]
    out, _ = VC.validate_plan(plan([{**pshot('DG1', 0, 100, 'diagram'), 'camera_flow': 'step_closer'}, *rest]), GAPS, Fraction(25))
    assert out['gaps'][0]['scenes'][0]['shots'][0]['camera_flow'] == 'step_closer'
    gap = {'gap_id': 'G1', 'scenes': [{'id': 'SC1', 'shots': [motion_shot()]}]}
    moved = {'gap_id': 'G1', 'scenes': [{'id': 'SC1', 'shots': [motion_shot(camera_flow='pull_back')]}]}
    assert VC.note_free_gap(gap) == VC.note_free_gap(moved)


def test_the_brief_names_the_shots_camera_flow_and_fixed_when_none():
    b = brief(motion_store())['brief']
    assert 'Camera: Fixed: the frame does not move; parts and labels move inside it.' in b
    b2 = brief(motion_store(sh=motion_shot(camera_flow='step_closer')))['brief']
    assert 'Camera: Step closer: once, from the whole to one part: the whole picture scales up as one group toward that part, then rests.' in b2
    assert b2.index('Camera: Step closer') < b2.index('Motion style (Lively)')   # a shot's own line, above the style


def test_a_flow_the_style_does_not_allow_is_a_plan_warning_not_a_refusal():
    def warns(run, flow):
        store = motion_store(sh=motion_shot(camera_flow=flow))
        session = VS.session_of(store, run, [])
        return [w for w in VS.carried_warnings(session, run, VS.current_plan(store, session), []) if w['kind'] == 'camera_flow']
    data_led = run_with(motion='data-led', font='Noto Sans')
    hit = warns(data_led, 'step_closer')
    assert len(hit) == 1 and hit[0]['shot_id'] == 'MO1' and 'Step closer is not one the film\'s motion style allows (Fixed)' in hit[0]['message']
    assert warns(NEW, 'step_closer') == [] and warns(data_led, 'fixed') == [] and warns(data_led, '') == []
    assert film.camera_allowed(run_with(font='Noto Sans'), 'follow')   # no style recorded yet: nothing to warn


# ---------- row 7: the shared look ----------

def two_drawn(store):
    edit_plan(store, lambda d: d['gaps'][0]['scenes'][0]['shots'].__setitem__(1, motion_shot(id='MO2', start_frame=100, end_frame=500)))


def note(store, shots, text='', remove=''):
    return VS.add_note(store, USER, NEW, [], {'shots': shots, 'text': text, 'remove': remove})


def test_the_shared_look_is_one_call_for_every_drawn_shot_and_every_brief_prints_it_apart():
    store = motion_store()
    two_drawn(store)
    out = note(store, ['all'], 'The tile pair is drawn from above, as in the footage.')
    assert out['note']['shots'] == ['MO1', 'MO2'] and out['note']['shared'] and out['next'].startswith('Recorded for every drawing of this film (the shared look)')
    note(store, ['all'], 'The tile pair is drawn from above, as in the footage.')   # the same line again is kept once
    note(store, ['all'], 'Motions (style Lively): Label slide, Build in order, Dim the rest. Extra for this film: Leader then label.')
    note(store, ['MO2'], 'The steel is shown cut across here.')
    for sid in ('MO1', 'MO2'):
        b = VS.motion_brief(store, NEW, [], sid)['brief']
        assert ('Shared look (every drawing of this film):\n- The tile pair is drawn from above, as in the footage.\n'
                '- Motions (style Lively): Label slide, Build in order, Dim the rest. Extra for this film: Leader then label.') in b
        assert 'Note on the view (the spec above wins where they differ): The tile pair' not in b
    assert 'Note on the view (the spec above wins where they differ): The steel is shown cut across here.' in VS.motion_brief(store, NEW, [], 'MO2')['brief']
    with pytest.raises(Problem, match='No note on MO1 reads'):
        g(lambda: note(store, ['MO1'], remove='The tile pair is drawn from above, as in the footage.'))   # a shared line leaves only with --shot all
    note(store, ['all'], remove='The tile pair is drawn from above, as in the footage.')
    assert 'The tile pair' not in VS.motion_brief(store, NEW, [], 'MO1')['brief'] and 'Motions (style Lively)' in VS.motion_brief(store, NEW, [], 'MO1')['brief']
    with pytest.raises(Problem, match='No shared-look line reads'):
        g(lambda: note(store, ['all'], remove='A line never recorded.'))


def test_a_film_with_no_shared_look_prints_no_such_line():
    assert 'Shared look' not in brief(motion_store())['brief']


# ---------- row 5: pictures to look at ----------

def test_the_brief_names_each_things_pictures_to_look_at_apart_from_those_to_place():
    store = motion_store()
    edit_session(store, lambda s: s['references'].update(F1={**ref('F1', 'approved'), 'kind': 'frame', 'name': 'the wall at the site'},
                                                        W9={**ref('W9', 'candidate'), 'kind': 'frame'}))
    out = brief(store)
    b = out['brief']
    assert ('Look at these before you draw (in refs/): Wall section: refs/F1.png (the wall at the site, from the footage), refs/comp-1.png (comp-1).') in b
    assert 'Pictures you may place (approved): assets/ref/comp-1.png = comp-1; assets/ref/ST1.png = ST1.' in b   # a footage frame is to look at, not to place
    assert b.count('Pictures you may place (approved): ') == 1 and 'W9' not in b and 'copies beside this brief' not in b
    assert out['refs'] == ['comp-1', 'ST1', 'F1']   # every picture named is downloaded beside the brief
    assert b.index('Look at these before you draw') < b.index('Pictures you may place')


def test_a_shot_whose_things_have_no_picture_has_no_look_line():
    store = motion_store()
    edit_session(store, lambda s: s.update(references={}))
    assert 'Look at these before you draw' not in brief(store)['brief']


# ---------- the corner area ----------

def test_the_corner_note_sentence_gives_its_box():
    b = brief(motion_store())['brief']
    assert ('Corner note: "illustrative, not to scale" is drawn by the server in the lower right corner of every frame, in the box from 80 % of the width '
            'and 90 % of the height to the edges. Do not draw it, and keep that corner free.') in b


# ---------- the texts ----------

def test_the_texts_say_the_camera_the_shared_look_the_binding_family_and_no_rule_from_the_guidance():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221c_wording_v3 as W
    import fixset2_wording as FIX2   # fix set phase 2: sentences added inside this script's sentences, and one replaced
    stage = FIX2.before(visuals())
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and olds[where].count(old) == 1, old[:50]
    import fixset3_wording as FIX3   # fix set phase 3: the frame limit and "a refused call" come inside this script's sentence of the builder
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').replace('\r\n', '\n').count(FIX3.now(file, new)) == 1, file
    plan, later = texts['plan'], texts['later']
    assert '`camera_flow`' in plan and 'One camera flow per shot; fixed when in doubt' in plan and 'a comparison and a quantity always' in plan
    gaps = (ROOT / 'plugin' / 'agents' / 'vw-plan-gaps.md').read_text(encoding='utf-8')
    assert '- `camera_flow` on a drawn shot' in gaps and 'One camera flow per shot; fixed when in doubt.' in gaps
    assert '`vw motion note --shot all --text' in later and 'Shared look (every drawing of this film)' in later and 'each with your recommended answer' in later
    assert 'goes back once to a new `vw-motion-shot` helper' in later and 'never as a fact-check rule' in later
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'A line the viewer reads holds at least 0.5 s' not in skill and 'Follow, in this order' in skill and '## The camera' in skill
    for extra in ('Leader then label', 'Count up', 'Grow from the baseline', 'Wipe between states', 'Step list'):
        assert f'- {extra} (' in skill
    assert '"Shared look (every drawing of this film)" lines hold for every drawing' in skill and 'Never stop to ask about them.' in skill
    assert 'the whole picture is one group that scales and moves' in skill and '10. The last second of the shot is still.' in skill and '8. Advice:' in skill
    assert 'Look at these before you draw' in skill and 'Look at these before you draw' in (ROOT / 'plugin' / 'agents' / 'vw-motion-shot.md').read_text(encoding='utf-8')
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert '"In every style" lines and the named motions: write no rule from them' in rules and W.FIXED_RULE in rules
    assert W.FIXED_RULE == 'The whole picture keeps its framing from the first frame to the last: nothing scales or pans the frame.'
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'those are the builder\'s guidance, not rules' in check and 'every frame where the picture holds still' in check and W.CORNER_BOX in check
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert all(s in retired for s in W.RETIRED) and all(len(s.split()) >= 4 for s in W.RETIRED)
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d221b(prompt, parts)') < split.index('d221c(prompt, parts)')
