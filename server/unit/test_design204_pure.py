"""design/204 (SK, 15 Nov 2026): the treatment answered on a Claude artifact page. The server gives the page its lines as data (the Direction
alone first, then the gaps) from the same items the chat asks, and records the answers the operator gave on the page, in one call, through the
same decision functions. The server stays the record; the page is the form."""
from copy import deepcopy
from app import core as _core   # SK, 23 Nov 2026: v3.json is read as a film with footage is served it

from app import page_flow as CF, visuals_stage as VS
from test_design126_a_pure import USER, run, treat
from test_design203_pure import PARTS, SECOND, doc

R = run('gemini')


class NoConn:
    def execute(self, sql, *a, **k):
        assert sql.startswith('insert into vw2_log'), 'the treatment page needs the database only for its log lines (design/205)'


def page(store):
    return CF.page(NoConn(), store, USER, R, [])


def record(store, answers):
    return CF.page_record(NoConn(), store, USER, R, [], answers)


def ans(line, choice, notes=''):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes}


def lines_of(p, state=None):
    return [l for l in p['lines'] if state is None or l['state'] == state]


def test_the_page_shows_the_direction_alone_first():
    out, store = treat(doc())
    p = page(store)
    assert p['step'] == 'Treatment' and p['open'] is True and [l['key'] for l in lines_of(p, 'open')] == ['direction']
    d = p['lines'][0]
    assert d['line'] == 'l01' and d['title'] == 'The direction of the film' and dict(d['rows'])['The idea'] == PARTS['idea']
    assert [(b['choice'], b['needs_words']) for b in d['buttons']] == [('accept', False), ('change', True), ('different', False)]
    assert 'after the Direction' in p['note'] and p['round'] and isinstance(p['summary'], str)


def test_accepting_the_direction_on_the_page_records_it_and_brings_the_gaps():
    out, store = treat(doc())
    r = record(store, [ans(page(store)['lines'][0], 'accept')])
    assert r['recorded'] == ['direction'] and r['refused'] == [] and r['stale'] == []
    p = r['page']
    assert [l['state'] for l in p['lines']][0] == 'recorded' and len(lines_of(p, 'open')) == 5 and p['round'] != page.__name__
    gap = lines_of(p, 'open')[0]
    assert gap['title'].startswith('Gap ') and dict(gap['rows'])['Shot 1 · why it fits the words'] and [b['choice'] for b in gap['buttons']] == ['accept', 'change']


def test_every_gap_accepted_records_the_whole_treatment_and_the_page_says_so():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    r = record(store, [ans(l, 'accept') for l in lines_of(page(store), 'open')])
    assert len(r['recorded']) == 5 and r['page']['open'] is False and 'recorded' in r['page']['note']
    assert VS.session_of(store, R, []).get('treatment') and all(l['state'] == 'recorded' and not l.get('reopen') for l in r['page']['lines'])


def test_change_this_sends_the_line_back_with_the_operators_words_and_it_returns_changed_as_asked():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    gap = lines_of(page(store), 'open')[2]
    r = record(store, [ans(gap, 'change', 'show a person at the wall')])
    back = next(l for l in r['page']['lines'] if l['key'] == gap['key'])
    assert r['recorded'] == [gap['key']] and back['state'] == 'with_assistant' and back['note'] == 'show a person at the wall'
    again = doc()
    again['gaps'][2]['picture'] = 'a mason points at the cavity'
    VS.treatment(store, USER, R, [], again, '')
    now = next(l for l in page(store)['lines'] if l['key'] == gap['key'])
    assert now['state'] == 'open' and now['asked'] is True and any('a mason points at the cavity' in c for c in now['changes'])


def test_change_without_words_is_refused_on_that_line_and_the_others_are_recorded():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    a, b = lines_of(page(store), 'open')[:2]
    r = record(store, [ans(a, 'change', '  '), ans(b, 'accept')])
    assert r['recorded'] == [b['key']] and r['refused'][0]['key'] == a['key'] and 'what' in r['refused'][0]['message'].lower()
    assert next(l for l in r['page']['lines'] if l['key'] == a['key'])['refused'] == r['refused'][0]['message']


