"""design/205 (SK, 15 Nov 2026): the Direction alone first, then the gap lines; the motion style chosen on the page, every style shown, the
recommended one with its reason; the earlier Direction shown whole; the log says what a draft returned and what the page recorded."""
import json
from app import core as _core   # SK, 23 Nov 2026: v3.json is read as a film with footage is served it
from copy import deepcopy
from pathlib import Path

import pytest

from app import film, page_flow as PF, runlog, visuals_stage as VS
from app.errors import Problem
from test_design126_a_pure import USER, VW12_GAPS, session, store_with
from test_design203_pure import PARTS, doc

OLD_RUN = {'id': 'run-1', 'code': 'VW-12', 'image_provider': 'gemini'}   # a film from before the film record: no motion style is asked


def film_run(**choices):
    return {'id': 'run-1', 'code': 'VW-30', 'title': 'Filler slab roofs', 'status': 'open', 'image_provider': 'gemini',
            'film': {'category': {'value': 'documentary-explainer'}, **{k: {'value': v} for k, v in choices.items()}}}


class Conn:
    """Stands in for the database: the film record's update and the log's rows."""
    def __init__(self, run):
        self.run, self.log = run, []

    def execute(self, sql, params=()):
        if sql.startswith('update vw2_runs set film'):
            self.run['film'] = {**(self.run.get('film') or {}), params[0]: params[1].obj}
            return type('Row', (), {'fetchone': lambda s: {'film': self.run['film']}})()
        if sql.startswith('insert into vw2_log'):
            self.log.append(dict(zip(('run_id', 'stage', 'kind', 'about', 'rule', 'entry', 'by_kind', 'by_name', 'quote', 'request_id'), params)))
            return None
        raise AssertionError('unexpected: ' + sql[:60])


def new_store():
    return store_with(session(source={'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': VW12_GAPS}))


def alone(parts=PARTS, **more):
    return {'direction_parts': deepcopy(parts), **more}


def send(store, document, run=OLD_RUN):
    return VS.treatment(store, USER, run, [], deepcopy(document), '')


def ans(line, choice, notes=''):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes}


# ---------- point 4: the Direction alone first ----------

def test_a_draft_that_holds_only_the_direction_is_taken():
    store = new_store()
    out = send(store, alone())
    assert out['draft'] is True and list(out['lines']) == ['direction'] and 'the Direction alone' in out['log']
    p = PF.page(Conn(OLD_RUN), store, USER, OLD_RUN, [])
    assert [l['key'] for l in p['lines']] == ['direction'] and p['lines'][0]['state'] == 'open' and 'after you accept the Direction' in p['note']


def test_the_direction_accepted_alone_is_not_the_treatment_and_the_assistant_is_told_to_write_the_gaps():
    store = new_store()
    send(store, alone())
    conn = Conn(OLD_RUN)
    r = PF.page_record(conn, store, USER, OLD_RUN, [], [ans(PF.page(conn, store, USER, OLD_RUN, [])['lines'][0], 'accept')])
    s = VS.session_of(store, OLD_RUN, [])
    assert r['recorded'] == ['direction'] and not s.get('treatment') and s['treatment_draft']['lines']['direction']['state'] == 'accepted'
    assert 'write every gap line' in r['then'] and 'whole treatment' in r['then']


def test_the_whole_treatment_sent_after_keeps_the_direction_accepted():
    store = new_store()
    send(store, alone())
    VS.treatment(store, USER, OLD_RUN, [], None, 'Accept', accept=['direction'])
    out = send(store, doc())
    assert out['lines']['direction'] == 'accepted' and all(v == 'to_accept' for k, v in out['lines'].items() if k != 'direction') and len(out['lines']) == 6
    p = PF.page(Conn(OLD_RUN), store, USER, OLD_RUN, [])
    assert [l['state'] for l in p['lines']] == ['recorded'] + ['open'] * 5


def test_the_direction_alone_again_unchanged_is_refused_when_gap_lines_exist():
    store = new_store()
    send(store, doc())
    with pytest.raises(ValueError, match='whole treatment'):
        send(store, alone())
    out = send(store, alone({**PARTS, 'idea': 'A cooler home for less.'}))   # a changed Direction is taken: the gaps are written again from it
    assert list(out['lines']) == ['direction']


def test_a_direction_sent_back_alone_comes_back_changed_as_asked():
    store = new_store()
    send(store, alone())
    VS.treatment(store, USER, OLD_RUN, [], None, 'Change this', send_back=['direction'], notes='tell it from the family')
    out = send(store, alone({**PARTS, 'viewpoint': 'Told from the family who will live in the house.'}))
    line = VS.session_of(store, OLD_RUN, [])['treatment_draft']['lines']['direction']
    assert out['lines'] == {'direction': 'to_accept'} and line.get('asked') and any('Whose story' in c for c in line['changes'])


# ---------- points 5 to 7: the motion style on the page ----------

def test_the_motion_style_is_not_needed_for_the_direction_alone_but_is_for_the_whole_treatment():
    store, run = new_store(), film_run()
    assert send(store, alone(), run)['draft'] is True
    with pytest.raises(Problem, match='no motion style yet') as e:
        send(store, doc(), run)
    assert e.value.code == 'FILM_MOTION' and 'vw visuals page' in e.value.message


