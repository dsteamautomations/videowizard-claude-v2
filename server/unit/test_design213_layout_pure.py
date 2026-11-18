"""design/213 (17 Nov 2026): step 2 of the references ("the sets") in its new layout, and the step-1 additions. The server decides, for the
page and the chat alike: the four groups and their order, the case of each line, its buttons (each with what it will do) and every sentence;
every answer the server took before is still reachable; no cost is named, and a limit with no room is said in one sentence with no
amount. VW-24's stored round (its shapes, `vw24_step2_shapes.json`) is drawn in the new layout as it is, its made sets with their three
pictures. A person whose kept footage picture shows the face is asked for the permission only. An older round is untouched (pinned in
test_design211c_lines_pure and test_design211_together_pure). Without a database."""
import json
import os
import re
from pathlib import Path

import pytest

from app import chat_flow as CF, page_flow as P, ref_sets, visuals_stage as VS
import d211_fixture as F
from test_design211c_kit_pure import Film, RUN, ans, labels, older_step1

W = CF.WORDS
G = CF.STEP2_GROUPS
MONEY = re.compile(r'₹|\bpaid\b|\bfree\b|\bprice|\bcost\b', re.I)


def read(x):
    if isinstance(x, dict):
        return ' '.join(read(v) for k, v in x.items() if k not in ('how', 'capabilities', 'pictures', 'then'))
    if isinstance(x, (list, tuple)):
        return ' '.join(read(v) for v in x)
    return x if isinstance(x, str) else ''


def acts(line):
    return [b['act'] for b in line['buttons']]


def btn(line, act):
    return next(b for b in line['buttons'] if b['act'] == act)


def chat(film, key):
    return next(i for i in film.items() if i['_key'] == key)


# ---------- the groups, the order, the cases ----------

def test_the_four_groups_in_order_and_the_layout_of_step_2(monkeypatch):
    film = Film(monkeypatch, '2')
    p = film.page()
    assert G == ['To judge', 'Could not be made', 'Waiting to be made', 'Settled']
    assert p['layout'] == {'kind': 'sets', 'made': 'Nothing is made until you say done in the chat.', 'help': [p['note'], W['help_set'], W['help_rest']], 'groups': G, 'pick': W['pick'], 'words': P.page_words()}
    assert [(l['key'], l.get('group'), l.get('case')) for l in p['lines']] == [
        ('sets:rest', None, None), ('set:T_LAY', G[0], 'judge'), ('set:MASON', G[0], 'judge'), ('set:STREET', G[0], 'judge'),   # the set Claude would make again first
        ('set:BRICK', G[2], 'wait'), ('set:TILE', G[2], 'wait'), ('set:TROWEL', G[3], 'settled')]
    lines = film.lines()
    for l in p['lines'][1:]:
        assert l['name'] and l['kind'] and l['tag'] and 'text' not in l and 'comment' not in l and 'notes' not in l, l['key']
    assert lines['set:T_LAY']['tag'] == 'Make again' and lines['set:MASON']['tag'] == 'Use it' and lines['set:BRICK']['tag'] == 'Waiting' and lines['set:TROWEL']['tag'] == 'Settled'
    assert lines['set:TROWEL']['head'] == W['settled_footage'] and 'buttons' not in lines['set:TROWEL'] and 'buttons' not in lines['set:BRICK']
    assert lines['set:BRICK']['head'] == W['wait_head'] and lines['set:BRICK']['wait_note'] == 'If not made, 2 shots would have no reference of it.' and lines['set:BRICK']['out'] is True
    assert 'Doubtful' not in read(p) and not MONEY.search(read(p)) and 'limit' not in read(p)
    assert [i['_key'] for i in film.items(every=False)] == ['set:T_LAY', 'set:MASON', 'set:STREET', 'sets:rest']   # the chat: the same order, the other sets asked last


