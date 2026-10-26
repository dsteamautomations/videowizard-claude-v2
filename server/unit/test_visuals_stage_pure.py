"""design/65: the treatment as a record and the gate on propose (B6), the cap (B7), the graphic sequence (B2'), the kinds of reference, the gates on still and
prepare-take, the gap output of a sequence. The store and the jobs table are faked; nothing touches a database or a provider."""
import json
from fractions import Fraction

import pytest

from app import visuals_stage as VS
from app.errors import Problem
from app.visual_contract import gap_digest


def g(fn):
    """The API wraps every stage call in guarded(): a ValueError from need() becomes a Problem."""
    return VS.guarded(fn)


def accepted(doc):
    return {gap['gap_id']: {'digest': gap_digest(doc, gap), 'quote': 'yes', 'by': 'u1'} for gap in doc['gaps']}


class FakeStore:
    def __init__(self, files=None):
        self.files = {k: (json.dumps(v).encode('utf-8') if not isinstance(v, bytes) else v) for k, v in (files or {}).items()}

    def get(self, key):
        if key not in self.files:
            raise Problem(404, 'FILE_MISSING', key)
        return self.files[key]

    def exists(self, key):
        return key in self.files

    def put(self, key, data, mime=None):
        self.files[key] = data
        return {'key': key}


class FakeConn:
    """vw2_jobs rows for the spend ledger; inserts are recorded."""

    def __init__(self, jobs=()):
        self.jobs, self.inserted, self.sql = list(jobs), [], []

    def execute(self, sql, params=()):
        conn = self
        self.sql.append((sql, params))

        class R:
            def fetchall(_):
                return [j for j in conn.jobs if j.get('run_id', 'run-1') == params[0]] if 'from vw2_jobs' in sql else []

            def fetchone(_):
                if 'insert into vw2_jobs' in sql:
                    conn.inserted.append(params)
                    return {'id': f'job-{len(conn.inserted)}'}
                return None
        return R()


RUN = {'id': 'run-1', 'code': 'VW-9'}
USER = {'id': 'u1', 'name': 'SK'}
GAPS = {'G1': {'start_frame': 0, 'end_frame': 500, 'passage_ids': ['P001'], 'requirement': 'the cavity'}, 'G2': {'start_frame': 900, 'end_frame': 1150, 'passage_ids': ['P002'], 'requirement': 'curing'}}
STATE = {'position': {'landmark_id': 'L1', 'relation': 'on it'}, 'facing': 'camera', 'pose': 'upright', 'holding': [], 'progress': 'whole'}


def shot(sid, a, b, vt, **extra):
    return {'id': sid, 'start_frame': a, 'end_frame': b, 'visual_type': vt, 'narration': '', 'purpose': 'show it', 'relation': 'illustration', 'framing': 'medium',
            'camera': 'static', 'focus': 'the wall', 'element_ids': ['E1'], 'information_progression': 'the section, then the cavities', **extra}


def plan_doc(g1_shots, g2_shots):
    scene = lambda sid, shots, lm: {'id': sid, 'purpose': 'p', 'location_time': 'yard, day', 'layout': 'wall centre', 'landmarks': [{'id': lm, 'description': 'the wall'}], 'boundary_continuity': 'none', 'shots': shots}
    return {'foundation': {'treatment': 'technical record with scenes of work', 'appearance': 'warm daylight'},
            'elements': [{'id': 'E1', 'name': 'Wall section', 'kind': 'graphic', 'identity': 'representative', 'requirements': 'a cut wall'}],
            'gaps': [{'gap_id': 'G1', 'intent': 'the cavity', 'treatment_fit': 'fits', 'scenes': [scene('SC1', g1_shots, 'L1')]},
                     {'gap_id': 'G2', 'intent': 'curing', 'treatment_fit': 'fits', 'scenes': [scene('SC2', g2_shots, 'L2')]}]}


