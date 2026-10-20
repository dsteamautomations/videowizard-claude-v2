"""design/52 A and B, the parts that need no database: compact catalog rows, the usage directory from job and output rows,
the final record's summary, and the page state document."""
from datetime import datetime, timezone

from app import voices as V

RAW = {'voice_id': 'v1', 'name': 'Adamya Sharma', 'labels': {'accent': 'indian', 'gender': 'male', 'age': 'middle_aged', 'use_case': 'informative_educational', 'descriptive': 'confident'},
       'description': 'A 30-year-old Indian male, ' + 'authoritative voice, ' * 20, 'preview_url': 'https://x/p.mp3', 'category': 'professional', 'scope': 'library',
       'high_quality_base_model_ids': ['eleven_v4'], 'verified_languages': [{'language': 'en'}], 'sharing': {'public_owner_id': 'o1', 'original_voice_id': 'v1'}, 'public_owner_id': 'o1'}


def test_compact_row_keeps_the_identifying_fields_and_cuts_the_description():
    row = V.compact(RAW, register={'v1': {'favourite': True, 'note': 'warm'}}, usage={'v1': {'narrations': 2, 'auditions': 5, 'last_used': '2026-10-18'}}, account_ids={'v1'})
    assert row['voice_id'] == 'v1' and row['accent'] == 'indian' and row['gender'] == 'male' and row['age'] == 'middle_aged' and row['use_case'] == 'informative_educational'
    assert len(row['description']) <= 161 and row['description'].endswith('…') and row['preview_url'] == 'https://x/p.mp3'
    assert row['favourite'] is True and row['note'] == 'warm' and row['on_account'] is True and row['narrations'] == 2 and row['auditions'] == 5
    assert row['library'] == {'public_owner_id': 'o1', 'original_voice_id': 'v1'}
    assert set(row) <= {'voice_id', 'name', 'accent', 'gender', 'age', 'use_case', 'descriptive', 'description', 'preview_url', 'scope', 'on_account', 'favourite', 'note',
                        'narrations', 'auditions', 'last_used', 'library', 'category'}


def test_compact_row_without_register_or_usage():
    row = V.compact({'voice_id': 'v2', 'name': 'X', 'labels': {}, 'description': None}, register={}, usage={}, account_ids=set())
    assert row['favourite'] is False and row['on_account'] is False and row['narrations'] == 0 and row['description'] == ''


def when(day):
    return datetime(2026, 10, day, 12, 0, tzinfo=timezone.utc)


JOBS = [{'request': {'kind': 'audition', 'voice_id': 'v1', 'name': 'A'}, 'status': 'ready', 'created_at': when(1), 'code': 'VW-5', 'title': 'T5', 'client': 'C'},
        {'request': {'kind': 'narration', 'voice_id': 'v1', 'name': 'A'}, 'status': 'ready', 'created_at': when(2), 'code': 'VW-5', 'title': 'T5', 'client': 'C'},
        {'request': {'kind': 'narration', 'voice_id': 'v2', 'name': 'B'}, 'status': 'failed', 'created_at': when(3), 'code': 'VW-6', 'title': 'T6', 'client': 'D'},
        {'request': {'kind': 'audition', 'voice_id': 'v2', 'name': 'B'}, 'status': 'ready', 'created_at': when(4), 'code': 'VW-6', 'title': 'T6', 'client': 'D'}]
OUTPUTS = [{'summary': {'voice_id': 'v1', 'name': 'A'}, 'created_at': when(5), 'code': 'VW-5', 'title': 'T5', 'client': 'C'}]


def test_directory_counts_ready_jobs_and_final_narrations_per_voice():
    d = V.aggregate(JOBS, OUTPUTS)
    assert d['v1'] == {'name': 'A', 'narrations': 1, 'auditions': 1, 'final_in': [{'code': 'VW-5', 'title': 'T5', 'client': 'C', 'date': '2026-10-05'}],
                       'narrated_in': [{'code': 'VW-5', 'title': 'T5', 'client': 'C', 'date': '2026-10-02'}], 'auditioned_in': [{'code': 'VW-5', 'title': 'T5', 'client': 'C', 'date': '2026-10-01'}],
                       'last_used': '2026-10-05'}
    assert d['v2']['narrations'] == 0 and d['v2']['auditions'] == 1 and d['v2']['final_in'] == [] and d['v2']['last_used'] == '2026-10-04'


def test_release_rules_are_decided_from_the_register_row():
    assert V.release_refusal({'source': 'custom'}) == 'custom voices are never deleted here'
    assert 'favourite since 2026-10-18, by SK; unmark it first' == V.release_refusal({'source': 'library', 'favourite': True, 'favourite_at': when(18), 'favourite_by': 'SK'})
    assert V.release_refusal({'source': 'library', 'favourite': False}) is None
    assert V.release_refusal(None) == 'not in the register'


def test_page_state_starts_empty_and_keeps_every_narration():
    state = V.new_page_state()
    assert state == {'contract': 'vw2-voice-page-v1', 'shortlist': [], 'excerpt': None, 'pick': None, 'narrations': [], 'final': None}
    V.add_narration(state, {'job_id': 'j1', 'voice_id': 'v1', 'name': 'A', 'direction_digest': 'd1', 'tweaks': [], 'by': 'SK', 'at': '2026-10-20T10:00:00+00:00'})
    V.add_narration(state, {'job_id': 'j2', 'voice_id': 'v1', 'name': 'A', 'direction_digest': 'd1', 'tweaks': [], 'by': 'SK', 'at': '2026-10-20T10:05:00+00:00'})
    assert [n['number'] for n in state['narrations']] == [1, 2]
    V.mark_direction_change(state, 'd2')
    assert all(n['made_before_direction_change'] for n in state['narrations'])
    V.add_narration(state, {'job_id': 'j3', 'voice_id': 'v2', 'name': 'B', 'direction_digest': 'd2', 'tweaks': [], 'by': 'SK', 'at': '2026-10-20T10:09:00+00:00'})
    assert state['narrations'][2]['number'] == 1 and not state['narrations'][2].get('made_before_direction_change')


def test_final_summary_names_the_voice_the_direction_and_the_words():
    job = {'id': 'j1', 'request': {'voice_id': 'v1', 'name': 'A', 'model_id': 'eleven_v4', 'settings': {'stability': 0.5, 'similarity_boost': 0.75}, 'source_script': 'sha', 'direction_digest': 'd1', 'tweaks': []},
           'result': {'audio_key': 'r/voice/j1.mp3', 'sha256': 'a', 'bytes': 1, 'timing_key': 'r/voice/j1.timing.json', 'timing_sha256': 'b', 'timing_bytes': 2, 'duration_s': 9.5}, 'cost': {'characters': 100}}
    body = V.final_body(job, 'sha', beats=[{'beat_id': 'BEAT_01'}], quote='Make this the final narration', direction={'chosen': 'best_fit', 'digest': 'd1'})
    assert body['stage'] == 'voice' and body['accepted_quote'] == 'Make this the final narration'
    assert [f['name'] for f in body['files']] == ['narration.mp3', 'timing.json'] and all(f['location'] == 'storage' for f in body['files'])
    s = body['summary']
    assert s['voice_id'] == 'v1' and s['job_id'] == 'j1' and s['direction'] == {'chosen': 'best_fit', 'digest': 'd1'} and s['beats'] == [{'beat_id': 'BEAT_01'}] and s['recorded_from'] == 'page'