def vw24(monkeypatch):
    """A film whose round stands where VW-24's stood on 17 Nov 2026: two sets made (a person; a place made from three footage pictures),
    one not made, 17 that wait for the second go (6 of them people), 14 settled from their footage."""
    things = json.loads((Path(__file__).parent / 'vw24_step2_shapes.json').read_text(encoding='utf-8'))['things']
    plan = F.plan()
    plan['elements'] = [{'id': t['id'], 'name': 'Thing ' + t['id'].title(), 'kind': t['kind'], 'identity': 'representative', 'requirements': '', 'required_views': [], 'size': [],
                         'description': 'What it looks like.'} for t in things]
    plan['gaps'] = [{'gap_id': 'BEAT_11-B1', 'scenes': [{'id': 'B-S1', 'location_time': 'the yard, morning', 'outfit': {}, 'shots': [F._shot(f"B-S1-SH{t['id']}", 'image', 'MS', [t['id']]) for t in things]}]}]
    s = F.session('2')
    refs, rows, inputs = {}, {}, {}
    look = {'who': 'helper', 'at': F.NOW, 'view': 'whole', 'verdict': 'pass', 'seen': 'Seen.'}
    for t in things:
        eid = t['id']
        rows[eid] = {'frames': [], 'keywords': '', 'verdict': 'approve', 'search_id': None, 'error': None, 'prompt': '', 'corrections': [], 'set': None, 'round': 0, 'rec': 'set', 'reason': 'Why.',
                     'doubt': False, 'first': False, 'operator_words': [], 'history': []}
        frames = [f'f-{eid}-{n}' for n in range(t['compare'] if t['case'] == 'judge' else t['pictures'] if t['case'] == 'settled' else 0)]
        for fid in frames:
            refs[fid] = {'id': fid, 'element_id': eid, 'kind': 'frame', 'status': 'approved', 'key': f"{RUN['id']}/visuals/references/{fid}.png", 'sha256': 'a' * 64, 'view': 'whole', 'look': dict(look), 'weak': False}
        rows[eid]['frames'] = frames
        if t['case'] == 'settled':
            rows[eid]['from_footage'] = True
        elif t['case'] == 'judge':
            F.VIEWS.setdefault(eid, ['the whole place', 'from the other side', 'its fixed things'])
            sid, new = F._set(eid, t['kind'], failed=(('the view', 'Not the view asked.'),))
            refs.update(new)
            rows[eid].update(set=sid, round=1, made={'at': F.NOW, 'specs': {}, 'photo': None, 'fp': 'fp'}, set_look={'who': 'helper', 'at': F.NOW, 'set': sid, 'recommend': t['rec'], 'golden': None, 'reason': 'Why.'})
            inputs[eid] = [{'ref': f, 'role': 'footage', 'view': 'whole'} for f in frames]
        elif t['case'] == 'notmade':
            rows[eid]['error'] = "ROOM: its set was not made: the request places something at 'middle'."
    s['references'], s['drawings'], s['golden'] = refs, {}, {}
    s['round'].update(elements=rows, rest=[t['id'] for t in things if t['case'] == 'wait'], **{'pass': 2})
    s.pop('found')
    film = Film(monkeypatch, state='2', session=s, plan=plan)
    film.inputs = inputs
    film.fails['ROOM'] = {'cause': 'other', 'model': None, 'text': "The request places something at 'middle' with no landmark."}
    return film, things


def test_vw24s_stored_round_shows_in_the_new_layout_as_it_is(monkeypatch):
    film, things = vw24(monkeypatch)
    before = json.loads(json.dumps(film.session()))
    p = film.page()
    rest, lines = p['lines'][0], p['lines'][1:]
    assert rest['key'] == 'sets:rest' and len(p['lines']) == 35                                                   # as the live server gave it: 35 lines
    assert [len([l for l in lines if l['group'] == g]) for g in G] == [2, 1, 17, 14]
    assert [G.index(l['group']) for l in lines] == sorted(G.index(l['group']) for l in lines)
    by = {l['key'][4:]: l for l in lines}
    assert [l['key'] for l in lines[:3]] == ['set:MASON', 'set:SITE_DECK', 'set:ROOM']
    mason, deck, room = by['MASON'], by['SITE_DECK'], by['ROOM']
    assert len([x for x in mason['pics'] if not x.get('ref_only')]) == 3 and 'pick' not in mason and mason['rule'] == W['rule_person']      # its made set keeps its three pictures
    assert [x.get('ref_only', False) for x in deck['pics']] == [True] * 3 + [False] * 3 and deck['pick'] is True
    assert [x['letter'] for x in deck['pics'][3:]] == ['A', 'B', 'C'] and all(x['choice'].startswith('use:') and x['say'] == W['say_use'].format(letter=x['letter']) for x in deck['pics'][3:])
    assert acts(mason) == ['again', 'approve', 'fix'] and btn(mason, 'again')['sug'] is True and [b['choice'] for b in mason['buttons']] == ['no', 'yes', 'correct']
    assert acts(deck) == ['again', 'approve', 'fix'] and btn(deck, 'approve')['choice'] == 'use' and deck['rec']['label'] == 'Make it again'
    assert deck['check']['state'] == 'fail' and deck['check']['chip'] == "Claude's check found 1 fault" and deck['pics'][4].get('flag') is True
    assert room['case'] == 'notmade' and room['head'] == 'This set could not be made.' and room['why'].startswith('The request places') and acts(room) == ['make', 'leave']
    assert rest['head'] == '17 more sets wait for your word' and rest['show'] == 'Show the 17' and len(rest['covers']) == 17 and labels(rest) == ['Make them', 'Do not make these sets']
    assert rest['buttons'][0]['big'] == 'Make the other 17' and rest['buttons'][0]['say'] == 'The other 17 sets will be made.'
    loss = rest['buttons'][1]['loss']
    assert len(loss['rows']) == 11 and loss['head'] == 'Without these 11 sets' and loss['button'] == 'Do not make these 11 sets; make the other 6' == chat(film, 'sets:rest')['buttons'][1]['label'] and loss['people'].startswith('The 6 people always get a set: ') \
        and loss['people'].endswith('Not making the others also has their 6 sets made, on the same word, when you say done in the chat.')
    assert rest['buttons'][1]['say'] == '6 sets will be made. 11 are not made.' and 'waits' not in rest
    assert len([l for l in lines if l.get('wait_note') == W['wait_person']]) == 6 and len([l for l in lines if l.get('out')]) == 11
    assert all(l['case'] == 'settled' and l['pics'] and l['head'] == W['settled_footage'] for l in lines if l['group'] == G[3])
    assert film.session() == before                                                                              # showing it stores nothing: no re-post is needed
    assert not MONEY.search(read(p)) and len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) < P.ROUND_BYTES
    assert p['summary'] == '34 things: 3 to answer, 0 kept, 17 not ready yet, 14 recorded.'


