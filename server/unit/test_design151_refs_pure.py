"""design/151 (SK, 4 Nov 2026): references made the kept way on new films. Frames unchanged; a person's character sheet as a set from the plan's words;
a thing's set by the kept Nano Banana method (the preamble, one way, a set of separate pictures, the four notes, Google Search on); the round silent,
the sets shown in one shot with Yes / No / Correct it; the golden picture always the operator's tick; the older search and picks refused by name on
new films and kept on older ones."""
import base64
import json
from io import BytesIO

import pytest

from app import visuals_stage as VS
from app import visual_workers as VW
from app import visual_contract as VC
from app.errors import Problem
from test_visuals_stage_pure import FakeConn, FakeStore, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with

NEW = {'id': 'run-1', 'code': 'VW-20', 'image_provider': 'gemini', 'film': {'shape': {'value': 'horizontal', 'video': 'horizontal', 'fps': 25}}}
OLD = {'id': 'run-1', 'code': 'VW-9', 'image_provider': 'gemini'}   # film NULL: before design/139; the older references kept (design/35)
MASON = {'id': 'P1', 'name': 'Mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'the mason who lays the plinth', 'description': 'a man of about forty, lean, dark skin, short grey hair, a thin moustache, a cotton lungi folded to the knee and a faded shirt'}
HELPER = {'id': 'P2', 'name': 'Helper', 'kind': 'person', 'identity': 'representative', 'requirements': 'the helper who carries bricks', 'description': 'a young man of about twenty, stocky, dark skin, thick black hair, clean-shaven, shorts and a sleeveless vest'}
KILN = {'id': 'E2', 'name': 'Clamp kiln', 'kind': 'place', 'identity': 'representative', 'requirements': 'a country brick kiln of Tamil Nadu'}


def _req(p):
    """The request of an inserted vw2_jobs row (a psycopg Jsonb, or the dict)."""
    v = p[2]
    return v.obj if hasattr(v, 'obj') else v


def doc_with(*els):
    doc = plan_doc([shot('IM1', 0, 500, 'image', element_ids=['E1'])], [shot('VS1', 900, 1150, 'video', element_ids=['E1'])])
    doc['elements'][0] = {'id': 'E1', 'name': 'Plinth', 'kind': 'object', 'identity': 'exact', 'requirements': 'the client\'s own plinth', 'size': [{'part': 'top', 'measure': 'width', 'value': 230, 'unit': 'mm', 'source': 'measured on F1', 'status': 'measured'}]}
    doc['elements'] += list(els)
    for gap in doc['gaps']:
        for sc in gap['scenes']:
            sc['outfit'] = {'P1': 'a white lungi and a blue shirt', 'P2': 'khaki shorts and a red vest'}
    return doc


def new_store(doc, refs=None, **over):
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', references=refs or {}, **over)
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    return store


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


# ---------- the prompts ----------

def test_a_things_prompt_is_the_kept_preamble_the_set_line_the_subject_the_cosmetics_and_the_four_notes():
    doc = doc_with(KILN)
    sess = session()
    p = VS.thing_prompt(doc, NEW, sess, KILN, 'a country brick kiln as it stands during firing, the stack and its openings the subject, nobody in the picture')
    assert p.startswith(VS.KEPT_PREAMBLE) and VS.KEPT_SET_LINE in p and 'What the picture must represent: a country brick kiln' in p
    assert p.index(VS.KEPT_PREAMBLE) < p.index(VS.KEPT_SET_LINE) < p.index('What the picture must represent') < p.index('Cosmetic requirements') < p.index(VS.KEPT_NOTES)
    assert 'warm daylight' in p and 'yard, day' in p   # the cosmetics from the plan (Q7): its appearance and the scenes' place
    assert 'no filters, no stylisation, no illustration' in p and 'No person' in p
    assert 'show one way of doing it' in VS.KEPT_PREAMBLE and 'never as a collage' in VS.KEPT_SET_LINE and 'with URLs' in VS.KEPT_NOTES


def test_a_subject_block_that_describes_how_the_work_is_done_is_refused():
    doc = doc_with(KILN)
    with pytest.raises(ValueError, match='how the work is done'):
        VS.thing_prompt(doc, NEW, session(), KILN, 'the kiln: step by step, first stack the bricks then seal them')


def test_a_persons_prompt_carries_the_description_the_role_the_outfit_the_place_the_others_and_the_poses():
    doc = doc_with(MASON, HELPER)
    p = VS.person_prompt(doc, NEW, MASON, 'he kneels on the plinth all day, so the lungi is folded to the knee')
    assert 'a man of about forty, lean' in p and 'the mason who lays the plinth' in p and 'a white lungi and a blue shirt' in p and 'yard, day' in p
    assert 'Why: he kneels on the plinth' in p
    assert 'Not P2' in p and 'about twenty, stocky' in p   # the others in one line each, so the model keeps them apart
    assert VS.PERSON_SET in p and 'close-up of the face' in VS.PERSON_SET and 'never a collage' in VS.PERSON_SET and 'alone on plain' in VS.PERSON_SET


def test_two_people_alike_on_every_trait_are_refused_before_any_payment():
    twin = {**HELPER, 'id': 'P3', 'name': 'Second helper', 'requirements': 'another helper'}
    doc = doc_with(MASON, HELPER, twin)
    with pytest.raises(ValueError, match='P2 and P3 .* alike'):
        VS.distinct_people(doc)
    doc = doc_with(MASON, HELPER, {**twin, 'description': 'a young man of about twenty, lean, dark skin, cropped hair, a beard, long trousers'})
    VS.distinct_people(doc)   # different traits pass
    assert VS.traits('a man of about forty, lean, short grey hair, a thin moustache') == frozenset({'40s', 'lean', 'short hair', 'grey', 'moustache'})


# ---------- the round on a new film: frames, then the sets, then one shot ----------

def frames_only(doc):
    f1 = {**ref('F1'), 'kind': 'frame', 'element_id': 'E1', 'width': 1920, 'height': 1080}
    return new_store(doc, {'F1': f1})


def test_round_start_on_a_new_film_is_kept_takes_a_prompt_per_element_and_refuses_the_search():
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    conn = FakeConn([])
    with pytest.raises(Problem, match='E2: give its prompt'):
        g(lambda: VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'frames': []}, {'element_id': 'P1', 'prompt': 'why'}], conn=conn))
    out = VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top, the subject'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}], conn=conn)
    s = saved(store)
    assert s['refs'] == 'kept' and out == {'pass': 1, 'elements': 3, 'kept': True} and s['round']['elements']['E2']['prompt'] == 'the kiln during firing'
    with pytest.raises(Problem, match='retired on this film'):
        g(lambda: VS.search(store, USER, NEW, [], 'E2', 'brick kiln Tamil Nadu', 'yes'))
    with pytest.raises(Problem, match='retired on this film'):
        g(lambda: VS.pick(store, USER, NEW, [], 's1', [{'n': 1}], 'yes'))
    with pytest.raises(Problem, match='retired on this film'):
        g(lambda: VS.round_done(store, USER, NEW, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'search'}, 'P1': {'verdict': 'ignore'}}, 'yes', conn=conn))


