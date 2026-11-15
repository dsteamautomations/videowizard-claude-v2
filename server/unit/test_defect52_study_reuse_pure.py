"""Defect 52 (VW-24, 15 Nov 2026): every clip of the film was already in the client's library and was skipped, so the film had no studied clip,
the brand-generic answer could not be recorded and the options could not be prepared. SK's decision: a skipped clip that is the same file brings
its stored study into the new film, free; its line fits are kept only for a sentence whose words are exactly the same in both films."""
import json

import pytest

from app import brandlib as B, study_reuse as R
from app.errors import Problem


def beats(*texts):
    return [{'beat_id': f'BEAT_{i:02d}', 'text': t} for i, t in enumerate(texts, 1)]


OLD = beats('The slab is cast.', 'Tiles replace the lower concrete.', 'The roof stays strong.', 'Water curing follows.')


# ---------- which sentences are the same ----------

def test_identical_scripts_map_every_sentence_to_itself():
    assert R.sentence_map(OLD, beats(*[b['text'] for b in OLD])) == {1: 1, 2: 2, 3: 3, 4: 4}


def test_a_moved_sentence_keeps_its_fits_and_a_reworded_or_removed_one_does_not():
    new = beats('A new opening line.', 'The slab is cast.', 'Tiles replace the lower part of the concrete.', 'Water curing follows.')
    assert R.sentence_map(OLD, new) == {1: 2, 4: 4}   # 1 moved to 2; 2 was reworded; 3 was removed; 4 is where it was


def test_only_spaces_may_differ_and_a_sentence_said_twice_is_matched_in_order():
    assert R.sentence_map(beats('Same  words here.'), beats('Same words here.')) == {1: 1}
    assert R.sentence_map(beats('Again.', 'Other.', 'Again.'), beats('Again.', 'Again.', 'Other.')) == {1: 1, 2: 3, 3: 2}
    assert R.sentence_map(beats('The Slab.'), beats('The slab.')) == {}   # a changed letter is a changed sentence


# ---------- the study's fits carried over ----------

def study():
    return json.dumps({'clip_id': 'ABC', 'filename': 'C1.mp4', 'descriptive_name': 'tile laid', 'sub_clips': [
        {'sub_clip_id': 'SUB_ABC_01', 'continuity_and_story': {
            'primary_fit_for_beats': ['BEAT_02', 'BEAT_03'], 'secondary_fit_for_beats': ['BEAT_04'],
            'beat_fit_reasoning': 'BEAT_02 1.0-3.0 s EXACT: the tile is laid\nBEAT_03 0.5-2.0 s PARTLY: strength is implied\nBEAT_04 2.0-4.0 s RELATED: water nearby',
            'beat_fit_limits': 'BEAT_03 the load is not shown'}},
        {'sub_clip_id': 'SUB_ABC_02', 'continuity_and_story': {'primary_fit_for_beats': [], 'secondary_fit_for_beats': [], 'beat_fit_reasoning': '', 'beat_fit_limits': ''}}]})


def test_the_same_script_leaves_the_study_exactly_as_it_was():
    raw = study()
    out, counts = R.carry(raw, {1: 1, 2: 2, 3: 3, 4: 4}, 4, 4)
    assert out is raw and counts == {'kept': 'all', 'dropped': 0}


def test_fits_follow_their_sentence_and_the_others_are_dropped():
    out, counts = R.carry(study(), {2: 5, 4: 4}, 4, 12)   # sentence 2 is now 5, 4 stays, 3 is gone
    story = json.loads(out)['sub_clips'][0]['continuity_and_story']
    assert story['primary_fit_for_beats'] == ['BEAT_05'] and story['secondary_fit_for_beats'] == ['BEAT_04']
    assert story['beat_fit_reasoning'] == 'BEAT_05 1.0-3.0 s EXACT: the tile is laid\nBEAT_04 2.0-4.0 s RELATED: water nearby'
    assert story['beat_fit_limits'] == '' and counts == {'kept': 2, 'dropped': 1}
    body = json.loads(out)
    assert body['descriptive_name'] == 'tile laid' and body['sub_clips'][1]['sub_clip_id'] == 'SUB_ABC_02'   # nothing else is touched


def test_a_longer_script_gets_wider_sentence_numbers():
    out, _ = R.carry(study(), {2: 105}, 4, 120)
    assert json.loads(out)['sub_clips'][0]['continuity_and_story']['primary_fit_for_beats'] == ['BEAT_105']


def test_no_matching_sentence_keeps_the_study_with_no_fits():
    out, counts = R.carry(study(), {}, 4, 9)
    story = json.loads(out)['sub_clips'][0]['continuity_and_story']
    assert story['primary_fit_for_beats'] == [] and story['beat_fit_reasoning'] == '' and counts == {'kept': 0, 'dropped': 3}


def test_an_answer_that_is_not_a_study_is_not_reused():
    assert R.carry('not json', {1: 1}, 1, 2) == (None, None)
    assert R.carry('[1, 2]', {1: 1}, 1, 2) == (None, None)


# ---------- whether a stored study may be reused at all ----------

class Store:
    def __init__(self, files):
        self.files = files

    def exists(self, k):
        return k in self.files

    def get(self, k):
        return self.files[k]