# ---------- every answer the server takes is reachable, on both front ends ----------

def test_a_persons_set_approve_corrections_and_make_again(monkeypatch):
    film = Film(monkeypatch, '2')
    m = film.lines()['set:MASON']
    assert [(b['label'], b['choice'], b['act'], b['needs_words']) for b in m['buttons']] == [('Approve', 'yes', 'approve', False), ('Minor corrections', 'correct', 'fix', True), ('Make again', 'no', 'again', False)]
    assert btn(m, 'approve')['sug'] is True and btn(m, 'approve')['say'] == W['say_yes'] and btn(m, 'again')['ask'] == W['again_ask'] and '{words}' in btn(m, 'fix')['say']
    assert m['own']['label'] == 'Upload my own' and m['own']['say'] == W['say_own_person'] and m['rec'] == {'do': 'use', 'label': 'Use this set', 'reason': 'All three agree with the plan.'}
    item = chat(film, 'set:MASON')
    assert [(b['label'], b['choice']) for b in item['buttons']] == [('Approve', 'yes'), ('Minor corrections', 'correct'), ('Make again', 'no'), ('Correct every picture of it', 'correct_all')] and item['question'].endswith('is this set right for this person?')
    out = film.record(ans(m, 'correct', 'His shirt is blue.'))
    assert out['refused'] == [] and {k: film.session()['round']['elements']['MASON']['answer'][k] for k in ('verdict', 'golden', 'words')} == {'verdict': 'correct', 'golden': None, 'words': 'His shirt is blue.'}
    assert film.record(ans(m, 'correct'))['refused'][0]['key'] == 'set:MASON'                                      # corrections need the operator's words


def test_a_things_set_approve_takes_the_picture_chosen(monkeypatch):
    film = Film(monkeypatch, '2')
    s = film.lines()['set:STREET']
    made = [x for x in s['pics'] if not x.get('ref_only')]
    assert s['pick'] is True and btn(s, 'approve')['choice'] == 'use' and [x['choice'] for x in made] == ['use:s-street-1', 'use:s-street-1-2', 'use:s-street-1-3']
    assert made[1]['say'] == 'Approve: picture B is the reference; pictures of this thing start from it.' and 'every shot' not in read(s)
    assert [(b['label'], b['choice']) for b in chat(film, 'set:STREET')['buttons']] == [('Approve A', 'use:s-street-1'), ('Approve B', 'use:s-street-1-2'), ('Approve C', 'use:s-street-1-3'), ('Minor corrections', 'correct')]
    assert film.record(ans(s, 'use:s-street-1-2'))['refused'] == [] and film.session()['round']['elements']['STREET']['answer']['golden'] == 's-street-1-2'
    assert film.record(ans(s, 'use'))['refused'][0]['key'] == 'set:STREET'                                         # "Approve" alone is no answer: the page sends the picture chosen
    assert s['own']['say'] == W['say_own'] and 'pictures of this thing start from it' in s['own']['text']