def test_round_done_approves_the_frames_and_queues_every_set_silently(monkeypatch):
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}], conn=conn)
    out = VS.round_done(store, USER, NEW, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'approve'}}, 'Yes, the frame.', conn=conn)
    s = saved(store)
    assert s['references']['F1']['status'] == 'approved' and out['pass'] == 'making' and sorted(out['queued']) == ['E2', 'P1'] and out['from_footage'] == ['E1'] and out['cost_inr'] > 0
    assert len(conn.inserted) == 2   # SK 5 Nov 2026: E1's approved footage picture is its reference; no AI set, no money
    made = {r['element_id']: r for r in s['references'].values() if r.get('kind') == 'sheet'}
    assert made['E2']['status'] == 'generating' and made['E2']['set'] == made['E2']['id'] and made['E2']['set_n'] == 1
    req = {_req(p)['reference']['element_id']: _req(p) for p in conn.inserted}
    assert req['E2']['set'] is True and req['E2']['search'] is True and req['E2']['prompt'].startswith(VS.KEPT_PREAMBLE) and req['E2']['parents'] == []
    assert 'E1' not in req and s['golden']['E1'] == 'F1' and s['round']['elements']['E1']['from_footage'] is True   # SK 5 Nov 2026 (replaces Q1): the frame is the reference and the golden picture
    assert req['P1']['set'] is True and 'search' not in req['P1'] and VS.PERSON_SET in req['P1']['prompt'] and req['P1']['parents'] == []   # design/124 decision 5 held
    assert [l['check'] for l in made['E2']['server_checklist']] == [l['check'] for l in VS.KEPT_THING_LINES] and 'labelled' not in json.dumps(made['E2']['server_checklist'])
    assert [l['check'] for l in made['P1']['server_checklist']] == [l['check'] for l in VS.PERSON_SET_LINES]
    assert VS._round_view(s)['pass'] == 'making' and VS._round_view(s)['elements']['E2']['set'] == [made['E2']['id']]
    assert VS.golden_due(s, doc) == [] and VS.sheet_due(s, doc) == []   # the round makes the sheets; no separate golden call on a kept film