def session(**over):
    base = {'contract': 'vw2-visuals-session-v1', 'source': {'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': GAPS},
            'versions': [], 'current': None, 'accepted': {}, 'choice_selections': {}, 'references': {}, 'bindings': {}, 'generator_choices': {}, 'preparations': {},
            'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}}
    return {**base, **over}


def store_with(sess, plan=None):
    files = {'run-1/visuals/session.json': sess}
    if plan is not None:
        files['run-1/visuals/plan-v1.json'] = {'document': plan}
    return FakeStore(files)


def saved(store):
    return json.loads(store.files['run-1/visuals/session.json'])


TREATMENT = {'gaps': [{'gap_id': 'G1', 'intended': ['Cutaway section revealing hollow cavities inside the wall.'], 'picture': 'the wall section builds: bricks on edge, then the cavities, then the air gap labelled',
                       'routes': ['graphic_sequence'], 'seconds': 20, 'images': 3},
                      {'gap_id': 'G2', 'intended': [], 'picture': 'water poured over a finished wall in the yard', 'routes': ['video'], 'seconds': 10, 'images': 1, 'departure': ''}]}


# ---------- the treatment is a record; propose waits for it (B6) ----------

def test_treatment_is_recorded_with_the_words_totals_and_estimate(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = store_with(session())
    out = VS.treatment(store, USER, RUN, [], TREATMENT, 'Yes, this treatment.')
    sess = saved(store)
    assert sess['treatment']['quote'] == 'Yes, this treatment.' and sess['treatment']['by'] == 'u1' and sess['treatment']['digest']
    assert out['totals'] == {'gaps': 2, 'images': 4, 'routes': {'graphic_sequence': 1, 'video': 1}, 'seconds': {'graphic_sequence': 20.0, 'video': 10.0}, 'frozen_seconds': 0.0}
    assert out['estimate_inr'] == 4 * 20.0 + 10 * 8.0 and sess['treatment']['estimate_inr'] == out['estimate_inr']


def test_the_treatment_totals_the_frozen_seconds_and_shows_the_share_of_the_film(monkeypatch):
    """design/89 B4: the expected frozen share before approval."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    store = store_with(session())
    first_cut = {'stage': 'first_cut', 'unit': None, 'summary': {'duration_frames': 2500}}   # a 100 s film
    doc = {'gaps': [{**TREATMENT['gaps'][0], 'frozen_seconds': 12}, TREATMENT['gaps'][1]]}
    out = VS.treatment(store, USER, RUN, [first_cut], doc, 'yes')
    assert out['totals']['frozen_seconds'] == 12 and out['totals']['frozen_share'] == 0.12 and out['totals']['frozen_limit'] == 0.1
    with pytest.raises(Problem, match='frozen_seconds'):
        g(lambda: VS.treatment(store, USER, RUN, [], {'gaps': [{**TREATMENT['gaps'][0], 'frozen_seconds': 99}, TREATMENT['gaps'][1]]}, 'yes'))


def test_treatment_refuses_a_missing_gap_an_unknown_route_or_no_words():
    store = store_with(session())
    with pytest.raises(Problem, match='covers every gap'):
        g(lambda: VS.treatment(store, USER, RUN, [], {'gaps': TREATMENT['gaps'][:1]}, 'yes'))
    bad = {'gaps': [{**TREATMENT['gaps'][0], 'routes': ['hand_made']}, TREATMENT['gaps'][1]]}
    with pytest.raises(Problem, match='route'):
        g(lambda: VS.treatment(store, USER, RUN, [], bad, 'yes'))
    assert VS.treatment(store, USER, RUN, [], TREATMENT, '  ')['draft'] is True   # no words: the draft the page shows, not a record
    with pytest.raises(Problem, match='unknown gap'):
        g(lambda: VS.treatment(store, USER, RUN, [], {'gaps': TREATMENT['gaps'] + [{**TREATMENT['gaps'][0], 'gap_id': 'G9'}]}, 'yes'))


def test_propose_is_refused_without_a_treatment_and_when_a_route_departs_from_it(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'section', 'hold_s': 7}, {'what_appears': 'cavities', 'hold_s': 7}, {'what_appears': 'label', 'hold_s': 6}])],
                   [shot('VS1', 900, 1150, 'video')])
    store = store_with(session())
    with pytest.raises(Problem, match='Record the treatment first'):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], doc))
    VS.treatment(store, USER, RUN, [], TREATMENT, 'yes')
    out = VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert out['version'] == 1 and out['routes']['graphic_sequence'] == 1 and out['routes']['video'] == 1
    departed = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])   # G1 planned as a still, the treatment said a sequence
    with pytest.raises(Problem, match="gap G1: the plan uses \\['still'\\] but the treatment says \\['graphic_sequence'\\]"):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], departed))
    # footage in the treatment allows a still in the plan (a frame shown as a still)
    VS.treatment(store, USER, RUN, [], {'gaps': [{**TREATMENT['gaps'][0], 'routes': ['footage']}, TREATMENT['gaps'][1]]}, 'yes again')
    assert VS.propose(FakeConn(), store, USER, RUN, [], departed)['version'] == 2


# ---------- the cap (B7) ----------

def job(provider, status='ready', **req):
    return {'id': f'j-{provider}-{len(req)}', 'unit': 'u', 'run_id': 'run-1', 'provider': provider, 'status': status, 'request': req, 'error': None, 'cost': None, 'result': None}


def test_spend_counts_images_and_take_seconds_at_the_configured_prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    conn = FakeConn([job('openai'), job('openai', 'running'), job('openai', 'failed'), job('video', duration_seconds=10), job('video', 'rejected', duration_seconds=10), job('gemini')])
    sp = VS.visuals_spend(conn, RUN)
    assert sp == {'images': 2, 'fixes': 0, 'take_seconds': 10.0, 'spent_inr': 120.0, 'prices': {'image_inr': 20.0, 'video_inr_per_s': 8.0}}


def test_spend_prices_an_image_from_its_tokens_and_a_job_without_tokens_at_the_flat_price(monkeypatch):
    """design/82 U2: the ledger from tokens at OpenAI's rates, in rupees."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9, 'usd_inr': 88.0})
    with_tokens = {**job('openai'), 'id': 'j-tok', 'cost': {'input_tokens': 2000, 'output_tokens': 1078}}
    conn = FakeConn([with_tokens, job('openai'), job('video', duration_seconds=6)])
    sp = VS.visuals_spend(conn, RUN)
    assert sp['images'] == 2 and sp['take_seconds'] == 6.0
    assert sp['spent_inr'] == round((2000 * 8 + 1078 * 30) / 1e6 * 88 + 4.0 + 6 * 8.9, 2) == 61.65
    assert VS.IMAGE_MODELS == {'generate': 'gpt-image-2.5-flare-2026-09-08', 'edit': 'gpt-image-2.5-sunburst-2026-09-08'}   # design/82 U4


def test_record_gap_registers_a_still_asset_file_so_the_record_finds_it(monkeypatch):
    """design/82 U1 (L48): a still set from a reference was never an upload; the record checks every storage file against the uploads table."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(current='pd1', versions=[{'plan_digest': 'pd1', 'file': {'key': 'run-1/visuals/plan-v1.json'}}], accepted={'G1': {'quote': 'yes', 'by': 'u1'}},
                   assets={'IM1': {'kind': 'still', 'key': 'run-1/visuals/references/R1.png', 'sha256': 'abc', 'bytes': 5, 'reference_id': 'R1', 'placement': {'start_frame': 0, 'end_frame': 500}}})
    store = store_with(sess, plan=doc)
    recorded = []
    monkeypatch.setattr(VS.core, 'output', lambda conn, user, run, body: (recorded.append(body) or {'id': 'o1'}))
    conn = FakeConn()
    out = VS.record_gap(conn, store, USER, RUN, [], 'G1', 'record it')
    assert out == {'gap_id': 'G1', 'output': 'o1', 'shots': 1}
    assert any('insert into vw2_files' in s and p[0] == 'run-1/visuals/references/R1.png' and p[3] == 'IM1-asset.png' for s, p in conn.sql)
    assert recorded[0]['files'][0]['name'] == 'IM1-asset.png' and recorded[0]['summary']['shots'][0]['source'] == 'asset'


def test_the_cap_refuses_a_paid_call_that_would_pass_it_and_a_session_cap_is_kept(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    conn = FakeConn([job('openai') for _ in range(49)])   # ₹980 spent
    assert VS.cap_of(session()) == 5000.0   # design/66 C4: the default cap
    sess = session(cap_inr=1000.0)
    VS.check_cap(conn, RUN, sess, 20.0, 'one image')       # exactly the cap: allowed
    with pytest.raises(Problem) as exc:
        VS.check_cap(conn, RUN, sess, 40.0, 'a 5 s take')
    assert exc.value.code == 'VISUALS_CAP' and '₹980' in exc.value.message and '₹1,000' in exc.value.message and 'about ₹40' in exc.value.message
    assert exc.value.extra == {'spent_inr': 980.0, 'cap_inr': 1000.0, 'estimate_inr': 40.0}
    VS.check_cap(conn, RUN, session(cap_inr=1500.0), 40.0, 'a 5 s take')   # design/74 L26: a film whose session holds a cap keeps it; no front end changes it


def test_budget_reports_spend_cap_and_what_the_plan_still_needs(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 10}, {'what_appears': 'b', 'hold_s': 10}])], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1')
    b = VS.budget(FakeConn([job('openai')]), store_with(sess, doc), RUN, [])
    assert b['spent_inr'] == 20.0 and b['cap_inr'] == 5000.0 and b['planned'] == {'images': 4, 'video_seconds': 10.0, 'inr': 4 * 20.0 + 10 * 8.0}   # two states, a start and an end image
    assert b['left_inr'] == 4980.0


def test_generate_image_and_submit_take_check_the_cap_first(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', cap_inr=30.0, accepted=accepted(doc))
    store = store_with(sess, doc)
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'shot_id': 'IM1', 'subject': 'the wall', 'prompt': 'a wall section'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)          # ₹0 + ₹20 ≤ ₹30
    assert out['op'] == 'generate'
    with pytest.raises(Problem) as exc:
        VS.generate_image(FakeConn([job('openai')]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2'})   # ₹20 + ₹20 > ₹30
    assert exc.value.code == 'VISUALS_CAP'
    with pytest.raises(Problem, match='A state is generated from the previous state'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r3', 'kind': 'state'}))


# ---------- the graphic sequence (B2') and the gates (B3) ----------

def ref(rid, status='candidate', parents=()):
    return {'id': rid, 'name': rid, 'kind': 'state' if parents else 'keyframe', 'element_id': 'E1', 'status': status, 'key': f'run-1/visuals/references/{rid}.png', 'sha256': 'sha-' + rid, 'bytes': 100, 'subject': 'the wall',
            'generation': {'op': 'edit' if parents else 'generate', 'parents': [{'id': p} for p in parents]}}


def test_a_sequence_approves_its_states_in_one_call_and_holds_them_for_the_shot():
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'section', 'hold_s': 7}, {'what_appears': 'cavities', 'hold_s': 7}, {'what_appears': 'label', 'hold_s': 6}])],
                   [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', parents=['R1']), 'R3': ref('R3', parents=['R2'])})
    store = store_with(sess, doc)
    out = VS.sequence(store, USER, RUN, [], 'AN1', ['R1', 'R2', 'R3'], 'Yes, these three states.')
    s = saved(store)
    assert all(s['references'][r]['status'] == 'approved' for r in ('R1', 'R2', 'R3')) and s['references']['R2']['approval']['quote'] == 'Yes, these three states.'
    asset = s['assets']['AN1']
    assert asset['kind'] == 'sequence' and [st['hold_frames'] for st in asset['states']] == [175, 175, 150] and sum(st['hold_frames'] for st in asset['states']) == 500
    assert asset['dissolve_frames'] == 12 and asset['motion'] == 'none' and asset['states'][1]['sha256'] == 'sha-R2' and asset['placement'] == {'start_frame': 0, 'end_frame': 500}
    assert [w for w in out['warnings'] if 'no shot recorded' not in w] == [] and out['states'] == 3


def test_a_sequence_warns_when_a_state_was_not_made_from_the_previous_one_and_refuses_the_wrong_count_or_shot():
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 10}, {'what_appears': 'b', 'hold_s': 10}])], [shot('DG1', 900, 1150, 'diagram')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1'), 'R2': ref('R2'), 'R3': ref('R3', parents=['R1'])})
    out = VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['R1', 'R2'], 'yes')
    assert out['warnings'][1:] == ['state 2 (R2) was not generated from state 1 (R1); check the drawing is the same'] and 'no shot recorded' in out['warnings'][0]
    with pytest.raises(Problem, match='plans 2 states; 3 references'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['R1', 'R2', 'R3'], 'yes'))
    with pytest.raises(Problem, match='diagram shot: it takes a still'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'DG1', ['R1'], 'yes'))
    with pytest.raises(Problem, match='not a candidate or approved reference'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['R1', 'R9'], 'yes'))


def test_still_and_prepare_take_gates_follow_the_routes():
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 10}, {'what_appears': 'b', 'hold_s': 10}])], [shot('DG1', 900, 1150, 'diagram')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), references={'R1': ref('R1', 'approved')})
    with pytest.raises(Problem, match='animation shot: it takes a graphic sequence'):
        g(lambda: VS.still_from_reference(store_with(sess, doc), USER, RUN, [], 'AN1', 'R1', 'yes'))
    out = VS.still_from_reference(store_with(sess, doc), USER, RUN, [], 'DG1', 'R1', 'yes')
    assert out['kind'] == 'still'
    with pytest.raises(Problem, match='takes a graphic sequence'):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {'shot_id': 'AN1', 'motion_prompt': 'm', 'subject_reconciliation': {}, 'start_image': 'R1'}))
    with pytest.raises(Problem, match='takes a still'):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {'shot_id': 'DG1', 'motion_prompt': 'm', 'subject_reconciliation': {}, 'start_image': 'R1'}))


def test_prepare_take_needs_a_start_and_a_distinct_end_image_and_freezes_both():
    """design/66 C2: every take is driven by two approved pictures; consecutive segments share their boundary picture."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])   # subjects as validation would default them
    plan, gap = doc, doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved'), 'R3': ref('R3')},
                   bindings={'VS1': {'gap_digest': gap_digest(plan, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    body = {'shot_id': 'VS1', 'motion_prompt': 'water poured along the top', 'subject_reconciliation': {}, 'start_image': 'R1', 'continuity_notes': 'the wall and the yard light stay'}
    with pytest.raises(Problem, match='Continuity notes are required'):   # design/84 V2
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**body, 'end_image': 'R2', 'continuity_notes': ' '}))
    with pytest.raises(Problem, match='start and an end image') as exc:
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], body))
    assert '--kind keyframe --parents <start>' in exc.value.message and '--start R --end R2' in exc.value.message
    with pytest.raises(Problem, match='distinct'):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**body, 'end_image': 'R1'}))
    with pytest.raises(Problem, match='end_image must be an approved reference'):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**body, 'end_image': 'R3'}))
    store = store_with(sess, doc)
    out = VS.prepare_take(store, USER, RUN, [], {**body, 'end_image': 'R2'})
    assert out['duration_seconds'] == 10 and out['exact_seconds'] == 10.0
    record = json.loads(store.files[saved(store)['preparations']['VS1']['key']])
    assert record['start_image']['reference_id'] == 'R1' and record['end_image']['reference_id'] == 'R2' and '<LAST_FRAME>@Image2' in record['effective_prompt'] and 'one continuous shot' in record['effective_prompt'] and 'Continuity: the wall and the yard light stay' in record['effective_prompt']


def test_a_keyframe_may_be_generated_from_a_candidate_keyframe(monkeypatch):
    """design/66 C3: the end keyframe is made from the start keyframe before either is approved, so the pair is approved together."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'K1': ref('K1'), 'S1': {**ref('S1'), 'kind': 'sheet'}, 'A1': ref('A1', 'approved')})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'Image 1 is the start; the same yard, the bucket now empty', 'parents': ['K1']}
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert out['op'] == 'edit' and saved(store)['references'][out['reference_id']]['generation']['parents'] == [{'id': 'K1', 'key': 'run-1/visuals/references/K1.png', 'sha256': 'sha-K1'}]
    with pytest.raises(Problem, match='Parents must be approved'):   # a candidate sheet is not a start keyframe
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2', 'parents': ['S1']}))
    with pytest.raises(Problem, match='Parents must be approved'):   # only a keyframe is made from a candidate
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r3', 'kind': 'isolated', 'parents': ['K1']}))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r4', 'kind': 'isolated', 'parents': ['A1']})
    assert out['op'] == 'edit'


def test_the_packet_carries_the_start_end_and_motion_instructions():
    """design/67 A-C: the start is composed for the whole segment with the end in mind; the end names positions and changes nothing else."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    prep = VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']
    start, end, motion = prep['start_image_instruction'], prep['end_image_instruction'], prep['video_instruction']
    assert prep['image_instruction'] == start   # the old name still answers for one release
    assert 'Write the start prompt and the end prompt together before generating either' in start and 'room in the frame for the move' in start and 'what the motion heads for already in frame' in start
    assert 'from the approved start image as its parent' in end and "the server sends the start's own references with it" in end
    assert 'its position against its landmark and its side of the frame, its facing' in end and 'Change nothing else' in end and 'result of its last beat' in end
    assert motion.startswith('Read the actual accepted starting image')
    lib = prep['library']   # design/68 L3
    assert lib['version'] == VS.library.latest() and [s['step'] for s in lib['steps']] == ['start', 'end', 'take'] and lib['steps'][2]['task'] == 'clip-from-frame'
    assert 'library/video/models/gemini-omni-1-1/FACT-SHEET.md' in lib['steps'][2]['files'] and all(isinstance(p, str) for s in lib['steps'] for p in s['files'])
    assert lib['job_forms']['take']['video_seconds'] == 10 and lib['job_forms']['take']['job_id'] == 'VW-9-VS1-1' and lib['job_forms']['start']['task'] == 'keyframe'
    assert lib['job_forms']['start']['images'] == [{'id': 'R1', 'tag': 'approved', 'element_id': 'E1', 'keep': 'a cut wall'}]
    from app.planning.digest import digest
    full = VS.packet(store_with(sess, doc), RUN, [], 'VS1')
    assert full['preparation_digest'] == digest({k: v for k, v in full['preparation'].items() if k not in ('library', 'context', 'footage_character')})   # design/88: context and footage never make a take stale   # the card and the rules never make a take stale
    with_card = VS.packet(store_with(sess, doc), RUN, [], 'VS1', card={'industry': 'education'}, rules=['no PPE claims'])
    assert with_card['preparation_digest'] == full['preparation_digest'] and with_card['preparation']['library']['job_forms']['take']['industry'] == 'education'


