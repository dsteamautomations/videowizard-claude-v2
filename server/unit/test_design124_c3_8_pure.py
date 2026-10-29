"""design/124 Changes 3, 6, 7, 8.
Change 3: the treatment's Direction box (required; kept; the plan's foundation.treatment starts from it).
Change 6: accept or send back each line of the treatment draft (the Direction and every gap); recorded when all are accepted; a revision keeps
the acceptance of an unchanged line and returns a changed one to "to accept", marked changed; the whole-draft approval still records.
Change 7: warning_answers per shot (a warning counts as answered when its kind has an entry; the job form never reads it); the facts line per shot.
Change 8: a plain sentence per warning kind the operator sees; the technical kinds are kept from the operator."""
import json
import re
from fractions import Fraction
from pathlib import Path

import pytest

from app import library, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design101_pure import take_store
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, USER, FakeConn, TREATMENT, g, plan_doc, saved, session, shot, store_with

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
DIRECTION = TREATMENT['direction']


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def draft(store, doc=None):
    return VS.treatment(store, USER, RUN, [], doc or TREATMENT, '')


def lines(store):
    return {k: v['state'] for k, v in saved(store)['treatment_draft']['lines'].items()}


# ---------- Change 3: the Direction ----------

def test_a_treatment_without_a_direction_is_refused_and_the_direction_is_kept():
    store = store_with(session())
    with pytest.raises(Problem, match='direction'):
        g(lambda: VS.treatment(store, USER, RUN, [], {'gaps': TREATMENT['gaps']}, ''))
    draft(store)
    assert saved(store)['treatment_draft']['direction'] == DIRECTION
    VS.treatment(store, USER, RUN, [], None, 'Yes, as drafted.')
    assert saved(store)['treatment']['direction'] == DIRECTION


def test_propose_checks_the_plans_treatment_starts_from_the_direction():
    doc = plan_doc([shot('AN1', 0, 500, 'animation', states=[{'what_appears': 'a', 'hold_s': 5}, {'what_appears': 'b', 'hold_s': 5}, {'what_appears': 'c', 'hold_s': 5}, {'what_appears': 'd', 'hold_s': 5}])],
                   [shot('VS1', 900, 1150, 'video')])
    store = store_with(session())
    VS.treatment(store, USER, RUN, [], {**TREATMENT, 'direction': 'Show the hollow inside the wall.'}, 'yes')
    with pytest.raises(Problem, match='Direction'):
        g(lambda: VS.propose(FakeConn(), store, USER, RUN, [], doc))
    doc['foundation']['treatment'] = 'Show the hollow  inside the wall.\nThen the rest of the brief.'   # starts from it; spacing is not a difference
    assert VS.propose(FakeConn(), store, USER, RUN, [], doc)['version'] == 1


def test_a_treatment_recorded_before_the_direction_still_lets_propose_through():
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    old = {'gaps': [{**TREATMENT['gaps'][0], 'routes': ['still']}, TREATMENT['gaps'][1]], 'quote': 'yes', 'by': 'u1', 'at': 't', 'digest': 'x', 'totals': {}, 'estimate_inr': 0}
    store = store_with(session(treatment=old))
    assert VS.propose(FakeConn(), store, USER, RUN, [], doc)['version'] == 1


# ---------- Change 6: a state per line ----------

def test_one_gap_sent_back_while_the_rest_stay_accepted_and_the_record_waits_for_every_line():
    store = store_with(session())
    draft(store)
    assert lines(store) == {'direction': 'to_accept', 'G1': 'to_accept', 'G2': 'to_accept'}
    out = VS.treatment(store, USER, RUN, [], None, 'Yes to these.', accept=['direction', 'G1'])
    assert not out.get('recorded') and lines(store) == {'direction': 'accepted', 'G1': 'accepted', 'G2': 'to_accept'} and 'treatment' not in saved(store)
    with pytest.raises(Problem, match='notes'):
        g(lambda: VS.treatment(store, USER, RUN, [], None, '', send_back=['G2']))
    VS.treatment(store, USER, RUN, [], None, '', send_back=['G2'], notes='show the water on the wall, not the yard')
    l = saved(store)['treatment_draft']['lines']
    assert l['G2']['state'] == 'sent_back' and l['G2']['note'] == 'show the water on the wall, not the yard' and l['G1']['state'] == 'accepted'
    with pytest.raises(Problem, match='G7'):
        g(lambda: VS.treatment(store, USER, RUN, [], None, 'yes', accept=['G7']))
    # the assistant revises only G2: G1 and the Direction stay accepted, G2 comes back to accept, marked changed
    revised = {**TREATMENT, 'gaps': [TREATMENT['gaps'][0], {**TREATMENT['gaps'][1], 'picture': 'water poured over the finished wall, the wall darkening'}]}
    draft(store, revised)
    l = saved(store)['treatment_draft']['lines']
    assert lines(store) == {'direction': 'accepted', 'G1': 'accepted', 'G2': 'to_accept'} and l['G2'].get('changed') is True and not l['G1'].get('changed')
    out = VS.treatment(store, USER, RUN, [], None, 'Yes, G2 now.', accept=['G2'])
    s = saved(store)
    assert out['recorded'] is True and s['treatment']['gaps'][1]['picture'].endswith('darkening') and 'treatment_draft' not in s and 'Yes, G2 now.' in s['treatment']['quote']


