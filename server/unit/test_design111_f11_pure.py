"""design/111 F11 (+F41): one golden picture per element, made at the References step right after the sheet (and the material spec) are approved,
written by the assistant on the server's cue; every later picture of the element has it as Image 1; a derived picture is never a parent (the start
of an end excepted, and a graphic's states); a flawed picture cannot be golden; the footage-frame rule applies to the golden picture's making;
an end image is an edit inside one region (a rectangle in fractions of the frame, a third at most): the server masks it and copies the start back
outside it, and keeps how much the model changed outside."""
import base64
import copy
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_design106_pure import END, approvable, revise_start, start_store
from test_visuals_stage_pure import RUN, USER, FakeConn, accepted, g, ref, saved

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
REGION = {'left': 0.1, 'top': 0.2, 'width': 0.5, 'height': 0.5}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def put(store, s):
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


def golden_store(with_frame=True):
    """start_store plus E2, the client's own wall (an exact object) with an approved sheet S2 and, by default, an approved footage frame F2; VS1 shows E1 and E2."""
    store = start_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'].append({'id': 'E2', 'name': 'Rat-trap wall', 'kind': 'object', 'identity': 'exact', 'requirements': 'the client\'s wall'})
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'E2']
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    s['references']['S2'] = {**ref('S2', 'approved'), 'kind': 'sheet', 'element_id': 'E2'}
    if with_frame:
        s['references']['F2'] = {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'E2'}
    put(store, s)
    return store


def image(store, **body):
    base = {'request_id': body.pop('request_id', 'q-' + str(abs(hash(json.dumps(body, sort_keys=True))))[:8]), 'element_id': 'E2', 'name': 'wall', 'kind': 'isolated', 'subject': 'the wall',
            'prompt': 'Image 1 is the sheet of the wall. The wall in its yard.', 'parents': ['S2']}
    b = {**base, **body}
    if len(b['parents']) > 1 and 'Image 2' not in b['prompt']:   # design/111 F21: a job line per picture
        b['prompt'] += ' ' + ' '.join(f'Image {k} is reference {k}: take its look.' for k in range(2, len(b['parents']) + 1))
    return VS.generate_image(FakeConn([]), store, USER, RUN, [], b)


# ---------- the golden picture: due, made, approved ----------

def test_the_golden_picture_is_due_after_the_sheet_is_approved_made_with_the_footage_frame_and_marked_on_approval():
    store = golden_store()
    assert VS.status(FakeConn([]), store, RUN, [], repair=False)['golden_due'] == [{'element_id': 'E2', 'next': 'write the golden picture of E2 now: `vw visuals image --element E2 --kind isolated --golden --parents S2,F2 …`'}]
    with pytest.raises(Problem, match="E2 is the client's own: send one of its approved footage frames"):
        g(lambda: image(store, golden=True))
    out = image(store, golden=True, parents=['S2', 'F2'], request_id='q-gold')
    row = saved(store)['references'][out['reference_id']]
    assert row['golden_candidate'] is True and VS.status(FakeConn([]), store, RUN, [], repair=False)['golden_due'] == []   # being made: not due twice
    approvable(store, out['reference_id'])
    VS.approve_reference(store, USER, RUN, [], out['reference_id'], 'a' * 64, '', FakeConn([]))
    s = saved(store)
    assert s['golden'] == {'E2': out['reference_id']}
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9', False)
    assert view['golden'] == {'E2': out['reference_id']} and next(r for r in view['references'] if r['id'] == out['reference_id'])['golden'] is True
    with pytest.raises(Problem, match='E2 already has its golden picture'):
        g(lambda: image(store, golden=True, parents=['S2', 'F2'], request_id='q-gold2'))
    with pytest.raises(Problem, match='golden picture is a picture of an object'):
        g(lambda: image(store, golden=True, kind='keyframe', parents=['S2', 'F2'], request_id='q-gold3'))