def test_a_set_made_the_most_times_offers_no_remake_and_a_thing_may_be_left_out(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: [s['round']['elements'][e].update(round=3) for e in ('MASON', 'STREET')])
    m, s = film.lines()['set:MASON'], film.lines()['set:STREET']
    assert acts(m) == ['approve'] and m['most'] == 'This set was made 3 times, which is the most: use it, or add your own picture.' and m['made_n'] == 'made 3 times'
    assert acts(s) == ['approve', 'leave'] and s['most'] == 'This set was made 3 times, which is the most: use one of these pictures, add your own, or go on without a reference.'
    assert s['loss'] == {'text': 'This 1 shot is then made with no reference of it:', 'shots': s['loss']['shots']} and len(s['loss']['shots']) == 1
    assert btn(s, 'leave')['say'] == 'Go on without a reference. 1 shot will be made with no reference of it.' and s['most'] in chat(film, 'set:STREET')['text']
    film.change(lambda x: x['round']['elements']['STREET'].update(round=2))
    assert film.lines()['set:STREET']['made_n'] == 'made twice'


def test_the_plan_changed_a_partial_set_and_a_set_made_again(monkeypatch):
    film = Film(monkeypatch, '2')
    film.changed.add('STREET')
    s = film.lines()['set:STREET']
    assert btn(s, 'remake')['label'] == 'Make it again from the changed plan' and s['changed'] == W['set_changed']
    film.record(ans(s, 'remake'))
    assert film.called('set_make') == [('STREET', 'Make it again from the changed plan')]

    def cut(x):
        x['references'].pop('s-street-1-3')
    film.change(cut)
    s = film.lines()['set:STREET']
    assert s['partial'] == '2 of 3 pictures came back; missing: its fixed things.' and len(s['pics']) == 2                                 # shown as it is
    film = Film(monkeypatch, 'complete')
    film.state = 2
    film.change(lambda x: [r.update(status='candidate') for r in x['references'].values() if r.get('set') == 's-t_lay-2'] and x['round']['elements']['T_LAY'].update(verdict='approve'))
    t = film.lines()['set:T_LAY']
    assert t['asked'] == 'Made again as you asked: "Show the hand pressing the brick down."' and len(t['earlier']) == 3 and t['made_n'] == 'made twice'
    assert t['asked'] in chat(film, 'set:T_LAY')['text']


def test_a_doubt_reads_look_closely_and_the_models_notes_are_two_plain_lines(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['round']['elements']['STREET']['set_look'].update(recommend='doubt'))
    real = film.set_facts
    monkeypatch.setattr(ref_sets, 'set_facts', lambda *a: {**real(*a), 'model': {'chose': 'the bamboo scaffold of the photographs', 'aside': 'the wooden scaffold the request named'}, 'footage': []})
    s = film.lines()['set:STREET']
    assert s['rec']['label'] == 'Look closely' and s['tag'] == 'Look closely' and not any(b.get('sug') for b in s['buttons'])
    assert s['look'] == {'chose': 'the bamboo scaffold of the photographs', 'aside': 'the wooden scaffold the request named'}
    page, said = json.dumps(film.page()), chat(film, 'set:STREET')['text']
    assert 'One method, the most common' not in page and 'One method, the most common' not in said                                         # the raw notes stay in the record
    assert 'The image model chose: the bamboo scaffold of the photographs' in said and 'It set aside: the wooden scaffold the request named' in said
    assert ['What the image model did', ['The image model chose: the bamboo scaffold of the photographs', 'It set aside: the wooden scaffold the request named']] in s['details']


def test_a_set_of_one_picture_has_no_choice_of_a_b_c(monkeypatch):
    film = Film(monkeypatch, '2')

    def one(s):
        for rid in ('s-street-1-2', 's-street-1-3'):
            s['references'].pop(rid)
    film.change(one)
    real = film.set_facts
    monkeypatch.setattr(ref_sets, 'set_facts', lambda *a: {**real(*a), 'partial': None})
    s = film.lines()['set:STREET']
    made = [x for x in s['pics'] if not x.get('ref_only')]
    assert len(made) == 1 and 'choice' not in made[0] and made[0]['letter'] == '' and made[0]['label'] == 'the whole place' and 'pick' not in s
    assert btn(s, 'approve')['choice'] == 'use:s-street-1' and btn(s, 'approve')['say'] == W['say_use_one'] and s['rec']['label'] == 'Use this picture' and s['ask'] == W['ask_one_set']
    assert [(b['label'], b['choice']) for b in chat(film, 'set:STREET')['buttons']][0] == ('Approve', 'use:s-street-1')
    assert film.record(ans(s, 'use:s-street-1'))['refused'] == []


