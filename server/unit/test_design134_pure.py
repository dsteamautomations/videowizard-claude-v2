"""design/134: SK's decisions on the Codex process review (2 Nov 2026), the server side. Findings 1, 2, 3, 6, 7, 8, 9/10 (the retired sentences),
12, 16, 17, 18."""
import inspect
import json
import re
from pathlib import Path

from app import library, visual_contract as VC, visuals_stage as VS
from app.stage3 import delivery as D

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
V3 = json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
PLAN = {'elements': [{'id': 'mason', 'name': 'Mason', 'kind': 'person'}, {'id': 'trowel', 'name': 'trowel', 'kind': 'object'}, {'id': 'level', 'name': 'spirit level', 'kind': 'object'},
                     {'id': 'wall', 'name': 'wall', 'kind': 'object'}, {'id': 'lorry', 'name': 'lorry', 'kind': 'object'}]}
SCENE = {'landmarks': [{'id': 'L1', 'description': 'the half-built wall'}], 'light': 'dim interior, one bulb'}


# ---------- 1: the tool sentence ----------

def shot_with(*props):
    return {'id': 'S1', 'props': list(props), 'subjects': []}


def test_1_a_holder_with_two_tools_is_never_told_he_holds_nothing_else():
    lines = VS.tool_lines(PLAN, SCENE, shot_with({'element_id': 'trowel', 'holder': 'mason', 'start': {'relation': 'in front of', 'landmark_id': 'L1'}},
                                                 {'element_id': 'level', 'holder': 'mason', 'start': {'relation': 'on', 'landmark_id': 'L1'}}), 'start')
    assert len(lines) == 2 and not any('holds nothing else' in l for l in lines) and all('fully inside the frame' in l for l in lines)


def test_1_a_tool_carried_out_is_not_also_fully_inside_at_the_end():
    p = {'element_id': 'trowel', 'holder': 'mason', 'start': {'relation': 'in front of', 'landmark_id': 'L1'}, 'end': {'where': 'carried_out', 'cause': 'the mason'}}
    assert 'fully inside the frame' in VS.tool_lines(PLAN, SCENE, shot_with(p), 'start')[0]
    for when in ('end', 'motion'):
        line = VS.tool_lines(PLAN, SCENE, shot_with(p), when)[0]
        assert 'fully inside the frame' not in line and 'out of frame' in line


# ---------- 7: a planned look at the camera ----------

def gazing(target):
    return {'id': 'S1', 'subjects': [{'element_id': 'mason', 'start': {'gaze': {'target': 'L1', 'head_turn': 'none', 'mouth': 'closed'}},
                                      'end': {'gaze': {'target': target, 'head_turn': 'none', 'mouth': 'closed'}}}], 'props': []}


def test_7_no_one_looks_at_the_lens_unless_the_plan_says_so():
    assert 'No one looks at the lens' in ' '.join(VS.gaze_lines(PLAN, SCENE, gazing('L1'), 'end'))
    assert 'looks at the lens' not in ' '.join(VS.gaze_lines(PLAN, SCENE, gazing(VC.GAZE_CAMERA), 'end'))   # found here: the prompt line had the same clash
    src = inspect.getsource(VS.picture_rule_lines)
    assert "no one looks at the lens" in src and 'looks_at_camera' in src


# ---------- 3: the film's measured light against the scene's own ----------

class Store:
    def get(self, key):
        return b''


def light_session():
    return {'footage': {'summary': {'look': 'natural', 'camera': 'unknown'}},
            'references': {f'F{i}': {'kind': 'frame', 'status': 'approved', 'key': f'k{i}'} for i in range(3)}}


def test_3_a_scene_with_its_own_light_keeps_only_the_look_and_the_no_glow_clause(monkeypatch):
    monkeypatch.setattr(VS.image_check, '_light', lambda b: {'brightness': 0.9, 'saturation': 0.6, 'warmth': 0.1})
    s = light_session()
    whole = VS.real_light_line(Store(), s)
    assert 'bright light' in whole and 'No studio light, no glow, no added saturation' in whole
    own = VS.real_light_line(Store(), s, SCENE)
    assert 'bright' not in own and 'warm cast' not in own and 'natural look' in own and 'No studio light, no glow, no added saturation' in own
    assert VS.real_light_line(Store(), s, {'landmarks': []}) == whole   # a scene with no light of its own: as today


# ---------- 2 and 16: the drawn-shot brief's pictures and rules ----------

def brief_session():
    refs = {'SH-W': {'status': 'approved', 'key': 'k', 'kind': 'sheet', 'element_id': 'wall'}, 'SH-L': {'status': 'approved', 'key': 'k', 'kind': 'sheet', 'element_id': 'lorry'},
            'GO-W': {'status': 'approved', 'key': 'k', 'kind': 'isolated', 'element_id': 'wall'}, 'ST': {'status': 'approved', 'key': 'k', 'kind': 'style', 'element_id': '_STYLE'},
            'CO-L': {'status': 'approved', 'key': 'k', 'kind': 'component', 'element_id': 'lorry'}, 'OLD': {'status': 'rejected', 'key': 'k', 'kind': 'sheet', 'element_id': 'wall'}}
    return {'references': refs, 'golden': {'wall': 'GO-W'}}


def test_2_16_the_brief_gets_the_shots_own_pictures_its_golden_picture_and_the_style():
    ids = [rid for rid, _ in VS.brief_pictures(brief_session(), {'element_ids': ['wall']})]
    assert sorted(ids) == ['GO-W', 'SH-W', 'ST']
    assert sorted(rid for rid, _ in VS.brief_pictures(brief_session(), {'element_ids': ['lorry']})) == ['CO-L', 'SH-L', 'ST']


