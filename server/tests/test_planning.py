"""Planning P1–P13: the chat model's plan is authored here programmatically against the real package; the server checks it."""
import json
import re
from copy import deepcopy

import psycopg
import pytest

from app import analysis_jobs
from conftest import connected, vw
from test_analysis import FakeTransport, gemini  # noqa: F401
from test_stages_text import SOURCE, write_proposal
from test_voice_media import clip, drain, fake  # noqa: F401


def clip25(path, seconds=2, tone=440):
    import subprocess
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc=duration={seconds}:size=64x64:rate=25', '-f', 'lavfi', '-i', f'sine=frequency={tone}:duration={seconds}',
                    '-c:a', 'aac', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)


def run_until_planning(home, database, fake, gemini, n_clips=1):
    """Full pipeline on procedure version 1 (real stage table): intake → brief → script → voice → media → analysis."""
    connected(home, database)
    rc, out, err = vw(home, 'start', '--client', 'VK', '--version', '1', '--need-gb', '0')  # v1 evidence contract until step 4
    assert rc == 0, (out, err)
    ws = home['runs'] / out['code']
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    vw(home, 'stage', 'intake', 'prepare')
    write_proposal(ws, 'intake', {'remove': [], 'titles': ['Earth Blocks'], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'brief', {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e'})
    assert vw(home, 'stage', 'brief', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'script', {'spoken_text': 'Earth blocks are pressed.\n\nNot fired.', 'notes': '', 'assessment': '', 'changes': []})
    assert vw(home, 'stage', 'script', 'record', '--quote', 'yes')[0] == 0
    assert vw(home, 'voice', 'narrate', '--voice', 'v1')[0] == 0
    drain()
    job = vw(home, 'voice', 'jobs')[1][0]
    assert vw(home, 'voice', 'fetch', '--job', job['id'])[0] == 0
    assert vw(home, 'stage', 'voice', 'record', '--quote', 'yes')[0] == 0
    for i in range(n_clips):
        clip25(ws / 'in' / f'c{i}.mp4', tone=440 + 110 * i)
    assert vw(home, 'stage', 'media', 'prepare')[0] == 0
    rc, out, err = vw(home, 'stage', 'media', 'record', '--quote', 'yes')
    assert rc == 0, err
    rc, out, err = vw(home, 'analysis', 'start', '--camera-audio', 'excluded', '--film-type', 'documentary')
    assert rc == 0, err
    drain()
    assert vw(home, 'next')[1]['stage'] == 'planning'
    return ws


PREPARE = ['planning', 'prepare', '--fps', '25', '--resolution', '64x64', '--source-audio', 'none', '--visible-speaking', 'avoid']


def prepared(home, ws):
    rc, out, err = vw(home, *PREPARE)
    assert rc == 0, err
    package = json.loads((ws / 'work' / 'planning-package.json').read_text(encoding='utf-8'))
    words = package['context']['mapped_words']
    scenes = [{'first_word_id': words[0]['id'], 'last_word_id': words[-1]['id'], 'title': 'The whole film', 'reason': 'one continuous idea'}]
    (ws / 'out' / 'scenes.json').write_text(json.dumps(scenes), encoding='utf-8')
    rc, out, err = vw(home, 'planning', 'scenes', '--file', 'out/scenes.json', '--quote', 'yes these scenes')
    assert rc == 0, err
    return json.loads((ws / 'work' / 'planning-package.json').read_text(encoding='utf-8'))


def make_plan(package, questions=None):
    ctx = package['context']
    sid = next(iter(ctx['sources']))
    src = ctx['sources'][sid]
    passage = ctx['passage_ids'][0]
    ref_key = next(k for k in ctx['evidence_registry'] if k.startswith(sid + '/visual_events/'))
    ref = {'source_id': sid, 'collection': 'visual_events', 'item_id': ref_key.rsplit('/', 1)[1]}
    frames = ctx['duration_frames']
    shot = {'id': 'S1', 'kind': 'video', 'source_id': sid, 'source_start_frame': 0, 'source_end_frame': frames, 'timeline_start_frame': 0, 'timeline_end_frame': frames,
            'crop_px': None, 'passage_ids': [passage], 'reason': 'The only clip shows the block being pressed.', 'uncertainty': '', 'visible_talking': 'absent', 'evidence_refs': [ref]}
    clause = ctx['script_passages'][passage].split('.')[0]
    decision = {'shot_id': 'S1', 'meaning_and_support': 'A block rests on the table while the narration explains pressing.', 'new_information': 'Shows the block itself.',
                'duration_reason': 'Covers the whole narration.', 'crop_tradeoff': 'No crop needed.', 'limitations': '',
                'role': 'b_roll', 'source_audio_role': 'neither', 'required_companion': '',
                'script_connections': [{'passage_id': passage, 'script_clause': clause, 'connection': 'The block in view is what the narration describes.', 'evidence_refs': [ref]}],
                'relevance': 'Directly shows the subject.', 'action_support': [], 'reuse': {'earlier_shot_ids': [], 'reason': ''}}
    notes = {'shot_decisions': [decision], 'combinations': [], 'story_check': {k: 'fine' for k in ('opening', 'progression', 'new_information', 'action_readability', 'pace_and_ending')},
             'important_omissions': [], 'factual_conflicts': []}
    return {'contract': 'direct-gemini-edit-v3', 'experiment_id': ctx['experiment_id'], 'fps': ctx['fps'], 'duration_frames': frames, 'shots': [shot], 'narration_pauses': [],
            'sequence_reason': 'A single clip covers the narration.', 'unresolved': [], 'decision_notes': notes, 'alternatives': [],
            'alternative_review': [{'passage_ids': [passage], 'title': 'The whole film', 'recommendation_reason': 'Only one clip exists.', 'status': 'no_relevant_footage',
                                    'reason': 'No other footage was supplied.', 'candidates': [], 'alternative_ids': []}],
            'gap_decisions': [], 'clarification_questions': questions or [], 'review_explanations': []}


def write_plan(ws, plan, name='out/plan.json'):
    (ws / name).write_text(json.dumps(plan), encoding='utf-8')


def assessment(package, plan, context_digest, ledger_digest):
    from app.planning.digest import digest
    comps = {k: {'status': 'uncertain', 'relied_on': False, 'reason': 'not relied on', 'evidence_refs': []} for k in
             ('object_identity', 'person_hand_association', 'contact_state', 'movement_sequence', 'timestamp_mapping', 'question_scope')}
    return {**{k: True for k in ('user_constraints_respected', 'illustration_not_proof', 'certainty_overstatements_flagged', 'question_context_checked', 'excerpt_claims_checked', 'reuse_checked', 'alternative_coverage_checked')},
            'plan_digest': digest(plan), 'context_digest': context_digest, 'ledger_digest': ledger_digest, 'assessment': 'The plan is honest about its one clip.',
            'remaining_limitations': ['Only one clip; no alternatives.'], 'unresolved_relied_on_claims': [],
            'component_reviews': [{'sequence_id': 'recommendation', 'shot_id': 'S1', 'components': comps}]}


def test_p7_p1_to_p5_p10_p13_happy_path_and_rejections(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    rc, out, err = vw(home, *PREPARE)
    assert rc == 0, err
    package = json.loads((ws / 'work' / 'planning-package.json').read_text(encoding='utf-8'))
    words = package['context']['mapped_words']
    # P7: scene groups out of order
    (ws / 'out' / 'scenes.json').write_text(json.dumps([{'first_word_id': words[-1]['id'], 'last_word_id': words[0]['id'], 'title': 't', 'reason': 'r'}]), encoding='utf-8')
    rc, out, _ = vw(home, 'planning', 'scenes', '--file', 'out/scenes.json', '--quote', 'yes')
    assert rc == 2 and 'contiguous' in out['message']
    (ws / 'out' / 'scenes.json').write_text(json.dumps([{'first_word_id': words[0]['id'], 'last_word_id': words[-1]['id'], 'title': 'The whole film', 'reason': 'one idea'}]), encoding='utf-8')
    assert vw(home, 'planning', 'scenes', '--file', 'out/scenes.json', '--quote', 'yes these scenes')[0] == 0
    package = json.loads((ws / 'work' / 'planning-package.json').read_text(encoding='utf-8'))
    assert package['context']['passage_ids'] == ['P001']
    good = make_plan(package)
    # P1 shots do not reach duration_frames
    bad = deepcopy(good); bad['shots'][0]['timeline_end_frame'] -= 5; bad['shots'][0]['source_end_frame'] -= 5
    write_plan(ws, bad)
    rc, out, _ = vw(home, 'planning', 'check', '--file', 'out/plan.json')
    assert out['status'] == 'rejected' and 'endpoint' in out['error']
    # P2 speed mismatch
    bad = deepcopy(good); bad['shots'][0]['source_end_frame'] -= 10
    write_plan(ws, bad)
    assert 'Natural speed' in vw(home, 'planning', 'check', '--file', 'out/plan.json')[1]['error']
    # P3 evidence of another clip / unknown
    bad = deepcopy(good); bad['shots'][0]['evidence_refs'] = [{'source_id': good['shots'][0]['source_id'], 'collection': 'visual_events', 'item_id': 'NOPE'}]
    bad['decision_notes']['shot_decisions'][0]['script_connections'][0]['evidence_refs'] = bad['shots'][0]['evidence_refs']
    write_plan(ws, bad)
    assert 'evidence' in vw(home, 'planning', 'check', '--file', 'out/plan.json')[1]['error'].lower()
    # P4 crop outside source
    bad = deepcopy(good); bad['shots'][0]['crop_px'] = {'x': 10, 'y': 10, 'width': 64, 'height': 64}
    write_plan(ws, bad)
    assert 'Crop' in vw(home, 'planning', 'check', '--file', 'out/plan.json')[1]['error']
    # P5 pause (one passage: a pause after it changes duration; wrong duration → rejected)
    bad = deepcopy(good); bad['narration_pauses'] = [{'after_passage_id': 'P001', 'additional_frames': 5, 'reason': 'breath'}]
    write_plan(ws, bad)
    assert 'duration' in vw(home, 'planning', 'check', '--file', 'out/plan.json')[1]['error'].lower()
    # happy draft
    write_plan(ws, good)
    rc, out, err = vw(home, 'planning', 'check', '--file', 'out/plan.json')
    assert rc == 0 and out['status'] == 'draft_technically_valid', (out, err)
    rc, out, err = vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')
    assert rc == 0 and out['version'] == 1, err
    st = vw(home, 'planning', 'status')[1]
    assert st['next'] == 'finalize' and st['pending'] == []
    # P10 finalize with a shot lacking component reviews
    review = assessment(package, good, st['context_digest'], None)
    from app.planning.digest import digest
    review['ledger_digest'] = digest({'observations': [], 'frame_results': []})
    bad_review = deepcopy(review); bad_review['component_reviews'] = []
    (ws / 'out' / 'assessment.json').write_text(json.dumps(bad_review), encoding='utf-8')
    rc, out, _ = vw(home, 'planning', 'finalize', '--file', 'out/assessment.json', '--quote', 'yes')
    assert rc == 2 and 'S1' in out['message']
    (ws / 'out' / 'assessment.json').write_text(json.dumps(review), encoding='utf-8')
    rc, out, err = vw(home, 'planning', 'finalize', '--file', 'out/assessment.json', '--quote', 'yes, finalize')
    assert rc == 0, err
    assert out['certificate']['gaps'] == [] and out['certificate']['duration_frames'] == package['context']['duration_frames']
    assert vw(home, 'next')[1]['stage'] == 'edit'
    # P13 handoff narration pieces are frame aligned
    with psycopg.connect(database) as c:
        pass
    import httpx
    tok = json.loads((home['home'] / 'session.json').read_text())['token']
    run_id = json.loads((ws / 'manifest.json').read_text())['run_id']
    h = httpx.get(f"{home['env']['VW2_SERVER_URL']}/api/runs/{run_id}/planning/handoff", headers={'Authorization': 'Bearer ' + tok}).json()
    assert h['contract'] == 'videowizard-compiled-edit-v2' and h['narration_pieces']
    for p in h['narration_pieces']:
        assert p['timeline_start_frame'] * 1 == round(p['timeline_start_s'] * 25) and p['timeline_end_frame'] == round(p['timeline_end_s'] * 25)
    # P11 revise after finalize → stage reopened, later stages stale
    rc, out, _ = vw(home, 'revise', '--stage', 'planning')
    assert rc == 0 and vw(home, 'next')[1]['stage'] == 'planning'


def test_p6_three_invalid_drafts_then_decision(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    package = prepared(home, ws)
    bad = make_plan(package); bad['shots'][0]['timeline_end_frame'] -= 5; bad['shots'][0]['source_end_frame'] -= 5
    write_plan(ws, bad)
    for _ in range(2):
        rc, out, _ = vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')
        assert rc == 2 and out['code'] == 'PLAN_REJECTED'
    rc, out, _ = vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')
    assert rc == 3 and out['code'] == 'NEEDS_USER_DECISION'


def test_p8_mechanical_answer(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    package = prepared(home, ws)
    sid = next(iter(package['context']['sources']))
    q = {'id': 'Q1', 'recipient': 'codex', 'sequence_id': 'recommendation', 'shot_id': 'S1', 'property': 'timestamp_mapping', 'question': 'What seconds are frames 0-25?',
         'why_needed': 'timing', 'what_answer_changes': 'nothing', 'inspect': []}
    write_plan(ws, make_plan(package, [q]))
    rc, out, err = vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')
    assert rc == 0, err
    rc, out, err = vw(home, 'planning', 'mechanical', '--question', 'Q1', '--check', json.dumps({'kind': 'source_range', 'source_id': sid, 'start_frame': 0, 'end_frame': 25}))
    assert rc == 0 and out['result']['duration_s'] == 1.0, err
    assert vw(home, 'planning', 'status')[1]['pending'] == []


def test_p9_paid_inspection_review_ledger_revise_finalize(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    package = prepared(home, ws)
    sid = next(iter(package['context']['sources']))
    q = {'id': 'Q1', 'recipient': 'flash', 'sequence_id': 'recommendation', 'shot_id': 'S1', 'property': 'movement_sequence', 'question': 'Does the block move?',
         'why_needed': 'motion', 'what_answer_changes': 'cut point', 'inspect': [{'source_id': sid, 'start_s': 0, 'end_s': 1.5}]}
    write_plan(ws, make_plan(package, [q]))
    assert vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')[0] == 0
    rc, out, err = vw(home, 'planning', 'inspect', '--question', 'Q1')
    assert rc == 0 and out['queued'] == ['Q1'], err
    drain()
    st = vw(home, 'planning', 'status')[1]
    assert st['jobs']['Q1']['status'] == 'retained' and st['jobs']['Q1']['cost']['input_tokens'] == 1200 and st['pending'] == []
    rc, out, _ = vw(home, 'planning', 'review-input')
    review = {'response_digest': out['response_digest'], 'fields': [{'path': f['path'], 'value_digest': f['value_digest'], 'scope': 'inside_target', 'reason': 'within the asked interval'} for f in out['fields']],
              'excluded_observation_ids': []}
    (ws / 'out' / 'answer-review.json').write_text(json.dumps(review), encoding='utf-8')
    assert vw(home, 'planning', 'review', '--file', 'out/answer-review.json')[0] == 0
    rc, out, err = vw(home, 'planning', 'ledger')
    assert rc == 0 and out['observations'] == 1, err
    ledger_digest = out['ledger_digest']
    write_plan(ws, make_plan(package))  # revision: questions resolved
    rc, out, err = vw(home, 'planning', 'revise', '--file', 'out/plan.json', '--quote', 'revised')
    assert rc == 0 and out['version'] == 2, err
    st = vw(home, 'planning', 'status')[1]
    review = assessment(package, make_plan(package), st['context_digest'], ledger_digest)
    (ws / 'out' / 'assessment.json').write_text(json.dumps(review), encoding='utf-8')
    rc, out, err = vw(home, 'planning', 'finalize', '--file', 'out/assessment.json', '--quote', 'yes')
    assert rc == 0, err
    assert vw(home, 'view', '--stage', 'planning')[1]['outputs'][0]['summary']['inspections'] == 1


def test_p12_timing_words_mismatch_refused(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    # corrupt the retained timing: swap a word
    import httpx
    from app.storage import storage
    run_id = json.loads((ws / 'manifest.json').read_text())['run_id']
    with psycopg.connect(database) as c:
        from psycopg.rows import dict_row
        c.row_factory = dict_row
        key = c.execute("select key from vw2_files where run_id=%s and name like '%%timing.json'", (run_id,)).fetchone()['key']
    st = storage()
    t = json.loads(st.get(key).decode('utf-8'))
    t['words'][0]['text'] = 'Mud'
    st.put(key, json.dumps(t).encode('utf-8'), 'application/json')
    rc, out, _ = vw(home, *PREPARE)
    assert rc == 2 and 'narration' in out['message'].lower()