def test_a_set_not_made_a_refused_photo_and_a_thing_back(monkeypatch):
    film = Film(monkeypatch, '2')
    film.fails['STREET'] = {'cause': 'refused', 'model': 'm', 'text': 'Google refused the request.'}
    film.change(lambda s: [r.update(status='failed') for r in s['references'].values() if r.get('set') == 's-street-1'])
    s = film.lines()['set:STREET']
    assert (s['group'], s['case'], s['head'], s['why']) == (G[1], 'notmade', 'This set could not be made.', 'Google refused the request.')
    assert [(b['label'], b['choice'], b['act']) for b in s['buttons']] == [('Make it', 'make', 'make'), ('Go on without a reference', 'aside', 'leave')] and s['own']['label'] == 'Upload my own'
    assert ['Why it could not be made', 'Google refused the request.'] in s['details']
    film.record(ans(s, 'make'))
    assert film.called('set_make') == [('STREET', 'Make it')]
    monkeypatch.setattr(VS, '_set_state', lambda session, plan, step, eid, row, budget: {'next': 'Give another photo.'} if eid == 'STREET' else {})
    s = film.lines()['set:STREET']
    assert s['case'] == 'photo' and s['head'] == W['photo_refused'] and [(b['label'], b['choice'], b['needs_words']) for b in s['buttons']] == [('Another photo', 'photo', False), ('A stand-in', 'standin', True)]
    assert btn(s, 'standin')['hint'] == W['standin_hint']
    monkeypatch.undo()
    film = Film(monkeypatch, '2')
    film.change(lambda x: x['round']['elements']['FAN'].update(reopened='new', ignored=False))
    f = film.lines()['set:FAN']
    assert (f['group'], f['case'], f['head']) == (G[0], 'back', W['reopen_new']) and [(b['label'], b['choice'], b['act']) for b in f['buttons']] == [
        ('Make a set', 'approve', 'set'), ('Add words for the picture', 'words', 'fix'), ('No reference needed', 'ignore', 'leave')]
    film.record(ans(f, 'words', 'The blades are brown.'))
    assert film.called('round_reopen') == [('FAN', 'approve', 'The blades are brown.', 'Add words for the picture')]


def test_the_waiting_sets_make_them_and_leave_some_out(monkeypatch):
    film = Film(monkeypatch, '2')
    aside = []
    monkeypatch.setattr(VS, 'set_aside', lambda store, user, run, outputs, eid, words='', back=False: aside.append(eid) or {'element_id': eid})
    rest = film.lines()['sets:rest']
    assert [(b['label'], b['choice']) for b in rest['buttons']] == [('Make them', 'rest'), ('Do not make these sets', 'rest_out')] and rest['why'] == W['rest_why']
    assert rest['buttons'][1]['say'] == '2 are not made. No other set waits.' and len(rest['buttons'][1]['loss']['rows']) == 2
    item = chat(film, 'sets:rest')
    assert [(b['label'], b['choice']) for b in item['buttons']] == [('Make the other 2 sets', 'rest'), ('Do not make these 2 sets', 'rest_out')]
    assert rest['buttons'][1]['loss']['button'] == 'Do not make these 2 sets'                                              # no person waits: the same words on the page and in the chat
    film.record(ans(rest, 'rest'))
    assert len(film.called('round_rest')) == 1 and not aside
    out = film.record(ans(rest, 'rest_out'))                                                                       # the server refuses it while a first set is unjudged: the page is not the only door
    assert out['refused'][0]['message'] == W['rest_first'] and not aside
    lines = film.lines()
    out = film.record(ans(rest, 'rest_out'), ans(lines['set:MASON'], 'yes'), ans(lines['set:STREET'], 'use:s-street-1'), ans(lines['set:T_LAY'], 'no'))   # judged in the same visit: taken after them
    assert out['refused'] == [] and aside == ['BRICK', 'TILE'] and len(film.called('round_rest')) == 1              # no person waits: nothing more is ordered