def test_the_packet_carries_end_targets_context_and_exact_patterns():
    """design/86 K6, K7, K8."""
    sub = {'element_id': 'E1', 'role': 'primary', 'screen_position': 'centre', 'behaviour': 'acts', 'beats': [],
           'start': {'position': {'landmark_id': 'L2', 'relation': 'beside'}, 'facing': 'camera', 'pose': 'standing', 'holding': ['O_BRICK'], 'progress': 'one course laid'},
           'end': {'position': {'landmark_id': 'L2', 'relation': 'at the far end of'}, 'facing': 'away', 'pose': 'bending to the course', 'holding': [], 'progress': 'two courses laid'}}
    first = shot('VS0', 900, 1000, 'video', narration='Every wall begins with a course.', subjects=[{**sub, 'end': {**sub['end'], 'progress': 'the first brick set'}}])
    second = shot('VS1', 1000, 1150, 'video', narration='Then the next course goes on.', subjects=[sub])
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [first, second])
    doc['elements'].append({'id': 'O_BOND', 'name': 'Rat-trap bond', 'kind': 'object', 'identity': 'exact', 'requirements': 'bricks on edge, two leaves, a cavity'})
    second['element_ids'] = ['E1', 'O_BOND']
    gap = doc['gaps'][1]
    rejected = {**ref('X1'), 'status': 'rejected', 'rejection': {'notes': 'the helper too large against the house'}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'F9': {**ref('F9', 'approved'), 'kind': 'frame', 'element_id': 'O_BOND'}, 'X1': rejected},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}], 'O_BOND': [{'id': 'F9', 'sha256': 'sha-F9'}]}}},
                   treatment={'gaps': [{'gap_id': 'G2', 'picture': 'water poured over a finished wall', 'routes': ['video'], 'intended': ['curing shown']}], 'quote': 'yes', 'by': 'u1', 'at': 't', 'digest': 'x', 'totals': {}, 'estimate_inr': 0},
                   intended_visuals=[{'heading': 'Curing', 'narration_starts': 'Then the next course', 'lines': ['the wall wetted']}, {'heading': 'Elsewhere', 'narration_starts': 'A kiln', 'lines': []}])
    prep = VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']
    assert prep['end_targets'] == ['E1 ends at the far end of the wall, facing away, bending to the course, holding nothing; two courses laid.']
    assert 'Carry each line of end_targets word for word' in prep['end_image_instruction']
    ctx = prep['context']
    assert ctx['gap_words'] == 'Every wall begins with a course. Then the next course goes on.' and ctx['treatment_picture']['picture'] == 'water poured over a finished wall'
    assert [iv['heading'] for iv in ctx['intended_visuals']] == ['Curing']
    assert ctx['neighbours']['previous']['shot_id'] == 'VS0' and ctx['neighbours']['previous']['ends'][0]['progress'] == 'the first brick set' and ctx['neighbours']['next'] is None
    assert ctx['earlier_rejections'] == [{'reference_id': 'X1', 'element_id': 'E1', 'name': 'X1', 'kind': 'keyframe', 'notes': 'the helper too large against the house'}]
    assert prep['exact_patterns'][0]['element_id'] == 'O_BOND' and prep['exact_patterns'][0]['pattern_references'] == ['F9'] and 'medium and close shots' in prep['exact_patterns'][0]['rule']


def test_two_candidates_queue_jobs_with_valid_request_ids(monkeypatch):
    """Defect 27: vw2_jobs.request_id is a uuid column; the two candidates sent '<uuid>-a' and '<uuid>-b', and Postgres refused both."""
    import uuid as _uuid
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': {**ref('R1', 'approved'), 'kind': 'sheet'}}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}, 'packet_read_at': 't'}})
    rid = 'a6638116-0fe9-4305-9ea3-db7263d79c01'
    body = {'request_id': rid, 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'the wall, bucket full', 'parents': ['R1'], 'variants': 2}
    conn = FakeConn([])
    out = VS.generate_image(conn, store_with(sess, doc), USER, RUN, [], body)
    ids = [params[3] for params in conn.inserted]
    assert len(ids) == 2 and len(set(ids)) == 2 and rid not in ids
    assert all(str(_uuid.UUID(i)) == i for i in ids)   # each one a uuid Postgres accepts
    again = FakeConn([])   # the same request gives the same ids, so a retried call finds the same rows
    out2 = VS.generate_image(again, store_with(sess, doc), USER, RUN, [], body)
    assert [params[3] for params in again.inserted] == ids and out2['reference_ids'] == out['reference_ids']
    one = FakeConn([])   # one variant keeps the request id as sent
    VS.generate_image(one, store_with(sess, doc), USER, RUN, [], {**body, 'variants': 1})
    assert [params[3] for params in one.inserted] == [rid]


def test_two_candidates_for_a_start_and_the_end_written_with_it_is_queued_on_approval(monkeypatch):
    """design/86 K4, K1."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': {**ref('R1', 'approved'), 'kind': 'sheet'}}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}, 'packet_read_at': 't'}})
    end_answer = {'status': 'ready', 'prompt': 'Image 1 is the start; the bucket now empty.', 'checklist': [{'check': 'bucket', 'pass_when': 'empty', 'weight': 'must'}], 'exact_text': []}
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'keyframe-start-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'the wall, bucket full', 'parents': ['R1'],
            'variants': 2, 'end_prompt': end_answer['prompt'], 'end_answer': end_answer}
    conn, store = FakeConn([]), store_with(sess, doc)
    out = VS.generate_image(conn, store, USER, RUN, [], body)
    assert len(conn.inserted) == 2 and len(out['reference_ids']) == 2 and out['reference_id'] == out['reference_ids'][0]
    refs = saved(store)['references']
    a, b = (refs[i] for i in out['reference_ids'])
    assert a['name'] == 'keyframe-start-VS1-a' and b['name'] == 'keyframe-start-VS1-b' and a['pending_end']['prompt'] == end_answer['prompt'] and a['generation']['prompt'] == b['generation']['prompt']
    with pytest.raises(Problem, match='names Image 1'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2', 'end_prompt': 'the bucket empty'}))
    with pytest.raises(Problem, match='start keyframe only'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r3', 'kind': 'sheet', 'end_prompt': None, 'end_answer': None}))
    # the start retained and approved: the end is queued from it with the pre-written prompt, once
    s2 = saved(store)
    s2['references'][a['id']].update(status='candidate', sha256='a' * 64, width=1536, height=864, key=f"run-1/visuals/references/{a['id']}.png", bytes=9)
    store = store_with(s2, doc)
    conn = FakeConn([])
    row = VS.approve_reference(store, USER, RUN, [], a['id'], 'a' * 64, 'Yes, this one.', conn)
    assert row['status'] == 'approved' and row['end_reference_id'] and len(conn.inserted) == 1
    s3 = saved(store)
    end = s3['references'][row['end_reference_id']]
    assert end['kind'] == 'keyframe' and end['name'] == 'keyframe-end-VS1-a' and [p['id'] for p in end['generation']['parents']] == [a['id'], 'R1'] and end['answer'] == end_answer
    assert s3['references'][a['id']]['end_queued'] == end['id']
    conn = FakeConn([])
    VS.approve_reference(store, USER, RUN, [], a['id'], 'a' * 64, 'Yes, again.', conn)   # approving again queues nothing more
    assert conn.inserted == []
    assert VS.approve_reference(store, USER, RUN, [], a['id'], 'a' * 64, 'Yes.')['status'] == 'approved'   # without a connection (chat path today): approval only


def test_an_approved_picture_keeps_its_fingerprint_and_the_check_reads_it_not_the_store():
    """Finding 9."""
    from io import BytesIO
    PIL = pytest.importorskip('PIL.Image')
    from PIL import ImageDraw
    img = PIL.new('RGB', (160, 90), (90, 120, 60))
    ImageDraw.Draw(img).rectangle((20, 10, 100, 70), fill=(200, 30, 30))
    buf = BytesIO()
    img.save(buf, format='PNG')
    sess = session(references={'R1': {**ref('R1'), 'sha256': 'a' * 64}, 'R2': {**ref('R2'), 'sha256': 'b' * 64}})
    store = store_with(sess)
    store.files['run-1/visuals/references/R1.png'] = buf.getvalue()
    store.files['run-1/visuals/references/R2.png'] = buf.getvalue()
    VS.approve_reference(store, USER, RUN, [], 'R1', 'a' * 64, 'yes')
    VS.approve_reference(store, USER, RUN, [], 'R2', 'b' * 64, 'yes')
    s = saved(store)
    assert isinstance(s['references']['R1']['dhash']['picture'], int)
    s['assets'] = {'IM1': {'kind': 'still', 'reference_id': 'R1', 'key': 'gone/1.png', 'placement': {'start_frame': 0, 'end_frame': 100}},
                   'IM2': {'kind': 'still', 'reference_id': 'R2', 'key': 'gone/2.png', 'placement': {'start_frame': 3000, 'end_frame': 3100}}}
    assert [(p['a'], p['b']) for p in VS.look_alike_placed(store_with(s), s)] == [('IM1', 'IM2')]   # the files are not read: their keys lead nowhere


def test_the_feedback_file_opens_with_the_rounds_summary():
    """design/86 K9."""
    records = [{'kind': 'image', 'verdict': 'pass'}, {'kind': 'image', 'verdict': 'reject'}, {'kind': 'image', 'verdict': 'pass'}, {'kind': 'take', 'verdict': 'pass'}, {'kind': 'image', 'verdict': 'pass'}]
    assert VS.rounds_summary(records) == {'image': {'approved': 3, 'rejected': 1, 'rounds_per_approved': 1.33}, 'take': {'approved': 1, 'rejected': 0, 'rounds_per_approved': 1.0}}
    assert VS.rounds_summary([{'kind': 'image', 'verdict': 'reject'}]) == {'image': {'approved': 0, 'rejected': 1, 'rounds_per_approved': None}}
    sess = session(feedback=[{'app': 'videowizard', 'kind': 'image', 'verdict': 'pass', 'id': 'x', 'checklist': []}])
    out = VS.feedback(store_with(sess), RUN, [])
    assert out['yaml'].startswith('# image: approved 1, rejected 0, rounds per approved 1.0\n- app: videowizard') and out['summary']['image']['approved'] == 1


def test_prepare_measures_the_footage_tells_it_and_the_neighbours_reach_the_packet(monkeypatch):
    """design/88 F2, F3, F4, F6."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    store = store_with(sess, doc)
    store.files['run-1/master-v1.json'] = json.dumps({'events': [{'kind': 'event', 'sub_clip_id': 'c1:SUB_01'}, {'kind': 'gap', 'gap_id': 'G2'}, {'kind': 'event', 'sub_clip_id': 'c2:SUB_03'}]}).encode()
    store.files['run-1/ev-c1.json'] = json.dumps({'contract_version': 'clip-log-v1', 'log': {'contrast_profile': 'Standard_Normal', 'sub_clips': [{'camera_and_optics': {'movement_type': 'Handheld'}}]}}).encode()
    store.files['run-1/ev-c2.json'] = json.dumps({'contract_version': 'clip-log-v1', 'log': {'contrast_profile': 'Standard_Normal', 'sub_clips': [{'camera_and_optics': {'movement_type': 'Gimbal'}}]}}).encode()
    media = {'stage': 'media', 'unit': None, 'files': [], 'summary': {'clips': [{'id': 'c1', 'name': 'C0012.MP4', 'color_transfer': 'bt709'}, {'id': 'c2', 'name': 'DJI_0071.MP4', 'color_transfer': 'bt709'}]}}
    outputs = [media, {'stage': 'master', 'unit': None, 'files': [{'name': 'master-v1.json', 'key': 'run-1/master-v1.json'}], 'summary': {}},
               {'stage': 'analysis', 'unit': 'c1', 'summary': {}, 'files': [{'name': 'c1.evidence.json', 'key': 'run-1/ev-c1.json'}]},
               {'stage': 'analysis', 'unit': 'c2', 'summary': {}, 'files': [{'name': 'c2.evidence.json', 'key': 'run-1/ev-c2.json'}]}]
    monkeypatch.setattr(VS, 'gaps_source', lambda store, outputs: sess['source'])
    monkeypatch.setattr(VS.core, 'stage_table', lambda v: [{'name': 'visuals', 'prompt': '', 'steps': []}])
    monkeypatch.setattr(VS.core, 'effective_rules', lambda conn, run, outputs: [])
    out = VS.prepare(FakeConn([]), store, USER, {**RUN, 'procedure_version': '2'}, outputs)
    assert out['footage'] == 'Your footage: mixed cameras (1 not known, 1 drone), mixed support (1 handheld, 1 gimbal), natural look (measured from the clips)'
    s = saved(store)
    assert s['gap_neighbours'] == {'G2': {'before': 'c1', 'after': 'c2'}} and s['footage']['per_clip']['c2']['camera'] == 'drone'
    nb = VS.packet(store, RUN, outputs, 'VS1')['preparation']['context']['footage_neighbours']
    assert nb['before']['clip_id'] == 'c1' and nb['before']['camera'] == 'unknown' and nb['before']['support'] == 'handheld' and nb['after']['support'] == 'gimbal'
    # the correction wins on both front ends (the API and the page call the same function); it never makes a prepared take stale
    before = VS.packet(store, RUN, outputs, 'VS1')['preparation_digest']
    with pytest.raises(Problem, match="operator's words"):
        g(lambda: VS.correct_footage(store, USER, RUN, outputs, {'camera': 'cinema'}, ''))
    with pytest.raises(Problem, match='camera is one of'):
        g(lambda: VS.correct_footage(store, USER, RUN, outputs, {'camera': 'film'}, 'yes'))
    view = VS.correct_footage(store, USER, RUN, outputs, {'camera': 'cinema', 'support': 'handheld'}, 'professional camera, handheld, natural')
    assert view['line'] == 'Your footage: cinema camera, handheld, natural look (your correction)' and view['measured']['camera'] == 'mixed'
    assert VS.packet(store, RUN, outputs, 'VS1')['preparation_digest'] == before and VS.status(FakeConn([]), store, RUN, outputs)['footage']['line'] == view['line']
    # F6: an answer recorded at the media step before design/88 stands as the correction at the next prepare
    old = {**media, 'summary': {**media['summary'], 'footage_character': {'camera': 'mirrorless', 'support': 'handheld', 'look': 'natural', 'quote': 'Sony, handheld'}}}
    s2 = saved(store); s2.pop('footage_correction')
    store2 = store_with(s2, doc); store2.files.update({k: v for k, v in store.files.items() if k not in store2.files})
    out = VS.prepare(FakeConn([]), store2, USER, {**RUN, 'procedure_version': '2'}, [old] + outputs[1:])
    assert out['footage'] == 'Your footage: mirrorless camera, handheld, natural look (your correction)' and saved(store2)['footage_correction']['from'] == 'the media step'


