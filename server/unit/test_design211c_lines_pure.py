"""design/211 part C (section 6.3): what the operator sees of a v2 reference round, on the page and in the chat with the same words.
Step 1: the proposals, then the things in the five groups of design/212; each line with the plan's description, the shots that use the thing, what
the footage has, Claude's proposal and its reason, each footage picture answered on its own. Step 2: the first sets with both checks, the
image model's notes, the set before, and "make the rest". design/212 (SK, 17 Nov 2026): no cost is named at either step, the buttons of
step 1 are short and follow the case of the thing, and a person the footage does not show is not asked (test_design212_layout_pure). A round without `v == 2` shows exactly what it showed before.
Parts A and B are stood in for (test_design211c_kit_pure). Without a database."""
import copy
import hashlib
import json

import pytest

from app import chat_flow as CF, page_flow as P, ref_sets as RS
import d211_fixture as F
from test_design211c_kit_pure import Film, RUN, labels, older_step1

W = CF.WORDS
G = CF.STEP1_GROUPS
NOT_ANALYSED = ''   # design/211 review: the clips with no analysis are named once, in the step's summary (UNREAD), not on every line
UNREAD = ' Not searched for any thing, because they have no analysis: C003.mp4.'


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')).hexdigest()[:16]


def public(items):
    return [{k: v for k, v in i.items() if not k.startswith('_')} for i in items]


# ---------- step 1: the order, and each field of a line ----------

def test_step_1_shows_the_proposals_then_the_things_in_their_five_groups(monkeypatch):
    p = Film(monkeypatch).page()
    assert p['step'] == P.REFS_STEP and p['open'] is True
    assert [l['key'] for l in p['lines']] == ['refs:proposals', 'ref:BRICK', 'ref:STREET', 'ref:T_LAY', 'ref:TILE', 'ref:TROWEL', 'ref:FAN', 'ref:MASON']
    assert [l.get('group') for l in p['lines']] == [None, G[0], G[0], G[0], G[0], G[1], G[1], G[4]]   # design/212: routine; with footage pictures; no action needed
    assert [l['item'] for l in p['lines']][:3] == ['round1:all', 'round1:BRICK', 'round1:STREET'] and all(l['state'] == 'open' for l in p['lines'])
    assert '_' not in ''.join(k[0] for l in p['lines'] for k in l) and not any('_key' in x for l in p['lines'] for x in l.get('pics') or [])


