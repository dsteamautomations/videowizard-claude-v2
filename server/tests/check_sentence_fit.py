"""design/193: Gemini 4 Hydrogen watches every clip and fits by sentence; the placer's list carries each piece's own lines; a related piece is
not a direct match. Without a database (run: python tests/check_sentence_fit.py from server/). The real functions, small inputs."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'server'))
from app import analysis   # noqa: E402
from app.stage2 import package as P   # noqa: E402
from app.stage2 import validator as VAL   # noqa: E402

RUN = {'id': 'r1', 'code': 'VW-T', 'client': 'c', 'film': {'shape': {'value': 'horizontal', 'video': 'horizontal', 'fps': 25}}}
SCRIPT = {'spoken_text': 'The wall is built. It is then cured for a week.\n\nThe result is strong.', 'content_digest': 'd',
          'passages': {'P001': 'The wall is built. It is then cured for a week.', 'P002': 'The result is strong.'},
          'beats': [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'The wall is built. It is then cured for a week.'}, {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'The result is strong.'}]}
CLIP = {'id': 'abcdef0123456789', 'name': 'C1.mp4', 'duration_s': 3.0, 'fps': '25/1', 'sha256': 'x', 'width': 1920, 'height': 1080}
POLICY = {'camera_audio': 'excluded', 'understand_audio': True}
SETTINGS = {'thinking_level': 'HIGH', 'media_resolution': 'MEDIA_RESOLUTION_HIGH', 'max_output_tokens': 65536}


def procedure(**settings):
    return {'contract_version': 'clip-log-v1', 'model': 'gemini-4-hydrogen', 'settings': {**SETTINGS, **settings}}


def sub(reasoning, limits, primary=(), secondary=()):
    return {'visual_action_observed': 'A hand places a part.', 'continuity_and_story': {'beat_fit_reasoning': reasoning, 'beat_fit_limits': limits,
                                                                                    'primary_fit_for_beats': list(primary), 'secondary_fit_for_beats': list(secondary)},
            'max_usable_window': {'in_s': 1.0, 'out_s': 9.0}}


def demo():
    # ---- R2: the request gives the script as its sentences, and says so; a paragraph request is as before ----
    beats = analysis.sentence_beats(SCRIPT)
    assert [b['beat_id'] for b in beats] == ['BEAT_01', 'BEAT_02', 'BEAT_03'] and beats[1]['text'] == 'It is then cured for a week.', beats
    req = analysis.build_request(RUN, procedure(processing_mode='AGENTIC', fit_unit='sentence'), {}, SCRIPT, CLIP, POLICY)
    assert req['identity']['fit_unit'] == 'sentence' and req['identity']['sentences'] == 3
    assert [b['text'] for b in req['project_config']['script_beats']] == [b['text'] for b in beats]
    assert 'ONE sentence' in req['prompt'] and 'EXACT, PARTLY or RELATED' in req['prompt'] and 'BEAT_01..BEAT_03' in req['prompt']
    old = analysis.build_request(RUN, procedure(processing_mode='auto', agentic_over_seconds=15), {}, SCRIPT, CLIP, POLICY)
    assert 'fit_unit' not in old['identity'] and len(old['project_config']['script_beats']) == 2 and 'ONE sentence' not in old['prompt'] and 'Tier-1 direct' in old['prompt']
    assert req['schema'] == old['schema']   # no field is added to the form
    # a script with no spoken text falls back to its paragraphs, and does not claim a fit by sentence
    bare = analysis.build_request(RUN, procedure(fit_unit='sentence'), {}, {**SCRIPT, 'spoken_text': ''}, CLIP, POLICY)
    assert 'fit_unit' not in bare['identity'] and len(bare['project_config']['script_beats']) == 2
    # more than 99 sentences: three digits
    many = analysis.sentence_beats({'spoken_text': ' '.join(f'Line {i}.' for i in range(120))})
    assert many[0]['beat_id'] == 'BEAT_001' and many[-1]['beat_id'] == 'BEAT_120'

    # ---- R1: every clip is watched the look-again way ----
    assert analysis.processing_mode(procedure(processing_mode='AGENTIC'), 3.0) == 'AGENTIC'
    assert analysis.processing_mode(procedure(processing_mode='auto', agentic_over_seconds=15), 3.0) == 'STATIC'   # the older setting still reads as it did
    served = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']
    st = next(s for s in served if s['name'] == 'analysis')
    assert st['model'] == 'gemini-4-hydrogen' and st['settings']['processing_mode'] == 'AGENTIC' and st['settings']['fit_unit'] == 'sentence', st['settings']
    assert st['settings']['thinking_level'] == 'HIGH' and st['settings']['media_resolution'] == 'MEDIA_RESOLUTION_HIGH'
    assert 'Flash' not in json.dumps(st['steps']) and 'Hydrogen' in json.dumps(st['steps'])

    # ---- R3: reading the fit lines; what is wrong is left out and counted ----
    s = sub('BEAT_02 2.9-4.5 s PARTLY: the part is placed, not fixed\nBEAT_03 1.0 - 9.0 s RELATED: suits the subject / BEAT_07 2.0-3.0 s EXACT: no such sentence\nBEAT_01 looks right to me\nBEAT_01 0.2-12.0 s EXACT: outside the piece',
            'BEAT_02: it is not fixed in these seconds. BEAT_03: nothing of the result is shown.', primary=['BEAT_01'], secondary=['BEAT_02', 'BEAT_03'])
    own = P.own_lines(s, 3)
    assert own['what'] == 'A hand places a part.'
    assert [(f['sentence'], f['match'], f['from_s'], f['to_s']) for f in own['sentence_fits']] == [(2, 'PARTLY', 2.9, 4.5), (3, 'RELATED', 1.0, 9.0), (1, 'EXACT', None, None)], own['sentence_fits']
    assert own['sentence_fits'][0]['missing'].startswith('it is not fixed') and own['sentence_fits'][2]['why'] == 'no line given'   # a primary with no usable line still counts
    assert own['fit_lines_unread'] == 3   # an unknown sentence, a line not in the form, seconds outside the piece
    assert P.own_lines(sub('It suits the opening.', 'nothing', primary=['BEAT_01']), 0) == {'what': 'A hand places a part.'}   # a paragraph log: nothing is read as a sentence fit

    # ---- R3: the fit of a piece to a scene, from the sentences ----
    windows = [{'beat_id': 'BEAT_01', 'timeline_start_frame': 0, 'timeline_end_frame': 100, 'process_stages': ['build']}, {'beat_id': 'BEAT_02', 'timeline_start_frame': 100, 'timeline_end_frame': 200, 'process_stages': []}]
    sentences = [{'start_frame': 0, 'end_frame': 40}, {'start_frame': 45, 'end_frame': 95}, {'start_frame': 105, 'end_frame': 190}]
    rows = [{'sub_clip_id': 'a', 'primary_fits': ['BEAT_01'], 'secondary_fits': ['BEAT_02', 'BEAT_03'], 'process_stage': None, **own},
            {'sub_clip_id': 'b', 'primary_fits': [], 'secondary_fits': [], 'process_stage': 'build', 'what': 'x', 'sentence_fits': [], 'fit_lines_unread': 0}]
    P.scene_fits_by_sentence(rows, windows, sentences)
    a, b = rows
    assert a['fit_kinds'] == {'BEAT_01': 'direct', 'BEAT_02': 'related'} and a['primary_fits'] == ['BEAT_01'] and a['secondary_fits'] == ['BEAT_02'] and a['fit_unit'] == 'sentence', a
    assert [(f['step_id'], f['match']) for f in a['sentence_fits']] == [('BEAT_01.S2', 'PARTLY'), ('BEAT_02.S1', 'RELATED'), ('BEAT_01.S1', 'EXACT')]
    assert a['model_fits'] == {'primary': ['BEAT_01'], 'secondary': ['BEAT_02', 'BEAT_03']}
    assert b['fit_kinds'] == {'BEAT_01': 'chapter'}   # the scene's chapter still counts

    # ---- which kind of log a film holds: every clip by sentence and the counts agree, else by paragraph, with the reason ----
    by = lambda n: {'fit_unit': 'sentence', 'sentences': n}
    assert P.fit_unit([by(3), by(3)], 3) == ('sentence', '')
    assert P.fit_unit([by(3), {}], 3)[0] == 'paragraph' and 'before' in P.fit_unit([by(3), {}], 3)[1]
    assert P.fit_unit([by(4), by(4)], 3)[0] == 'paragraph' and '4' in P.fit_unit([by(4), by(4)], 3)[1]
    assert P.fit_unit([{}, {}], 3) == ('paragraph', '')   # an older film: as today, nothing to say

    # ---- R4: a piece only related to a sentence is not a direct match for it ----
    row = {'fit_unit': 'sentence', 'sentence_fits': a['sentence_fits']}
    assert VAL.related_as_direct(row, 'BEAT_02.S1', {'match': 'direct'}) and 'B-roll' in VAL.related_as_direct(row, 'BEAT_02.S1', {'match': 'direct'})
    assert 'no fit' in VAL.related_as_direct(row, 'BEAT_02.S9', {'match': 'direct'})          # no fit at all for that sentence
    assert VAL.related_as_direct(row, 'BEAT_02.S1', {'match': 'b_roll'}) is None                 # as B-roll it passes
    assert VAL.related_as_direct(row, 'BEAT_01.S2', {'match': 'direct'}) is None                 # partly may be direct
    assert VAL.related_as_direct(row, 'BEAT_01.S1', {'match': 'direct'}) is None                 # exact
    assert VAL.related_as_direct({'sentence_fits': []}, 'BEAT_02.S1', {'match': 'direct'}) is None   # an older log is not checked
    assert VAL.related_as_direct({'fit_unit': 'sentence', 'library': True, 'sentence_fits': []}, 'BEAT_02.S1', {'match': 'library'}) is None

    # ---- R3: the tool's pieces file shows each piece's own lines; the clip's overview once ----
    spec = importlib.util.spec_from_file_location('vw_tool', ROOT / 'plugin' / 'scripts' / 'vw.py')
    vw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vw)
    piece = lambda sid, fit: {'sub_clip_id': sid, 'clip_id': 'c1', 'clip_name': 'C1.mp4', 'grade': 'A', 'duration_s': 3.0, 'fit_kinds': {'BEAT_01': fit}, 'what': 'own ' + sid, 'beat_fit_limits': 'not ' + sid,
                               'sentence_fits': [{'step_id': 'BEAT_01.S1', 'match': 'EXACT', 'from_s': 1.0, 'to_s': 2.0, 'missing': ''}, {'step_id': 'BEAT_02.S1', 'match': 'RELATED', 'from_s': 1.0, 'to_s': 2.0, 'missing': 'm'}]}
    data = {'cards': [{'clip_id': 'c1', 'lines': ['1 OVERVIEW: the whole clip']}], 'beats': [{'beat_id': 'BEAT_01', 'title': 't', 'process_stages': [], 'steps': []}],
            'sub_clips': [piece('p1', 'direct'), piece('p2', 'direct'), piece('p3', 'related')]}
    scenes, _other = vw.pieces_by_scene(data)
    got = scenes[0]['pieces']
    assert got[0]['what'] == 'own p1' and got[0]['does_not_show'] == 'not p1' and got[0]['seen'] == 'the whole clip' and 'seen' not in got[1], got[:2]
    assert got[0]['fits'] == [{'step_id': 'BEAT_01.S1', 'match': 'EXACT', 'from_s': 1.0, 'to_s': 2.0}]   # only this scene's sentences
    assert got[2]['what'] == 'own p3' and 'fits' not in got[2]   # a related piece keeps its short row, with its own description
    assert 'does_not_show' not in vw.pieces_by_scene({**data, 'sub_clips': [{**piece('p1', 'direct'), 'fit_unit': 'sentence'}]})[0][0]['pieces'][0]   # by sentence: what is missing is inside `fits`
    # a common action: the exact pieces in full, then ten more, the rest as short rows; exact first
    partly = lambda i: {**piece(f'q{i:02d}', 'direct'), 'clip_id': f'c{i}', 'clip_name': f'C{i}.mp4', 'fit_unit': 'sentence', 'in_frame': 1, 'out_frame': 9,
                        'sentence_fits': [{'step_id': 'BEAT_01.S1', 'match': 'PARTLY', 'from_s': 1.0, 'to_s': 2.0, 'missing': 'm'}]}
    exact = {**partly(99), 'sub_clip_id': 'exact', 'sentence_fits': [{'step_id': 'BEAT_01.S1', 'match': 'EXACT', 'from_s': 1.0, 'to_s': 2.0, 'missing': ''}]}
    crowd = vw.pieces_by_scene({**data, 'sub_clips': [partly(i) for i in range(14)] + [exact]})[0][0]['pieces']
    assert crowd[0]['sub_clip_id'] == 'exact' and sum(1 for p in crowd if 'fits' in p) == 11 and sum(1 for p in crowd if 'fits' not in p) == 4, [list(p) for p in crowd]
    assert all(p['fit'] == 'direct' and p['what'] for p in crowd)

    # ---- R5: the rule is in the options instructions and the second look ----
    text = json.dumps(next(s for s in served if s['name'] == 'options'), ensure_ascii=False)
    assert 'opposite directions' in text and 'one choice' in text
    print('ok: the sentence-fit checks pass')


if __name__ == '__main__':
    demo()