def test_a_thing_approved_from_its_frame_needs_no_measure_and_no_set(monkeypatch):
    doc = doc_with()
    doc['elements'][0]['size'][0].update(value=None, status='unknown')
    store = frames_only(doc)
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}], conn=conn)
    out = VS.round_done(store, USER, NEW, [], {'E1': {'verdict': 'approve'}}, 'yes', conn=conn)
    assert out['queued'] == [] and out['errors'] == {} and out['from_footage'] == ['E1'] and conn.inserted == []   # SK 5 Nov 2026: the footage picture is the reference; no set, so no measure before it


def with_sets(doc, person=True):
    """A round at pass 'making' with every set's pictures back: E2 (two pictures), P1 (three); E1 is referenced by its approved frame F1 (SK, 5 Nov 2026)."""
    store = frames_only(doc)
    conn = FakeConn([])
    rows = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}] + ([{'element_id': 'P1', 'prompt': 'kneels'}] if person else [])
    VS.round_start(store, USER, NEW, [], rows, conn=conn)
    VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in rows}, 'yes', conn=conn)
    s = saved(store)
    counts = {'E1': 3, 'E2': 2, 'P1': 3}
    for r in list(s['references'].values()):
        if r.get('kind') != 'sheet':
            continue
        r.update(status='candidate', sha256='sha-' + r['id'], key=f"run-1/visuals/references/{r['id']}.png", notes='(1) one method chosen', sources=[{'url': 'https://example.org/kiln', 'title': 'kiln'}])
        for k in range(2, counts[r['element_id']] + 1):
            s['references'][f"{r['id']}-{k}"] = {**r, 'id': f"{r['id']}-{k}", 'set_n': k, 'sha256': f"sha-{r['id']}-{k}"}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store, conn, s


def test_the_one_shot_verdicts_yes_needs_the_golden_tick_on_a_thing_and_approves_the_set():
    doc = doc_with(KILN, MASON)
    store, conn, s = with_sets(doc)
    assert VS._round_view(s)['pass'] == 2   # every set is back
    sets = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid) for eid in ('E2', 'P1')}
    with pytest.raises(Problem, match='E2: tick the golden picture'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes'}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn))
    with pytest.raises(Problem, match='P1: a verdict is required'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}}, 'yes', conn=conn))
    with pytest.raises(Problem, match='E2: .* not a picture of its set'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['P1'][0]}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn))
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][1]}, 'P1': {'verdict': 'yes'}}, 'All good.', conn=conn)   # E1: from the footage, nothing asked
    s = saved(store)
    assert out['pass'] == 'complete' and s['round']['pass'] == 'complete'
    assert all(s['references'][i]['status'] == 'approved' and s['references'][i]['approval']['quote'] == 'All good.' for eid in sets for i in sets[eid])
    assert s['golden'] == {'E1': 'F1', 'E2': sets['E2'][1], 'P1': sets['P1'][0]}   # Q2: the tick; a person's golden is the full-length front (set picture 1); E1's its frame
    assert s['feedback'][-1]['verdict'] == 'pass'