def test_each_gap_carries_its_narration_timed_and_the_packet_its_sentences():
    """design/89 A1: from the options package, in film time; a gap of three sentences gives three, with the sentence before and after."""
    w = lambda i, text, a, b: {'id': f'w{i}', 'text': text, 'start_frame': a, 'end_frame': b, 'sentence_end': text.endswith('.')}
    words = [w(0, 'Before.', 850, 890), w(1, 'Bricks', 900, 910), w(2, 'on', 912, 918), w(3, 'edge.', 920, 940), w(4, 'A', 960, 965), w(5, 'cavity.', 967, 1000),
             w(6, 'Heat', 1020, 1040), w(7, 'stays.', 1042, 1080), w(8, 'After.', 1160, 1190)]
    s = lambda text, a, b: {'text': text, 'start_frame': a, 'end_frame': b}
    sents = [s('Before.', 850, 890), s('Bricks on edge.', 900, 940), s('A cavity.', 960, 1000), s('Heat stays.', 1020, 1080), s('After.', 1160, 1190)]
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    store = store_with(sess, doc)
    store.files['run-1/stage2/session.json'] = json.dumps({'package': {'key': 'run-1/stage2/package.json'}}).encode()
    store.files['run-1/stage2/package.json'] = json.dumps({'narration': {'words': words, 'sentences': sents}}).encode()
    timing = VS.gap_timing(store, RUN, GAPS, '25')['G2']
    assert [x['text'] for x in timing['sentences']] == ['Bricks on edge.', 'A cavity.', 'Heat stays.'] and timing['before'] == 'Before.' and timing['after'] == 'After.'
    assert timing['sentences'][0] == {'text': 'Bricks on edge.', 'start_s': 0.0, 'end_s': 1.6, 'film_start_s': 36.0, 'film_end_s': 37.6, 'whole': True}
    assert len(timing['words']) == 7 and timing['words'][0] == {'text': 'Bricks', 'start_frame': 900, 'end_frame': 910}
    assert VS.gap_timing(FakeStore({}), RUN, GAPS, '25') == {}   # a run without an options package: none, never a crash
    sess2 = saved(store)
    sess2['source']['gaps']['G2']['timing'] = timing
    ctx = VS.packet(store_with(sess2, doc), RUN, [], 'VS1')['preparation']['context']
    assert [x['text'] for x in ctx['timing']['sentences']] == ['Bricks on edge.', 'A cavity.', 'Heat stays.'] and ctx['timing']['before'] == 'Before.' and 'words' not in ctx['timing']
    assert VS.film_frames([{'stage': 'first_cut', 'unit': None, 'summary': {'duration_frames': 8000}}]) == 8000 and VS.film_frames([]) is None


def test_a_packet_before_bind_is_a_refusal_with_the_message_not_a_crash():
    """defect 19 (VW-6, 21 Oct): the route returned a bare 500 because the packet call ran outside the guard; the message existed all along."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc))
    with pytest.raises(Problem) as exc:
        g(lambda: VS.packet(store_with(sess, doc), RUN, [], 'VS1'))
    assert exc.value.status == 422 and 'Bind references for this shot' in exc.value.message


def test_library_version_is_recorded_at_prepare_and_an_older_session_reads_the_latest():
    assert VS.library_version_of(session()) == VS.library.latest()
    assert VS.library_version_of(session(library_version='vwlib-2026-01-01-aaaaaaaaaaaa')) == 'vwlib-2026-01-01-aaaaaaaaaaaa'
    pack = VS.library_pack(store_with(session()), RUN, [])
    assert pack['version'] == VS.library.latest() and 'start' in pack['steps']


def test_an_answer_is_linted_and_stored_with_the_image_and_the_take(monkeypatch):
    """design/68 L5: the answer form travels with the prompt; without it the call works as today."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}, 'packet_read_at': 't'}})
    answer = {'status': 'ready', 'prompt': 'a wall section', 'checklist': [{'check': 'c', 'pass_when': 'p', 'weight': 'must'}], 'exact_text': []}
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'a wall section', 'answer': answer}
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert saved(store)['references'][out['reference_id']]['answer'] == answer
    with pytest.raises(Problem, match='prompt differs'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2', 'prompt': 'another wall'}))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r3', 'answer': None})   # as today
    assert out['op'] == 'generate'
    take = {'shot_id': 'VS1', 'motion_prompt': 'water poured', 'subject_reconciliation': {}, 'continuity_notes': 'the wall stays', 'start_image': 'R1', 'end_image': 'R2'}
    store = store_with(sess, doc)
    VS.prepare_take(store, USER, RUN, [], {**take, 'answer': {**answer, 'prompt': 'water poured'}})
    record = json.loads(store.files[saved(store)['preparations']['VS1']['key']])
    assert record['answer']['prompt'] == 'water poured' and record['motion_prompt'] == 'water poured'
    with pytest.raises(Problem, match='at least one must line'):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**take, 'answer': {**answer, 'prompt': 'water poured', 'checklist': []}}))
    out = VS.prepare_take(store_with(sess, doc), USER, RUN, [], take)   # as today
    assert out['duration_seconds'] == 10


