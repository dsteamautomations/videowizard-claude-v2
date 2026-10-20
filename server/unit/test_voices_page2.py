"""design/54: the catalogue mirror, the browser filter's server twin, the tryout and narration caps, the test passages, the page step."""
import pytest

from app import voices as V
from app import voice_direction as VD
from app.errors import Problem

SHARED = {'voice_id': 'lib1', 'name': 'Santhi Prakash', 'description': 'Warm, clear, measured', 'preview_url': 'https://p/1.mp3', 'category': 'professional', 'public_owner_id': 'o1',
          'language': 'en', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'narrative_story', 'descriptive': 'warm', 'is_added_by_user': True,
          'cloned_by_count': 120, 'usage_character_count_1y': 50000}


class FakeProvider:
    def __init__(self):
        self.calls = []

    def request(self, method, path, **kw):
        import httpx
        params = kw.get('params') or {}
        self.calls.append((path, params))
        if path == '/v1/shared-voices':
            page = int(params.get('page', 0))
            voices = [{**SHARED, 'voice_id': f'lib{page}{k}', 'is_added_by_user': k == 'a'} for k in 'abc']
            return httpx.Response(200, json={'voices': voices, 'has_more': page < 1, 'total_count': 6})
        if path == '/v2/voices':
            return httpx.Response(200, json={'voices': [{'voice_id': 'acc1', 'name': 'UD - Narrator', 'labels': {'accent': 'indian', 'gender': 'male'}, 'description': 'x', 'preview_url': 'https://p/2.mp3',
                                                        'category': 'cloned'}], 'has_more': False})
        return httpx.Response(404)