def test_no_and_correct_it_reject_the_set_and_make_the_next_round_from_the_words():
    doc = doc_with(KILN, MASON)
    store, conn, s = with_sets(doc)
    sets = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid) for eid in ('E2', 'P1')}
    with pytest.raises(Problem, match='E2: say what to correct'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'correct'}, 'P1': {'verdict': 'no'}}, 'yes', conn=conn))
    n0 = len(conn.inserted)
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'correct', 'words': 'no chimney, the clamp is sealed with mud'}, 'P1': {'verdict': 'no', 'words': 'too young'}}, 'Round 2.', conn=conn)
    s = saved(store)
    assert out['pass'] == 'making' and sorted(out['queued']) == ['E2', 'P1'] and len(conn.inserted) == n0 + 2
    assert all(s['references'][i]['status'] == 'rejected' and s['references'][i]['rejection']['notes'] == 'no chimney, the clamp is sealed with mud' for i in sets['E2'])
    assert s['golden'] == {'E1': 'F1'} and s['round']['elements']['E2']['round'] == 2
    new = [r for r in s['references'].values() if r.get('kind') == 'sheet' and r['status'] == 'generating']
    assert {r['element_id'] for r in new} == {'E2', 'P1'}
    req = [_req(p) for p in conn.inserted[n0:]]
    kiln = next(r for r in req if r['reference']['element_id'] == 'E2')
    assert "The operator's correction: no chimney, the clamp is sealed with mud." in kiln['prompt'] and all(p['id'] not in sets['E2'] for p in kiln['parents'])   # a rejected picture is never a parent
    assert "The operator's correction: too young." in next(r for r in req if r['reference']['element_id'] == 'P1')['prompt']


