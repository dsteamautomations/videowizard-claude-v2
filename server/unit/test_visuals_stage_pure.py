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
        self.jobs, self.inserted = list(jobs), []

    def execute(self, sql, params=()):
        conn = self

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
    assert out['totals'] == {'gaps': 2, 'images': 4, 'routes': {'graphic_sequence': 1, 'video': 1}, 'seconds': {'graphic_sequence': 20.0, 'video': 10.0}}
    assert out['estimate_inr'] == 4 * 20.0 + 10 * 8.0 and sess['treatment']['estimate_inr'] == out['estimate_inr']


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
    assert sp == {'images': 2, 'take_seconds': 10.0, 'spent_inr': 120.0, 'prices': {'image_inr': 20.0, 'video_inr_per_s': 8.0}}


def test_the_cap_refuses_a_paid_call_that_would_pass_it_and_the_operator_raises_it(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    conn = FakeConn([job('openai') for _ in range(49)])   # ₹980 spent
    assert VS.cap_of(session()) == 5000.0   # design/66 C4: the default cap
    sess = session(cap_inr=1000.0)
    VS.check_cap(conn, RUN, sess, 20.0, 'one image')       # exactly the cap: allowed
    with pytest.raises(Problem) as exc:
        VS.check_cap(conn, RUN, sess, 40.0, 'a 5 s take')
    assert exc.value.code == 'VISUALS_CAP' and '₹980' in exc.value.message and '₹1,000' in exc.value.message and 'about ₹40' in exc.value.message and 'vw visuals cap' in exc.value.message
    assert exc.value.extra == {'spent_inr': 980.0, 'cap_inr': 1000.0, 'estimate_inr': 40.0}
    store = store_with(sess)
    with pytest.raises(Problem, match='operator'):
        g(lambda: VS.set_cap(store, USER, RUN, [], 1500, ''))
    with pytest.raises(Problem, match='more than'):
        g(lambda: VS.set_cap(store, USER, RUN, [], 0, 'raise it'))
    out = VS.set_cap(store, USER, RUN, [], 1500, 'Raise the cap to 1500, the diagrams are worth it.')
    assert out['cap_inr'] == 1500.0 and saved(store)['cap_inr'] == 1500.0 and saved(store)['cap_history'][0]['quote'].startswith('Raise')
    VS.check_cap(conn, RUN, saved(store), 40.0, 'a 5 s take')   # under the new cap


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
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', cap_inr=30.0)
    store = store_with(sess, doc)
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'n', 'kind': 'keyframe', 'subject': 'the wall', 'prompt': 'a wall section'}
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
    assert out['warnings'] == [] and out['states'] == 3


def test_a_sequence_warns_when_a_state_was_not_made_from_the_previous_one_and_refuses_the_wrong_count_or_shot():
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 10}, {'what_appears': 'b', 'hold_s': 10}])], [shot('DG1', 900, 1150, 'diagram')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1'), 'R2': ref('R2'), 'R3': ref('R3', parents=['R1'])})
    out = VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['R1', 'R2'], 'yes')
    assert out['warnings'] == ['state 2 (R2) was not generated from state 1 (R1); check the drawing is the same']
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
    body = {'shot_id': 'VS1', 'motion_prompt': 'water poured along the top', 'subject_reconciliation': {}, 'start_image': 'R1'}
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
    assert record['start_image']['reference_id'] == 'R1' and record['end_image']['reference_id'] == 'R2' and 'second image as the ending frame' in record['effective_prompt']


def test_a_keyframe_may_be_generated_from_a_candidate_keyframe(monkeypatch):
    """design/66 C3: the end keyframe is made from the start keyframe before either is approved, so the pair is approved together."""
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1',
                   references={'K1': ref('K1'), 'S1': {**ref('S1'), 'kind': 'sheet'}, 'A1': ref('A1', 'approved')})
    body = {'request_id': 'r1', 'element_id': 'E1', 'name': 'end', 'kind': 'keyframe', 'subject': 'the wall', 'prompt': 'the same yard, the bucket now empty', 'parents': ['K1']}
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert out['op'] == 'edit' and saved(store)['references'][out['reference_id']]['generation']['parents'] == [{'id': 'K1', 'key': 'run-1/visuals/references/K1.png', 'sha256': 'sha-K1'}]
    with pytest.raises(Problem, match='Parents must be approved'):   # a candidate sheet is not a start keyframe
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r2', 'parents': ['S1']}))
    with pytest.raises(Problem, match='Parents must be approved'):   # only a keyframe is made from a candidate
        g(lambda: VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r3', 'kind': 'isolated', 'parents': ['K1']}))
    out = VS.generate_image(FakeConn([]), store_with(sess, doc), USER, RUN, [], {**body, 'request_id': 'r4', 'kind': 'isolated', 'parents': ['A1']})
    assert out['op'] == 'edit'


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
