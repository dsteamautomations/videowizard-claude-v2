"""design/126, builder A (server): ST1 (no silent GPT Image), OP2 (no two-chapter warning), OP3 (N17's chapter warning for information),
OP4 (dashes and curly quotes on the cards), MA1 (a rejected shot's gap says what it showed and why), TR1 (the treatment warns on a graphics run
over 8 s), TR2 (one picture price per film), U5 (search keywords 2 to 12 words)."""
import inspect
import json
from copy import deepcopy

import pytest

from app import core, visuals_stage as VS
from app.errors import Problem
from app.stage2 import slides as SL, stage as S, validator as V
from test_design127_review_pure import USER as S_USER, answer_all, decide, plan as master_plan, session_store
from test_design91_b2_pure import check as b2_check, doc as b2_doc, package as b2_package
from test_review_page import FakeConn, RUN as S_RUN
from test_visuals_stage_pure import USER, g, saved, session, store_with


# ---------- ST1 ----------

def test_st1_create_run_has_no_default_picture_ai():
    assert inspect.signature(core.create_run).parameters['image_provider'].default is inspect.Parameter.empty


def test_st1_a_run_without_a_picture_ai_is_refused_by_name():
    for run in ({}, {'image_provider': None}, {'image_provider': ''}, None):
        with pytest.raises(Problem, match=r'this film has no picture AI; it is chosen at `vw start --images`'):
            VS.provider_of(run)
    assert VS.provider_of({'image_provider': 'openai'}) == 'openai' and VS.provider_of({'image_provider': 'gemini'}) == 'gemini'
    assert 'runs from before the choice' not in VS.provider_of.__doc__


# ---------- OP2: its test replaces P7's in test_design125_stage7_a_pure.py ----------


# ---------- OP3 ----------

def chapter_flag():
    pk = b2_package()
    pk['sub_clips'][0]['process_stage'] = 'curing'
    return next(f for f in b2_check(b2_doc(), pk)['flags'] if 'is shown by a clip of the stage' in f)


def test_op3_the_chapter_warning_has_its_own_kind_and_no_operator_decides():
    f = chapter_flag()
    assert '(the operator decides)' not in f and f.endswith('the right step?') and V.RULE_RE.search(f).group(1) == 'N17 stage'


def test_op3_on_a_cut_shaped_like_vw12_act_on_keeps_e2_and_r5_only():
    claim = 'OPTION #7: N17 step BEAT_09.S1 is a claim (x) shown by footage: the shot must show its evidence or its result, or leave a blank for a graphic or a scene of the result'
    flags = ([chapter_flag()] * 10 + ['OPTION #3 blank at event 4: E2 AI blank of 18.6 s is over 12 s'] * 4 + ['OPTION #6 event 2: R5 a wide shot held 3.1 s, under 4 s']
             + ['OPTION #1 event 2: R1 cut not at a natural cut point'] * 16 + ['OPTION #2 event 1: R10 colour group changes'] * 12 + ['OPTION #4 event 3: R4 energy drops'] * 4)
    out = V.answer_flags(flags)
    assert sorted({f.split(': ')[1].split()[0] for f in out['act_on']}) == ['E2', 'R5'] and len(out['act_on']) == 5
    assert out['for_information'] == '42 for information: R1 16, R10 12, N17 stage 10, R4 4'
    assert V.answer_flags([claim])['act_on'] == [claim]   # the claim N17 flag stays to act on


# ---------- OP4 ----------

def test_op4_dashes_and_curly_quotes_stay_readable():
    assert SL.ascii_text('challenge—how') == 'challenge - how'
    assert SL.ascii_text('it’s') == "it's" and SL.ascii_text('‘a’ “b” c–d') == "'a' \"b\" c - d"
    assert SL.ascii_text('café') == 'cafe'   # the NFKD cleaning still runs


# ---------- MA1 ----------

def with_overview(store, line):
    pk = json.loads(store.files['p'])
    pk['cards'] = [{'clip_id': 'c2', 'descriptive_name': 'workers on site', 'lines': ['1 OVERVIEW: ' + line, '2 ACTION: walking']}]
    store.files['p'] = json.dumps(pk).encode('utf-8')


def rejected_reason(store, note=''):
    answer_all(store, **{'1.3': None})
    S.decide(FakeConn({}), store, S_USER, S_RUN, '1.3', 'REJECT', note, None)
    decide(store, '1.3A1', 'REJECT')
    S.build_master(FakeConn({}), store, S_USER, S_RUN)
    return master_plan(store)['gaps'][1]['reason']


def test_ma1_a_rejected_shot_says_what_it_showed_without_a_note():
    store = session_store()
    with_overview(store, 'masons sweep a brick course')
    reason = rejected_reason(store)
    assert 'in place of rejected Scene 1 · Shot 3 (it showed: masons sweep a brick course)' in reason
    assert 'Shot 3: less. Bricks' not in reason and 'the operator:' not in reason


