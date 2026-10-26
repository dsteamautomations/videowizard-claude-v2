"""design/103, Release 5 (course batch A; design/93 G1, G2): the plan's new fields, their warnings, the fingerprints they leave alone,
the take's light line, the keyframe prompt's light warning, the procedure and the page."""
import json
from fractions import Fraction
from pathlib import Path

from app import visual_contract as VC, visuals_stage as VS
from app.video_providers import motion_text
from test_design101_pure import snapshot, take_store
from test_visuals_stage_pure import RUN, gap_digest
from test_visuals_pure import GAPS, plan, shot as pshot

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
LIGHT = 'Late-morning sun from behind the half-built house, hard and warm; the lane in its light, the stacks in soft shade'


def doc_(*shots, **scene):
    d = plan(list(shots))
    d['gaps'][0]['scenes'][0].update(scene)
    return d


def kinds(d, fps=Fraction(25)):
    return [(w.get('scene_id') or w.get('shot_id') or w.get('element_id') or w.get('gap_id'), w['kind']) for w in VC.validate_plan(d, GAPS, fps)[1]]


def sized(sid, a, b, size, vt='video', **extra):
    return {**pshot(sid, a, b, vt), 'size': size, **extra}


# ---------- the fields: defaults, absent stays absent ----------

def test_the_new_fields_default_empty_and_stay_absent_when_absent():
    out, _ = VC.validate_plan(doc_(pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video')), GAPS, Fraction(25))
    sc, sh, el = out['gaps'][0]['scenes'][0], out['gaps'][0]['scenes'][0]['shots'][0], out['elements'][0]
    assert not {'light', 'air'} & set(sc) and not {'size', 'size_reason', 'camera_reason', 'claim'} & set(sh) and 'size' not in el
    d = doc_(sized('VS1', 0, 500, 'WS', camera_reason='eye level: honest', claim='visible'), pshot('VS2', 500, 1000, 'video'), light=LIGHT, air='fine dust in the light')
    d['elements'][0]['size'] = [{'part': 'block', 'measure': 'length', 'value': 29, 'unit': 'cm', 'source': 'client sheet', 'status': 'confirmed'}]
    out, _ = VC.validate_plan(d, GAPS, Fraction(25))
    assert out['gaps'][0]['scenes'][0]['light'] == LIGHT and out['gaps'][0]['scenes'][0]['shots'][0]['size'] == 'WS' and out['elements'][0]['size'][0]['value'] == 29


# ---------- the warnings ----------

def test_a1_a4_a5_warn_until_filled():
    d = doc_(pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video'))
    k = kinds(d)
    assert ('SC1', 'light_missing') in k and ('VS1', 'camera_reason_missing') in k and ('E1', 'element_size_missing') in k
    d = doc_({**pshot('VS1', 0, 500, 'video'), 'camera_reason': 'eye level, honest'}, {**pshot('VS2', 500, 1000, 'video'), 'camera_reason': 'a slow push draws in'}, light=LIGHT)
    d['elements'][0]['size'] = [{'part': 'block', 'measure': 'length', 'value': 29, 'unit': 'cm', 'status': 'confirmed'}]
    k = kinds(d)
    assert not {'light_missing', 'camera_reason_missing', 'element_size_missing'} & {w for _, w in k}
    d['elements'][0].update(kind='place', size=[])
    assert ('E1', 'element_size_missing') not in kinds(d)   # a place's size is optional


def test_a3_size_order_rules_and_a_stated_reveal():
    k = kinds(doc_(sized('VS1', 0, 300, 'CU'), sized('VS2', 300, 1000, 'MS')))
    assert ('VS1', 'size_open') in k and ('VS1', 'size_close_first') in k
    k = kinds(doc_(sized('VS1', 0, 200, 'WS'), sized('VS2', 200, 400, 'MS'), sized('VS3', 400, 600, 'MS'), sized('VS4', 600, 1000, 'MS')))
    assert ('VS4', 'size_repeat') in k and not any(w in ('size_open', 'size_close_first') for _, w in k)
    k = kinds(doc_(sized('VS1', 0, 500, 'WS'), sized('VS2', 500, 1000, 'CU')))
    assert not any(w.startswith('size_') for _, w in k)   # seen wide first, then close
    k = kinds(doc_(sized('VS1', 0, 300, 'ECU', size_reason='a reveal: the hand first, the wall after'), sized('VS2', 300, 1000, 'WS')))
    assert not any(w.startswith('size_') for _, w in k)


def test_g1_graphic_seconds_in_a_row_and_g2_a_visible_claim_on_a_graphic():
    short = kinds(doc_(pshot('DG1', 0, 100, 'diagram'), pshot('DG2', 100, 175, 'diagram'), pshot('VS1', 175, 600, 'video'), pshot('VS9', 600, 1000, 'video')))
    assert not any(w == 'graphics_run' for _, w in short)   # 7 s
    k = VC.validate_plan(doc_(pshot('DG1', 0, 125, 'diagram'), pshot('DG2', 125, 250, 'diagram'), pshot('VS1', 250, 1000, 'video')), GAPS, Fraction(25))[1]
    run = [w for w in k if w['kind'] == 'graphics_run']
    assert run and '10.0 s' in run[0]['message'] and 'next release' not in run[0]['message']
    k = VC.validate_plan(doc_(pshot('DG1', 0, 175, 'diagram'), pshot('DG2', 175, 350, 'diagram'), pshot('VS1', 350, 1000, 'video')), GAPS, Fraction(25))[1]
    assert 'refused from the next release' in [w for w in k if w['kind'] == 'graphics_run'][0]['message']
    k = kinds(doc_(pshot('DG1', 0, 125, 'diagram'), pshot('VS0', 125, 200, 'video'), pshot('DG2', 200, 325, 'diagram'), pshot('VS1', 325, 1000, 'video')))
    assert not any(w == 'graphics_run' for _, w in k)   # a camera shot between resets the run
    k = kinds(doc_({**pshot('DG1', 0, 100, 'diagram'), 'claim': 'visible'}, {**pshot('VS1', 100, 600, 'video'), 'claim': 'visible'}, pshot('VS9', 600, 1000, 'video')))
    assert ('DG1', 'claim_visible_graphic') in k and ('VS1', 'claim_visible_graphic') not in k


# ---------- the fingerprints ----------

def test_the_new_fields_change_no_gaps_digest_and_no_takes_preparation_digest():
    plain, store_plain = take_store()[1], take_store()[0]
    store_lined, lined = take_store()
    sc = lined['gaps'][1]['scenes'][0]
    sc.update(light=LIGHT, air='dust')
    sc['shots'][0].update(size='WS', size_reason='', camera_reason='eye level', claim='visible')
    lined['elements'][0]['size'] = [{'part': 'p', 'measure': 'm', 'status': 'unknown'}]
    store_lined.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': lined}).encode('utf-8')
    assert gap_digest(plain, plain['gaps'][1]) == gap_digest(lined, lined['gaps'][1])
    assert VS.packet(store_plain, RUN, [], 'VS1')['preparation_digest'] == VS.packet(store_lined, RUN, [], 'VS1')['preparation_digest']
    assert VS.packet(store_lined, RUN, [], 'VS1')['preparation']['scene']['light'] == LIGHT   # the writer still reads them


# ---------- the take's light line; the keyframe prompt's light warning ----------

def test_every_new_take_in_a_lit_scene_keeps_its_light():
    text = motion_text(snapshot(light=LIGHT))
    assert text.count('The light does not change: ' + LIGHT + '.') == 1
    assert 'The light does not change' not in motion_text(snapshot())


def test_a_keyframe_prompt_without_its_scenes_light_sentence_is_warned():
    assert VS.light_warning({'light': LIGHT}, 'keyframe', 'A labourer walks the lane.')
    assert not VS.light_warning({'light': LIGHT}, 'keyframe', 'A labourer walks the lane. ' + LIGHT + '.')
    assert not VS.light_warning({}, 'keyframe', 'A labourer walks the lane.') and not VS.light_warning({'light': LIGHT}, 'sheet', 'x')


# ---------- the procedure and the page ----------

def test_the_procedure_carries_a4_a6_a7():
    doc = json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    steps = next(s for s in doc['stages'] if s['name'] == 'visuals')['steps']
    assert 'eye level is honest' in steps[2] and 'non-speaking angles' in steps[2]
    assert 'has no real footage beside it' in steps[1]
    assert 'real size' in steps[3]


def test_the_page_shows_size_reason_light_air_and_element_sizes():
    for words in ("'Size: '+esc(s.size)", "'Camera: '+esc(s.camera_reason)", "'Light: '+esc(s.light)", "'Air: '+esc(s.air)", "'Size: '+e.size.map("):
        assert words in PAGE, words