def test_an_end_keyframe_carries_the_start_keyframes_own_references(monkeypatch):
    """design/67 D: the child names only the start; the server sends the start's sheets behind it, in order, without repeating one the child named."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sheets = {'S1': {**ref('S1', 'approved'), 'kind': 'sheet'}, 'S2': {**ref('S2', 'approved'), 'kind': 'sheet'}}
    start = {**ref('K1'), 'generation': {'op': 'edit', 'parents': [{'id': 'S1', 'key': sheets['S1']['key'], 'sha256': 'sha-S1'}, {'id': 'S2', 'key': sheets['S2']['key'], 'sha256': 'sha-S2'}]}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), references={**sheets, 'K1': start})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'Image 1 is the start; the bucket now empty', 'parents': ['K1']}
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert [p['id'] for p in saved(store)['references'][out['reference_id']]['generation']['parents']] == ['K1', 'S1', 'S2']
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'r2', 'parents': ['K1', 'S2']})   # a sheet named by the child is not repeated
    assert [p['id'] for p in saved(store)['references'][out['reference_id']]['generation']['parents']] == ['K1', 'S2', 'S1']
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'r3', 'kind': 'isolated', 'parents': ['S1']})   # not a keyframe: as today
    assert [p['id'] for p in saved(store)['references'][out['reference_id']]['generation']['parents']] == ['S1']


def test_status_carries_the_treatment_and_the_budget(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = store_with(session())
    VS.treatment(store, USER, RUN, [], TREATMENT, 'yes')
    st = VS.status(FakeConn([job('openai')]), store, RUN, [])
    assert st['treatment']['totals']['images'] == 4 and st['treatment']['quote'] == 'yes' and st['budget']['spent_inr'] == 20.0 and st['budget']['cap_inr'] == 5000.0


# ---------- design/65 §8: the draft and the page view ----------

def test_a_treatment_without_words_is_the_draft_and_the_page_records_it(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = store_with(session())
    out = VS.treatment(store, USER, RUN, [], TREATMENT, '')
    assert out['draft'] is True and saved(store)['treatment_draft']['totals']['images'] == 4 and 'treatment' not in saved(store)
    with pytest.raises(Problem, match='Record the treatment first'):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])))
    out = VS.treatment(store, USER, RUN, [], None, 'Yes, from the page.')   # the page: the words alone record the draft
    assert out['recorded'] is True and saved(store)['treatment']['quote'] == 'Yes, from the page.' and 'treatment_draft' not in saved(store)
    with pytest.raises(Problem, match='No treatment draft'):
        g(lambda: VS.treatment(store_with(session()), USER, RUN, [], None, 'yes'))


def test_page_view_carries_the_gaps_shots_pictures_takes_and_budget(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 10}, {'what_appears': 'b', 'hold_s': 10}])], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', parents=['R1'])}, bindings={'VS1': {'references': {'E1': [{'id': 'R1'}]}}},
                   selections={'VS1': {'job_id': 'j-video-1'}}, reviews={'j-video-1': [{'decision': 'accepted', 'notes': 'fine', 'quote': 'yes', 'by': 'u1'}]})
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': [{'heading': 'Scene 2', 'lines': ['Cutaway section'], 'narration_starts': 'Unlike'}]}).encode('utf-8')
    VS.sequence(store, USER, RUN, [], 'AN1', ['R1', 'R2'], 'yes')
    take = {'id': 'j-video-1', 'unit': 'VS1', 'run_id': 'run-1', 'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 10}, 'error': None, 'cost': None,
            'result': {'key': 'run-1/visuals/takes/t1.mp4', 'sha256': 's', 'evidence': {'duration_seconds': 10.0, 'timing_matches_placement': True}}}
    view = VS.page_view(FakeConn([take, job('openai')]), store, RUN, [], 'VW-9')
    assert view['state'] == 'prepared' and view['intended_visuals'][0]['heading'] == 'Scene 2' and view['treatment'] is None
    g1, g2 = view['gaps']
    assert g1['gap_id'] == 'G1' and g1['accepted'] and g1['shots'][0]['route'] == 'graphic_sequence' and g1['shots'][0]['asset']['kind'] == 'sequence'
    assert [st['url'] for st in g1['shots'][0]['asset']['states']] == ['/runs/VW-9/file/run-1/visuals/references/R1.png', '/runs/VW-9/file/run-1/visuals/references/R2.png']
    assert g2['shots'][0]['route'] == 'video' and g2['shots'][0]['bound'] == ['R1'] and g2['shots'][0]['takes'][0]['url'] == '/runs/VW-9/file/run-1/visuals/takes/t1.mp4'
    assert g2['shots'][0]['takes'][0]['selected'] is True and g2['shots'][0]['takes'][0]['reviews'][0]['decision'] == 'accepted' and g2['shots'][0]['takes'][0]['duration_s'] == 10.0
    refs = {r['id']: r for r in view['references']}
    assert refs['R2']['parents'] == ['R1'] and refs['R2']['url'].endswith('/R2.png') and refs['R1']['status'] == 'approved'
    assert view['budget']['spent_inr'] == 20.0 + 10 * 8.0 and view['budget']['cap_inr'] == 5000.0
    assert VS.page_view(FakeConn([]), FakeStore({}), RUN, [], 'VW-9') == {'state': 'not_prepared'}


# ---------- design/71 P1, P2, P3, F2: the end image names its pictures, a cap of 16 inputs, sizes, the prompt lint ----------

def rid(request_id):
    return VS.digest({'run': 'run-1', 'request': request_id})[:32]


def test_an_end_keyframe_must_name_image_1_and_the_packet_says_so(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'K1': ref('K1'), 'R1': ref('R1', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}, 'packet_read_at': 't'}})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'The bucket now empty, the mason one step left.', 'parents': ['K1']}
    with pytest.raises(Problem, match='names "Image 1"'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'prompt': 'Image 1 is the start. ' + body['prompt']})
    assert out['op'] == 'edit'
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2', 'parents': []})   # a start keyframe has no parent: no numbering needed
    assert out['op'] == 'generate'
    end = VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']['end_image_instruction']
    assert 'Image 1 is the start image; images 2 onward are its identity sheets, sent by the server: take identity from them, nothing else.' in end


def test_more_than_16_inputs_after_inheritance_are_refused_with_the_count(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sheets = {f'S{i}': {**ref(f'S{i}', 'approved'), 'kind': 'sheet'} for i in range(16)}
    start = {**ref('K1'), 'generation': {'op': 'edit', 'parents': [{'id': s, 'key': sheets[s]['key'], 'sha256': 'x'} for s in sheets]}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), references={**sheets, 'K1': start})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'Image 1 is the start; the bucket now empty.', 'parents': ['K1']}
    with pytest.raises(Problem, match='17 input pictures'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    fewer = {**start, 'generation': {'op': 'edit', 'parents': start['generation']['parents'][:15]}}
    out = VS.generate_image(FakeConn([]), store_with(session(**{**sess, 'references': {**sheets, 'K1': fewer}}), doc), USER, RUN, [], body)
    assert out['op'] == 'edit'


def test_the_image_size_follows_the_frame_and_an_edit_takes_its_parents_size(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    refs = {'K1': {**ref('K1'), 'width': 1088, 'height': 1936}, 'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'width': 1920, 'height': 1080}, 'S1': {**ref('S1', 'approved'), 'kind': 'sheet', 'width': 1536, 'height': 864}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), references=refs)
    brief = [{'stage': 'brief', 'unit': None, 'summary': {'production': {'format': {'frame': '9:16'}}}}]
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'shot_id': 'IM1', 'subject': 'the wall', 'prompt': 'a wall'}

    def size_of(outputs, **over):
        store = store_with(sess, doc)
        VS.generate_image(FakeConn([]), store, USER, RUN, outputs, {**body, **over})
        return saved(store)['references'][rid(over.get('request_id', 'r1'))]['generation']['size']
    assert size_of(brief) == '1088x1936'                                                                                   # a 9:16 film
    assert size_of([]) == '1536x864'                                                                                       # no brief: 16:9
    assert size_of([], request_id='r3', prompt='Image 1 is the start; the bucket empty.', parents=['K1']) == '1088x1936'   # the start keyframe's own size
    assert size_of([], request_id='r4', parents=['F1']) == '1536x864'                                                     # a 1920x1080 frame: 1080 is not a multiple of 16
    assert size_of([], request_id='r5', parents=['S1'], size='1024x1024') == '1024x1024'                                   # an explicit size still wins


def test_prepare_take_refuses_a_start_and_end_of_different_aspect_and_accepts_a_frame_with_an_edit():
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    refs = {'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'width': 1920, 'height': 1080}, 'E1': {**ref('E1', 'approved'), 'width': 1536, 'height': 864},
            'V1': {**ref('V1', 'approved'), 'width': 1088, 'height': 1936}, 'O1': ref('O1', 'approved')}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references=refs, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'F1', 'sha256': 'sha-F1'}]}}})
    body = {'shot_id': 'VS1', 'motion_prompt': 'water poured', 'subject_reconciliation': {}, 'continuity_notes': 'the wall stays', 'start_image': 'F1', 'end_image': 'E1'}
    assert VS.prepare_take(store_with(sess, doc), USER, RUN, [], body)['duration_seconds'] == 10   # 1920x1080 and 1536x864 share 16:9
    with pytest.raises(Problem, match='aspect') as exc:
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**body, 'end_image': 'V1'}))
    assert '1920x1080' in exc.value.message and '1088x1936' in exc.value.message
    assert VS.prepare_take(store_with(sess, doc), USER, RUN, [], {**body, 'end_image': 'O1'})['duration_seconds'] == 10   # a reference without a recorded size: no check


def test_every_prompt_is_linted_for_a_logo_a_model_name_a_size_or_a_resolution(monkeypatch):
    """design/71 F2: lint rules 3 and 8 are the server's, with or without an answer form."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'The NARDEP logo top right, the wall below.'}
    with pytest.raises(Problem, match='asks for a logo'):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    with pytest.raises(Problem, match="names a model \\('kling'\\)"):
        g(lambda: VS.prepare_take(store_with(sess, doc), USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'Kling: water poured', 'subject_reconciliation': {}, 'continuity_notes': 'the wall stays', 'start_image': 'R1', 'end_image': 'R2'}))


# ---------- design/74: L7 the picture reject and the feedback record, L25 the treatment's shot routes, L26 the cap message, L6 the checklist ----------

def test_a_rejected_picture_cannot_be_approved_bound_held_or_used_as_a_parent(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'K1': ref('K1'), 'A1': ref('A1', 'approved'), 'S2': ref('S2', parents=['A1']), 'F1': ref('F1', 'failed')})
    store = store_with(sess, doc)
    row = VS.reject_reference(store, USER, RUN, [], 'K1', 'the bucket is on the wrong side', 'No, the bucket moved.')
    s = saved(store)
    assert row['status'] == 'rejected' and s['references']['K1']['rejection'] == {'notes': 'the bucket is on the wrong side', 'quote': 'No, the bucket moved.', 'by': 'u1', 'at': s['references']['K1']['rejection']['at']}
    with pytest.raises(Problem, match='not a candidate'):
        g(lambda: VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'yes'))
    with pytest.raises(Problem, match='rejected'):
        g(lambda: VS.reject_reference(store, USER, RUN, [], 'F1', 'n', 'q'))   # neither candidate nor approved
    # design/99: a click needs no typed words; this step no longer refuses without them
    with pytest.raises(Problem, match='not approved'):
        g(lambda: VS.bind(store, USER, RUN, [], 'VS1', {'E1': ['K1']}, {}))
    with pytest.raises(Problem, match='not an approved reference'):
        g(lambda: VS.still_from_reference(store, USER, RUN, [], 'IM1', 'K1', 'yes'))
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'Image 1 is the start; the bucket empty.', 'parents': ['K1']}
    with pytest.raises(Problem, match='from the approved start, not from the candidate chain'):   # design/71 P6, the server check
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))
    VS.reject_reference(store, USER, RUN, [], 'S2', 'the label drifted', 'No.')
    with pytest.raises(Problem, match='last approved state'):
        g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'r2', 'kind': 'state', 'prompt': 'the next label', 'parents': ['S2']}))


