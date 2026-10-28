"""design/120 set B: the image request on a gemini run: the provider and model, the size as aspect and tier, no transparent background (chroma green for a
component instead), the fourteen-picture ceiling by kind, the region sentence instead of a mask; an openai run unchanged."""
import json

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design111_f11_pure import golden_store, put
from test_design117_p1_pure import component_store
from test_visuals_stage_pure import FakeConn, RUN, USER, g, ref, saved

RUN_G = {**RUN, 'image_provider': 'gemini'}


def image(store, run=RUN_G, **body):
    base = {'request_id': 'q-' + str(abs(hash(json.dumps(body, sort_keys=True))))[:8], 'element_id': 'E2', 'name': 'wall', 'kind': 'isolated', 'subject': 'the wall',
            'prompt': 'Image 1 is the sheet of the wall. The wall in its yard.', 'parents': ['S2']}
    b = {**base, **body}
    if len(b['parents']) > 1 and 'Image 2' not in b['prompt']:
        b['prompt'] += ' ' + ' '.join(f'Image {k} is reference {k}: take its look.' for k in range(2, len(b['parents']) + 1))
    return VS.generate_image(FakeConn([]), store, USER, run, [], b)


def test_a_gemini_run_queues_a_gemini_image_job_with_aspect_and_tier_and_an_openai_run_is_unchanged(monkeypatch):
    store = golden_store(with_frame=False)
    conn = FakeConn([])
    out = VS.generate_image(conn, store, USER, RUN_G, [], {'request_id': 'q-g1', 'element_id': 'E2', 'name': 'wall', 'kind': 'isolated', 'subject': 'the wall', 'prompt': 'Image 1 is the sheet. The wall.', 'parents': ['S2']})
    gen = saved(store)['references'][out['reference_id']]['generation']
    assert gen['provider'] == 'gemini' and gen['model'] == VS.settings().GEMINI_IMAGE_MODEL and gen['size'] == {'aspect': '16:9', 'tier': VS.settings().GEMINI_IMAGE_SIZE} and 'background' not in gen
    assert 'gemini-image' in conn.inserted[-1] and out['model'] == VS.settings().GEMINI_IMAGE_MODEL
    store = golden_store(with_frame=False)
    conn = FakeConn([])
    out = VS.generate_image(conn, store, USER, RUN, [], {'request_id': 'q-o1', 'element_id': 'E2', 'name': 'wall', 'kind': 'isolated', 'subject': 'the wall', 'prompt': 'Image 1 is the sheet. The wall.', 'parents': ['S2']})
    gen = saved(store)['references'][out['reference_id']]['generation']
    assert gen['provider'] == 'openai' and gen['size'] == '1536x864' and gen['model'] == VS.IMAGE_MODELS['edit'] and 'openai' in conn.inserted[-1]


def test_the_fourteen_picture_ceiling_counts_by_kind_on_gemini():
    store = golden_store(with_frame=False)
    s = saved(store)
    for i in range(1, 9):
        s['references'][f'O{i}'] = {**ref(f'O{i}', 'approved'), 'kind': 'web', 'element_id': 'E2'}
    put(store, s)
    seven = ['S2'] + [f'O{i}' for i in range(1, 7)]
    with pytest.raises(Problem, match='7 object pictures.*Gemini takes at most 6'):
        g(lambda: image(store, parents=seven))
    out = image(store, parents=seven[:6], request_id='q-six')
    assert out['reference_id']
    out = image(store, run=RUN, parents=seven, request_id='q-seven-openai')   # OpenAI: sixteen untyped
    assert out['reference_id']


def test_a_component_on_gemini_asks_for_chroma_green_and_the_worker_is_told_to_key_it_out():
    store = component_store()
    out = VS.generate_image(FakeConn([]), store, USER, RUN_G, [], {'request_id': 'q-c', 'element_id': 'E2', 'name': 'wall-component', 'kind': 'component', 'subject': 'the wall', 'prompt': 'One rat-trap wall, front on, alone.', 'parents': []})
    gen = saved(store)['references'][out['reference_id']]['generation']
    assert 'flat, even chroma green' in gen['prompt'] and 'transparent background' not in gen['prompt'].split('chroma green')[1] and gen.get('chroma_key') is True and 'background' not in gen
    out = VS.generate_image(FakeConn([]), component_store(), USER, RUN, [], {'request_id': 'q-c2', 'element_id': 'E2', 'name': 'wall-component', 'kind': 'component', 'subject': 'the wall', 'prompt': 'One rat-trap wall, front on, alone.', 'parents': []})
    gen = saved(component_store())['references'].get(out['reference_id']) or {}
    assert VS.COMPONENT_BLOCK.format(name='x').count('transparent background') == 1   # OpenAI keeps the transparent background


def test_a_region_edit_on_gemini_says_the_region_in_words():
    from test_design106_pure import revise_start, start_store
    store = start_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])
    out = VS.generate_image(FakeConn([]), store, USER, RUN_G, [], {'request_id': 'q-end', 'element_id': 'E1', 'name': 'end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer', 'role': 'end',
                                                                  'region': {'left': 0.1, 'top': 0.2, 'width': 0.5, 'height': 0.5}, 'parents': ['K1'],
                                                                  'prompt': 'Image 1 is the start image: keep everything; the labourer lays the brick.'})
    gen = saved(store)['references'][out['reference_id']]['generation']
    assert 'Change only what is inside the region left 10 %, top 20 %, width 50 %, height 50 % of Image 1; everything outside it exactly as Image 1.' in gen['prompt'] and gen['region']


def test_the_ledger_prices_gemini_flat_and_counts_both_providers():
    pr = {'image_inr': 4.0, 'video_inr_per_s': 8.9, 'usd_inr': 88.0}
    assert VS.image_cost_inr({'provider': 'gemini', 'tier': '2K', 'inputs': 2}, pr) == pytest.approx((0.134 + 2 * 0.0011) * 88.0)
    assert VS.image_cost_inr({'provider': 'gemini', 'tier': '4K', 'inputs': 0}, pr) == pytest.approx(0.24 * 88.0)
    assert VS.image_cost_inr({'provider': 'openai'}, pr) == 4.0 and VS.image_cost_inr(None, pr) == 4.0
    rows = [{'provider': 'openai', 'status': 'retained', 'request': {}, 'cost': None}, {'provider': 'gemini-image', 'status': 'retained', 'request': {}, 'cost': {'provider': 'gemini', 'tier': '2K', 'inputs': 0}}]

    class Conn:
        def execute(self, sql, params=()):
            assert "'gemini-image'" in sql

            class R:
                def fetchall(_):
                    return rows
            return R()
    sp = VS.visuals_spend(Conn(), RUN)
    assert sp['images'] == 2 and sp['spent_inr'] == pytest.approx(4.0 + 0.134 * VS.prices()['usd_inr'], abs=0.01)
