"""design/151 section 13 (SK, 4 Nov 2026): a reference set is one conversation with the picture AI, one picture per turn, on gemini-nano-banana-2.1 with
Google Search + Image Search grounding and thinking HIGH on every turn; the views named by the server."""
import base64
import copy
import json
import types
from io import BytesIO

import pytest
from pydantic import SecretStr

from app import visual_workers as VW
from app import visuals_stage as VS
from test_design151_refs_pure import FakeStore, Resp, png_bytes


def _settings(monkeypatch, tmp_path):
    from app import keys
    keys.reset()
    monkeypatch.setattr(VW, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=SecretStr(''), GEMINI_API_KEYS=SecretStr('g1'), OPENAI_API_KEY=SecretStr(''), OPENAI_API_KEYS=SecretStr(''),
                                                                      GEMINI_IMAGE_MODEL='gemini-nano-banana-2.1', GEMINI_IMAGE_SIZE='2K'))
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    store = FakeStore({})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    return store


def turn(n, text='', image=True, chunks=()):
    parts = [{'text': text or f'Here is image {n}. '}]
    if image:
        parts.append({'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png_bytes(64, 32, (n * 40, 10, 10))).decode()}})
    gm = {'groundingChunks': [{'web': {'uri': u, 'title': t}} for u, t in chunks], 'webSearchQueries': ['clay pot'], 'imageSearchQueries': ['clay pot photo']}
    return {'candidates': [{'content': {'role': 'model', 'parts': parts}, 'groundingMetadata': gm}], 'usageMetadata': {'promptTokenCount': 100 * n, 'candidatesTokenCount': 2000, 'thoughtsTokenCount': 900}}


REQ = {'kind': 'image', 'op': 'generate', 'provider': 'gemini', 'model': 'gemini-nano-banana-2.1', 'prompt': 'PREAMBLE. The pot.', 'size': {'aspect': '16:9', 'tier': '2K'}, 'quality': 'high',
       'parents': [], 'reference': {'id': 'S1', 'kind': 'sheet', 'element_id': 'E2'}, 'set': True, 'search': True, 'views': ['the whole pot', 'a three-quarter view', 'a close-up of the rim']}


def test_a_set_is_three_turns_of_one_conversation_with_image_search_and_thinking_high(monkeypatch, tmp_path):
    store = _settings(monkeypatch, tmp_path)
    sent = []
    answers = [turn(1, chunks=[('https://a', 'A')]), turn(2, chunks=[('https://a', 'A'), ('https://b', 'B')]), turn(3, 'Here is image 3: the rim. What the photographs showed: fired red clay.')]
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(copy.deepcopy(kw['json'])) or Resp(200, answers[len(sent) - 1]))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'retained', error
    assert len(sent) == 3
    for body in sent:   # SK's AI Studio settings on every turn
        assert body['tools'] == [{'google_search': {'searchTypes': {'webSearch': {}, 'imageSearch': {}}}}]
        assert body['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'high'} and body['generationConfig']['responseModalities'] == ['TEXT', 'IMAGE']
    # turn 1: the prompt and the first view; turn n: the earlier turns (the model's text and picture) then the next view
    assert sent[0]['contents'][0]['role'] == 'user' and 'Image 1 of 3: the whole pot.' in sent[0]['contents'][0]['parts'][-1]['text'] and 'PREAMBLE' in sent[0]['contents'][0]['parts'][-1]['text']
    assert [c['role'] for c in sent[2]['contents']] == ['user', 'model', 'user', 'model', 'user']
    assert any(p.get('inlineData') for p in sent[2]['contents'][1]['parts']) and sent[2]['contents'][-1]['parts'][0]['text'] == 'Image 3 of 3: a close-up of the rim.'
    assert [x['key'] for x in result['extra']] == ['run-1/visuals/references/S1-2.png', 'run-1/visuals/references/S1-3.png'] and all(k in store.files for k in ('run-1/visuals/references/S1.png', 'run-1/visuals/references/S1-3.png'))
    assert 'fired red clay' in result['notes'] and result['sources'] == [{'url': 'https://a', 'title': 'A'}, {'url': 'https://b', 'title': 'B'}]   # the turns' sources, each once
    assert cost['pictures'] == 3 and cost['input_tokens'] == 600 and cost['output_tokens'] == 6000


def test_a_turn_without_a_picture_ends_the_set_with_a_note_and_keeps_what_came_back(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    answers = [turn(1), turn(2, 'I cannot draw that.', image=False), turn(3)]
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(1) or Resp(200, answers[len(sent) - 1]))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'retained' and len(sent) == 2 and result['extra'] == [] and cost['pictures'] == 1
    assert 'picture 2 (a three-quarter view) did not come back: I cannot draw that.' in result['notes']


def test_no_picture_on_the_first_turn_fails_the_set_as_today(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: Resp(200, turn(1, 'Blocked.', image=False)))
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ})
    assert status == 'failed' and result['failure'] == 'no_image' and 'Blocked.' in error