def test_feedback_records_are_written_on_approve_reject_select_and_rejected_review(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    answer = {'status': 'ready', 'prompt': 'Image 1 is the start; the bucket empty.', 'checklist': [{'check': 'bucket', 'pass_when': 'empty', 'weight': 'must'}], 'exact_text': [], 'suggestion': 'video-frame.md §4: say the size.'}
    k1 = {**ref('K1'), 'answer': answer, 'generation': {'op': 'edit', 'model': 'gpt-image-2.5-sunburst', 'prompt': answer['prompt'], 'parents': [{'id': 'A1'}]}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc), library_version='vwlib-x',
                   references={'K1': k1, 'A1': ref('A1', 'approved'), 'R2': ref('R2', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'A1', 'sha256': 'sha-A1'}]}}})
    store = store_with(sess, doc)
    VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'Yes, this one.')
    rec = saved(store)['feedback'][0]
    assert rec['app'] == 'videowizard' and rec['library_version'] == 'vwlib-x' and rec['run_code'] == 'VW-9' and rec['kind'] == 'image' and rec['job_id'].startswith('VW-9-E1-')
    assert rec['task'] == 'first-last-frame' and rec['playbook'] == 'video-frame' and rec['model'] == 'gpt-image-2.5-sunburst' and rec['inputs'] == [{'picture_id': 'A1', 'tag': 'approved'}]
    assert rec['verdict'] == 'pass' and rec['verdict_by'] == 'person' and rec['quote'] == 'Yes, this one.' and rec['prompt'] == answer['prompt'] and rec['checklist'] == answer['checklist'] and rec['suggestion'] == answer['suggestion']
    VS.reject_reference(store, USER, RUN, [], 'K1', 'the bucket is full', 'No.')
    rec = saved(store)['feedback'][1]
    assert rec['verdict'] == 'reject' and rec['what_went_wrong'] == 'the bucket is full' and rec['quote'] == 'No.'
    text = VS.feedback_yaml(saved(store)['feedback'])
    assert text.startswith('- app: videowizard\n') and '  verdict: reject\n' in text and '  checklist:\n    - line: "bucket: empty (must)"\n' in text and 'suggestion: "video-frame.md' in text
    # takes: the selection is a pass, a rejected review a reject, with the preparation's checklist
    VS.prepare_take(store, USER, RUN, [], {'shot_id': 'VS1', 'motion_prompt': 'water poured', 'subject_reconciliation': {}, 'continuity_notes': 'the wall stays', 'start_image': 'A1', 'end_image': 'R2', 'answer': {**answer, 'prompt': 'water poured', 'suggestion': ''}})
    prep = saved(store)['preparations']['VS1']
    take = {'id': 'j-video-1', 'unit': 'VS1', 'run_id': 'run-1', 'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 10, 'preparation_id': prep['preparation_id'], 'request_key': prep['key']}, 'error': None, 'cost': None,
            'result': {'key': 'run-1/visuals/takes/t1.mp4', 'sha256': 's', 'bytes': 1, 'evidence': {'duration_seconds': 10.0, 'timing_matches_placement': True}}}

    class Conn(FakeConn):
        def execute(self, sql, params=()):
            if 'select * from vw2_jobs' in sql:
                class R:
                    def fetchone(_):
                        return take
                return R()
            return super().execute(sql, params)
    VS.review_take(Conn([take]), store, USER, RUN, [], 'j-video-1', 'rejected', 'the hand jumps', '', 'No, the hand jumps.')
    rec = saved(store)['feedback'][2]
    assert rec['kind'] == 'take' and rec['task'] == 'clip-from-frame' and rec['verdict'] == 'reject' and rec['what_went_wrong'] == 'the hand jumps' and rec['checklist'] == answer['checklist'] and rec['prompt'] == 'water poured'
    VS.select_take(Conn([take]), store, USER, RUN, [], 'j-video-1', 'Yes, after watching.', notes='checked the hand')
    rec = saved(store)['feedback'][3]
    assert rec['verdict'] == 'pass' and rec['quote'] == 'Yes, after watching.' and rec['job_id'] == 'VW-9-VS1-j-video-'


def test_treatment_takes_routes_from_the_shots_when_one_is_named_and_refuses_an_unnamed_shot_route(monkeypatch):
    """design/74 L25 (VW-6, 21 Oct: seven gaps mixed routes under one named route and propose refused every one)."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    one = {**TREATMENT['gaps'][1], 'routes': ['video'], 'shots': [{'id': 'S1', 'route': 'video', 'seconds': 6}, {'id': 'S2', 'route': 'still', 'seconds': 4}]}
    store = store_with(session())
    out = VS.treatment(store, USER, RUN, [], {'gaps': [TREATMENT['gaps'][0], one]}, 'yes')
    assert out['recorded'] and saved(store)['treatment']['gaps'][1]['routes'] == ['video', 'still']
    several = {**one, 'routes': ['video', 'graphic_sequence']}   # names two, a shot uses a third
    with pytest.raises(Problem, match="gap G2: shot S2 uses the route 'still', which the entry does not name"):
        g(lambda: VS.treatment(store_with(session()), USER, RUN, [], {'gaps': [TREATMENT['gaps'][0], several]}, 'yes'))


def test_the_cap_message_tells_the_operator_the_spend_and_names_the_builder(monkeypatch):
    """design/74 L26: no front end raises the cap; the builder changes the setting on SK's word."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    with pytest.raises(Problem) as exc:
        VS.check_cap(FakeConn([job('openai') for _ in range(49)]), RUN, session(cap_inr=1000.0), 40.0, 'a 5 s take')
    assert 'tell the operator the spend' in exc.value.message and 'builder' in exc.value.message and 'vw visuals cap' not in exc.value.message
    assert not hasattr(VS, 'set_cap')


def test_page_view_carries_each_pictures_checklist_the_takes_checklist_and_a_rejected_status(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    lines = [{'check': 'label', 'pass_when': 'reads air', 'weight': 'must'}]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': {**ref('R1'), 'answer': {'status': 'ready', 'prompt': 'p', 'checklist': lines, 'exact_text': []}}, 'R2': {**ref('R2'), 'status': 'rejected', 'rejection': {'notes': 'n', 'quote': 'q', 'by': 'u1', 'at': 't'}}},
                   preparations={'VS1': {'preparation_id': 'prep-1', 'key': 'run-1/visuals/takes/prep-1.request.json', 'checklist': lines}})
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    take = {'id': 'j-video-1', 'unit': 'VS1', 'run_id': 'run-1', 'provider': 'video', 'status': 'ready', 'request': {'duration_seconds': 10, 'preparation_id': 'prep-1'}, 'error': None, 'cost': None,
            'result': {'key': 'run-1/visuals/takes/t1.mp4', 'sha256': 's', 'evidence': {'duration_seconds': 10.0, 'timing_matches_placement': True}}}
    view = VS.page_view(FakeConn([take]), store, RUN, [], 'VW-9')
    refs = {r['id']: r for r in view['references']}
    assert refs['R1']['checklist'] == lines and refs['R2']['status'] == 'rejected' and refs['R2']['rejection']['notes'] == 'n' and refs['R2']['checklist'] is None
    assert view['gaps'][1]['shots'][0]['takes'][0]['checklist'] == lines
    st = VS.status(FakeConn([take]), store, RUN, [])
    assert st['jobs'][0]['checklist'] == lines


def test_a_gap_acceptance_keeps_its_words_for_the_assistant_the_page_and_the_feedback_file(monkeypatch):
    """design/75 (defect 20): SK's 18 comments on the page were stored as each gap's acceptance and nothing read them back."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', library_version='vwlib-x')
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    VS.accept(store, USER, RUN, [], ['G2'], 'instead of an animated diagram, I would like an AI video for G2')
    s = saved(store)
    rec = s['feedback'][0]
    assert rec['kind'] == 'gap' and rec['id'] == 'G2' and rec['verdict'] == 'pass' and rec['quote'].startswith('instead of') and rec['library_version'] == 'vwlib-x' and rec['job_id'] == 'VW-9-G2-G2'
    st = VS.status(FakeConn([]), store, RUN, [])
    g1, g2 = st['gaps']
    assert g1['accepted'] is False and 'quote' not in g1 and g2['accepted'] is True and g2['quote'].startswith('instead of') and g2['by'] == 'u1'
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')
    assert view['gaps'][1]['quote'].startswith('instead of') and view['gaps'][1]['by'] == 'u1' and 'quote' not in view['gaps'][0]


# ---------- design/77: L35 the packet before a keyframe, L38 the end keeps the camera, L39 the scale anchor, L41 a client material from a frame ----------

def video_session(doc, **over):
    gap = doc['gaps'][1]
    base = dict(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                references={'S1': {**ref('S1', 'approved'), 'kind': 'sheet'}}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'S1', 'sha256': 'sha-S1'}]}}})
    return session(**{**base, **over})


def test_a_start_keyframe_for_a_video_shot_waits_for_its_packet(monkeypatch):
    """design/77 L35 (VW-6: 14 starts generated before any packet was read)."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = video_session(doc)
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'start', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'prompt': 'the yard, the wall centre'}
    with pytest.raises(Problem, match='Bind the shot and read its packet') as exc:
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    assert 'VS1' in exc.value.message
    store = store_with(sess, doc)
    VS.packet(store, RUN, [], 'VS1')   # reading the packet marks the binding
    assert saved(store)['bindings']['VS1']['packet_read_at']
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert out['op'] == 'edit' or out['op'] == 'generate'
    still_doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('IM2', 900, 1150, 'image')])   # an element used by still shots only: unaffected
    out = VS.generate_image(FakeConn([]), store_with(session(versions=sess['versions'], current='d1', accepted=accepted(still_doc)), still_doc), USER, RUN, [], {**body, 'shot_id': 'IM2'})
    assert out['op'] == 'generate'


def test_an_end_keyframe_that_moves_the_camera_is_refused_and_the_packet_says_so(monkeypatch):
    """design/77 L38 (VW-6 BEAT_01: "the camera has drifted slightly forward" against "keep exactly as in Image 1")."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = video_session(doc, references={'S1': {**ref('S1', 'approved'), 'kind': 'sheet'}, 'K1': ref('K1')})
    sess['bindings']['VS1']['packet_read_at'] = 't'
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the wall', 'parents': ['K1'],
            'prompt': 'Image 1 is the start. The helper five metres on. The camera has drifted slightly forward, so the stack is larger.'}
    with pytest.raises(Problem, match="moves the camera \\('camera has drifted'\\)"):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    with pytest.raises(Problem, match="moves the camera \\('push in'\\)"):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'prompt': 'Image 1 is the start. A slight push in on the wall top.'}))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'prompt': 'Image 1 is the start. He pushes the brick level; the camera does not move.'})
    assert out['op'] == 'edit'   # a mason pushing a brick is not a camera move
    prep = VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']
    assert 'The camera does not move between the two images' in prep['end_image_instruction'] and 'never the same frozen pose' in prep['end_image_instruction']
    assert 'one human-scale anchor against a named landmark' in prep['start_image_instruction'] and prep['scene']['landmarks'] == [{'id': 'L2', 'description': 'the wall'}]   # L39


def test_a_keyframe_for_a_shot_with_a_client_material_needs_a_footage_frame_as_a_parent(monkeypatch):
    """design/77 L41 (VW-6: the rat-trap bond drawn from words twice, wrongly)."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[], element_ids=['E1', 'WALL'])])
    doc['elements'].append({'id': 'WALL', 'name': 'The client\'s rat-trap wall face', 'kind': 'object', 'identity': 'exact', 'requirements': 'courses of equal height, long then short faces'})
    frame = {**ref('F1', 'approved'), 'kind': 'frame', 'element_id': 'WALL', 'width': 1920, 'height': 1080}
    sess = video_session(doc, references={'S1': {**ref('S1', 'approved'), 'kind': 'sheet'}, 'F1': frame})
    sess['bindings']['VS1'] = {'gap_digest': gap_digest(doc, doc['gaps'][1]), 'references': {'E1': [{'id': 'S1', 'sha256': 'sha-S1'}], 'WALL': [{'id': 'F1', 'sha256': 'sha-F1'}]}, 'packet_read_at': 't'}
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'start', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the mason at the wall', 'prompt': 'the mason lays a brick on the wall', 'parents': ['S1']}
    with pytest.raises(Problem, match="WALL is the client's own: send one of its approved footage frames as a parent"):
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], body))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'parents': ['S1', 'F1']})
    assert out['op'] == 'edit'
    no_frame = {**sess, 'references': {'S1': sess['references']['S1']}}   # the element has no frame yet: nothing to require, the prompt rule asks for one
    out = VS.generate_image(FakeConn([]), store_with(session(**no_frame), doc), USER, RUN, [], body)
    assert out['op'] == 'edit'