def test_search_params_follow_the_tab_and_the_filters():
    p = V.search_params({'tab': 'explore', 'language': 'en', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'narrative_story', 'search': 'measured', 'sort': 'trending', 'page': 2})
    assert p == {'page_size': 100, 'page': 2, 'language': 'en', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_cases': 'narrative_story', 'search': 'measured', 'sort': 'trending'}
    p = V.search_params({'tab': 'explore'})
    assert p == {'page_size': 100, 'page': 0, 'sort': 'trending'}
    assert V.search_params({'tab': 'explore', 'sort': 'weird'})['sort'] == 'trending'


def test_search_explore_returns_compact_rows_with_the_register_and_usage(monkeypatch):
    V._SEARCH.clear()
    monkeypatch.setattr(V, 'register_rows', lambda conn, ids=None: {'lib0a': {'favourite': True, 'note': 'warm'}})
    monkeypatch.setattr(V, 'history', lambda conn, voice_id=None: {'lib0b': {'narrations': 1, 'auditions': 2, 'last_used': '2026-10-18'}})
    remembered = []
    monkeypatch.setattr(V, 'remember_many', lambda conn, rows: remembered.extend(r['voice_id'] for r in rows))
    prov = FakeProvider()
    out = V.search(None, prov, {'tab': 'explore', 'gender': 'male', 'page': 0})
    assert out['total'] == 6 and out['has_more'] is True and out['page'] == 0 and [r['voice_id'] for r in out['voices']] == ['lib0a', 'lib0b', 'lib0c']
    r = out['voices'][0]
    assert r['favourite'] is True and r['on_account'] is True and r['preview_url'] == 'https://p/1.mp3' and r['accent'] == 'indian' and r['library']['public_owner_id'] == 'o1'
    assert out['voices'][1]['narrations'] == 1 and out['voices'][1]['on_account'] is False
    assert remembered == ['lib0a', 'lib0b', 'lib0c']
    V.search(None, prov, {'tab': 'explore', 'gender': 'male', 'page': 0})
    assert len([c for c in prov.calls if c[0] == '/v1/shared-voices']) == 1   # the second call is served from the two-minute cache


def test_search_mine_and_favourites(monkeypatch):
    V._SEARCH.clear()
    monkeypatch.setattr(V, 'register_rows', lambda conn, ids=None: {'acc1': {'favourite': True, 'note': ''}, 'gone1': {'favourite': True, 'name': 'Gone', 'public_owner_id': 'o9'}})
    monkeypatch.setattr(V, 'history', lambda conn, voice_id=None: {})
    monkeypatch.setattr(V, 'remember_many', lambda conn, rows: None)
    prov = FakeProvider()
    mine = V.search(None, prov, {'tab': 'mine'})
    assert [r['voice_id'] for r in mine['voices']] == ['acc1'] and mine['voices'][0]['on_account'] is True and mine['total'] == 1
    fav = V.search(None, prov, {'tab': 'favourites'})
    ids = {r['voice_id']: r for r in fav['voices']}
    assert ids['acc1']['favourite'] is True and ids['gone1'].get('missing') is True and ids['gone1']['name'] == 'Gone'


def test_known_voices_list_last_voice_favourites_and_my_voices(monkeypatch):
    rows = V.known_voices(last_voice={'voice_id': 'acc1', 'name': 'UD - Narrator'}, favourites=[{'voice_id': 'lib0a', 'name': 'Santhi', 'missing': False}],
                          mine=[{'voice_id': 'acc1', 'name': 'UD - Narrator'}, {'voice_id': 'acc2', 'name': 'Other'}])
    assert [(r['voice_id'], r['why']) for r in rows] == [('acc1', 'last film'), ('lib0a', 'favourite'), ('acc2', 'in my voices')]


def test_caps_for_tryout_and_narration():
    V.check_cap(list('abcdef'), V.TRYOUT_MAX, 'tryout')
    with pytest.raises(Problem) as exc:
        V.check_cap(list('abcdefg'), V.TRYOUT_MAX, 'tryout')
    assert 'six' in exc.value.message
    with pytest.raises(Problem) as exc:
        V.check_cap(['a', 'b', 'c', 'd'], V.NARRATE_MAX, 'narration')
    assert 'three' in exc.value.message
    with pytest.raises(Problem):
        V.check_cap([], V.NARRATE_MAX, 'narration')


TEXT = ' '.join(f'Word{i}.' if i % 10 == 0 else f'word{i}' for i in range(1, 161)) + '\n'   # 160 words, a sentence end every ten words


def test_words_and_test_passages_are_contiguous_sentence_starts_of_fifty_to_hundred_words():
    words = VD.words_of(TEXT)
    assert len(words) == 160 and words[0]['id'] == 'W00001' and TEXT[words[10]['start']:words[10]['end']] == 'word11'
    ok = [{'passage_id': 'P001', 'first_word': 11, 'last_word': 70, 'why': 'the figures'}]
    assert VD.validate_passages(ok, TEXT) == []
    assert 'start of a sentence' in VD.validate_passages([{'passage_id': 'P001', 'first_word': 12, 'last_word': 70, 'why': ''}], TEXT)[0]
    assert '50 to 100 words' in VD.validate_passages([{'passage_id': 'P001', 'first_word': 11, 'last_word': 40, 'why': ''}], TEXT)[0]
    assert '50 to 100 words' in VD.validate_passages([{'passage_id': 'P001', 'first_word': 1, 'last_word': 120, 'why': ''}], TEXT)[0]
    assert 'three' in VD.validate_passages([ok[0]] * 4, TEXT)[0]
    assert VD.passage_text(TEXT, 11, 70).startswith('word11 word12') and VD.passage_text(TEXT, 11, 70).endswith('Word70.')


def test_page_state_has_a_step_and_a_tried_list():
    state = V.new_page_state()
    assert state['step'] == 'browse' and state['tried'] == [] and state['contract'] == 'vw2-voice-page-v2'
    V.set_step(state, 'try')
    assert state['step'] == 'try'
    with pytest.raises(Problem):
        V.set_step(state, 'sideways')


def test_the_procedure_route_serves_every_prompt_of_a_stage():
    """VW-6, 20 Oct: the direction prompt was missing from the keys the procedure route serves, so the assistant improvised the direction."""
    import json
    from pathlib import Path
    from app import core
    stages = json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v2.json').read_text(encoding='utf-8'))['stages']
    for st in stages:
        for k in st:
            if k.endswith('prompt') or k in ('steps', 'output_shape', 'output_file'):
                assert k in core.PROCEDURE_KEYS, (st['name'], k)


def test_sub_request_ids_are_valid_uuids_and_stable():
    """VW-6, 20 Oct: the tryout gave each voice's job '<request id>-<n>', which the uuid column refused (500 on the page)."""
    import uuid
    base = str(uuid.uuid4())
    a, b = V.sub_request_id(base, 0), V.sub_request_id(base, 1)
    assert uuid.UUID(a) and uuid.UUID(b) and a != b and a == V.sub_request_id(base, 0) and a != base
