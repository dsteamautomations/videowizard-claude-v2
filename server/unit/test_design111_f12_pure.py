"""design/111 F12: every element carries a "not this" list, made by one method (the near misses and nothing-fits reasons of the round, one Gemini call for the
common wrong forms, this film's own rejections as they happen), kept across films in the library's store, pasted by the server into every prompt that
shows the element, a shot's named exception left out of its line; a material's list is built with its spec approval when it is still missing."""
import json
from pathlib import Path

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design106_pure import revise_start
from test_design111_f10_pure import material_store
from test_visuals_stage_pure import RUN, USER, FakeConn, g, ref, saved

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def put(store, s):
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


class Transport:
    calls = []

    def __init__(self, key, model, **kw):
        self.model = model

    def generate(self, payload):
        Transport.calls.append(payload)
        return {'body': {'lines': ['no running bond', 'no honeycomb holes', 'no plaster over the face', 'no plaster over the face']}, 'raw': ''}


def listed_store(monkeypatch):
    store = material_store()
    s = saved(store)
    s['searches'] = {'S9': {'search_id': 'S9', 'element_id': 'BRICK', 'keywords': 'rat trap bond wall', 'results': [{'n': 1, 'title': 'plastered garden wall', 'site': 'x'}, {'n': 2, 'title': 'rat-trap bond close-up', 'site': 'y'}],
                            'picked': [2], 'nothing_fits': None}}
    s['references']['X1'] = {**ref('X1', 'rejected'), 'kind': 'isolated', 'element_id': 'BRICK', 'rejection': {'notes': 'the bricks are long and thin, not on edge', 'quote': 'no', 'by': 'u1', 'at': 't'}}
    put(store, s)
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Transport)
    real = VS.settings()

    class Settings:
        GEMINI_API_KEY = __import__('types').SimpleNamespace(get_secret_value=lambda: 'k')

        def __getattr__(self, name):
            return getattr(real, name)
    monkeypatch.setattr(VS, 'settings', lambda: Settings())
    Transport.calls = []
    return store


# ---------- built by one method, kept in the library ----------

def test_the_list_is_built_from_the_round_the_model_and_the_rejections_and_kept_across_films(monkeypatch):
    store = listed_store(monkeypatch)
    out = VS.not_this(store, USER, RUN, [], 'BRICK')
    assert out['lines'] == ['no running bond', 'no honeycomb holes', 'no plaster over the face', 'the bricks are long and thin, not on edge']   # the model's lines once, then this film's rejection
    assert out['from'] == {'library': 0, 'model': 3, 'rejections': 1} and len(Transport.calls) == 1
    asked = json.dumps(Transport.calls[0])
    assert 'plastered garden wall' in asked and 'rat-trap bond close-up' not in asked and 'Material spec, Red brick' in asked   # the unticked result and the spec go to the model; the picked one does not
    assert saved(store)['not_this']['BRICK']['lines'] == out['lines']
    kept = json.loads(store.files['library/not-this/red-brick.json'])
    assert kept['lines'] == out['lines'] and kept['element'] == 'Red brick'
    store2 = listed_store(monkeypatch)
    store2.files['library/not-this/red-brick.json'] = json.dumps({'element': 'Red brick', 'lines': ['no pitched coping', 'no running bond']}).encode('utf-8')
    out2 = VS.not_this(store2, USER, RUN, [], 'BRICK')
    assert out2['lines'][:2] == ['no pitched coping', 'no running bond'] and out2['from']['library'] == 2 and 'no running bond' not in out2['lines'][2:]
    with pytest.raises(Problem, match='not an element'):
        g(lambda: VS.not_this(store, USER, RUN, [], 'NOPE'))


def test_a_rejection_adds_its_line_at_once(monkeypatch):
    store = listed_store(monkeypatch)
    VS.not_this(store, USER, RUN, [], 'BRICK')
    s = saved(store)
    s['references']['X2'] = {**ref('X2', 'candidate'), 'kind': 'isolated', 'element_id': 'BRICK'}
    put(store, s)
    VS.reject_reference(store, USER, RUN, [], 'X2', 'holes between the bricks', 'no')
    s = saved(store)
    assert s['not_this']['BRICK']['lines'][-1] == 'holes between the bricks' and json.loads(store.files['library/not-this/red-brick.json'])['lines'][-1] == 'holes between the bricks'
    VS.reject_reference(store, USER, RUN, [], 'X2', 'holes between the bricks', 'no')   # the same words again: once
    assert saved(store)['not_this']['BRICK']['lines'].count('holes between the bricks') == 1


# ---------- pasted into every prompt; a shot's exception left out; the spec approval builds it when missing ----------

def test_the_server_pastes_the_list_into_every_prompt_and_a_shots_exception_is_left_out(monkeypatch):
    store = listed_store(monkeypatch)
    with pytest.raises(Problem, match='material spec of BRICK is not approved'):
        g(lambda: revise_start(store, role='start'))
    VS.approve_spec(store, USER, RUN, [], 'element:BRICK', '')   # builds the list on the way, once
    assert len(Transport.calls) == 1 and saved(store)['not_this']['BRICK']['lines']
    rid = revise_start(store, role='start')['reference_id']
    p = saved(store)['references'][rid]['generation']['prompt']
    assert p.count('Not this (Red brick): ') == 1 and 'no running bond; no honeycomb holes; no plaster over the face; the bricks are long and thin, not on edge' in p
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['gaps'][1]['scenes'][0]['shots'][0]['allows'] = ['honeycomb holes']
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    from test_visuals_stage_pure import accepted
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    put(store, s)
    rid2 = revise_start(store, role='start', request_id='r-allow')['reference_id']
    p2 = saved(store)['references'][rid2]['generation']['prompt']
    assert 'no honeycomb holes' not in p2 and 'no running bond' in p2 and 'Except in this shot: honeycomb holes' in p2
    st = VS.status(FakeConn([]), store, RUN, [], repair=False)
    assert st['not_this']['BRICK'][0] == 'no running bond'
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9', False)
    assert next(e for e in view['elements'] if e['id'] == 'BRICK')['not_this'][:1] == ['no running bond']


def test_the_page_and_the_tool_know_the_list():
    assert 'Not this:' in PAGE and 'e.not_this' in PAGE
    proc = (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')
    assert 'vw visuals not-this' in proc and 'not this' in proc.lower()