def test_an_older_film_keeps_the_search_the_picks_and_the_sheet_from_words():
    doc = doc_with(KILN)
    store = frames_only(doc)
    conn = FakeConn([])
    out = VS.round_start(store, USER, OLD, [], [{'element_id': 'E1', 'frames': ['F1'], 'keywords': 'plinth'}, {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln Tamil Nadu'}], conn=conn)
    assert out == {'pass': 1, 'elements': 2} and 'refs' not in saved(store)
    with pytest.raises(Problem, match='E2: a verdict is required'):   # the old round's own wording; nothing of design/151 on it
        g(lambda: VS.round_done(store, USER, OLD, [], {'E1': {'verdict': 'approve'}}, 'yes', conn=conn))
    with pytest.raises(Problem, match='No reference round is waiting for its sets'):
        g(lambda: VS.round_sets(store, USER, OLD, [], {}, 'yes', conn=conn))


def test_the_golden_call_and_a_sheet_from_web_pictures_are_refused_on_a_kept_film():
    doc = doc_with(KILN)
    store, conn, s = with_sets(doc, person=False)
    sheet = next(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'E2')
    body = {'element_id': 'E2', 'kind': 'isolated', 'name': 'gold', 'prompt': 'Image 1 is the sheet: take identity. The kiln.', 'subject': 'the kiln', 'parents': [sheet], 'golden': True, 'request_id': 'r-1'}
    with pytest.raises(Problem, match='retired on this film'):
        g(lambda: VS.generate_image(conn, store, USER, NEW, [], body))


# ---------- the picture call: Google Search on, every picture kept, the notes and sources stored ----------

class Resp:
    def __init__(self, status_code, body):
        self.status_code, self._body, self.text = status_code, body, json.dumps(body)
        self.content = self.text.encode('utf-8')

    def json(self):
        return self._body


def png_bytes(w, h, colour):
    from PIL import Image
    out = BytesIO()
    Image.new('RGB', (w, h), colour).save(out, format='PNG')
    return out.getvalue()


def answer(n=3):
    parts = [{'text': 'I searched and chose the clamp kiln. '}]
    for k in range(n):
        parts.append({'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png_bytes(64, 32, (k * 40, 10, 10))).decode()}})
    parts.append({'text': '(1) the clamp kiln, no chimney; (2) stacked green bricks sealed with mud; (3) nothing contradicted; (4) sources below.'})
    return {'candidates': [{'content': {'parts': parts}, 'groundingMetadata': {'groundingChunks': [{'web': {'uri': 'https://example.org/kiln', 'title': 'Clamp kilns'}}]}}],
            'usageMetadata': {'promptTokenCount': 1200, 'candidatesTokenCount': 3900}}


def test_a_set_call_turns_google_search_on_and_keeps_every_picture_with_the_notes_and_sources(monkeypatch, tmp_path):
    import types
    from pydantic import SecretStr
    from app import keys
    keys.reset()
    monkeypatch.setattr(VW, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=SecretStr(''), GEMINI_API_KEYS=SecretStr('g1'), OPENAI_API_KEY=SecretStr(''), OPENAI_API_KEYS=SecretStr(''),
                                                                      GEMINI_IMAGE_MODEL='gemini-3-pro-image', GEMINI_IMAGE_SIZE='2K'))
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append((url, kw)) or Resp(200, answer(3)))
    req = {'kind': 'image', 'op': 'generate', 'provider': 'gemini', 'model': 'gemini-3-pro-image', 'prompt': VS.KEPT_PREAMBLE + ' The kiln.', 'size': {'aspect': '16:9', 'tier': '2K'}, 'quality': 'high',
           'parents': [], 'reference': {'id': 'S1', 'kind': 'sheet', 'element_id': 'E2'}, 'set': True, 'search': True}
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': req})
    assert status == 'retained', error
    body = sent[0][1]['json']
    assert body['tools'] == VW.SEARCH_TOOLS and body['generationConfig']['responseModalities'] == ['TEXT', 'IMAGE']   # design/151 section 13: web + image search
    assert result['key'] == 'run-1/visuals/references/S1.png' and [x['key'] for x in result['extra']] == ['run-1/visuals/references/S1-2.png', 'run-1/visuals/references/S1-3.png']
    assert all(k in store.files for k in ('run-1/visuals/references/S1.png', 'run-1/visuals/references/S1-2.png', 'run-1/visuals/references/S1-3.png'))
    assert result['notes'].startswith('I searched') and '(4) sources below' in result['notes'] and result['sources'] == [{'url': 'https://example.org/kiln', 'title': 'Clamp kilns'}]
    assert cost['pictures'] == 3 and VS.image_cost_inr(cost, {'usd_inr': 88.0}) == pytest.approx(3 * 0.134 * 88.0)
    # a person's set: no search tool, image only
    sent.clear()
    status, result, error, cost, retry = VW.process_image({'id': 'j2', 'run_id': 'run-1', 'request': {**req, 'search': False, 'reference': {'id': 'S2', 'kind': 'sheet', 'element_id': 'P1'}}})
    assert status == 'retained' and 'tools' not in sent[0][1]['json'] and sent[0][1]['json']['generationConfig']['responseModalities'] == ['TEXT', 'IMAGE']   # section 13: a set's notes need TEXT
    # a single-picture job is unchanged
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, answer(1)))
    status, result, error, cost, retry = VW.process_image({'id': 'j3', 'run_id': 'run-1', 'request': {**req, 'set': False, 'search': False, 'reference': {'id': 'S3', 'kind': 'isolated', 'element_id': 'E2'}}})
    assert status == 'retained' and 'extra' not in result and 'pictures' not in cost


def test_more_than_four_pictures_keeps_the_first_four_and_says_so(monkeypatch, tmp_path):
    import types
    from pydantic import SecretStr
    from app import keys
    keys.reset()
    monkeypatch.setattr(VW, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=SecretStr(''), GEMINI_API_KEYS=SecretStr('g1'), OPENAI_API_KEY=SecretStr(''), OPENAI_API_KEYS=SecretStr(''),
                                                                      GEMINI_IMAGE_MODEL='gemini-3-pro-image', GEMINI_IMAGE_SIZE='2K'))
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: FakeStore({}))
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, answer(6)))
    req = {'kind': 'image', 'op': 'generate', 'provider': 'gemini', 'model': 'm', 'prompt': 'p', 'size': {'aspect': '16:9', 'tier': '2K'}, 'quality': 'high', 'parents': [], 'reference': {'id': 'S1', 'kind': 'sheet', 'element_id': 'E2'}, 'set': True, 'search': True}
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': req})
    assert status == 'retained' and len(result['extra']) == 3 and cost['pictures'] == 4 and '6 pictures' in result['notes']


