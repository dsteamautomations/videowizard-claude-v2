"""design/129 I: P4, the second look's record kept with the cut's version and shown on the review page; old ways 9 and 10, the declared-gap list no
longer copied into a version; the minimum tool 0.65.1."""
import inspect
import json
from pathlib import Path

from app.config import Settings
from app.stage2 import stage as S
from test_design127_review_pure import session_store
from test_review_page import FakeConn, RUN

REVIEW = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')
OPTIONS = [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [{'blank': True, 'timeline_frames': 150, 'intent': 'x'}]}]


def joined(**over):
    return {'at': '2026-11-01T12:20:00+00:00', 'scenes': 9, 'changed': ['BEAT_01', 'BEAT_03'], 'unchanged': {'BEAT_02': 'the house is right'},
            'no_fix_file': ['BEAT_09'], 'fixes': [{'scene': 'BEAT_01', 'option': 1, 'why': 'S2 shows the edge'}], 'joined_sha': S.options_sha(OPTIONS), **over}


def test_p4_no_record_when_the_cut_carries_none_or_a_broken_one():
    assert S.second_look_record({'options': OPTIONS}) is None
    assert S.second_look_record({'options': OPTIONS, 'second_look': 'yes'}) is None


def test_p4_the_record_keeps_what_ran_and_what_changed():
    r = S.second_look_record({'options': OPTIONS, 'second_look': joined()})
    assert r['at'] == '2026-11-01T12:20:00+00:00' and r['scenes'] == 9 and r['changed'] == ['BEAT_01', 'BEAT_03'] and r['unchanged'] == {'BEAT_02': 'the house is right'}
    assert r['no_fix_file'] == ['BEAT_09'] and r['fixes'] == [{'scene': 'BEAT_01', 'option': 1, 'why': 'S2 shows the edge'}] and r['edited_after'] is False


def test_p4_options_changed_after_the_join_are_named():
    other = [{**OPTIONS[0], 'events': [{'blank': True, 'timeline_frames': 150, 'intent': 'changed by hand'}]}]
    assert S.second_look_record({'options': other, 'second_look': joined()})['edited_after'] is True


def test_p4_a_malformed_or_huge_record_is_kept_as_far_as_it_reads_and_never_refuses():
    r = S.second_look_record({'options': OPTIONS, 'second_look': {'scenes': 'nine', 'changed': 'BEAT_01', 'unchanged': ['x'], 'fixes': [{'scene': 5}] * 500,
                                                                   'at': 'x' * 500}})
    assert r['scenes'] == 0 and r['changed'] == [] and r['unchanged'] == {} and len(r['fixes']) == 200 and len(r['at']) <= 40 and r['edited_after'] is True


def test_p4_propose_keeps_the_record_beside_the_version_and_out_of_its_fingerprint():
    src = inspect.getsource(S.propose)
    assert "second = second_look_record(doc)" in src and "work.pop('second_look', None)" in src
    assert src.index("work.pop('second_look', None)") < src.index('identity = digest(work)') and "'second_look': second" in src


def test_p4_the_review_page_reads_and_shows_the_record():
    store = session_store()
    sess = json.loads(store.files['run-1/stage2/session.json'])
    sess['versions'][0]['second_look'] = S.second_look_record({'options': OPTIONS, 'second_look': joined()})
    store.files['run-1/stage2/session.json'] = json.dumps(sess).encode('utf-8')
    assert S.review_view(FakeConn({}), store, RUN)['second_look']['scenes'] == 9
    for needle in ('Second look: ran ', 'Second look: not recorded for this version', 'the cut was changed after the second look'):
        assert needle in REVIEW, needle


def test_old_ways_9_and_10_a_version_no_longer_copies_a_declared_gap_list():
    assert "work.get('gaps')" not in inspect.getsource(S.propose)


def test_the_minimum_tool_is_0_65_1_or_later():   # design/130 raised it to 0.66.0
    assert tuple(int(x) for x in Settings.model_fields['PLUGIN_MIN_VERSION'].default.split('.')) >= (0, 65, 1)
