"""design/139 R5 (SK, 2 Nov 2026, design/138 A7): never assume English. The analysis is told the languages are not given and reports what it hears; the
film's footage languages are named from the clip records (the main one first, one or two others when mixed, or no speech)."""
from app import analysis_jobs as AJ
from app.clip_log import gate


def sub(lang=None):
    block = {'spoken_language': lang} if lang else None
    return {'stage15': {'visual_eligibility': 'ELIGIBLE'}, 'usability_grade': 'A', 'people_and_speaker_analysis': {'speech_translation_block': block}, 'risk_flags': []}


def summary(*langs):
    return gate.summary_of({'status': 'accepted', 'log': {'sub_clips': [sub(l) for l in langs]}}, {'id': 'c', 'name': 'c', 'duration_s': 4})


def test_each_clip_records_the_languages_it_heard():
    assert summary('ta', 'ta', 'en', None)['languages'] == ['ta', 'en']
    assert summary(None)['languages'] == []


def test_the_film_names_its_main_language_first_and_at_most_two_others():
    units = [{'summary': {'languages': l}} for l in (['ta'], ['ta', 'en'], ['ta'], ['hi'], ['te'], [])]
    assert AJ.film_languages(units) == {'main': 'ta', 'others': ['en', 'hi'], 'clips_with_speech': 5}
    assert AJ.film_languages([{'summary': {'languages': []}}, {'summary': None}]) == {'main': None, 'others': [], 'clips_with_speech': 0}


def test_the_analysis_is_never_told_english():
    from app.analysis import language_config
    assert language_config({}) == {'expected_field_speech_languages': 'not given: detect and report each spoken language (ISO code)',
                                   'final_vo_language': 'not given: read it from the script beats'}
    assert language_config({'field_speech_languages': ['ta'], 'narration_language': 'ta'}) == {'expected_field_speech_languages': ['ta'], 'final_vo_language': 'ta'}