def test_a_flawed_picture_cannot_be_golden_and_a_persons_sheet_is_its_golden_picture():
    store = golden_store()
    out = image(store, golden=True, parents=['S2', 'F2'], request_id='q-gold')
    s = saved(approvable(store, out['reference_id']))
    s['references'][out['reference_id']]['not_yet_ok'] = True
    put(store, s)
    with pytest.raises(Problem, match='cannot be the golden picture: it was approved with a stated flaw'):
        g(lambda: VS.approve_reference(store, USER, RUN, [], out['reference_id'], 'a' * 64, '', FakeConn([])))
    assert 'golden' not in saved(store) or 'E2' not in saved(store)['golden']
    store = golden_store()
    doc = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    doc['elements'][0]['kind'] = 'person'
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['bindings']['VS1']['gap_digest'] = s['accepted']['G2']['digest']
    s['references']['SH1'] = {**ref('SH1', 'candidate'), 'kind': 'sheet', 'element_id': 'E1', 'sha256': 'b' * 64}
    put(store, s)
    VS.approve_reference(store, USER, RUN, [], 'SH1', 'b' * 64, '', FakeConn([]))
    assert saved(store)['golden']['E1'] == 'SH1' and 'E1' not in [d['element_id'] for d in VS.status(FakeConn([]), store, RUN, [], repair=False)['golden_due']]


# ---------- every later picture is an edit of the golden picture; the chain goes back to it ----------

def test_a_picture_of_an_element_with_a_golden_picture_starts_from_it_and_a_derived_parent_is_refused():
    store = golden_store()
    gold = image(store, golden=True, parents=['S2', 'F2'], request_id='q-gold')['reference_id']
    approvable(store, gold)
    VS.approve_reference(store, USER, RUN, [], gold, 'a' * 64, '', FakeConn([]))
    with pytest.raises(Problem, match=f'E2 has its golden picture \\({gold[:8]}'):
        g(lambda: image(store, request_id='q-wrong', parents=['S2']))
    start = image(store, request_id='q-start', kind='keyframe', shot_id='VS1', parents=[gold], prompt='Image 1 is the wall. The wall with the mason beside it.', role='start')['reference_id']
    approvable(store, start)
    s = saved(store)
    s['references'][start]['status'] = 'approved'
    put(store, s)
    with pytest.raises(Problem, match=f'E2 has its golden picture \\({gold[:8]}'):   # a start as the parent of another start: Image 1 is the golden picture
        g(lambda: image(store, request_id='q-derived', kind='keyframe', shot_id='VS1', parents=[start], prompt='Image 1 is the start. The wall again.', role='start'))
    s = saved(store)   # an element without a golden picture: a derived parent is refused on its own account
    s['references']['K2'] = {**ref('K2', 'approved'), 'kind': 'keyframe', 'element_id': 'E1', 'shot_id': 'VS1', 'role': 'start', 'generation': {'op': 'edit', 'parents': [{'id': 'K1'}]}}
    put(store, s)
    with pytest.raises(Problem, match='K2 is a derived picture'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'q-k2', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer',
                                                                       'prompt': 'Image 1 is the start; the labourer.', 'parents': ['K2'], 'role': 'start'}))
    end = image(store, request_id='q-end', kind='keyframe', shot_id='VS1', parents=[start], prompt='Image 1 is the start; the mason has laid the brick.', role='end', region=REGION)
    assert saved(store)['references'][end['reference_id']]['generation']['region'] == REGION   # an end from its start: the one allowed derivation
    with pytest.raises(Problem, match='fix round is never a parent'):
        s = saved(store)
        s['references']['FX1'] = {**ref('FX1', 'approved'), 'kind': 'keyframe', 'element_id': 'E2', 'shot_id': 'VS1', 'fix_of': start, 'generation': {'op': 'edit', 'parents': [{'id': start}]}}
        put(store, s)
        g(lambda: image(store, request_id='q-fromfix', kind='keyframe', shot_id='VS1', parents=['FX1'], prompt='Image 1 is the start; the end.', role='end', region=REGION))


def test_the_footage_frame_rule_moves_to_the_golden_pictures_making():
    store = golden_store()
    body = {'request_id': 'q-k', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer', 'prompt': 'Image 1 is the old start; the labourer at the stack.',
            'parents': ['K1'], 'role': 'start'}
    with pytest.raises(Problem, match="E2 is the client's own: send one of its approved footage frames"):   # no golden yet: the old rule holds on every keyframe
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))
    gold = image(store, golden=True, parents=['S2', 'F2'], request_id='q-gold')['reference_id']
    approvable(store, gold)
    VS.approve_reference(store, USER, RUN, [], gold, 'a' * 64, '', FakeConn([]))
    assert VS.generate_image(FakeConn([]), store, USER, RUN, [], body)['reference_id']   # the golden picture carries the frame; every edit inherits it


# ---------- the edit route: one region, masked, the outside copied back ----------