def test_the_finished_set_becomes_sibling_candidate_rows_in_the_session(monkeypatch):
    sess = session(references={'S1': {'id': 'S1', 'name': 'kiln-set', 'kind': 'sheet', 'element_id': 'E2', 'element_kind': 'place', 'status': 'generating', 'job_id': 'j1', 'set': 'S1', 'set_n': 1,
                                      'server_checklist': [{'check': 'one way', 'weight': 'must', 'pass_when': 'x'}], 'generation': {'op': 'generate', 'parents': []}}})
    store = FakeStore({'run-1/visuals/session.json': sess})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    recorded = []
    monkeypatch.setattr(VW.jobs, 'finish', lambda *a, **k: None)
    monkeypatch.setattr(VW.jobs, 'record_file', lambda conn, run_id, stage, key, name, sha, size, mime: recorded.append(key))
    conn = FakeConn([])
    result = {'key': 'run-1/visuals/references/S1.png', 'sha256': 'a', 'bytes': 10, 'width': 64, 'height': 32, 'notes': 'the notes', 'sources': [{'url': 'u', 'title': 't'}],
              'extra': [{'key': 'run-1/visuals/references/S1-2.png', 'sha256': 'b', 'bytes': 11, 'width': 64, 'height': 32}, {'key': 'run-1/visuals/references/S1-3.png', 'sha256': 'c', 'bytes': 12, 'width': 64, 'height': 32}]}
    due = VW.finalize_image(conn, {'id': 'j1', 'run_id': 'run-1', 'request': {'reference': {'id': 'S1'}}}, 'retained', result, None, {'provider': 'gemini', 'pictures': 3}, None)
    s = json.loads(store.files['run-1/visuals/session.json'])
    assert due is True and s['references']['S1']['status'] == 'candidate' and s['references']['S1']['notes'] == 'the notes' and s['references']['S1']['sources'][0]['url'] == 'u'
    assert s['references']['S1-2'] == {**{k: v for k, v in s['references']['S1'].items() if k not in ('check_pending',)}, 'id': 'S1-2', 'name': 'kiln-set-2', 'set_n': 2, 'sha256': 'b', 'bytes': 11, 'key': 'run-1/visuals/references/S1-2.png'}
    assert s['references']['S1-3']['set_n'] == 3 and s['references']['S1-3']['set'] == 'S1' and recorded == ['run-1/visuals/references/S1.png', 'run-1/visuals/references/S1-2.png', 'run-1/visuals/references/S1-3.png']


# ---------- downstream: a person's two pictures into a shot; the drawn brief; the approve path ----------