def test_the_packet_carries_the_recorded_footage_character_or_none():
    """design/77 L42."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    sess = video_session(doc)
    media = {'stage': 'media', 'unit': None, 'summary': {'clips': [], 'footage_character': {'camera': 'cinema', 'support': 'tripod', 'look': 'natural', 'quote': 'cinema camera'}}}
    assert VS.packet(store_with(sess, doc), RUN, [media], 'VS1')['preparation']['footage_character'] == {'line': None, 'summary': media['summary']['footage_character']}   # a session from before design/88
    assert VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']['footage_character'] == {'line': None, 'summary': None}
    assert VS.footage_character([{'stage': 'media', 'unit': None, 'summary': {'clips': []}}]) is None


# ---------- design/76: Accept and Revise ----------

def test_a_revision_drops_the_acceptance_keeps_the_words_and_clears_when_the_gap_is_proposed_again_or_accepted(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    store = store_with(session(library_version='vwlib-x'))
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    VS.treatment(store, USER, RUN, [], {'gaps': [{**TREATMENT['gaps'][0], 'routes': ['still']}, TREATMENT['gaps'][1]]}, 'yes')
    VS.propose(FakeConn(), store, USER, RUN, [], doc)   # version 1, validated as the real flow stores it
    VS.accept(store, USER, RUN, [], ['G1', 'G2'], 'yes both')
    with pytest.raises(Problem, match='operator'):
        g(lambda: VS.revise_gap(store, USER, RUN, [], 'G2', 'AI video instead', ''))
    with pytest.raises(Problem, match='Unknown gap'):
        g(lambda: VS.revise_gap(store, USER, RUN, [], 'G9', 'x', 'yes'))
    out = VS.revise_gap(store, USER, RUN, [], 'G2', 'AI video instead of the diagram', 'Make G2 an AI video.')
    s = saved(store)
    assert out['gap_id'] == 'G2' and 'G2' not in s['accepted'] and s['revisions']['G2']['notes'] == 'AI video instead of the diagram' and s['revisions']['G2']['quote'] == 'Make G2 an AI video.'
    assert s['feedback'][-1]['kind'] == 'gap' and s['feedback'][-1]['verdict'] == 'fix' and s['feedback'][-1]['what_went_wrong'] == 'AI video instead of the diagram'
    st = VS.status(FakeConn([]), store, RUN, [])
    assert st['gaps'][1]['accepted'] is False and st['gaps'][1]['revise']['quote'] == 'Make G2 an AI video.' and 'revise' not in st['gaps'][0]
    view = VS.page_view(FakeConn([]), store, RUN, [], 'VW-9')
    assert view['gaps'][1]['revise']['notes'] == 'AI video instead of the diagram'
    # proposing the same gap again unchanged keeps the revision; a changed gap clears it
    VS.propose(FakeConn(), store, USER, RUN, [], doc)
    assert 'G2' in saved(store)['revisions']
    changed = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', purpose='the water, closer')])
    VS.propose(FakeConn(), store, USER, RUN, [], changed)
    assert 'G2' not in saved(store)['revisions']
    # accepting a gap under revision clears it too
    VS.revise_gap(store, USER, RUN, [], 'G1', 'n', 'Change G1.')
    VS.accept(store, USER, RUN, [], ['G1'], 'Yes, G1 as it is after all.')
    assert 'G1' not in saved(store)['revisions'] and 'G1' in saved(store)['accepted']


# ---------- design/73: reference assets from the footage first, then Google Images ----------

def test_element_matches_list_where_each_element_is_seen_in_the_footage_best_first():
    plan = {'elements': [{'id': 'E_MASON', 'name': 'Village mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'a mason laying bricks on the wall'},
                         {'id': 'E_LORRY', 'name': 'Tipper lorry', 'kind': 'object', 'identity': 'representative', 'requirements': 'a tipper lorry'},
                         {'id': 'G_SECTION', 'name': 'Wall section drawing', 'kind': 'graphic', 'identity': 'exact', 'requirements': 'a drawing'}]}
    world = [{'clip': 'c2', 'entities': [{'name': 'bricks', 'kind': 'material', 'first_seen_s': 0.0, 'description': 'stacked bricks'}, {'name': 'mason', 'kind': 'person', 'first_seen_s': 5.5, 'description': 'the mason'}]},
             {'clip': 'c1', 'entities': [{'name': 'mason', 'kind': 'person', 'first_seen_s': 2.0, 'description': 'a mason laying bricks on a wall'}]},
             {'clip': 'c3', 'world_markers': ['old evidence shape']}]
    m = VS.element_matches(plan, world)
    assert [x['clip'] for x in m['E_MASON']] == ['c1'] and m['E_MASON'][0]['seconds'] == 2.0 and m['E_MASON'][0]['entity'] == 'mason' and m['E_MASON'][0]['score'] == 5   # c2's lone "mason" is too little
    assert m['E_LORRY'] == [] and 'G_SECTION' not in m   # a graphic is drawn, never matched
    kiln = {'elements': [{'id': 'P_KILN', 'name': 'Brick kiln', 'kind': 'place', 'identity': 'representative', 'requirements': 'a kiln with rows of green bricks drying'}]}
    walls = [{'clip': 'c1', 'entities': [{'name': 'rat_trap_bond_brick_wall', 'kind': 'structure', 'first_seen_s': 0.0, 'description': 'a brick wall'}]},
             {'clip': 'c2', 'entities': [{'name': 'brick kiln', 'kind': 'structure', 'first_seen_s': 0.0, 'description': 'a kiln with green bricks'}]}]
    assert [h['clip'] for h in VS.element_matches(kiln, walls)['P_KILN']] == ['c2']   # L44: one shared word ("brick") no longer ties a kiln to every wall


def test_fetch_image_refuses_a_non_https_or_private_address():
    with pytest.raises(ValueError, match='not an HTTPS picture address'):
        VS.fetch_image('http://img.example/1.jpg')
    with pytest.raises(ValueError, match='public address'):
        VS.fetch_image('https://127.0.0.1/1.jpg')


def test_a_search_is_stored_with_the_operators_yes_and_a_pick_becomes_a_web_reference_with_its_note(monkeypatch):
    from io import BytesIO
    PIL = pytest.importorskip('PIL.Image')
    png = BytesIO()
    PIL.new('RGB', (64, 48), (200, 80, 40)).save(png, format='PNG')
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1')
    rows = [{'n': 1, 'thumbnail': 'https://t/1.jpg', 'image_url': 'https://img.example/1.jpg', 'page_url': 'https://site.example/p1', 'site': 'site.example', 'width': 800, 'height': 600, 'title': 'kadapari'},
            {'n': 2, 'thumbnail': 'https://t/2.jpg', 'image_url': 'https://img.example/2.jpg', 'page_url': 'https://site.example/p2', 'site': 'site.example', 'width': 1200, 'height': 900, 'title': 'trowel'}]
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: rows)
    store = store_with(sess, doc)
    # design/99: a click needs no typed words; this step no longer refuses without them
    with pytest.raises(Problem, match='two to six words'):
        g(lambda: VS.search(store, USER, RUN, [], 'E1', 'a very long sentence that is not a keyword search at all', 'yes'))
    with pytest.raises(Problem, match='Unknown element'):
        g(lambda: VS.search(store, USER, RUN, [], 'E9', 'kadapari tool', 'yes'))
    out = VS.search(store, USER, RUN, [], 'E1', 'kadapari tool', 'Yes, search the web for it.')
    sid = out['search_id']
    s = saved(store)['searches'][sid]
    assert out['results'] == rows and s['element_id'] == 'E1' and s['keywords'] == 'kadapari tool' and s['quote'] == 'Yes, search the web for it.' and s['by'] == 'u1'
    monkeypatch.setattr(VS, 'fetch_image', lambda url: png.getvalue())
    with pytest.raises(Problem, match='not in the search'):
        g(lambda: VS.pick(store, USER, RUN, [], sid, [{'n': 9}], 'this'))
    # design/99: a click needs no typed words; this step no longer refuses without them
    out = VS.pick(store, USER, RUN, [], sid, [{'n': 2, 'note': 'avoid brand text'}, {'n': 1}], 'These two, the side from the second.')
    refs = saved(store)['references']
    first, second = out['references']
    assert first['kind'] == 'web' and first['element_id'] == 'E1' and first['status'] == 'approved' and first['source'] == {'url': 'https://img.example/2.jpg', 'page_url': 'https://site.example/p2', 'selection_reply': 'These two, the side from the second.', 'note': 'avoid brand text', 'search_id': sid, 'n': 2, 'from_thumbnail': False}
    assert second['source']['note'] == '' and second['source']['url'] == 'https://img.example/1.jpg' and first['width'] == 64 and refs[first['id']]['sha256']
    assert saved(store)['searches'][sid]['picked'] == [2, 1]
    # a picture the host refuses falls back to Google's thumbnail; one with neither is reported and the others still land (the pick that failed live on 22 Oct)
    def flaky(url):
        if url == 'https://img.example/2.jpg':
            raise ValueError('HTTP 403 from img.example')
        if url == 'https://t/1.jpg' or url == 'https://img.example/1.jpg':
            raise ValueError('HTTP 404')
        return png.getvalue()
    monkeypatch.setattr(VS, 'fetch_image', flaky)
    store2 = store_with(sess, doc)
    VS.search(store2, USER, RUN, [], 'E1', 'kadapari tool', 'yes')
    sid2 = next(iter(saved(store2)['searches']))
    out = VS.pick(store2, USER, RUN, [], sid2, [{'n': 2}, {'n': 1}], 'both')
    assert len(out['references']) == 1 and out['references'][0]['source']['from_thumbnail'] is True and out['failed'] == [{'n': 1, 'site': 'site.example', 'why': 'picture: HTTP 404; thumbnail: HTTP 404'}]
    monkeypatch.setattr(VS, 'fetch_image', lambda url: (_ for _ in ()).throw(ValueError('HTTP 403')))
    with pytest.raises(Problem, match='None of the ticked pictures could be downloaded'):
        g(lambda: VS.pick(store, USER, RUN, [], sid, [{'n': 1}], 'this'))
    out = VS.nothing_fits(store, USER, RUN, [], sid, 'all show the wrong tool, try the Tamil name')
    assert saved(store)['searches'][sid]['nothing_fits']['reason'] == 'all show the wrong tool, try the Tamil name'
    st = VS.status(FakeConn([]), store, RUN, [])
    assert st['searches'][0]['search_id'] == sid and st['searches'][0]['nothing_fits']['reason'].startswith('all show') and st['searches'][0]['picked'] == [2, 1]
    # design/83 P1: the picks are downloaded at once (a barrier only three concurrent downloads can pass), kept in the ticked order
    import threading
    gate = threading.Barrier(3, timeout=3)
    rows3 = rows + [{'n': 3, 'thumbnail': 'https://t/3.jpg', 'image_url': 'https://img.example/3.jpg', 'page_url': 'https://site.example/p3', 'site': 'site.example', 'width': 640, 'height': 480, 'title': 'float'}]
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: rows3)
    sid3 = VS.search(store, USER, RUN, [], 'E1', 'kadapari tool', 'yes again')['search_id']
    monkeypatch.setattr(VS, 'fetch_image', lambda url: (gate.wait() and None) or png.getvalue())
    out = VS.pick(store, USER, RUN, [], sid3, [{'n': 3}, {'n': 1}, {'n': 2}], 'all three')
    assert [r['source']['n'] for r in out['references']] == [3, 1, 2] and out['failed'] == []


def test_the_reference_round_runs_as_two_passes_on_one_page(monkeypatch):
    """design/79: every element at once; pass 1 approves frames and runs the searches; pass 2 takes the picks."""
    from io import BytesIO
    PIL = pytest.importorskip('PIL.Image')
    png = BytesIO()
    PIL.new('RGB', (64, 48), (120, 80, 40)).save(png, format='PNG')
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    doc['elements'] += [{'id': 'E2', 'name': 'Brick kiln', 'kind': 'place', 'identity': 'representative', 'requirements': 'a kiln'},
                        {'id': 'G1', 'name': 'Section drawing', 'kind': 'graphic', 'identity': 'exact', 'requirements': 'a drawing'}]
    doc['elements'][0]['kind'] = 'object'   # E1 is a graphic in the shared fixture; a round is for people, objects and places
    frame = {**ref('F1'), 'kind': 'frame', 'element_id': 'E1', 'width': 1920, 'height': 1080}
    other = {**ref('F2'), 'kind': 'frame', 'element_id': 'E2'}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', references={'F1': frame, 'F2': other})
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    with pytest.raises(Problem, match='G1 is a graphic'):
        g(lambda: VS.round_start(store, USER, RUN, [], [{'element_id': 'G1', 'frames': [], 'keywords': 'x y'}]))
    with pytest.raises(Problem, match='F2 is not a footage frame of E1'):
        g(lambda: VS.round_start(store, USER, RUN, [], [{'element_id': 'E1', 'frames': ['F2'], 'keywords': 'x y'}]))
    out = VS.round_start(store, USER, RUN, [], [{'element_id': 'E1', 'frames': [], 'keywords': 'village mason Tamil Nadu'}, {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln Tamil Nadu'}])
    rd = saved(store)['round']
    assert out == {'pass': 1, 'elements': 2} and rd['pass'] == 1 and rd['elements']['E1']['frames'] == ['F1'] and rd['elements']['E2']['frames'] == ['F2'] and rd['elements']['E2']['keywords'] == 'brick kiln Tamil Nadu'   # the elements' own frames, named or not
    sess['references']['F2']['status'] = 'rejected'
    store = store_with(sess, doc)
    store.files['run-1/visuals/package.json'] = json.dumps({'intended_visuals': []}).encode('utf-8')
    VS.round_start(store, USER, RUN, [], [{'element_id': 'E1', 'frames': ['F1'], 'keywords': 'village mason Tamil Nadu'}, {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln Tamil Nadu'}])
    assert saved(store)['round']['elements']['E2']['frames'] == []   # a rejected frame does not count
    st = VS.status(FakeConn([]), store, RUN, [])
    assert st['round']['pass'] == 1 and st['round']['elements']['E1']['verdict'] is None
    rows = [{'n': 1, 'thumbnail': 'https://t/1.jpg', 'image_url': 'https://img.example/1.jpg', 'page_url': 'https://site.example/p1', 'site': 'site.example', 'width': 800, 'height': 600, 'title': 'kiln'}]
    calls = []
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: calls.append(keywords) or rows)
    # design/99: a click needs no typed words; this step no longer refuses without them
    with pytest.raises(Problem, match='E2: a verdict is required'):
        g(lambda: VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'approve'}}, 'yes'))
    with pytest.raises(Problem, match='E2 has no frame to approve'):
        g(lambda: VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}}, 'yes'))
    out = VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'search', 'keywords': 'clamp kiln Tamil Nadu'}}, 'Yes: the first frame, and search for the kiln.')
    s = saved(store)
    assert s['references']['F1']['status'] == 'approved' and s['references']['F1']['approval']['quote'].startswith('Yes') and calls == ['clamp kiln Tamil Nadu']
    rd = s['round']
    assert out['pass'] == 2 and rd['pass'] == 2 and rd['elements']['E1']['verdict'] == 'approve' and rd['elements']['E2']['verdict'] == 'search' and rd['elements']['E2']['search_id'] and rd['elements']['E2']['keywords'] == 'clamp kiln Tamil Nadu'
    sid = rd['elements']['E2']['search_id']
    assert s['searches'][sid]['quote'].startswith('Yes') and s['feedback'][-1]['id'] == 'F1'
    monkeypatch.setattr(VS, 'fetch_image', lambda url: png.getvalue())
    with pytest.raises(Problem, match='not in this round'):
        g(lambda: VS.round_picks(store, USER, RUN, [], {'nope': [{'n': 1}]}, 'these'))
    out = VS.round_picks(store, USER, RUN, [], {sid: [{'n': 1, 'note': 'colour only'}]}, 'This one, colour only.')
    s = saved(store)
    assert out['complete'] is True and s['round']['pass'] == 'complete' and s['searches'][sid]['picked'] == [1]
    web = [r for r in s['references'].values() if r.get('kind') == 'web']
    assert len(web) == 1 and web[0]['element_id'] == 'E2' and web[0]['source']['note'] == 'colour only'
    # design/80 S5: three search rows run at once (a barrier that only three concurrent calls can pass)
    import threading
    VS.round_start(store, USER, RUN, [], [{'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln'}])
    sess3 = saved(store)
    sess3['round']['elements'].update({'E3': {'frames': [], 'keywords': 'clay pit', 'verdict': None, 'search_id': None, 'error': None}, 'E4': {'frames': [], 'keywords': 'lime mortar', 'verdict': None, 'search_id': None, 'error': None}})
    doc3 = {**doc, 'elements': doc['elements'] + [{**doc['elements'][0], 'id': 'E3', 'name': 'Pit'}, {**doc['elements'][0], 'id': 'E4', 'name': 'Mortar'}]}
    store = store_with(sess3, doc3)
    gate = threading.Barrier(3, timeout=3)
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: (gate.wait() and None) or rows)
    out = VS.round_done(store, USER, RUN, [], {'E2': {'verdict': 'search'}, 'E3': {'verdict': 'search'}, 'E4': {'verdict': 'search'}}, 'yes')
    assert out['pass'] == 2 and out['errors'] == {} and sorted(out['searched']) == ['E2', 'E3', 'E4']
    # a search that fails is recorded on its row and the round goes on
    VS.round_start(store, USER, RUN, [], [{'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln'}])
    monkeypatch.setattr(VS.apify, 'search_images', lambda keywords, n=10: (_ for _ in ()).throw(Problem(502, 'SEARCH', 'Apify answered HTTP 500 to the image search.')))
    out = VS.round_done(store, USER, RUN, [], {'E2': {'verdict': 'search'}}, 'yes')
    assert out['pass'] == 'complete' and saved(store)['round']['elements']['E2']['error'].startswith('Apify answered')
    # design/83 P1: the picks of every search in the round are downloaded at once (two searches, three picks, one barrier)
    import threading
    s2 = saved(store)
    s2['searches']['sid-b'] = {**s2['searches'][sid], 'search_id': 'sid-b', 'element_id': 'E1', 'picked': [], 'results': rows + [{**rows[0], 'n': 2, 'image_url': 'https://img.example/b2.jpg'}]}
    s2['round'] = {'pass': 2, 'at': 'now', 'by': 'u1', 'quote': 'yes', 'elements': {'E2': {'frames': [], 'keywords': 'brick kiln', 'verdict': 'search', 'search_id': sid, 'error': None},
                                                                             'E1': {'frames': [], 'keywords': 'x y', 'verdict': 'search', 'search_id': 'sid-b', 'error': None}}}
    store = store_with(s2, doc)
    gate = threading.Barrier(3, timeout=3)
    monkeypatch.setattr(VS, 'fetch_image', lambda url: (gate.wait() and None) or png.getvalue())
    out = VS.round_picks(store, USER, RUN, [], {sid: [{'n': 1, 'note': 'again'}], 'sid-b': [{'n': 1}, {'n': 2}]}, 'All three.')
    assert out['complete'] is True and len(out['references']) == 3 and out['failed'] == {} and saved(store)['searches']['sid-b']['picked'] == [1, 2]


def test_the_packet_carries_each_references_note_for_the_sheet_prompt():
    """design/73 R4a."""
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video', subjects=[])])
    gap = doc['gaps'][1]
    web = {**ref('W1', 'approved'), 'kind': 'web', 'source': {'url': 'https://img.example/2.jpg', 'note': 'avoid brand text', 'selection_reply': 'this'}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'W1': web, 'R1': ref('R1', 'approved')}, bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'W1', 'sha256': 'sha-W1'}, {'id': 'R1', 'sha256': 'sha-R1'}]}}})
    refs = VS.packet(store_with(sess, doc), RUN, [], 'VS1')['preparation']['references']
    assert refs[0]['note'] == 'avoid brand text' and refs[1]['note'] == ''


def test_apify_request_and_answer_shapes():
    from app import apify
    assert apify.build('kadapari tool', 10) == {'queries': ['kadapari tool'], 'maxResultsPerQuery': 10}
    items = [{'imageUrl': 'https://img/1.jpg', 'thumbnailUrl': 'https://t/1.jpg', 'contentUrl': 'https://site/p', 'origin': 'site', 'imageWidth': 800, 'imageHeight': 600, 'title': 'k', 'query': 'kadapari tool'},
             {'imageUrl': 'http://insecure/2.jpg', 'thumbnailUrl': 'https://t/2.jpg'}, {'imageUrl': 'https://img/3.jpg', 'thumbnailUrl': 'https://t/3.jpg', 'title': 'x'}]
    rows = apify.parse(items, 10)
    assert [r['n'] for r in rows] == [1, 2] and rows[0] == {'n': 1, 'thumbnail': 'https://t/1.jpg', 'image_url': 'https://img/1.jpg', 'page_url': 'https://site/p', 'site': 'site', 'width': 800, 'height': 600, 'title': 'k'}
    assert rows[1]['image_url'] == 'https://img/3.jpg'   # an http picture is dropped, the numbering stays dense
    from types import SimpleNamespace
    from pydantic import SecretStr
    import pytest as _pt
    mp = _pt.MonkeyPatch()
    mp.setattr(apify, 'settings', lambda: SimpleNamespace(APIFY_TOKEN=SecretStr('')))   # never the real token from server/.env: no paid call from a test
    try:
        with pytest.raises(Problem, match='APIFY_TOKEN'):
            apify.search_images('x y', 10)
    finally:
        mp.undo()


def test_record_gap_keeps_the_takes_start_and_end_ids():
    """design/71 P4: assembly needs the boundary pictures to see where two takes of one gap share one."""
    prep = {'start_image': {'reference_id': 'R1'}, 'end_image': {'reference_id': 'R2'}}
    assert VS.boundary_of(prep) == {'start_image': 'R1', 'end_image': 'R2'}
    assert VS.boundary_of({'start_image': {'reference_id': 'R1'}}) == {'start_image': 'R1', 'end_image': None}
