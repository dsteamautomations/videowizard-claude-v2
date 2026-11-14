"""design/144 (SK, 2 Nov 2026): the pronunciation list before the full narration (IPA for names, places and local words; a respelling for abbreviations),
kept as one ElevenLabs dictionary per run and carried by every later narration on both front ends; offered to the client's next film; the direction's
number on each narration; the tweak control findable from chat."""
import json

import pytest

from app import elevenlabs, voices as V
from app.errors import Problem

ITEMS = [{'word': 'Kanyakumari', 'say_as': 'kun-yaa-KOO-muh-ree', 'ipa': 'kənjaːˈkuməɾi', 'kind': 'place'},
         {'word': 'NARDEP', 'say_as': 'NAR-dep', 'ipa': 'ˈnɑːrdɛp', 'kind': 'abbreviation'},
         {'word': 'Kendra', 'say_as': 'KAYN-druh', 'ipa': '', 'kind': 'local'}]


class Store:
    def __init__(self):
        self.files = {}

    def exists(self, k):
        return k in self.files

    def get(self, k):
        return self.files[k]

    def put(self, k, data, mime=None):
        self.files[k] = data


def test_the_list_is_checked():
    assert V.check_pronunciations(ITEMS) == ITEMS
    for bad in ([], [{'word': 'X', 'say_as': '', 'ipa': '', 'kind': 'place'}], [{'word': 'X', 'say_as': 'x', 'kind': 'colour'}], [ITEMS[0], ITEMS[0]]):
        with pytest.raises(Problem):
            V.check_pronunciations(bad)


def test_ipa_for_names_and_places_a_respelling_for_abbreviations_and_longer_words_first():
    rules = V.pronunciation_rules(ITEMS + [{'word': 'Kanya', 'say_as': 'KUN-yaa', 'ipa': 'kənjaː', 'kind': 'name'}])
    by = {r['string_to_replace']: r for r in rules}
    assert by['Kanyakumari'] == {'type': 'phoneme', 'string_to_replace': 'Kanyakumari', 'phoneme': 'kənjaːˈkuməɾi', 'alphabet': 'ipa'}
    assert by['NARDEP'] == {'type': 'alias', 'string_to_replace': 'NARDEP', 'alias': 'NAR-dep'}
    assert by['Kendra']['type'] == 'alias'   # no IPA given: the respelling
    assert [r['string_to_replace'] for r in rules].index('Kanyakumari') < [r['string_to_replace'] for r in rules].index('Kanya')


def test_recording_makes_a_dictionary_versions_it_and_marks_older_narrations(monkeypatch):
    made = []
    monkeypatch.setattr(V, 'make_dictionary', lambda name, rules: (made.append((name, rules)) or {'pronunciation_dictionary_id': f'D{len(made)}', 'version_id': 'v1'}))
    store, run = Store(), {'id': 'r1', 'code': 'VW-20'}
    store.put(V._key(run, 'page.json'), json.dumps({**V.new_page_state(), 'narrations': [{'job_id': 'j1', 'voice_id': 'v'}]}).encode())
    doc = V.set_pronunciations(store, {'name': 'SK'}, run, ITEMS, 'yes, and add Kendra')
    assert doc['version'] == 1 and doc['dictionary']['pronunciation_dictionary_id'] == 'D1' and doc['quote'] == 'yes, and add Kendra' and made[0][0] == 'vw2-VW-20-v1'
    assert V.page_state(store, run)['narrations'][0]['made_before_pronunciations_change'] is True
    assert V.set_pronunciations(store, {'name': 'SK'}, run, ITEMS[:2], 'yes')['version'] == 2
    with pytest.raises(Problem):
        V.set_pronunciations(store, {'name': 'SK'}, run, ITEMS, ' ')   # the operator's words are required
    assert V.dictionaries_for(store, run) == [{'pronunciation_dictionary_id': 'D2', 'version_id': 'v1'}]
    assert V.dictionaries_for(Store(), run) == []


def test_a_refused_dictionary_refuses_the_record(monkeypatch):
    def refuse(name, rules):
        raise Problem(502, 'PROVIDER_REJECTED', 'ElevenLabs says: missing_permissions')
    monkeypatch.setattr(V, 'make_dictionary', refuse)
    with pytest.raises(Problem) as e:
        V.set_pronunciations(Store(), {'name': 'SK'}, {'id': 'r1', 'code': 'VW-20'}, ITEMS, 'yes')
    assert 'missing_permissions' in e.value.message


def test_the_narration_request_carries_the_dictionary(monkeypatch):
    sent = {}
    el = elevenlabs.ElevenLabs()
    monkeypatch.setattr(el, 'request', lambda method, path, **kw: sent.update(kw) or 'audio')
    el.synthesize({'voice_id': 'abc', 'text': 'hello', 'model_id': 'eleven_v4', 'settings': {}, 'dictionaries': [{'pronunciation_dictionary_id': 'D1', 'version_id': 'v1'}]})
    assert sent['json']['pronunciation_dictionary_locators'] == [{'pronunciation_dictionary_id': 'D1', 'version_id': 'v1'}]
    el.synthesize({'voice_id': 'abc', 'text': 'hello', 'model_id': 'eleven_v4', 'settings': {}})
    assert 'pronunciation_dictionary_locators' not in sent['json']


def test_the_clients_last_list_is_offered():
    store, old, new = Store(), {'id': 'r0'}, {'id': 'r1'}
    store.put(V._key(old, 'pronunciations.json'), json.dumps({'version': 1, 'items': ITEMS}).encode())
    assert V.last_client_list(store, [old]) == ITEMS
    assert V.last_client_list(store, [new]) == []


def test_each_direction_gets_a_number():
    assert V.next_direction_number(None) == 1 and V.next_direction_number({'number': 2}) == 3 and V.next_direction_number({'digest': 'x'}) == 2   # one recorded before numbers: it was the first


def test_the_direction_warns_about_volume_lowering_tags_on_deep_voices():   # design/144 V2
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    p = next(s for s in d['stages'] if s['name'] == 'voice')['direction_prompt']
    assert 'breathy or husky' in p and 'only in the\nexperimental list' in p and '[softly]' not in p and '[quietly proud]' not in p


def test_a_narration_answer_names_where_the_tweak_control_is():   # design/144 V4
    assert "A sentence's tone or pace" in V.TWEAK_HINT and 'vw voice tweak' in V.TWEAK_HINT and 'A word sounds wrong' in V.TWEAK_HINT   # design/194: the control renamed, the word control beside it
    from pathlib import Path
    page = (Path(V.__file__).parent / 'templates' / 'voices2.html').read_text(encoding='utf-8')
    assert "<summary>A sentence's tone or pace</summary>" in page and 'direction_number' in page and 'made_before_pronunciations_change' in page