def test_ma1_a_rejected_shot_carries_the_operators_note():
    store = session_store()
    with_overview(store, 'masons sweep a brick course')
    reason = rejected_reason(store, 'the bricks are rough')
    assert 'in place of rejected Scene 1 · Shot 3 (it showed: masons sweep a brick course; the operator: the bricks are rough)' in reason


# ---------- TR1, TR2 ----------

VW12_GAPS = {gid: {'start_frame': i * 1000, 'end_frame': i * 1000 + 900, 'passage_ids': [f'P{i}'], 'requirement': 'x'}
             for i, gid in enumerate(['BEAT_01-B1', 'BEAT_05-B1', 'BEAT_02-B2', 'BEAT_03-B2', 'BEAT_03-B1'])}


def entry(gid, shots, images=0):
    return {'gap_id': gid, 'intended': [], 'picture': 'p', 'routes': sorted({r for r, _ in shots}), 'seconds': round(sum(s for _, s in shots), 2), 'images': images,
            'shots': [{'id': f'{gid}-{n}', 'route': r, 'seconds': s} for n, (r, s) in enumerate(shots, 1)]}


def vw12(drawn=(23.92, 11.84, 10.84, 9.08)):
    return {'direction': 'a documentary explainer told from the site', 'gaps': [
        entry('BEAT_01-B1', [('video', 88.14)], images=20),   # with the 4 s + 4 s below: 96.14 s of video, as VW-12
        entry('BEAT_05-B1', [('video', 4.0), ('drawn', drawn[0]), ('still', 5.56)]),
        entry('BEAT_02-B2', [('drawn', drawn[1])]),
        entry('BEAT_03-B2', [('footage', 3.0), ('drawn', drawn[2])]),
        entry('BEAT_03-B1', [('drawn', drawn[3]), ('video', 4.0)])]}


def run(provider):
    return {'id': 'run-1', 'code': 'VW-12', 'image_provider': provider}


def treat(doc, provider='gemini', quote=''):
    store = store_with(session(source={'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': VW12_GAPS}))
    return VS.treatment(store, USER, run(provider), [], deepcopy(doc), quote), store


def test_tr1_vw12s_treatment_gives_four_graphics_run_warnings():
    out, store = treat(vw12())
    msgs = [w['message'] for w in out['warnings'] if w['kind'] == 'graphics_run']   # design/126 TR3 adds the length warnings beside them
    assert len(msgs) == 4 and [m.split(' s ')[0] for m in msgs] == ['23.9', '11.8', '10.8', '9.1']
    assert 'give the reason in the treatment' in msgs[0] and 'give the reason' not in msgs[3]
    assert saved(store)['treatment_draft']['warnings'] == out['warnings']
    out, store = treat(vw12(), quote='Yes.')
    assert len(out['warnings']) == len(saved(store)['treatment']['warnings']) and sum(w['kind'] == 'graphics_run' for w in out['warnings']) == 4


def test_tr1_drawn_shots_of_8_s_or_less_give_none():
    assert [w for w in treat(vw12(drawn=(8, 8, 7.5, 4)))[0]['warnings'] if w['kind'] == 'graphics_run'] == []


def test_tr2_vw12s_totals_on_a_gemini_run_and_an_openai_run():
    assert treat(vw12())[0]['estimate_inr'] == pytest.approx(1099.14, abs=0.01)   # 20 × $0.134 × 88 + 97 s × ₹8.90 (design/134 12: each take at its generated seconds, 88.14 → 89)
    assert treat(vw12(), provider='openai')[0]['estimate_inr'] == 943.3   # 20 × ₹4 + 97 s × ₹8.90 (design/134 12)


def test_tr2_one_picture_price_per_film(monkeypatch):
    s = VS.settings()
    assert VS.image_price_inr(run('openai')) == s.VISUALS_PRICE_IMAGE_INR
    assert VS.image_price_inr(run('gemini'), '4K') == pytest.approx(s.GEMINI_IMAGE_USD_4K * s.VISUALS_USD_INR)
    assert VS.image_price_inr(run('gemini'), '2K') == pytest.approx(s.GEMINI_IMAGE_USD * s.VISUALS_USD_INR)
    src = inspect.getsource(VS)
    assert "prices()['image_inr']" not in src and "pr['image_inr'] +" not in src and "* pr['image_inr']" not in src and "sp['prices']['image_inr']" not in src


# ---------- U5 ----------

def test_u5_keywords_are_two_to_twelve_words():
    twelve = ' '.join(f'w{i}' for i in range(12))
    plan = {'elements': [{'id': 'E1'}]}
    for kw in (twelve + ' w12', 'brick'):
        with pytest.raises(Problem, match='Keywords are two to twelve words: '):
            g(lambda: VS.search(None, USER, run('openai'), [], 'E1', kw, '', found={}))
        with pytest.raises(Problem, match='Keywords are two to twelve words: '):
            g(lambda: VS._search_into({}, USER, run('openai'), plan, 'E1', kw, '', results=[]))
        assert VS.search_rows(None, run('openai'), kw) == {}
    assert VS._search_into({}, USER, run('openai'), plan, 'E1', twelve, '', results=[])['keywords'] == twelve
    assert 'two to six' not in inspect.getsource(VS)