def test_a_limit_on_a_later_turn_requeues_the_whole_set(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    answers = [Resp(200, turn(1)), Resp(429, {'error': {'message': 'slow down'}})]
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(1) or answers[len(sent) - 1])
    status, result, error, cost, retry = VW.process_image({'id': 'j1', 'run_id': 'run-1', 'request': REQ, 'attempt': 1})
    assert status == 'queued' and retry == 1 and result['http_status'] == 429


def test_a_persons_set_has_its_three_views_without_the_search_tool(monkeypatch, tmp_path):
    _settings(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(VW.httpx, 'post', lambda url, **kw: sent.append(copy.deepcopy(kw['json'])) or Resp(200, turn(len(sent))))
    req = {**REQ, 'search': False, 'views': VS.PERSON_VIEWS, 'reference': {'id': 'S2', 'kind': 'sheet', 'element_id': 'P1'}}
    status, result, error, cost, retry = VW.process_image({'id': 'j2', 'run_id': 'run-1', 'request': req})
    assert status == 'retained' and len(sent) == 3 and all('tools' not in b for b in sent) and all(b['generationConfig']['thinkingConfig'] == {'thinkingLevel': 'high'} for b in sent)
    assert cost['pictures'] == 3 and 'Image 3 of 3: a close-up of the face.' == sent[2]['contents'][-1]['parts'][0]['text']


def test_the_views_and_the_set_lines_are_one_picture_per_turn():
    assert len(VS.THING_VIEWS) == 3 and len(VS.PERSON_VIEWS) == 3 and VS.SET_MAX == 3
    assert 'one per turn' in VS.KEPT_SET_LINE and 'two to four' not in VS.KEPT_SET_LINE and 'one per turn' in VS.PERSON_SET
    assert VS.set_views({'kind': 'object', 'name': 'the water pot'}) == [v.format(name='the water pot') for v in VS.THING_VIEWS]
    assert VS.set_views({'kind': 'person', 'name': 'Mason'}) == VS.PERSON_VIEWS


def test_the_instructions_and_the_command_text_say_three_pictures_one_per_turn():
    from pathlib import Path
    root = Path(VS.__file__).resolve().parents[2]
    v3 = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    search = next(p['text'] for p in next(s for s in v3['stages'] if s['name'] == 'visuals')['parts'] if p['name'] == 'picture-search')
    assert 'three separate pictures, one per turn of one conversation' in search and 'two to four separate pictures' not in search and 'Image Search' in search
    md = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'three separate pictures, one per turn' in md and 'two to four separate pictures' not in md


# ---------- hotfix 4 Nov 2026 (VW-18): kept from the first step; a set is a Gemini call on every film ----------

from test_design151_refs_pure import NEW, OLD, KILN, MASON, doc_with, frames_only, _req   # noqa: E402
from test_visuals_stage_pure import FakeConn, USER, accepted, g, saved   # noqa: E402
from app.errors import Problem  # noqa: E402


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


def test_a_new_film_is_kept_from_its_status_before_the_round_so_the_old_path_is_closed():
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    st = VS.status(FakeConn([]), store, NEW, [])
    assert st['kept'] is True and saved(store)['refs'] == 'kept' and st['sheet_due'] == [] and st['golden_due'] == []
    with pytest.raises(Problem, match='retired on this film'):
        g(lambda: VS.search(store, USER, NEW, [], 'E2', 'brick kiln Tamil Nadu', 'yes'))
    # an older film, or one with a sheet already, is not
    store = frames_only(doc)
    assert VS.status(FakeConn([]), store, OLD, [])['kept'] is False and 'refs' not in saved(store)
    store = frames_only(doc)
    s = json.loads(store.files[f"{NEW['id']}/visuals/session.json"])
    s['references']['S0'] = {'id': 'S0', 'kind': 'sheet', 'element_id': 'E1', 'status': 'approved'}
    store.files[f"{NEW['id']}/visuals/session.json"] = json.dumps(s).encode()
    assert VS.is_kept(s, NEW) is False


def test_a_set_runs_on_gemini_whatever_the_films_picture_ai(monkeypatch):
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    conn = FakeConn([])
    openai_film = {**NEW, 'image_provider': 'openai'}
    VS.round_start(store, USER, openai_film, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}], conn=conn)
    out = VS.round_done(store, USER, openai_film, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'approve'}}, 'Yes.', conn=conn)
    assert out['errors'] == {} and sorted(out['queued']) == ['E2', 'P1'] and out['from_footage'] == ['E1']
    req = {_req(p)['reference']['element_id']: _req(p) for p in conn.inserted}
    assert all(r['provider'] == 'gemini' and r['model'] == VS.settings().GEMINI_IMAGE_MODEL and 'aspect' in r['size'] for r in req.values())
    assert req['E2']['views'] == VS.set_views(KILN) and req['P1']['views'] == VS.PERSON_VIEWS
    assert out['cost_inr'] == pytest.approx(2 * VS.image_price_inr(openai_film, provider='gemini') * 3, abs=0.01) and VS.image_price_inr(openai_film) == 20.0