def test_a_thing_with_footage_shows_the_description_the_shots_the_pictures_and_the_proposal(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()['ref:TROWEL']
    assert l['title'] == "Mason's trowel (an object)" and l['ask'] == 'Use the footage pictures as the reference?'
    assert (l['desc'], l['used']) == ('A pointed steel blade, a reddish-brown handle.', 'Used in 2 shots; the closest is a close-up (shot 2 of gap 2).') and 'text' not in l   # design/212: the gap by its number, never its code name; the page shows the parts
    item = next(i for i in film.items() if i['id'] == 'round1:TROWEL')
    assert item['text'].startswith('A pointed steel blade, a reddish-brown handle.\nUsed in 2 shots; the closest is a close-up (shot 2 of gap 2).\nFrom your footage: 2 pictures.' + NOT_ANALYSED)   # the chat says them as one text
    assert l['rec'] == {'do': 'footage', 'label': 'Use footage', 'choice': 'use', 'reason': 'The film shows it whole and sharp from the side.'}
    assert labels(l) == ['Approve', 'Make a set', 'Minor corrections', 'Leave out'] and [b['choice'] for b in l['buttons']] == ['use', 'set', 'fix', 'ignore']   # design/212: short plain buttons, no cost
    assert [(x['label'], x['note'], x.get('weak', False), x['choice']) for x in l['pics']] == [
        ('side', 'The whole trowel, side on, sharp; the handle is reddish-brown.', False, 'not:f-trowel-side'),
        ('in the hand, lifting mortar', 'In the hand, the blade half covered by mortar.', True, 'not:f-trowel-use')]
    assert l['pics'][0]['code'] == P.pic_code(CF._ref_key(RUN, 'f-trowel-side'), film.session()['references']['f-trowel-side']['sha256'])
    assert l['warnings'] == [W['warn_exact']]
    assert 'comment' not in l and 'comment_hint' not in l                           # design/212: the words come with "Minor corrections", not in a box under every answer
    assert l['cost'] == 'If you leave it out, these shots are made with no reference of it: shot 1 of gap 2, shot 2 of gap 2.'
    assert l['own']['label'] == 'Upload my own' and 'kept' not in l


def test_the_footage_sentence_for_each_result_of_the_search(monkeypatch):
    film = Film(monkeypatch)
    l, said = film.lines(), {i['id']: i['text'] for i in film.items()}
    assert 'search' not in l['ref:TILE'] and '\nFrom your footage: 1 picture.' in said['round1:TILE']                                                # found
    assert l['ref:MASON']['search']['why'] == 'Searched: 1 clip (C001.mp4). Nothing close was seen.'                                                  # none, nothing close
    assert l['ref:FAN']['search'] == {'text': 'Not in your footage. The closest picture is shown.', 'why': 'Searched: 2 clips (C001.mp4, C002.mp4).'}   # none, with the closest
    assert l['ref:BRICK']['search'] == {'text': 'Not in your footage.', 'why': 'The helper was stopped.'}                                             # not searched (design/212: short, the reason behind "why")
    assert '\nNot in your footage. The helper was stopped.' in said['round1:BRICK']                                                                  # the chat says both
    fan = l['ref:FAN']['pics']
    assert [(x['label'], x['note'], x['choice']) for x in fan] == [('The closest: whole', 'A switch plate on a wall, not a fan regulator.', 'use:t0000000000c1')]
    assert 'pics' not in l['ref:MASON'] and 'pics' not in l['ref:BRICK']


def test_more_clips_than_are_named_end_in_an_ellipsis_and_a_weak_only_result_reads_as_found(monkeypatch):
    assert CF._search_words({'result': 'none', 'clips': 9, 'clip_names': ['a.mp4', 'b.mp4'], 'closest': None, 'not_searched': []}, []) == \
        ('Not in your footage.', 'Searched: 9 clips (a.mp4, b.mp4…). Nothing close was seen.')
    assert CF._search_words({'result': 'weak', 'clips': 1, 'clip_names': ['a.mp4'], 'not_searched': []}, [{'ref': 'f1'}]) == ('From your footage: 1 picture.', '')
    assert CF._search_words(None, []) == ('', '')   # a film with no footage has no search record: nothing is claimed


def test_the_words_has_no_picture_of_it_appear_nowhere_in_a_v2_round(monkeypatch):
    for state in ('1', 'making', 'looking', '2', 'rewrite'):
        film = Film(monkeypatch, state)
        text = json.dumps([film.page()['lines'], public(film.items())])
        assert 'has no picture of' not in text and 'no picture of it' not in text, state


def test_a_person_shown_in_a_made_picture_has_no_leave_it_out_and_a_thing_no_shot_names_says_so(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    assert labels(l['ref:MASON']) == ['Add words for the picture'] and 'cost' not in l['ref:MASON'] and l['ref:MASON']['ask'] == 'Make a set of this person?'   # design/212: not in the footage: nothing to decide
    assert 'warnings' not in l['ref:MASON']   # design/211 review: a size that is not known is no warning: nothing is decided by it
    plan = F.plan()
    for g in plan['gaps']:
        for sc in g['scenes']:
            for sh in sc['shots']:
                sh['element_ids'] = [e for e in sh['element_ids'] if e not in ('MASON', 'BRICK')]
    film = Film(monkeypatch, plan=plan)
    film.change(lambda s: s['round']['elements']['MASON'].update(rec='leave'))
    l = film.lines()
    assert labels(l['ref:MASON']) == ['Leave out', 'Make a set', 'Add words for the picture']   # no made picture shows this person now, and leaving out is proposed: it is asked
    assert l['ref:BRICK']['used'] == 'No shot of the plan names it.' and l['ref:BRICK']['cost'] == 'If you leave it out, no made shot loses it.'


def test_the_operators_words_are_asked_only_where_a_set_can_follow(monkeypatch):
    film = Film(monkeypatch)
    film.change(lambda s: (s['references'].update({'own-1': {'id': 'own-1', 'kind': 'supplied', 'element_id': 'BRICK', 'status': 'approved', 'key': 'run-211/visuals/references/own-1.png'}}),
                           s['round']['elements']['BRICK'].update(rec='footage')))
    l = film.lines()
    words = lambda line: [b['label'] for b in line['buttons'] if b['needs_words']]
    assert [words(l[k]) for k in ('ref:TROWEL', 'ref:TILE', 'ref:STREET', 'ref:MASON')] == [['Minor corrections'], ['Minor corrections'], ['Add words for the picture'], ['Add words for the picture']]
    assert not any('comment' in line or 'comment_hint' in line for line in l.values())   # design/212: no comment box at step 1
    brick = l['ref:BRICK']                                                         # the operator's own picture is its reference: no set can follow
    assert labels(brick) == ['Approve', 'Leave out'] and not words(brick) and 'search' not in brick
    said = next(i for i in film.items() if i['id'] == 'round1:BRICK')['text']
    assert W['own_is'] in said and brick['ask'] == 'Use your own picture as the reference?'


def test_the_proposed_answer_is_the_first_button_and_no_button_names_a_cost(monkeypatch):
    l = Film(monkeypatch).lines()
    assert labels(l['ref:FAN']) == ['Leave out', 'Approve', 'Make a set'] and l['ref:FAN']['rec'] == {'do': 'no_set', 'label': 'Leave out', 'choice': 'ignore', 'reason': 'One wide shot; its words carry it.'}
    assert labels(l['ref:TILE']) == ['Make a set', 'Minor corrections', 'Leave out'] and l['ref:TILE']['rec']['label'] == 'Make a set'   # approved drawings: a set, never the bare footage
    assert not any('₹' in b['label'] or 'paid' in b['label'] for line in l.values() for b in line['buttons'])   # design/212 (SK, 17 Nov 2026): no cost on a button; before: a paid button always showed its price


def test_the_warnings_of_a_line(monkeypatch):
    film = Film(monkeypatch)
    film.real.add('MASON')
    film.cause = {'element_id': 'BRICK', 'text': 'the material spec of Brick is not approved'}
    film.change(lambda s: s['found']['STREET'].update(stale=True))
    l = film.lines()
    assert l['ref:MASON']['warnings'] == [W['warn_person']] and l['ref:MASON']['group'] == G[4] and 'ref:MASON' not in l['refs:proposals']['covers']   # a real person's likeness is never routine (design/212: not in the footage: no action needed)
    assert l['ref:BRICK']['warnings'] == ['A set cannot be made now: the material spec of Brick is not approved.']
    assert l['ref:STREET']['warnings'] == [W['warn_stale']] and l['ref:STREET']['group'] == G[2] and 'ref:STREET' not in l['refs:proposals']['covers']   # not routine: no picture, a set is suggested
    assert 'warnings' not in l['ref:T_LAY']


def test_a_proposal_its_answer_would_not_carry_out_makes_the_line_doubtful(monkeypatch):
    film = Film(monkeypatch)
    film.change(lambda s: s['round']['elements']['BRICK'].update(rec='footage'))   # no footage picture stands: accepting would have a set made instead
    l = film.lines()
    assert l['ref:BRICK']['group'] == G[2] and 'ref:BRICK' not in l['refs:proposals']['covers'] and l['ref:BRICK']['rec']['label'] == 'Make a set'   # not routine; what can be done is said
    assert l['refs:proposals']['buttons'][0]['label'] == 'Accept all 3'


# ---------- "Accept the proposals" and the summary ----------

def test_accept_the_proposals_names_what_it_does_and_no_price(monkeypatch):
    l = Film(monkeypatch).lines()['refs:proposals']
    assert l['title'] == "Claude's proposals" and l['item'] == 'round1:all' and l['ask'] == 'Accept the proposals for the routine things?'
    # design/211 review (C4): the truth about the sets: three are made first, the others are asked after. design/212: no cost is named
    assert l['text'] == ('7 things have a proposal from Claude. Accepting the 4 routine ones asks for 4 sets, takes the footage pictures of 0 things as they are, and leaves 0 out. '
                         'At most 3 sets are made first, when you say done; any others are offered after you have judged those, and made only on your word. '
                         'A thing you answer yourself keeps your answer.')
    assert l['buttons'] == [{'label': 'Accept all 4', 'choice': 'accept_all', 'needs_words': False}] and 'own' not in l and 'pics' not in l


def test_accept_the_proposals_with_no_set_says_nothing_of_the_sets_made_first(monkeypatch):
    film = Film(monkeypatch)
    film.change(lambda s: [row.update(rec='leave', doubt=False) for row in s['round']['elements'].values()])
    l = film.lines()['refs:proposals']
    assert l['buttons'][0]['label'] == 'Accept all 5' and 'asks for 0 sets, takes' in l['text'] and 'leaves 5 out' in l['text'] and 'At most' not in l['text']
    # MASON has no "Leave out": doubtful; TROWEL keeps a weak frame: doubtful whatever its row says (design/211 review, M3)


def test_the_summary_of_step_1_names_no_money(monkeypatch):
    """design/212 (SK, 17 Nov 2026): before, the summary gave four figures and a warning when the limit would be passed."""
    film = Film(monkeypatch)
    p = film.page()
    assert p['summary'] == '7 things: 6 to answer, 1 answered.' + UNREAD
    assert p['note'].startswith('Look at each thing')
    film.planned = 3600.0
    p = film.page()
    assert p['summary'] == '7 things: 6 to answer, 1 answered.' + UNREAD and '₹' not in p['note'] and 'limit' not in p['note'] and p['open'] is True


def test_the_summary_is_the_same_when_the_cost_of_the_shots_cannot_be_worked_out(monkeypatch):
    film = Film(monkeypatch)
    monkeypatch.setattr(P.V, 'budget', lambda *a: (_ for _ in ()).throw(KeyError('no picture AI')))
    assert film.page()['summary'] == '7 things: 6 to answer, 1 answered.' + UNREAD


# ---------- step 2 ----------

def test_step_2_shows_make_the_rest_then_the_doubtful_sets_then_the_others_then_what_waits_and_what_is_recorded(monkeypatch):
    film = Film(monkeypatch, '2')
    p = film.page()
    assert p['step'] == P.SETS_STEP and [l['key'] for l in p['lines']] == ['sets:rest', 'set:T_LAY', 'set:MASON', 'set:STREET', 'set:BRICK', 'set:TILE', 'set:TROWEL']
    assert [l.get('group') for l in p['lines']] == [None, CF.GROUP_SETS_DOUBT, 'People', 'Places', W['g_wait'], W['g_wait'], W['g_done']]
    assert [l['state'] for l in p['lines']] == ['open', 'open', 'open', 'open', 'making', 'making', 'recorded']
    rest = p['lines'][0]
    assert rest['item'] == f'rest:{F.NOW}' and rest['title'] == 'The other sets'
    assert rest['text'] == 'These are the first 3 sets. 2 more are not ordered yet: Brick, Roof tile. Look at these first: a fault here would repeat in all of them.'   # design/212: no money (before: design/211 review, S13)
    assert rest['cost'] == 'If you leave these 2 out, these shots are made with no reference: Brick: shot 1 of gap 2, shot 2 of gap 2; Roof tile: shot 2 of gap 3.'   # (C5)
    assert labels(rest) == ['Make the other 2 sets', 'Leave these 2 out'] and [b['choice'] for b in rest['buttons']] == ['rest', 'rest_out']
    assert p['summary'] == '6 things: 3 to answer, 0 kept, 2 not ready yet, 1 recorded.'
    brick, trowel = p['lines'][4], p['lines'][6]
    assert brick['note'] == W['waiting'] and brick['tag'] == 'Not ordered'
    assert [x['label'] for x in trowel['pics']] == ['From your footage: side (the starting picture)', 'From your footage: in the hand, lifting mortar']   # taken from footage at step 1: listed, recorded


def test_a_set_shows_its_pictures_with_their_views_both_checks_the_notes_and_the_proposal(monkeypatch):
    l = Film(monkeypatch, '2').lines()
    t = l['set:T_LAY']
    assert t['item'] == 'set:T_LAY:s-t_lay-1' and t['ask'] == 'Which picture is the reference?'
    assert t['text'] == 'The right hand lowers the brick; the left hand rests on the wall.\nUsed in 1 shot; the closest is a medium shot (shot 1 of gap 2).'
    assert [(x['label'], x['note'], x.get('weak', False), x['choice'], x['choice_label']) for x in t['pics']] == [
        ('A · the action at its key moment', 'the action at its key moment: as asked.', False, 'use:s-t_lay-1', 'Use A'),
        ('B · the result just after', 'the result just after: as asked.', True, 'use:s-t_lay-1-2', 'Use B'),
        ('C · close on where it happens', 'close on where it happens: as asked.', False, 'use:s-t_lay-1-3', 'Use C')]
    assert t['check'] == {'state': 'fail', 'by': "The program's check (Gemini)", 'lines': ['Picture B: the action is shown: A tool lying still; no hand.']}
    assert t['notes'] == {'title': "The image model's notes", 'sources': 1,
                          'text': '(1) One method, the most common. (3) The request asked for a wooden scaffold; the photographs show bamboo: I drew bamboo.'}
    again = '(the set is made again)'   # design/212: no cost on a button
    assert t['rec'] == {'do': 'remake', 'label': f'Correct it {again}', 'reason': 'Picture B shows no hand at work.'}
    assert labels(t) == [f'Correct it {again}', 'Use A', 'Use B', 'Use C', f'None of these {again}'] and t['buttons'][0]['needs_words'] is True   # the proposed answer first
    assert t['comment'] is True and t['own']['label'] == 'Use my own picture' and 'partial' not in t and 'earlier' not in t
    m, s = l['set:MASON'], l['set:STREET']
    assert m['check'] == {'state': 'pass', 'by': "The program's check (Gemini)", 'lines': []} and m['ask'] == 'Is this set right for this person?'
    assert labels(m) == ['Yes', f'No {again}', f'Correct it {again}'] and m['rec'] == {'do': 'use', 'label': 'Yes', 'reason': 'All three agree with the plan.'}
    assert not any('choice' in x for x in m['pics'])                                # a person's starting picture is the server's choice
    assert labels(s)[0] == 'Use A' and s['rec']['label'] == 'Use A' and s['group'] == 'Places'


def test_the_inputs_of_a_set_come_first_to_compare_with_and_have_no_button(monkeypatch):
    film = Film(monkeypatch, '2')
    film.inputs['T_LAY'] = [{'ref': 'f-trowel-side', 'role': 'footage', 'view': 'side'}, {'ref': 'gone', 'role': 'drawing', 'view': ''}]
    pics = film.lines()['set:T_LAY']['pics']
    assert [(x['label'], x.get('ref_only', False), 'choice' in x) for x in pics][:2] == [('From your footage: side', True, False), ('A · the action at its key moment', False, True)] and len(pics) == 4
    film.inputs['T_LAY'] = [{'ref': 'iso', 'role': 'drawing', 'view': ''}]
    film.change(lambda s: s['drawings'].update(T_LAY=copy.deepcopy(s['drawings']['TILE'])))
    assert film.lines()['set:T_LAY']['pics'][0]['label'] == 'Drawing'


def test_a_check_that_did_not_run_says_so_and_blocks_nothing(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: [r.pop('check') for r in s['references'].values() if r.get('set') == 's-mason-1'])
    m = film.lines()['set:MASON']
    assert m['check'] == {'state': 'none', 'by': "The program's check (Gemini)", 'lines': []} and m['buttons'] and m['group'] == 'People'
    film.change(lambda s: s['references']['s-t_lay-1-3'].pop('check'))
    assert film.lines()['set:T_LAY']['check']['lines'] == ['Picture B: the action is shown: A tool lying still; no hand.', 'Picture C was not checked: the check did not run.']


def test_a_partial_set_is_shown_as_it_is_with_what_is_missing(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['references'].pop('s-street-1-3'))
    s = film.lines()['set:STREET']
    assert s['partial'] == '2 of 3 pictures came back; missing: its fixed things.' and len(s['pics']) == 2 and s['group'] == CF.GROUP_SETS_DOUBT
    assert 'three pictures' not in json.dumps(s).lower()


def remade(s):
    """The fixture's complete round with T_LAY's second set back with the operator, not yet judged."""
    for r in s['references'].values():
        if r.get('set') == 's-t_lay-2':
            r.update(status='candidate')
    s['round']['elements']['T_LAY']['verdict'] = None
    s['golden'].pop('T_LAY')


def test_a_set_made_again_shows_the_operators_words_and_the_set_before(monkeypatch):
    film = Film(monkeypatch, '2', session=F.session('complete'))
    film.change(remade)
    t = film.lines()['set:T_LAY']
    assert t['changes'] == ['Made again as you asked: "Show the hand pressing the brick down."'] and t['asked'] is True
    assert [x['label'] for x in t['earlier']] == ['Before: A', 'Before: B', 'Before: C'] and all(x['code'] and '_key' not in x for x in t['earlier'])
    assert t['earlier'][0]['code'] == P.pic_code(CF._ref_key(RUN, 's-t_lay-1'), film.session()['references']['s-t_lay-1']['sha256']) and t['earlier'][0]['code'] in {x['code'] for x in film.page()['pictures']}   # sent to the page like any picture


def test_a_set_made_three_times_offers_no_remake_and_says_why(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['round']['elements']['MASON'].update(round=3))
    m = film.lines()['set:MASON']
    assert labels(m) == ['Yes'] and m['text'].endswith('This set was made 3 times, which is the most: use one of these pictures, or add your own.')
    film.change(lambda s: s['round']['elements']['STREET'].update(round=3))
    street = film.lines()['set:STREET']   # the merger: a thing made the most times may be left out (the contract, 3.8; V.set_aside takes it); a person never
    assert labels(street) == ['Use A', 'Use B', 'Use C', 'Leave out'] and street['text'].endswith('use one of these pictures, add your own, or leave it out.')


def test_a_set_whose_plan_changed_is_marked_and_can_be_made_again(monkeypatch):
    film = Film(monkeypatch, '2')
    film.changed.add('STREET')
    s = film.lines()['set:STREET']
    assert s['text'].endswith(W['set_changed']) and labels(s)[-1] == 'Make it again from the changed plan' and s['group'] == CF.GROUP_SETS_DOUBT


def test_a_set_that_was_not_made_gives_the_real_cause(monkeypatch):
    film = Film(monkeypatch, '2')
    film.fails['STREET'] = {'cause': 'refused', 'model': 'gemini-nano-banana-2.1', 'text': 'Gemini (gemini-nano-banana-2.1) refused the request.'}

    def unmake(s):
        for rid in [r for r, x in s['references'].items() if x.get('set') == 's-street-1']:
            s['references'][rid].update(status='failed')
    film.change(unmake)
    s = film.lines()['set:STREET']
    assert s['item'] == 'setmake:STREET' and s['group'] == 'Not made' and s['text'].endswith('\nGemini (gemini-nano-banana-2.1) refused the request.')
    assert labels(s) == ['Make it', 'Leave out'] and s['ask'] == 'Make it now?' and s['cost'].startswith('If you leave it out')
    film.cause = {'element_id': 'STREET', 'text': 'the spend cap is reached: ₹3,740 spent of ₹3,754'}
    assert film.lines()['set:STREET']['text'].endswith('Its reference set was not made: the spend cap is reached: ₹3,740 spent of ₹3,754. It can be made when that is settled.')
    assert 'OpenAI' not in json.dumps(film.page()['lines'])


def test_the_lines_while_sets_are_made_looked_at_and_written_again(monkeypatch):
    p = Film(monkeypatch, 'making').page()
    by = {l['key']: l for l in p['lines']}
    assert all(by[k]['state'] == 'making' and by[k]['note'] == 'Its set is being made.' and 'tag' not in by[k] for k in ('set:MASON', 'set:STREET', 'set:T_LAY'))
    assert 'sets:rest' not in by and by['set:BRICK']['tag'] == 'Not ordered' and p['open'] is False and p['then'] == RS.SETS_MAKING   # the rest is offered once the first sets are judged; design/211 review (N4): wait, then look
    p = Film(monkeypatch, 'looking').page()
    by = {l['key']: l for l in p['lines']}
    assert all(by[k]['state'] == 'making' and by[k]['note'] == 'Claude is looking at it.' and by[k]['tag'] == 'Claude is looking' and 'pics' not in by[k] for k in ('set:MASON', 'set:STREET', 'set:T_LAY'))
    assert 'sets:rest' not in by and not [l for l in p['lines'] if l['state'] == 'open']                                         # no set is shown before its look
    p = Film(monkeypatch, 'rewrite').page()
    by = {l['key']: l for l in p['lines']}
    assert by['set:T_LAY']['note'] == 'The assistant is writing its request again from your words.' and by['set:T_LAY']['tag'] == 'Being rewritten'
    assert by['set:MASON']['state'] == 'recorded' and [x['label'] for x in by['set:MASON']['pics']] == ['A · full length, front (the starting picture)', 'B · right hand and forearm', 'C · the face']


def test_a_set_with_an_incomplete_look_is_not_shown_even_at_step_2(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: s['references']['s-street-1-2'].pop('look'))
    by = film.lines()
    assert by['set:STREET']['state'] == 'making' and by['set:STREET']['tag'] == 'Claude is looking' and by['set:MASON']['state'] == 'open'
    assert 'set:STREET:s-street-1' not in [i['id'] for i in film.items(every=False)]


def test_a_thing_back_after_the_round_was_sent_again_is_an_open_line(monkeypatch):
    film = Film(monkeypatch, '2')
    film.change(lambda s: (s['round']['elements']['FAN'].update(reopened='left_out'), s['round']['elements']['BRICK'].update(reopened='new')))
    by = film.lines()
    assert by['set:FAN']['item'] == 'reopen:FAN' and by['set:FAN']['group'] == 'Back with you' and by['set:FAN']['text'].endswith(W['reopen_left'])
    assert by['set:BRICK']['text'].endswith(W['reopen_new']) and labels(by['set:BRICK']) == ['Make a set', 'Leave out']
    assert 'Brick' not in by['sets:rest']['text'] and '1 more is not ordered yet: Roof tile.' in by['sets:rest']['text'] and labels(by['sets:rest']) == ['Make the other set', 'Leave it out']


# ---------- one flow, two front ends ----------

@pytest.mark.parametrize('state', ['1', '2'])
def test_the_chat_item_of_each_line_has_the_same_question_text_and_buttons_as_the_page(monkeypatch, state):
    film = Film(monkeypatch, state)
    items = {i['id']: i for i in film.items()}
    marks = {r['key']: r['sha256'] for r in [*film.session()['references'].values(), *F.trials()['trials'].values()] if r.get('key')}   # defect 55: a picture is its key and its content
    lines = [l for l in film.page()['lines'] if l['state'] == 'open']
    assert lines and {l['item'] for l in lines} == set(items)
    for l in lines:
        i = items[l['item']]
        own = [b['label'] for b in i['buttons'] + i.get('other_choices', []) if not (state == '1' and b['choice'].startswith(('not:', 'use:')))]
        assert CF._split(i['question'])[1] == l['ask'] and i['text'].startswith(l.get('text') or l['desc'] or l['used']) and own == labels(l), l['key']   # design/212: a thing's line of step 1 carries its parts
        for said in ([W['proposes'].format(**l['rec'])] if l.get('rec') else []) + [W['read_first'].format(warning=w) for w in l.get('warnings', [])] + l.get('check', {}).get('lines', []) \
                + [x['note'] for x in l.get('pics', []) if x.get('note')] + [l[k] for k in ('partial', 'cost') if l.get(k)]:
            assert said in i['text'], (l['key'], said)
        assert [P.pic_code(x['key'], marks[x['key']]) for x in i['show']] == [x['code'] for x in l.get('pics', [])]   # the chat shows the same pictures, in the same order


def test_in_the_chat_a_picture_is_answered_on_its_own_with_the_same_words(monkeypatch):
    film = Film(monkeypatch)
    trowel = next(i for i in film.items() if i['id'] == 'round1:TROWEL')
    assert [(b['label'], b['choice']) for b in trowel['other_choices']] == [('Not this picture: side', 'not:f-trowel-side'), ('Not this picture: in the hand, lifting mortar', 'not:f-trowel-use')]
    fan = next(i for i in film.items() if i['id'] == 'round1:FAN')
    assert [(b['label'], b['choice']) for b in fan['other_choices']] == [('That is it: The closest: whole', 'use:t0000000000c1')]


def test_the_chat_asks_the_proposals_first_and_then_each_open_thing(monkeypatch):
    film = Film(monkeypatch)
    got = film.next()['item']
    assert got['id'] == 'round1:all' and [b['label'] for b in got['buttons']] == ['Accept all 4', 'Ask me each one'] and got['position'] == 'References, 1 of 7'   # design/212: the person not in the footage is not asked
    out = film.decide('round1:all', 'each')
    assert out['item']['id'] == 'round1:BRICK' and out['item']['position'] == 'References, 1 of 6' and 'Claude suggests: Make a set.' in out['item']['message']   # the groups' order
    assert out['item']['buttons'][0]['description'] == 'A set of three pictures is made'   # the line under a button: no cost
    for eid in ('BRICK', 'STREET', 'T_LAY', 'TILE'):
        out = film.decide(f'round1:{eid}', 'set')
    assert out['item']['id'] == 'round1:TROWEL' and [b['label'] for b in out['item']['buttons']] == ['Approve', 'Make a set', 'Minor corrections', 'Leave out']
    out = film.decide('round1:TROWEL', 'not:f-trowel-use', quote='not that one')
    assert film.called('not_this') == [('TROWEL', 'f-trowel-use', 'not that one')] and out['item']['id'] == 'round1:TROWEL' and len(out['item']['show']) == 1   # the line comes back, open
    assert film.called('round_done') == []


def test_the_chat_accepts_the_proposals_through_the_same_function_and_closes_the_step_after_the_last_answer(monkeypatch):
    film = Film(monkeypatch)
    film.next()
    out = film.decide('round1:all', 'accept_all', quote='yes, take them')
    assert sorted(film.session()['chat_round']) == ['BRICK', 'STREET', 'TILE', 'T_LAY'] and out['item']['id'] == 'round1:TROWEL'   # design/212: MASON, not in the footage, is answered by the server at the end
    out = film.decide('round1:TROWEL', 'fix', quote='a clean set', notes='show the blade clean')   # "Minor corrections": a set from the footage pictures, with their words
    out = film.decide('round1:FAN', 'ignore')
    verdicts, quote = film.called('round_done')[0]
    assert verdicts == {'MASON': {'verdict': 'approve', 'words': ''}, 'TROWEL': {'verdict': 'clean', 'words': 'show the blade clean'}, 'FAN': {'verdict': 'ignore', 'words': ''},
                        'BRICK': {'verdict': 'approve', 'words': ''}, 'STREET': {'verdict': 'approve', 'words': ''}, 'T_LAY': {'verdict': 'approve', 'words': ''}, 'TILE': {'verdict': 'approve', 'words': ''}}
    assert out['then'].startswith('Step 1 is recorded. The first 3 sets are being made (about ₹105); 2 more wait')   # the server's own sentence


def test_in_the_chat_make_the_rest_is_asked_after_the_first_sets(monkeypatch):
    film = Film(monkeypatch, '2')
    assert [i['id'] for i in film.items(every=False)] == ['set:T_LAY:s-t_lay-1', 'set:MASON:s-mason-1', 'set:STREET:s-street-1', f'rest:{F.NOW}']
    assert [i['id'] for i in film.items()][0] == f'rest:{F.NOW}'


# ---------- the size of a round document ----------

def big(n, words):
    plan, s = F.plan(), F.session('1')
    plan['elements'] = [{'id': f'E{i:02d}', 'name': f'Thing {i}', 'kind': 'object', 'identity': 'representative', 'requirements': 'r', 'required_views': [], 'size': [], 'description': words} for i in range(n)]
    s['round']['elements'] = {e['id']: {**copy.deepcopy(s['round']['elements']['BRICK']), 'reason': 'It is seen close.'} for e in plan['elements']}
    s['found'], s['references'], s['drawings'] = {}, {}, {}
    return plan, s


def test_a_round_of_60_things_fits_one_document_of_the_page(monkeypatch):
    plan, s = big(60, 'A plain thing. ' * 20)
    p = Film(monkeypatch, plan=plan, session=s).page()
    assert len(p['lines']) == 61 and p['lines'][0]['key'] == 'refs:proposals' and 'Accept all 60' == p['lines'][0]['buttons'][0]['label']
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES
    plan, s = big(60, 'A long description of the thing, sentence after sentence. ' * 80)   # over the size of one document: the later lines wait for the next "done"
    p = Film(monkeypatch, plan=plan, session=s).page()
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) <= P.ROUND_BYTES and 1 < len(p['lines']) < 60
    assert 'refs:proposals' not in [l['key'] for l in p['lines']]                    # never "accept" for lines the operator cannot see
    assert 'more things appear here after you answer these' in p['note'] and '60 things: 60 to answer' in p['summary'] and 'more after these' in p['summary']


# ---------- a round without `v == 2`: exactly what it showed before (VW-24 is mid-round) ----------

OLDER = {'step1': (older_step1, P.REFS_STEP, '94b01dfc73e032f6', 'b0fada184a3af74a', '1bf2c4f46416666a'),
         'step2': (F.older_session, P.SETS_STEP, 'a660d1ed98a24377', '52730aab46a93702', '52730aab46a93702')}   # the digests were taken on the code of before design/211 part C


@pytest.mark.parametrize('step', ['step1', 'step2'])
def test_an_older_round_shows_exactly_the_lines_of_before(monkeypatch, step):
    make, name, page, every, chat = OLDER[step]
    film = Film(monkeypatch, session=make())
    real = P.pic
    monkeypatch.setattr(P, 'pic', lambda key, label, mark='': real(key, label))   # defect 55: but for the content's mark in a picture's code, the lines are those of before
    monkeypatch.setattr(CF, '_round_v2', lambda *a: (_ for _ in ()).throw(AssertionError('an older round never takes the new path')))
    p = film.page()
    assert p['step'] == name and digest({k: p[k] for k in ('step', 'open', 'lines', 'summary', 'note')}) == page
    assert digest(public(film.items())) == every and digest(public(film.items(every=False))) == chat
    new = {'group', 'rec', 'check', 'notes', 'earlier', 'partial', 'cost', 'comment_hint', 'tag'}
    assert not any(new & set(l) for l in p['lines']) and not any({'note', 'weak', 'choice_label', 'ref_only'} & set(x) for l in p['lines'] for x in l.get('pics') or [])
    assert [l['key'] for l in p['lines']][0] == ('ref:MASON' if step == 'step1' else 'set:MASON') and 'then' not in p


def test_an_older_round_keeps_its_two_sentences_and_its_step_1_answers(monkeypatch):
    film = Film(monkeypatch, session=older_step1())
    l = film.lines()
    assert 'Your footage has no picture of it.' in l['ref:FAN']['text'] and labels(l['ref:TROWEL']) == ['Yes, use it', 'Leave it out']
    out = film.record({'line': l['ref:FAN']['line'], 'key': 'ref:FAN', 'item': 'round1:FAN', 'choice': 'ignore', 'notes': '', 'pics': {'f-trowel-use': 'not'}})
    assert out['kept'] == ['ref:FAN'] and film.called('not_this') == [] and film.session()['chat_round']['FAN'] == {'verdict': 'ignore', 'quote': 'Leave it out', 'frames': ''}   # no new field, no new call