def test_a_revision_that_changes_an_accepted_line_returns_it_to_accept():
    store = store_with(session())
    draft(store)
    VS.treatment(store, USER, RUN, [], None, 'yes', accept=['direction', 'G1'])
    draft(store, {**TREATMENT, 'gaps': [{**TREATMENT['gaps'][0], 'seconds': 18}, TREATMENT['gaps'][1]]})   # the totals moved G1 too
    l = saved(store)['treatment_draft']['lines']
    assert l['G1']['state'] == 'to_accept' and l['G1']['changed'] is True and l['direction']['state'] == 'accepted'


def test_the_whole_draft_approved_as_today_still_records_and_an_old_draft_without_lines_takes_per_line_verdicts():
    store = store_with(session())
    draft(store)
    assert VS.treatment(store, USER, RUN, [], None, 'Yes, all of it.')['recorded'] is True
    old = {'gaps': TREATMENT['gaps'], 'totals': {}, 'estimate_inr': 0, 'by': 'u1', 'at': 't', 'digest': 'x'}   # drafted before Change 6: no direction, no lines
    store = store_with(session(treatment_draft=old))
    VS.treatment(store, USER, RUN, [], None, 'yes', accept=['G1'])
    assert VS.treatment(store, USER, RUN, [], None, 'yes', accept=['G2'])['recorded'] is True


def test_the_page_and_chat_reach_the_same_function():
    web = (ROOT / 'app' / 'web.py').read_text(encoding='utf-8')
    main = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
    assert "accept=list(body.get('accept') or [])" in web and 'send_back=' in web
    assert 'accept=body.accept' in main and 'send_back=body.send_back' in main and 'notes=body.notes' in main
    assert "data-a=\"t-accept\"" in PAGE and "data-a=\"t-back\"" in PAGE and 'tr.direction' in PAGE


# ---------- Change 7: warning answers and the facts line ----------

def test_a_warning_answered_in_warning_answers_counts_as_answered():
    doc = plan([pshot('IM1', 0, 100, 'image'), pshot('VS1', 100, 350, 'video'), pshot('VS2', 350, 600, 'video'), pshot('IM2', 600, 700, 'image'), pshot('VS3', 700, 950, 'video'), pshot('IM3', 950, 1000, 'image')])
    _, warns = VC.validate_plan(doc, GAPS, Fraction(25))
    cam = [w for w in warns if w['kind'] == 'camera_reason_missing' and w.get('shot_id') == 'VS1']
    assert cam and cam[0]['answered'] is False
    doc['gaps'][0]['scenes'][0]['shots'][1]['warning_answers'] = [{'kind': 'camera_reason_missing', 'answer': 'a plain record shot; the angle carries nothing'}]
    out, warns = VC.validate_plan(doc, GAPS, Fraction(25))
    by = {(w.get('shot_id'), w['kind']): w for w in warns}
    assert by[('VS1', 'camera_reason_missing')]['answered'] is True and by[('VS1', 'camera_reason_missing')]['answer'].startswith('a plain record')
    assert by[('VS2', 'camera_reason_missing')]['answered'] is False   # one shot's answer is not another's
    assert out['gaps'][0]['scenes'][0]['shots'][1]['warning_answers'][0]['kind'] == 'camera_reason_missing'
    assert 'warning_answers' not in out['gaps'][0]['scenes'][0]['shots'][0]   # absent stays absent
    doc['gaps'][0]['scenes'][0]['shots'][1]['warning_answers'] = [{'kind': 'camera_reson_missing', 'answer': 'x'}]
    with pytest.raises(ValueError, match='camera_reson_missing'):
        VC.validate_plan(doc, GAPS, Fraction(25))