def test_the_page_says_the_kept_way_before_the_round():
    from pathlib import Path
    html = (Path(VS.__file__).resolve().parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    for needle in ("const keptFilm=!!d.kept", "if(data.kept)return ['','waiting for the round']", 'The references are made the kept way', 'No set yet: the assistant posts the reference round'):
        assert needle in html, needle


def test_the_status_says_the_round_is_next_on_a_kept_film_until_it_is_posted():
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    conn = FakeConn([])
    assert VS.status(conn, store, NEW, [])['round_due'] is None   # no gap accepted yet: the plan comes first
    sess = json.loads(store.files[f"{NEW['id']}/visuals/session.json"]); sess['accepted'] = accepted(doc)
    store.files[f"{NEW['id']}/visuals/session.json"] = json.dumps(sess).encode()
    st = VS.status(conn, store, NEW, [])
    assert st['kept'] is True and st['round_due'] and 'vw visuals round --file out/reference-round.json' in st['round_due'] and "Gemini's image model" in st['round_due'] and st['set_provider'] == 'gemini'
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln'}, {'element_id': 'P1', 'prompt': 'kneels'}], conn=conn)
    assert VS.status(conn, store, NEW, [])['round_due'] is None
    store = frames_only(doc)
    assert VS.status(conn, store, OLD, [])['round_due'] is None   # an older film keeps its own order


# ---------- hotfix 4 Nov 2026 (VW-18): a re-post after Done merges; a set is judged on step 2, never picture by picture ----------

from test_design151_refs_pure import with_sets  # noqa: E402


def test_a_round_posted_again_after_done_keeps_the_sets_and_makes_only_the_missing_ones():
    doc = doc_with(KILN, MASON)
    store, conn, s = with_sets(doc)
    # E2's set was refused before the call (say: measure first): no rows, an error on its row
    for rid in [r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'E2']:
        del s['references'][rid]
    s['round']['elements']['E2'].update(set=None, error='E2: measure first')
    store.files[f"{NEW['id']}/visuals/session.json"] = json.dumps(s).encode()
    n0 = len(conn.inserted)
    with pytest.raises(Problem, match='P1 has its set already'):
        g(lambda: VS.round_start(store, USER, NEW, [], [{'element_id': 'P1', 'prompt': 'the mason again'}], conn=conn))
    with pytest.raises(Problem, match='E1 is referenced by its approved footage picture'):
        g(lambda: VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'prompt': 'the plinth again'}], conn=conn))
    out = VS.round_start(store, USER, NEW, [], [{'element_id': 'E2', 'prompt': 'the kiln, measured: 3 m high'}], conn=conn)
    s2 = saved(store)
    assert out['merged'] == ['E2'] and out['queued'] == ['E2'] and out['errors'] == {} and out['pass'] == 'making' and len(conn.inserted) == n0 + 1
    assert s2['round']['elements']['E1']['from_footage'] and s2['round']['elements']['P1']['set']   # untouched
    assert s2['round']['elements']['E2']['prompt'] == 'the kiln, measured: 3 m high' and s2['round']['elements']['E2']['error'] is None and s2['round']['elements']['E2']['set']
    assert sum(1 for r in s2['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'P1') == 3   # P1's pictures still there
    assert 'merged' not in VS.round_start(frames_only(doc), USER, NEW, [], [{'element_id': 'E1', 'prompt': 'x'}], conn=FakeConn([]))   # a first post is a fresh round


def test_a_kept_set_waits_as_one_step_2_item_not_picture_by_picture():   # UI change, 11 Nov 2026 (X1, X2): one item per set, on its element's card (was one item for all sets, on no card)
    doc = doc_with(KILN, MASON)
    store, conn, s = with_sets(doc)
    items = VS.waiting(s, doc, 'VW-20', [])
    labels = [i['label'] for i in items]
    assert labels == ['Set to judge · E2', 'Set to judge · P1'] and not any(l.startswith('Reference sheet') for l in labels)
    assert items[0]['link'] == '/runs/VW-20/visuals#references/E2/set'


def test_the_page_judges_a_set_on_step_2_only():
    from pathlib import Path
    html = (Path(VS.__file__).resolve().parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    for needle in ("inSet=!!(r.set&&d.kept)", "(inSet?'':fixBtn(r))", 'judge the whole set on step 2 of the reference round', "['dec','set made: judge it on step 2']"):
        assert needle in html, needle


# ---------- SK, 5 Nov 2026 (VW-18): an approved footage picture is the reference; no AI set is made for it ----------

def test_a_thing_approved_from_the_footage_gets_no_ai_set_and_its_frame_is_the_golden_picture():
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln'}, {'element_id': 'P1', 'prompt': 'kneels'}], conn=conn)
    out = VS.round_done(store, USER, NEW, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'approve'}}, 'Yes.', conn=conn)
    s = saved(store)
    assert out['from_footage'] == ['E1'] and sorted(out['queued']) == ['E2', 'P1'] and len(conn.inserted) == 2   # E1: no job, no money
    assert s['round']['elements']['E1']['from_footage'] is True and s['round']['elements']['E1']['set'] is None and s['golden']['E1'] == 'F1'
    assert not any(r.get('kind') == 'sheet' and r['element_id'] == 'E1' for r in s['references'].values())
    # step 2 asks nothing for E1; the round completes without a verdict on it
    for r in s['references'].values():
        if r.get('kind') == 'sheet':
            r.update(status='candidate', sha256='sha-' + r['id'])
    store.files[f"{NEW['id']}/visuals/session.json"] = json.dumps(s).encode()
    sets = {eid: [r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid] for eid in ('E2', 'P1')}
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}, 'P1': {'verdict': 'yes'}}, 'yes', conn=conn)
    assert out['pass'] == 'complete' and sorted(out['approved']) == ['E2', 'P1']
    with pytest.raises(Problem, match='E1 is referenced by its approved footage picture'):
        g(lambda: VS.round_start(store, USER, NEW, [], [{'element_id': 'E1', 'prompt': 'again'}], conn=conn))


def test_the_page_shows_a_footage_element_done_and_asks_no_verdict_for_it():
    from pathlib import Path
    html = (Path(VS.__file__).resolve().parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    for needle in ('Use the footage picture (no AI picture is made)', "if(r.from_footage)return", 'the golden picture, from your footage', "if(rd.elements[eid].ignored||rd.elements[eid].from_footage)return", "if(r.ignored||r.from_footage)return"):
        assert needle in html, needle


def test_the_instructions_say_a_footage_picture_needs_no_ai_set():
    from pathlib import Path
    root = Path(VS.__file__).resolve().parents[2]
    v3 = json.loads((root / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    parts = {p['name']: p['text'] for p in next(s for s in v3['stages'] if s['name'] == 'visuals')['parts']}
    assert 'a thing with an approved footage picture gets no AI set' in parts['picture-search'] and 'is made from it' not in parts['picture-search']
    assert "a thing's approved footage picture, else the ticked picture of its set" in parts['later']
    md = (root / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'gets no AI set' in md and 'is made from it' not in md