def test_a_start_image_takes_the_persons_full_length_front_and_the_face_close_up_by_default():
    """Q3: picture 1 (the golden) and picture 3 (the face) of the person's set; the other poses by name."""
    doc = doc_with(KILN, MASON)
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'P1']
    store, conn, s = with_sets(doc)
    sets = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid) for eid in ('E2', 'P1')}
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn)
    s = saved(store)
    face, front, pose = sets['P1'][2], sets['P1'][0], sets['P1'][1]
    parents, lines = VS.with_faces(s, [s['references'][front], s['references']['F1']], {'P1': 'Mason'})   # E1's golden is its frame
    assert [p['id'] for p in parents] == [front, 'F1', face] and lines == ['Image 3 is the face of P1 (Mason): take the face from it, nothing else.']
    parents, lines = VS.with_faces(s, [s['references'][front], s['references'][face]], {'P1': 'Mason'})   # the face named already: nothing added twice
    assert [p['id'] for p in parents] == [front, face] and lines == []
    parents, lines = VS.with_faces(s, [s['references'][pose]], {'P1': 'Mason'})   # another pose by name brings nothing by itself
    assert [p['id'] for p in parents] == [pose] and lines == []
    s['references'][face]['status'] = 'rejected'
    assert VS.with_faces(s, [s['references'][front]], {'P1': 'Mason'})[1] == []   # a rejected face is never a parent


def test_the_drawn_brief_and_the_page_payload_carry_the_set_and_its_notes():
    doc = doc_with(KILN)
    store, conn, s = with_sets(doc, person=False)
    sets = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid) for eid in ('E2',)}
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][1]}}, 'yes', conn=conn)
    s = saved(store)
    shown = [rid for rid, r in VS.brief_pictures(s, {'element_ids': ['E2']})]
    assert set(shown) == set(sets['E2'])
    st = VS.status(FakeConn([]), store, NEW, [])
    row = next(r for r in st['references'] if r['id'] == sets['E2'][0]) if isinstance(st['references'], list) else st['references'][sets['E2'][0]]
    assert row['set'] == sets['E2'][0] and row['set_n'] == 1 and row['notes'] == '(1) one method chosen' and row['sources'][0]['url'] == 'https://example.org/kiln'
    assert st['round']['pass'] == 'complete' and st['round']['kept'] is True


# ---------- the plan: every worker the script speaks of ----------

def test_a_person_the_script_acts_with_but_the_plan_lacks_is_a_warning():
    """Q4: warn only; answered like any plan warning."""
    doc = doc_with(MASON)
    sh = doc['gaps'][1]['scenes'][0]['shots'][0]
    sh['narration'] = 'Two helpers carry the bricks to the mason while the supervisor checks the line.'
    plan = VC.VisualPlan.model_validate(doc) if hasattr(VC, 'VisualPlan') else None
    warns = VS.script_people_warnings(doc)
    kinds = {(w['kind'], w['word']) for w in warns}
    assert ('script_person_missing', 'helpers') in kinds and ('script_person_missing', 'supervisor') in kinds and not any(w['word'] == 'mason' for w in warns)
    assert all(w['shot_id'] == 'VS1' for w in warns) and 'script_person_missing' in VC.WARNING_TECHNICAL
    sh['groups'] = [{'kind': 'helpers', 'count': 2, 'mode': 'different', 'items': ['tall', 'short']}]
    assert {w['word'] for w in VS.script_people_warnings(doc)} == {'supervisor'}   # a group entry answers the group word


# ---------- the page and the step texts ----------

def test_the_page_shows_a_kept_round_in_one_shot_with_yes_no_correct_and_the_golden_tick():
    from pathlib import Path
    html = (Path(VS.__file__).resolve().parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    for needle in ('rd.kept', 'data-a="round-sets"', 'value="yes"', 'value="no"', 'value="correct"', 'Correct it', 'data-golden=', 'being made', 'r.notes', "rd.pass==='making'"):
        assert needle in html, needle


def test_the_instructions_say_the_kept_round_and_name_what_is_retired():
    from pathlib import Path
    root = Path(VS.__file__).resolve().parents[2]
    v3 = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    later = next(p['text'] for p in next(s for s in v3['stages'] if s['name'] == 'visuals')['parts'] if p['name'] == 'later')
    assert 'kept method' in later and 'Yes, No or Correct it' in later and 'round --sets' in later
    md = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'round --sets' in md and 'the server adds the kept preamble' in md and 'tick' in md