def test_leave_some_out_makes_the_people_who_always_get_a_set_on_the_same_word(monkeypatch):
    film, _ = vw24(monkeypatch)
    aside = []
    monkeypatch.setattr(VS, 'set_aside', lambda store, user, run, outputs, eid, words='', back=False: aside.append(eid) or {'element_id': eid})
    assert chat(film, 'sets:rest')['buttons'][1]['label'] == 'Do not make these 11 sets; make the other 6'
    lines = film.lines()
    judged = [ans(lines['set:MASON'], 'yes'), ans(lines['set:SITE_DECK'], next(x['choice'] for x in lines['set:SITE_DECK']['pics'] if x.get('choice')))]
    monkeypatch.setattr(VS, '_set_budget', lambda run, s, spend: (F.CAP, F.CAP, F.SET_PRICE))                      # the limit has no room for the people's sets
    out = film.record(ans(lines['sets:rest'], 'rest_out'), *judged)
    assert out['refused'][0]['message'] == ref_sets.LIMIT_PLAIN and not aside and not film.called('round_rest')    # all or nothing: nothing is left out when the others cannot be made
    monkeypatch.setattr(VS, '_set_budget', lambda run, s, spend: (F.SPENT, F.CAP, F.SET_PRICE))
    out = film.record(ans(film.lines()['sets:rest'], 'rest_out'))
    assert out['refused'] == [] and len(aside) == 11 and len(film.called('round_rest')) == 1

# ---------- the limit, with no amount ----------

def test_a_limit_with_no_room_is_said_in_one_sentence_with_no_amount(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: [r.update(status='failed') for r in s['references'].values() if r.get('set') == 's-street-1'])
    film.cause = {'element_id': 'STREET', 'kind': 'cap', 'text': 'the spend cap is reached: ₹3,740 spent of ₹3,754'}
    s = film.lines()['set:STREET']
    assert s['head'] == ref_sets.LIMIT_PLAIN == 'These cannot be made now: the film has reached the limit its owner set. Ask the owner to raise it.' and 'why' not in s
    assert '₹' not in read(film.page()) and ref_sets.LIMIT_PLAIN in chat(film, 'set:STREET')['text'] and '₹' not in chat(film, 'set:STREET')['text']

    def full(*a, **k):
        raise ValueError(ref_sets.LIMIT_PLAIN)
    monkeypatch.setattr(ref_sets, 'round_rest', full)
    out = film.record(ans(film.lines()['sets:rest'], 'rest'))
    assert out['refused'][0]['message'] == ref_sets.LIMIT_PLAIN and film.lines()['sets:rest']['refused'] == ref_sets.LIMIT_PLAIN       # heard on the line, not silence
    with pytest.raises(ValueError, match='reached the limit its owner set'):
        chat(film, 'sets:rest')['_run']('rest', 'Make them', '')


# ---------- the plan against the footage, said openly ----------

def test_the_writers_words_are_shown_openly_where_the_thing_has_footage_pictures(monkeypatch):
    film = Film(monkeypatch, '1')
    film.change(lambda s: s['round']['elements']['TROWEL'].update(prompt='The footage shows it on the ground; the plan has it on a roof: take the look from the footage, the place from the plan.'))
    t = film.lines()['ref:TROWEL']
    assert t['differs'] == 'Claude added for the picture: The footage shows it on the ground; the plan has it on a roof: take the look from the footage, the place from the plan.'
    assert t['differs'] in chat(film, 'ref:TROWEL')['text'] and 'differs' not in film.lines()['ref:MASON']
    film, _ = vw24(monkeypatch)
    film.change(lambda s: s['round']['elements']['SITE_DECK'].update(prompt='On a roof, not on the ground.'))
    assert film.lines()['set:SITE_DECK']['differs'] == 'Claude added for the picture: On a roof, not on the ground.' and 'differs' not in film.lines()['set:MASON']


# ---------- a person the footage shows: the permission only ----------

def person_film(monkeypatch, face=True, child=False):
    film = Film(monkeypatch, '1')
    said = []
    monkeypatch.setattr(VS, 'likeness', lambda store, user, run, outputs, eid, quote, conn=None, stand_in=False: said.append((eid, quote, stand_in)))

    def shown(s):
        look = {'who': 'helper', 'at': F.NOW, 'view': 'the face', 'verdict': 'pass', 'seen': 'His face, close.', 'face': face, **({'child': True} if child else {})}
        s['references']['f-mason-face'] = {'id': 'f-mason-face', 'element_id': 'MASON', 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/f-mason-face.png", 'sha256': 'b' * 64,
                                           'view': 'the face', 'look': look, 'weak': False}
        s['round']['elements']['MASON']['frames'] = ['f-mason-face']
    film.change(shown)
    return film, said