def test_16_subject_rules_match_the_shots_own_words(monkeypatch):
    monkeypatch.setattr(VS, 'subject_rule_files', lambda: ['rat-trap-bond', 'lorry-delivery'])
    plan = {'foundation': {'appearance': 'a rat-trap bond wall and a lorry delivery'}, 'gaps': []}
    assert VS._subjects_of(plan, {'narration': 'The lorry delivery arrives at dawn.', 'depicts': 'a tipper lorry'}) == ['lorry-delivery']
    assert VS._subjects_of(plan) == ['rat-trap-bond', 'lorry-delivery']   # the whole film, as before, where no shot is named


# ---------- 6: approve all specs ----------

def test_6_bulk_approval_builds_the_not_this_list_and_the_page_shows_the_materials():
    src = inspect.getsource(VS.approve_specs)
    assert 'not_this(store, user, run, outputs' in src and 'except (Problem, ValueError)' in src
    assert 'material_spec' in PAGE[PAGE.index('function specsBlock'):PAGE.index('function materialBox')]


# ---------- 8: the shot's progression is not exact text ----------

def test_8_copy_is_none_unless_a_graphic_state_carries_labels():
    run, gap, card = {'code': 'VW-9', 'image_provider': 'gemini'}, {'intent': '', 'treatment_fit': ''}, {}
    shot = {'id': 'S1', 'narration': 'Steam rises.', 'purpose': 'kiln', 'information_progression': 'steam slowly builds above the kiln', 'end_frame': 100, 'start_frame': 0}
    form = library.job_form('still-scene', run=run, plan={'foundation': {}}, gap=gap, scene={}, shot=shot, refs=[], generator=None, brief={}, card=card, rules=[])
    assert form['copy'] == 'none'
    state = library.job_form('state', run=run, plan={'foundation': {}}, gap=gap, scene={}, shot={**shot, 'states': [{'what_appears': 'Fewer bricks'}]}, refs=[], generator=None, brief={}, card=card, rules=[])
    assert state['copy'] == [{'role': 'label', 'text': 'Fewer bricks'}]


# ---------- 9, 10 and the retired sentences ----------

RETIRED = json.loads((ROOT / 'retired-sentences.json').read_text(encoding='utf-8'))


def ai_text():
    st = next(s for s in V3['stages'] if s['name'] == 'visuals')
    agents = ''.join(p.read_text(encoding='utf-8') for p in list((ROOT.parent / 'plugin' / 'agents').glob('*.md')) + list((ROOT.parent / 'plugin' / 'commands').glob('*.md')))   # design/142: the command text too
    return json.dumps(V3, ensure_ascii=False) + st['prompt'] + ''.join(p['text'] for p in st['parts']) + agents


def test_9a_no_retired_sentence_is_in_the_text_the_ai_reads():
    assert RETIRED['sentences'] and all(len(s.split()) >= 4 for s in RETIRED['sentences'])
    text = ai_text()
    assert [s for s in RETIRED['sentences'] if s in text] == []


def test_9_10_the_new_wording_is_there():
    st = next(s for s in V3['stages'] if s['name'] == 'visuals')
    later = next(p for p in st['parts'] if p['name'] == 'later')['text']
    assert 'the older `bind`, `packet`, start image, `prepare-take` and `take` are retired for them' in later   # design/181: the guide replaces them (was: 'then the start image, with an end request only when end_state_exact is true')
    assert 'A labelled diagram is drawn (HyperFrames on a motion film)' in st['prompt'] and 'with `vw visuals draw` only on a `--drawn svg` film' in st['prompt']


# ---------- 12: the cost preview at the generated seconds ----------

def test_12_take_seconds_round_up_with_the_generators_minimum():
    assert VC.take_seconds(3.2) == 4 and VC.take_seconds(2.0) == 3 and VC.take_seconds(4.0) == 4 and VC.take_seconds(4.00000001) == 4


def test_12_routes_carry_the_generated_seconds_and_the_previews_use_them():
    plan = {'gaps': [{'gap_id': 'G1', 'scenes': [{'shots': [{'id': f'V{i}', 'visual_type': 'video', 'start_frame': 80 * i, 'end_frame': 80 * i + 80} for i in range(10)]}]}]}
    r = VC.routes(plan, 25)
    assert r['seconds']['video'] == 32.0 and r['video_take_seconds'] == 40
    src = inspect.getsource(VS)
    assert src.count("r['video_take_seconds']") >= 2 and 'take_seconds(float(x))' in inspect.getsource(VS.treatment)


# ---------- 17: the older delivery rebuild ----------

def test_17_the_bundle_points_to_the_new_route_only():
    src = inspect.getsource(D)
    assert '`--run --authorization' not in src and '`vw delivery open`' in src


# ---------- 18: no design-note labels in what the server says ----------

def test_18_no_refusal_or_next_message_carries_a_design_label():
    found = []
    for p in list((ROOT / 'app').glob('*.py')) + list((ROOT / 'app' / 'stage2').glob('*.py')) + list((ROOT / 'app' / 'stage3').glob('*.py')):
        for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('   #')[0]
            if re.search(r"(need\(|Problem\(|'next':).*\(?(proposed before )?design/\d", code):
                found.append(f'{p.name}:{n}')
    assert found == []


def test_every_file_in_procedures_is_a_procedure_the_server_can_load():
    """2 Nov 2026: a data file without a version in server/procedures/ stopped the server at start-up (db.migrate loads every *.json there)."""
    for p in (ROOT / 'procedures').glob('*.json'):
        assert 'version' in json.loads(p.read_text(encoding='utf-8')), p.name