class Conn:
    def __init__(self, job):
        self.job = job

    def execute(self, sql, args=()):
        return type('R', (), {'fetchone': lambda s: self.job})()


def stored(identity=None, by_sentence=True, old_beats=OLD):
    identity = {'contract_version': 'clip-log-v1', 'model': 'm1', 'schema_digest': 's1', **({'fit_unit': 'sentence', 'sentences': len(old_beats)} if by_sentence else {}), **(identity or {})}
    files = {'r0/analysis/a1.evidence.json': json.dumps({'identity': identity, 'log': {}}).encode(), 'r0/analysis/a1.response.json': study().encode(),
             'r0/analysis/a1.request.json': json.dumps({'identity': identity, 'project_config': {'script_beats': old_beats}}).encode()}
    return Store(files), Conn({'request': {'request_key': 'r0/analysis/a1.request.json'}})


def request(new_beats, by_sentence=True):
    return {'identity': {'contract_version': 'clip-log-v1', 'model': 'm1', 'schema_digest': 's1', **({'fit_unit': 'sentence', 'sentences': len(new_beats)} if by_sentence else {})},
            'project_config': {'script_beats': new_beats}}


ROW = {'evidence_key': 'r0/analysis/a1.evidence.json', 'films': ['VW-23'], 'name': 'C1.mp4'}


def test_the_same_file_with_the_same_script_is_reused_whole():
    store, conn = stored()
    got = R.plan(conn, store, ROW, request(OLD))
    assert got['raw'] == study() and got['from'] == 'VW-23' and got['fits'] == {'kept': 'all', 'dropped': 0}


def test_a_changed_script_reuses_the_study_and_carries_only_the_identical_sentences():
    store, conn = stored()
    got = R.plan(conn, store, ROW, request(beats('Something new.', 'Tiles replace the lower concrete.')))
    assert got['fits'] == {'kept': 1, 'dropped': 2} and json.loads(got['raw'])['sub_clips'][0]['continuity_and_story']['primary_fit_for_beats'] == ['BEAT_02']


def test_a_study_by_paragraph_or_a_film_by_paragraph_carries_no_fits():
    store, conn = stored(by_sentence=False)
    assert R.plan(conn, store, ROW, request(OLD))['fits'] == {'kept': 0, 'dropped': 3}
    store, conn = stored()
    assert R.plan(conn, store, ROW, request(OLD, by_sentence=False))['fits'] == {'kept': 0, 'dropped': 3}


@pytest.mark.parametrize('change', [{'contract_version': 'clip-log-v0'}, {'model': 'older-model'}, {'schema_digest': 'another form'}])
def test_a_study_of_another_form_or_model_is_not_reused(change):
    store, conn = stored(identity=change)
    assert R.plan(conn, store, ROW, request(OLD)) is None


def test_a_missing_file_or_record_means_no_reuse():
    store, conn = stored()
    del store.files['r0/analysis/a1.response.json']
    assert R.plan(conn, store, ROW, request(OLD)) is None
    store, conn = stored()
    assert R.plan(Conn(None), store, ROW, request(OLD)) is None            # the job that made the study is not on record
    assert R.plan(conn, store, {**ROW, 'evidence_key': None}, request(OLD)) is None


# ---------- the brand-generic answer when nothing new was studied ----------

RUN = {'id': 'r1', 'code': 'VW-24', 'status': 'open', 'client_id': 'C-086', 'film': {'library_skipped': [{'clip_id': 'a1', 'name': 'C1.mp4'}]}}
SKIPPED = [{'stage': 'media', 'unit': None, 'summary': {'clips': [{'id': 'a1', 'name': 'C1.mp4', 'sha256': 'a' * 64}]}},
           {'stage': 'analysis', 'unit': 'a1', 'files': [], 'summary': {'excluded': True, 'library_skipped': True}}]


class Rec:
    def __init__(self):
        self.sql = []

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        return type('R', (), {'fetchone': lambda s: None, 'fetchall': lambda s: []})()


def test_none_is_recorded_when_every_clip_was_skipped():
    conn = Rec()
    out = B.mark(conn, None, {'id': 'u1', 'name': 'Uma'}, RUN, SKIPPED, [], 'None')
    assert out == {'stored': 0, 'generic': [], 'skipped': 'every clip of this film is already in the library: nothing new to store'}
    rec = next(a for s, a in conn.sql if 'update vw2_runs set film' in s)
    assert rec[0].obj['asked'] is True and rec[0].obj['quote'] == 'None' and not any('insert into vw2_library' in s for s, _ in conn.sql)


def test_a_name_given_when_nothing_new_was_studied_is_refused_with_the_way_to_change_a_mark():
    with pytest.raises(Problem) as e:
        B.mark(Rec(), None, {'id': 'u1'}, RUN, SKIPPED, ['C1.mp4'], 'that one')
    assert 'already in the library' in e.value.message and 'vw library unmark' in e.value.message


def test_a_film_with_no_studied_clip_and_nothing_skipped_is_still_refused():
    with pytest.raises(Problem) as e:
        B.mark(Rec(), None, {'id': 'u1'}, {**RUN, 'film': {}}, SKIPPED[:1], [], 'none')
    assert 'No studied clips yet' in e.value.message