def test_a_person_whose_footage_shows_the_face_is_asked_for_the_permission_only(monkeypatch):
    film, said = person_film(monkeypatch)
    m = film.lines()['ref:MASON']
    assert m['case'] == 'likeness' and m['group'] == CF.STEP1_GROUPS[1] and m['likeness'] == {'ask': 'Your footage shows this person. Do you have their permission to make pictures of them?'}
    assert [(b['label'], b['choice'], b['needs_words']) for b in m['buttons']] == [('I have their permission', 'permit', True), ('Make a stand-in', 'standin', False)]
    assert m['buttons'][0]['hint'] == W['permit_hint'] and m['buttons'][1]['say'] == 'Make a stand-in: the set is made from the description. The made person will differ from the person in your clips.'
    assert 'will not resemble' not in read(m) and m['likeness']['ask'].endswith(m['ask']) and m['own']['label'] == 'Upload my own'
    item = chat(film, 'ref:MASON')
    assert [(b['label'], b['choice']) for b in item['buttons']] == [('I have their permission', 'permit'), ('Make a stand-in', 'standin')] and m['likeness']['ask'] in item['question'] + item['text']
    assert film.record(ans(m, 'permit'))['refused'][0]['key'] == 'ref:MASON' and not said                           # their own words are required
    assert film.record(ans(m, 'permit', 'He agreed on site, on camera.'))['refused'] == []
    assert said == [('MASON', 'He agreed on site, on camera.', False)]
    kept = film.session()['chat_round']['MASON']
    assert kept['verdict'] == 'approve' and kept['pics'] == {}                                                     # the kept frames go to the set


def test_the_permission_covers_only_the_ticked_pictures(monkeypatch):
    """The review of design/213: three kept frames (the face; a weak one that starts unticked; a side one the operator unticked): one goes to the set."""
    film, said = person_film(monkeypatch)

    def more(s):
        for fid, verdict in (('f-mason-weak', 'weak'), ('f-mason-side', 'pass')):
            s['references'][fid] = {**s['references']['f-mason-face'], 'id': fid, 'key': f"{RUN['id']}/visuals/references/{fid}.png", 'weak': verdict == 'weak',
                                    'look': {**s['references']['f-mason-face']['look'], 'verdict': verdict, 'face': False}}
        s['round']['elements']['MASON']['frames'] = ['f-mason-face', 'f-mason-weak', 'f-mason-side']
    film.change(more)
    m = film.lines()['ref:MASON']
    assert [bool(x.get('on')) for x in m['pics']] == [True, False, True] and m['tick'] == {'permit': W['tick_set']} and '{pictures}' in m['buttons'][0]['say']
    out = film.record(ans(m, 'permit', 'He agreed.', pics={'f-mason-side': 'not', 'f-mason-face': 'off', 'f-mason-weak': 'off'}))
    assert out['refused'][0]['message'] == W['tick_set'] and not said                                              # no picture ticked: nothing to make the set from, nothing recorded
    assert film.record(ans(m, 'permit', 'He agreed.', pics={'f-mason-side': 'not'}))['refused'] == []
    assert said == [('MASON', 'He agreed.', False)] and film.called('not_this') == [('MASON', 'f-mason-side', 'I have their permission')]
    kept = film.session()['chat_round']['MASON']
    assert kept['verdict'] == 'approve' and kept['words'] == '' and kept['pics'] == {'f-mason-side': 'not', 'f-mason-weak': 'off'}   # only the face frame feeds the likeness
    assert kept['quote'] == 'I have their permission'


def test_a_stand_in_uses_nothing_of_the_footage_person(monkeypatch):
    film, said = person_film(monkeypatch)
    assert film.record(ans(film.lines()['ref:MASON'], 'standin'))['refused'] == []
    assert said == [('MASON', 'Make a stand-in', True)]
    kept = film.session()['chat_round']['MASON']
    assert kept['verdict'] == 'approve' and kept['pics'] == {'f-mason-face': 'off'}


def test_a_child_asks_for_a_parent_or_guardian_and_hands_alone_ask_nothing(monkeypatch):
    film, _ = person_film(monkeypatch, child=True)
    assert film.lines()['ref:MASON']['likeness']['ask'] == 'Your footage shows this person, a child. Do you have the permission of a parent or guardian to make pictures of them?'
    film, _ = person_film(monkeypatch, face=False)
    m = film.lines()['ref:MASON']
    assert m['case'] == 'footage' and 'likeness' not in m and 'permit' not in [b['choice'] for b in m['buttons']]


# ---------- no cost; an older round ----------

@pytest.mark.parametrize('state', ['2', 'making', 'looking', 'rewrite', 'complete'])
def test_no_cost_is_named_at_step_2_on_the_page_or_in_the_chat(monkeypatch, state):
    film = Film(monkeypatch, state)
    page = film.page()
    said = read({k: v for k, v in page.items() if k in ('lines', 'summary', 'note', 'layout')}) + read([{k: v for k, v in i.items() if not k.startswith('_')} for i in film.items()])
    assert not MONEY.search(said), MONEY.search(said)
    assert 'every shot of this' not in said