def test_an_answer_to_an_older_text_of_a_line_is_ignored():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    old = lines_of(page(store), 'open')[2]
    again = doc()
    again['gaps'][2]['picture'] = 'a mason points at the cavity'
    VS.treatment(store, USER, R, [], again, '')
    r = record(store, [ans(old, 'accept')])
    assert r['recorded'] == [] and r['stale'] == [old['key']] and next(l for l in r['page']['lines'] if l['key'] == old['key'])['state'] == 'open'


def test_a_different_direction_is_asked_from_the_page_and_the_second_is_taken_there():
    out, store = treat(doc())
    r = record(store, [ans(page(store)['lines'][0], 'different')])
    assert r['recorded'] == ['direction'] and 'second Direction' in r['tell'] and r['page']['lines'][0]['state'] == 'with_assistant'
    VS.treatment(store, USER, R, [], doc(direction_alternative=SECOND), '')
    d = page(store)['lines'][0]
    assert [b['choice'] for b in d['buttons']] == ['accept', 'accept_second', 'change', 'different'] and dict(d['rows'])['Second · Whose story'] == SECOND['viewpoint']
    r = record(store, [ans(d, 'accept_second')])
    assert VS.session_of(store, R, [])['treatment_draft']['direction_parts']['viewpoint'] == SECOND['viewpoint']
    assert all(l['state'] == 'with_assistant' for l in r['page']['lines'] if l['key'] != 'direction')


def test_a_direction_not_accepted_drops_the_gap_answers_sent_with_it():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    gaps = lines_of(page(store), 'open')
    d = next(l for l in page(store)['lines'] if l['key'] == 'direction')
    r = record(store, [ans(gaps[0], 'accept'), {**ans(d, 'reopen', 'tell it from the family')}])
    assert r['recorded'] == ['direction'] and r['dropped'] == [gaps[0]['key']]
    assert VS.session_of(store, R, [])['treatment_draft']['lines'][gaps[0]['key']]['state'] == 'to_accept'


def test_a_recorded_line_can_be_reopened_with_words_while_the_treatment_is_still_a_draft():
    out, store = treat(doc())
    record(store, [ans(page(store)['lines'][0], 'accept')])
    gap = lines_of(page(store), 'open')[0]
    r = record(store, [ans(gap, 'accept')])
    done = next(l for l in r['page']['lines'] if l['key'] == gap['key'])
    assert done['state'] == 'recorded' and done['reopen'] is True
    r = record(store, [ans(done, 'reopen', '')])
    assert r['refused'] and 'words' in r['refused'][0]['message'] and next(l for l in r['page']['lines'] if l['key'] == gap['key'])['state'] == 'recorded'
    r = record(store, [ans(done, 'reopen', 'on second thoughts, wider')])
    assert next(l for l in r['page']['lines'] if l['key'] == gap['key'])['state'] == 'with_assistant'
    assert record(store, [ans(done, 'reopen', 'again')])['stale'] == [gap['key']]   # it is already back with the assistant


def test_a_choice_that_is_not_one_of_the_lines_buttons_is_refused():
    out, store = treat(doc())
    r = record(store, [ans(page(store)['lines'][0], 'delete everything')])
    assert r['recorded'] == [] and 'Not an answer' in r['refused'][0]['message']


def test_no_answers_records_nothing_and_says_how_many_are_open():
    out, store = treat(doc())
    r = record(store, [])
    assert r['recorded'] == [] and r['open'] == 1 and 'Nothing was answered' in r['then']


def test_with_no_draft_the_page_has_nothing_to_decide():
    out, store = treat(doc())
    s = VS.session_of(store, R, [])
    s.pop('treatment_draft')
    VS.save_session(store, R, s)
    p = page(store)
    assert p['open'] is False and p['lines'] == [] and 'No treatment' in p['note']


def test_an_older_paragraph_direction_is_shown_as_text():
    from test_design126_a_pure import vw12
    from test_design202_pure import reasoned
    out, store = treat(reasoned(vw12()))
    d = page(store)['lines'][0]
    assert d['rows'] == [] and 'a documentary explainer told from the site' in d['text']


def test_the_step_lines_name_the_page_and_do_not_send_the_assistant_to_the_notes_file():
    import json
    from pathlib import Path
    steps = next(s for s in _core.for_footage(json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8')), 'own')['stages'] if s['name'] == 'visuals')['steps']
    assert 'intended-visuals' not in steps[0] and 'read prompt.md and gaps.json;' in steps[0]
    assert '`vw visuals page --record`' in steps[1] and '--send-back' not in steps[1] and 'the card where it cannot be shown' in steps[1]