def test_the_page_asks_the_motion_style_first_with_every_style_and_the_reason():
    store, run = new_store(), film_run()
    send(store, alone(), run)
    p = PF.page(Conn(run), store, USER, run, [])
    m = p['lines'][0]
    assert [l['key'] for l in p['lines']] == ['motion', 'direction'] and m['line'] == 'l00' and m['state'] == 'open' and p['lines'][1]['line'] == 'l01'
    assert [b['choice'] for b in m['buttons']] == film.recommend_styles('documentary-explainer') and len(m['buttons']) == len(film.styles()) == 8
    assert m['buttons'][0]['label'] == 'Restrained' and 'Recommended: Restrained' in m['text'] and 'documentary' in m['text']
    assert len(m['rows']) == 8 and m['rows'][0][0] == 'Restrained (recommended)' and 'For documentaries' in m['rows'][0][1]
    assert [s['name'] for s in m['styles']] == [b['choice'] for b in m['buttons']]
    assert m['sample'] == {'title': 'Filler slab roofs', 'words': PARTS['idea'], 'frame': '16:9'}


def test_the_motion_style_can_be_asked_before_any_direction_is_written():
    store, run = new_store(), film_run()
    p = PF.page(Conn(run), store, USER, run, [])
    assert p['open'] is True and [l['key'] for l in p['lines']] == ['motion'] and 'Direction' in p['note'] and p['lines'][0]['sample']['words'] == 'Filler slab roofs'


def test_a_film_from_before_and_a_film_with_its_style_are_not_asked():
    store = new_store()
    send(store, alone())
    assert [l['key'] for l in PF.page(Conn(OLD_RUN), store, USER, OLD_RUN, [])['lines']] == ['direction']
    run = film_run(motion='lively')
    m = PF.page(Conn(run), store, USER, run, [])['lines'][0]
    assert m['key'] == 'motion' and m['state'] == 'recorded' and 'Lively' in m['title'] and not m.get('buttons')


def test_the_motion_style_and_the_direction_answered_in_one_visit_are_recorded_and_logged_with_the_operators_words():
    store, run = new_store(), film_run()
    send(store, alone(), run)
    conn = Conn(run)
    p = PF.page(conn, store, USER, run, [])
    r = PF.page_record(conn, store, USER, run, [], [ans(p['lines'][1], 'accept'), ans(p['lines'][0], 'lively')])
    assert r['recorded'] == ['motion', 'direction'] and film.motion(run) == 'lively' and run['film']['motion']['quote'] == 'Lively'
    assert 'write every gap line' in r['then'] and r['page']['lines'][0]['state'] == 'recorded'
    rows = {x['about']: x for x in conn.log}
    assert rows['line motion, choice lively']['by_kind'] == 'operator' and rows['line motion, choice lively']['quote'] == 'Lively'
    assert rows['line direction, choice accept']['quote'] == 'Accept' and all(x['stage'] == 'visuals' and x['kind'] == 'step' for x in conn.log)
    assert 'recorded motion, direction' in r['log']
    again = PF.page_record(conn, store, USER, run, [], [ans(p['lines'][0], 'bold')])
    assert again['stale'] == ['motion'] and film.motion(run) == 'lively'


def test_a_style_the_server_does_not_hold_is_refused_on_its_line_and_logged():
    store, run = new_store(), film_run()
    send(store, alone(), run)
    conn = Conn(run)
    p = PF.page(conn, store, USER, run, [])
    r = PF.page_record(conn, store, USER, run, [], [{**ans(p['lines'][0], 'zippy')}])
    assert r['refused'][0]['key'] == 'motion' and 'not a motion style' in r['refused'][0]['message'] and film.motion(run) is None
    assert conn.log[0]['kind'] == 'refusal' and 'zippy' in conn.log[0]['about']


def test_the_words_typed_on_the_page_are_the_logs_quote():
    store = new_store()
    send(store, alone())
    conn = Conn(OLD_RUN)
    PF.page_record(conn, store, USER, OLD_RUN, [], [ans(PF.page(conn, store, USER, OLD_RUN, [])['lines'][0], 'change', 'tell it from the family')])
    assert conn.log[0]['quote'] == 'tell it from the family' and conn.log[0]['about'] == 'line direction, choice change'


# ---------- point 1: the earlier Direction is shown whole ----------

def test_the_earlier_direction_is_shown_whole():
    before = 'By the end the viewer should understand one idea. ' * 12   # 600 characters: over the old 400 cut
    assert len(before) > 400
    (line,) = VS.direction_changes(before, None, {'direction_parts': PARTS})
    assert line == f'Before: "{before.strip()}"' and '…' not in line


# ---------- point 8: the log ----------

def test_a_drafts_log_line_says_what_it_returned():
    store = new_store()
    out = send(store, doc())
    assert '5 gaps' in out['log'] and '6 lines to accept' in out['log'] and 'warnings:' in out['log'] and 'reasons missing: 0' in out['log']
    e = runlog.entry_from('/api/runs/00000000-0000-0000-0000-000000000000/visuals/treatment', {'request_id': 'r'}, 200, out)
    assert e['entry'].startswith('visuals/treatment') and '5 gaps' in e['entry'] and e['kind'] == 'step'


# ---------- points 2 to 4: the served words ----------

def served():
    d = _core.for_footage(json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8')), 'own')
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    return next(p for p in st['parts'] if p['name'] == 'treatment')['text'], st['steps']


def test_the_served_words():
    t, steps = served()
    assert 'A still always moves slowly' not in t and 'A still moves slowly; one the viewer must read (a document, a page, a sign) is held steady, your call.' in t
    assert 'three to five beats' not in t and 'one beat for each turn in what the viewer learns' in t
    assert 'Write the Direction alone first' in t and 'Write no gap line before the Direction is accepted' in t and 'motion style' in t
    assert 'the Direction alone first' in steps[1]