def test_an_older_round_has_no_layout_and_its_lines_of_before(monkeypatch):
    film = Film(monkeypatch, '2', session=F.older_session())
    p = film.page()
    assert 'layout' not in p and not any('case' in l or 'act' in json.dumps(l.get('buttons') or []) for l in p['lines'])
    film = Film(monkeypatch, '1', session=older_step1())
    assert 'layout' not in film.page()


# ---------- the round the page checks draw (test_design213_browser_pure) is the server's own ----------

def page_round(monkeypatch):
    """The round document the page checks draw: VW-24's round in its shapes, as the server builds it, and one line of each case VW-24 has
    not got (a set of one picture, made again, made the most times, a changed plan, a refused photo, a thing back, a kept answer), each
    built by the server on the shared fixture and given a key of its own."""
    film, _ = vw24(monkeypatch)
    film.change(lambda s: s['round']['elements']['SITE_DECK'].update(prompt='The footage shows it on the ground; the plan has it on a roof: the look from the footage, the place from the plan.'))
    real = film.set_facts
    monkeypatch.setattr(ref_sets, 'set_facts', lambda *a: {**real(*a), 'model': {'chose': 'the raised deck the plan describes, with the boards of the footage', 'aside': 'the bare ground of the footage pictures'}, 'footage': []})
    page = film.page()
    doc = {k: page[k] for k in ('step', 'open', 'summary', 'note', 'layout')}
    extra = []

    def take(film, key, name):
        line = film.lines()[key]
        extra.append({**line, 'key': f'set:{name}', 'name': f"{line['name']} ({name.lower().replace('_', ' ')})"})

    def one(s):
        for rid in ('s-street-1-2', 's-street-1-3'):
            s['references'].pop(rid)
    film = Film(monkeypatch, '2')
    film.change(one)
    real1 = film.set_facts
    monkeypatch.setattr(ref_sets, 'set_facts', lambda *a: {**real1(*a), 'partial': None})
    take(film, 'set:STREET', 'ONE_PICTURE')
    film = Film(monkeypatch, 'complete')
    film.state = 2
    film.change(lambda x: [r.update(status='candidate') for r in x['references'].values() if r.get('set') == 's-t_lay-2'] and x['round']['elements']['T_LAY'].update(verdict='approve'))
    take(film, 'set:T_LAY', 'MADE_AGAIN')
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['round']['elements']['STREET'].update(round=3))
    take(film, 'set:STREET', 'MADE_MOST')
    film = Film(monkeypatch, '2')
    film.changed.add('STREET')   # the plan changed, one picture did not come back, and an answer of an earlier visit was refused for the limit
    film.change(lambda s: (s['references'].pop('s-street-1-3'), s.update(page_refused={'set:STREET': ref_sets.LIMIT_PLAIN})))
    take(film, 'set:STREET', 'PLAN_CHANGED')
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['round']['elements']['STREET'].update(answer={'verdict': 'yes', 'golden': 's-street-1-2', 'words': '', 'set': 's-street-1', 'by': 'u1', 'at': F.NOW}))
    take(film, 'set:STREET', 'KEPT')
    film = Film(monkeypatch, '2')
    film.change(lambda s: [r.update(status='failed') for r in s['references'].values() if r.get('set') == 's-mason-1'])
    monkeypatch.setattr(VS, '_set_state', lambda session, plan, step, eid, row, budget: {'next': 'Give another photo.'} if eid == 'MASON' else {})
    take(film, 'set:MASON', 'PHOTO_REFUSED')
    film.change(lambda x: x['round']['elements']['FAN'].update(reopened='new', ignored=False))
    take(film, 'set:FAN', 'BACK')
    lines = page['lines'][:1] + sorted(page['lines'][1:] + extra, key=lambda l: G.index(l['group']))
    doc['lines'] = [{**l, 'line': f'l{n:02d}'} for n, l in enumerate(lines, 1)]
    return doc


def test_the_round_of_the_page_checks_is_what_the_server_builds(monkeypatch):
    doc = page_round(monkeypatch)
    path = Path(__file__).with_name('d213_sets_round.json')
    if os.environ.get('VW_WRITE_D213'):   # written again from the server's own output when the lines change
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    assert json.loads(path.read_text(encoding='utf-8')) == json.loads(json.dumps(doc))
    cases = {l.get('case') for l in doc['lines']}
    assert cases >= {'judge', 'notmade', 'photo', 'back', 'wait', 'settled'} and any(l.get('kept') for l in doc['lines']) and any(l.get('most') for l in doc['lines'])