def test_an_ends_region_is_a_third_at_most_and_may_be_written_with_the_start():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    s = saved(approvable(store, rid))
    s['references'][rid]['status'] = 'approved'
    put(store, s)
    body = {'request_id': 'q-e', 'element_id': 'E1', 'name': 'keyframe-end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer', 'prompt': 'Image 1 is the start; the labourer at the edge.',
            'parents': [rid], 'role': 'end'}
    assert VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'q-whole'})['reference_id']   # no region: several things change, the end is made whole
    with pytest.raises(Problem, match='covers 50 % of the frame'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'region': {'left': 0, 'top': 0, 'width': 1, 'height': 0.5}}))
    with pytest.raises(Problem, match='inside the frame'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'region': {'left': 0.8, 'top': 0, 'width': 0.5, 'height': 0.2}}))
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'region': REGION})
    assert saved(store)['references'][out['reference_id']]['generation']['region'] == REGION
    with pytest.raises(Problem, match='covers 50 %'):
        g(lambda: revise_start(store, role='start', request_id='q-s3', end_region={'left': 0, 'top': 0, 'width': 1, 'height': 0.5}))
    s2 = revise_start(store, role='start', request_id='q-s2', end_region=REGION)['reference_id']   # the end's region, written with the start
    assert saved(store)['references'][s2]['pending_end']['region'] == REGION
    approvable(store, s2)
    s = saved(store)
    s['references']['K1']['status'] = s['references'][rid]['status'] = 'rejected'
    put(store, s)
    row = VS.approve_reference(store, USER, RUN, [], s2, 'a' * 64, '', FakeConn([]))
    assert saved(store)['references'][row['end_reference_id']]['generation']['region'] == REGION


def png_of(colour, size=(64, 36)):
    buf = BytesIO()
    Image.new('RGB', size, colour).save(buf, 'PNG')
    return buf.getvalue()


def test_the_worker_masks_the_region_and_copies_the_start_back_outside_it(tmp_path, monkeypatch):
    red, green = png_of((200, 30, 30)), png_of((30, 200, 30))

    class Store:
        files = {'run-1/visuals/references/S.png': red}

        def get(self, key):
            return self.files[key]

        def put(self, key, data, mime):
            self.files[key] = data
    sent = {}

    def openai(path, **kw):
        sent.update(path=path, files=kw.get('files'))
        body = json.dumps({'data': [{'b64_json': base64.b64encode(green).decode()}], 'usage': {}})
        return type('R', (), {'status_code': 200, 'text': body, 'content': body.encode(), 'json': lambda self: json.loads(body)})()
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: Store())
    monkeypatch.setattr(VW, 'openai_client', openai)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda *a, **k: None)
    job = {'id': 'j1', 'run_id': 'run-1', 'request': {'op': 'edit', 'prompt': 'p', 'size': '64x36', 'quality': 'high', 'model': 'm', 'region': {'left': 0.5, 'top': 0, 'width': 0.5, 'height': 1},
                                                      'parents': [{'id': 'S', 'key': 'run-1/visuals/references/S.png', 'sha256': 's'}], 'reference': {'id': 'r1'}}}
    status, result, error, cost, retry = VW.process_image(job)
    assert status == 'retained' and error is None, error
    names = [f[0] for f in sent['files']]
    assert names == ['image[]', 'mask'] and sent['path'] == '/images/edits'
    mask = Image.open(BytesIO(sent['files'][1][1][1]))
    assert mask.size == (64, 36) and mask.getpixel((10, 10))[3] == 255 and mask.getpixel((50, 10))[3] == 0   # opaque outside, clear inside the region
    out = Image.open(BytesIO(Store.files[result['key']]))
    assert out.getpixel((10, 10))[:3] == (200, 30, 30) and out.getpixel((50, 10))[:3] == (30, 200, 30)   # the start outside, the model inside
    assert result['edit']['region'] == job['request']['region'] and result['edit']['outside_changed_pct'] > 30 and result['edit']['composited'] is True
    status, result, *_ = VW.process_image({**job, 'id': 'j2', 'request': {**job['request'], 'region': None}})
    assert status == 'retained' and 'edit' not in result   # no region: the picture as the model made it


def test_the_page_and_the_tool_carry_the_golden_picture_and_the_region():
    assert 'golden' in PAGE and "r.golden?" in PAGE and 'not from the golden picture' in PAGE
    proc = (ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8')
    assert '--golden' in proc and '--region' in proc and 'golden picture' in proc
