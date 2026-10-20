"""design/54: the catalogue mirror, the browser filter's server twin, the tryout and narration caps, the test passages, the page step."""
import pytest

from app import voices as V
from app import voice_direction as VD
from app.errors import Problem

LIB = {'voice_id': 'lib1', 'name': 'Santhi', 'labels': {'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'narrative_story', 'descriptive': 'warm'},
       'description': 'd' * 700, 'preview_url': 'https://p/1.mp3', 'category': 'professional', 'public_owner_id': 'o1', 'language': 'en', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged'}
ACC = {'voice_id': 'acc1', 'name': 'UD - Narrator', 'labels': {'accent': 'indian', 'gender': 'male'}, 'description': 'x', 'preview_url': 'https://p/2.mp3', 'category': 'cloned',
       'sharing': {'public_owner_id': 'o2', 'original_voice_id': 'orig2'}}


def test_mirror_row_from_a_library_voice_and_an_account_voice():
    r = V.mirror_row(LIB, 'library')
    assert r['voice_id'] == 'lib1' and r['scope'] == 'library' and r['public_owner_id'] == 'o1' and r['original_voice_id'] == 'lib1' and r['accent'] == 'indian' and r['language'] == 'en'
    assert len(r['description']) == 601 and r['preview_url'] == 'https://p/1.mp3' and r['on_account'] is False
    r = V.mirror_row(ACC, 'account')
    assert r['scope'] == 'account' and r['on_account'] is True and r['public_owner_id'] == 'o2' and r['original_voice_id'] == 'orig2' and r['language'] == ''


class FakeProvider:
    def __init__(self):
        self.calls = []

    def request(self, method, path, **kw):
        import httpx
        self.calls.append((path, kw.get('params')))
        page = int((kw.get('params') or {}).get('page', 0))
        if path == '/v1/shared-voices':
            voices = [{**LIB, 'voice_id': f'lib{page}a'}, {**LIB, 'voice_id': f'lib{page}b'}]
            return httpx.Response(200, json={'voices': voices, 'has_more': page < 1})
        if path == '/v2/voices':
            return httpx.Response(200, json={'voices': [ACC], 'has_more': False})
        return httpx.Response(404)


def test_refresh_walks_every_library_page_and_the_account():
    rows = V.mirror_rows_from_provider(FakeProvider())
    ids = [r['voice_id'] for r in rows]
    assert ids == ['lib0a', 'lib0b', 'lib1a', 'lib1b', 'acc1'] and rows[-1]['on_account'] is True


def test_filter_rows_matches_labels_search_and_flags():
    rows = [{'voice_id': 'a', 'name': 'Santhi Prakash', 'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'narrative_story', 'descriptive': 'warm', 'description': 'measured and clear', 'language': 'en', 'on_account': True, 'favourite': False},
            {'voice_id': 'b', 'name': 'Asha', 'accent': 'indian', 'gender': 'female', 'age': 'young', 'use_case': 'conversational', 'descriptive': 'bright', 'description': 'quick', 'language': 'en', 'on_account': False, 'favourite': True}]
    assert [r['voice_id'] for r in V.filter_rows(rows, {'gender': 'male'})] == ['a']
    assert [r['voice_id'] for r in V.filter_rows(rows, {'search': 'MEASURED'})] == ['a']
    assert [r['voice_id'] for r in V.filter_rows(rows, {'favourites_only': True})] == ['b']
    assert [r['voice_id'] for r in V.filter_rows(rows, {'on_account': True})] == ['a']
    assert [r['voice_id'] for r in V.filter_rows(rows, {})] == ['b', 'a']   # favourites first


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


def test_mirror_page_filters_server_side_and_caps_the_answer(monkeypatch):
    rows = [{'voice_id': f'v{i}', 'name': f'Voice {i}', 'accent': 'indian' if i % 2 else 'british', 'gender': 'male', 'age': 'middle_aged', 'use_case': '', 'descriptive': '', 'description': '',
             'language': 'en', 'on_account': False, 'favourite': i == 3} for i in range(500)]
    monkeypatch.setattr(V, 'mirror_rows', lambda conn: {'voices': rows, 'refreshed_at': '2026-10-20T07:47:00', 'count': 500})
    page = V.mirror_page(None, {'accent': 'indian'})
    assert page['matched'] == 250 and len(page['voices']) == 200 and page['voices'][0]['voice_id'] == 'v3' and page['count'] == 500 and page['refreshed_at']
    assert V.mirror_page(None, {'search': 'voice 499'})['matched'] == 1


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
