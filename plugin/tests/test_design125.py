"""design/125, the review of the whole flow on VW-11: the chat tool's side.
I1, I4, M1 the operator command text; I2 the --images help; B1 an empty list of footage languages; M1 the camera-sound answer required;
S3 the script's claims kept and written for the visuals stage."""
import json

import pytest

from conftest import PLUGIN, STAGES
import stages_av as AV
import vw
from stages_text import Refused, digest, production_inputs, script_record
from test_script import SOURCE, prior_of, proposal

COMMAND = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')


def test_i1_i4_m1_the_operator_command_text():
    assert 'ask the operator which picture AI this film uses' in COMMAND and '--images openai|gemini' in COMMAND
    assert 'procedure version 2, the current default' not in COMMAND and 'procedure versions 2 and 3' not in COMMAND   # I4, then version 2 retired (design/125 stage 7)
    media = next(line for line in COMMAND.split('\n') if line.startswith('**Media**'))
    assert '--camera-audio allowed|excluded' in media and 'camera sound' in media


def test_i2_the_images_help_carries_no_change_history_label():
    source = (PLUGIN / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    line = next(l for l in source.split('\n') if "add_argument('--images'" in l)
    assert 'design/' not in line.split('help=')[1]


def test_b1_nobody_speaks_in_the_footage_is_an_answer():
    out = production_inputs({'field_speech_languages': [], 'narration_language': 'en'})
    assert out['field_speech_languages'] == []
    with pytest.raises(Refused, match='asked of the operator on every film'):
        production_inputs({'narration_language': 'en'})
    with pytest.raises(Refused, match='asked of the operator on every film'):
        production_inputs({'field_speech_languages': ['ta'], 'narration_language': ''})


def media_ws(tmp_path):
    ws = tmp_path / 'VW-9'
    (ws / 'work').mkdir(parents=True)
    (ws / 'out').mkdir()
    clip = {'id': 'c1', 'name': 'C1.mp4', 'sha256': 'a' * 64, 'bytes': 3, 'duration_s': 1.0, 'has_audio': False, 'fps': '25/1', 'start_timecode': '', 'reel': '', 'original_name': ''}
    (ws / 'work' / 'media-clips.json').write_text(json.dumps([clip]), encoding='utf-8')
    return ws


def test_m1_the_camera_sound_answer_is_required(tmp_path):
    ws = media_ws(tmp_path)
    with pytest.raises(AV.Refused, match='may the camera sound be used in the film'):
        AV.media_record(ws, {}, None, lambda *a: {}, copies='copies')
    out = AV.media_record(ws, {}, None, lambda stage, path, sha, size: {'name': 'C1.mp4'}, camera_audio='excluded', note='not in the film', copies='copies')
    assert out['summary']['camera_audio'] == 'excluded'


def test_s3_the_scripts_claims_are_kept_in_the_record(ws):
    (ws / 'out' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    claims = [{'text': 'pressed, not fired', 'checked': True, 'source': 'https://example.org/cseb'}, {'text': 'keeps the carbon in the ground', 'checked': False}]
    proposal(ws, SOURCE, claims=claims)
    assert script_record(ws, STAGES['script'], prior_of())['summary']['claims'] == claims
    proposal(ws, SOURCE)
    assert script_record(ws, STAGES['script'], prior_of())['summary']['claims'] == []
    proposal(ws, SOURCE, claims=[{'text': '', 'checked': 'no'}])
    with pytest.raises(Refused, match='claims'):
        script_record(ws, STAGES['script'], prior_of())


def test_s3_the_claims_are_written_for_the_visuals_stage(tmp_path):
    files = vw.visuals_reading_files(tmp_path, {'prompt': 'p', 'script_claims': [{'text': '75 kg/cm2', 'checked': False}]})
    assert json.loads((tmp_path / 'work' / 'visuals' / 'claims.json').read_text(encoding='utf-8')) == [{'text': '75 kg/cm2', 'checked': False}]
    assert any(f['file'] == 'work/visuals/claims.json' for f in files)
    assert 'script_claims' not in json.loads((tmp_path / 'work' / 'visuals' / 'rest.json').read_text(encoding='utf-8'))