def test_the_job_form_and_the_packet_carry_no_warning_answer():
    store, doc = take_store()
    plain = VS.packet(store, RUN, [], 'VS1')
    doc['gaps'][1]['scenes'][0]['shots'][0]['warning_answers'] = [{'kind': 'look_only', 'answer': 'WARNING-ANSWER-TEXT'}]
    store, _ = take_store()
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    pk = VS.packet(store, RUN, [], 'VS1')
    assert 'WARNING-ANSWER-TEXT' not in json.dumps(pk) and pk['preparation_digest'] == plain['preparation_digest']
    shot_ = doc['gaps'][1]['scenes'][0]['shots'][0]
    form = library.job_form('take', run=RUN, plan=doc, gap=doc['gaps'][1], scene=doc['gaps'][1]['scenes'][0], shot=shot_, refs=[], generator=None, brief=None, card=None, rules=[])
    assert 'WARNING-ANSWER-TEXT' not in json.dumps(form)


def test_the_facts_line_for_a_shot_with_a_beat_and_a_count():
    plan_ = {'elements': [{'id': 'E2', 'name': 'the carter'}, {'id': 'E3', 'name': 'bricks'}]}
    obj = lambda n: [{'element_id': 'E3', 'count': n, 'place': {'landmark_id': 'L1', 'relation': 'on the pan'}}]
    sh = {'id': 'VS1', 'size': 'WS', 'narration': 'homes going up',
          'subjects': [{'element_id': 'E2', 'start': {'objects': obj(0)}, 'end': {'objects': obj(6)},
                        'beats': [{'action': 'lifts a brick', 'done': 'lifted one brick', 'result': 'one brick'}, {'action': 'sets bricks', 'done': 'set 6 bricks on the pan', 'result': 'at the stack'}]}]}
    assert VS.facts_line(plan_, sh) == "Wide · under 'homes going up' · the carter: set 6 bricks on the pan · ends at the stack · bricks 0 → 6"
    assert VS.facts_line(plan_, {'id': 'IM1', 'narration': ''}) == ''


def test_the_plan_page_shows_the_facts_line_and_the_answers():
    assert 's.facts_line' in PAGE and 'warning_answers' in PAGE


# ---------- Change 8: plain words ----------

def test_every_warning_kind_is_plain_or_technical_once():
    src = (ROOT / 'app' / 'visual_contract.py').read_text(encoding='utf-8') + (ROOT / 'app' / 'visuals_stage.py').read_text(encoding='utf-8')
    found = set(re.findall(r"'kind': '([a-z_]+)'(?:, 'message'|,$)", src, re.M)) | set(re.findall(r"'kind': '(look_alike)'", src))
    assert len(found) >= 40 and 'look_alike' in found and 'cut_off_pause' in found
    assert found <= set(VC.WARNING_PLAIN) | set(VC.WARNING_TECHNICAL) and not set(VC.WARNING_PLAIN) & set(VC.WARNING_TECHNICAL)
    assert 'size_close_first' in VC.WARNING_PLAIN and 'camera_reason_missing' in VC.WARNING_TECHNICAL
    assert all(s[0].isupper() and s.endswith('.') and '_' not in s for s in VC.WARNING_PLAIN.values())


def test_the_page_shows_the_plain_sentence_with_its_gap_and_never_a_technical_kind():
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    warns = [{'shot_id': 'VS1', 'kind': 'size_close_first', 'message': 'technical', 'answered': True, 'answer': 'a reveal'},
             {'shot_id': 'VS1', 'kind': 'camera_reason_missing', 'message': 'technical', 'answered': False},
             {'gap_id': 'G1', 'kind': 'graphics_run', 'message': 'technical', 'answered': False}]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': warns}], current='d1')
    view = VS.page_view(FakeConn([]), store_with(sess, doc), RUN, [], 'VW-9')
    g1, g2 = view['gaps']
    assert g2['warnings'] == [{'kind': 'size_close_first', 'shot_id': 'VS1', 'plain': VC.WARNING_PLAIN['size_close_first'], 'answer': 'a reveal'}]
    assert [w['kind'] for w in g1['warnings']] == ['graphics_run']
    assert 'g.warnings' in PAGE and 'w.plain' in PAGE
