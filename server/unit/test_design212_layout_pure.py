"""design/212 (SK, 17 Nov 2026): step 1 of the references in its new layout. The server decides, for the page and the chat alike: the five
groups and their order, the case of each thing and the buttons that case allows, that a person the footage does not show is not asked and
gets a set at done, what each button records, and every sentence; no cost is named anywhere at the two steps of a v2 round, except in a
refusal after "done". The stored round is not changed: VW-24's round as the live release posted it (its shapes, `vw24_step1_shapes.json`)
is drawn in the new layout as it is. An older round is untouched (pinned in test_design211_together_pure). Without a database."""
import json
import re
from pathlib import Path

import pytest

from app import chat_flow as CF, page_flow as P, ref_find
import d211_fixture as F
from test_design211c_kit_pure import Film, RUN, ans, labels

W = CF.WORDS
G = CF.STEP1_GROUPS
MONEY = re.compile(r'₹|\bpaid\b|\bfree\b|\bprice|\blimit\b|\bcost\b', re.I)


def choices(line):
    return [b['choice'] for b in line['buttons']]


def read(x):
    """Every sentence of a built answer that the operator reads: all its text values (the field names are not read)."""
    if isinstance(x, dict):
        return ' '.join(read(v) for k, v in x.items() if k not in ('how', 'capabilities', 'pictures'))
    if isinstance(x, (list, tuple)):
        return ' '.join(read(v) for v in x)
    return x if isinstance(x, str) else ''


# ---------- B: the five groups, in order ----------

def test_the_five_groups_and_their_order_on_the_fixture(monkeypatch):
    film = Film(monkeypatch)
    p = film.page()
    assert G == ['Routine: accept together', 'With footage pictures', 'No picture: a set is suggested', 'No picture: no reference suggested', 'No action needed']
    assert [(l['key'], l.get('group')) for l in p['lines']] == [
        ('refs:proposals', None), ('ref:BRICK', G[0]), ('ref:STREET', G[0]), ('ref:T_LAY', G[0]), ('ref:TILE', G[0]),
        ('ref:TROWEL', G[1]), ('ref:FAN', G[1]), ('ref:MASON', G[4])]
    assert p['layout']['kind'] == 'things' and p['layout']['made'] == 'Nothing is made until you say done in the chat.'
    assert p['layout']['help'].endswith('A set you ask to change is made again, at most 3 times.')
    chat = [i['id'] for i in film.items(every=False)]
    assert chat == ['round1:all', 'round1:BRICK', 'round1:STREET', 'round1:T_LAY', 'round1:TILE', 'round1:TROWEL', 'round1:FAN']   # the same order; the person not in the footage is not asked
    assert 'Doubtful' not in read(p) and 'Doubtful' not in read(film.items())


def vw24(monkeypatch):
    """A film whose round has VW-24's 49 things in their shapes: kind, proposal, doubt, footage pictures (weak or not), a closest picture,
    the search result, whether a made shot shows it, whether a footage picture alone can be its reference (not with approved drawings)."""
    things = json.loads((Path(__file__).parent / 'vw24_step1_shapes.json').read_text(encoding='utf-8'))['things']
    plan = F.plan()
    plan['elements'] = [{'id': t['id'], 'name': 'Thing ' + t['id'].title(), 'kind': t['kind'], 'identity': 'representative', 'requirements': '', 'required_views': [], 'size': [],
                         'description': 'What it looks like.'} for t in things]
    shot = lambda t, n: F._shot(f"B-S1-SH{t['id']}{n}", 'footage' if t['kind'] == 'person' and t['leave'] else 'image', 'MS', [t['id']])
    plan['gaps'] = [{'gap_id': 'BEAT_11-B1', 'scenes': [{'id': 'B-S1', 'location_time': 'the yard, morning', 'outfit': {}, 'shots': [shot(t, n) for t in things for n in range(min(t['shots'], 1))]}]}]
    s = F.session('1')
    look = lambda weak: {'who': 'helper', 'at': F.NOW, 'view': 'whole', 'verdict': 'weak' if weak else 'pass', 'seen': 'Seen.'}
    refs, rows, found, drawn = {}, {}, {}, {}
    for t in things:
        ids = [f"f-{t['id']}-{n}" for n in range(len(t['frames']))]
        for fid, weak in zip(ids, t['frames']):
            refs[fid] = {'id': fid, 'element_id': t['id'], 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/{fid}.png", 'view': 'whole', 'look': look(weak), 'weak': weak}
        rows[t['id']] = {'frames': ids, 'keywords': '', 'verdict': None, 'search_id': None, 'error': None, 'prompt': '', 'corrections': [], 'set': None, 'round': 0,
                         'rec': t['rec'], 'reason': 'Why.', 'doubt': t['doubt'], 'first': False, 'operator_words': [], 'history': []}
        found[t['id']] = {'result': t['search'], 'clips': 2, 'clip_names': ['a.mp4', 'b.mp4'], 'not_searched': [], 'note': 'No clip could show it.', 'stale': False,
                          'closest': {'trial': 't-' + t['id'], 'key': f"{RUN['id']}/visuals/trials/t-{t['id']}.jpg", 'view': 'whole', 'seen': 'Close.'} if t['closest'] else None}
        if t['frames'] and not t['use'] and t['kind'] != 'person':   # a set is made even with footage: it has approved drawings
            drawn[t['id']] = {'status': 'approved', 'sha256': 'e' * 64, 'views': []}
    s['references'], s['drawings'], s['round']['elements'] = refs, drawn, rows
    s.pop('found')
    film = Film(monkeypatch, session=s, plan=plan)
    for f in found.values():
        if f['closest']:
            film.store.files[f['closest']['key']] = film.store.files[next(iter(refs.values()))['key']]
    monkeypatch.setattr(ref_find, 'found_all', lambda store, run, session, plan: found)
    return film, things


def test_vw24s_round_as_the_live_release_posted_it_shows_in_the_new_layout(monkeypatch):
    film, things = vw24(monkeypatch)
    before = json.loads(json.dumps(film.session()['round']))
    p = film.page()
    lines = [l for l in p['lines'] if l['key'] != 'refs:proposals']
    assert len(lines) == 49 and [len([l for l in lines if l['group'] == g]) for g in G] == [6, 25, 3, 11, 4]      # as on the trial page the owner approved
    assert [G.index(l['group']) for l in lines] == sorted(G.index(l['group']) for l in lines)                    # sent in the groups' order
    order = [t['id'] for t in things]
    for g in G:
        ids = [l['key'][4:] for l in lines if l['group'] == g]
        assert ids == sorted(ids, key=order.index), g                                                            # the plan's order inside a group
    assert {l['key'][4:] for l in lines if l['group'] == G[4]} == {'MOTHER', 'FATHER', 'CHILD', 'NEIGHBOUR'}
    assert [l['case'] for l in lines if l['group'] == G[4]] == ['auto'] * 4 and all(l.get('kept') for l in lines if l['case'] == 'auto')
    assert p['summary'].startswith('49 things: 45 to answer, 4 answered.')
    assert p['lines'][0]['covers'] == ['ref:MASON', 'ref:REBAR_GRID', 'ref:BRICK', 'ref:STRAIGHTEDGE', 'ref:WIRE_COIL', 'ref:T_SCREED']
    assert film.session()['round'] == before and 'chat_round' not in film.session()                              # nothing stored is changed by showing it
    assert not MONEY.search(read(p)), MONEY.search(read(p))
    assert len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8')) < P.ROUND_BYTES


# ---------- C: the case of each thing and its buttons ----------

def test_the_four_cases_and_their_buttons(monkeypatch):
    l = Film(monkeypatch).lines()
    trowel, fan, brick, mason = l['ref:TROWEL'], l['ref:FAN'], l['ref:BRICK'], l['ref:MASON']
    # 1: footage pictures
    assert trowel['case'] == 'footage' and labels(trowel) == ['Approve', 'Make a set', 'Make a set with words', 'No reference needed'] and choices(trowel) == ['use', 'set', 'fix', 'ignore']
    assert trowel['own']['label'] == 'Upload my own' and [b.get('needs_words', False) for b in trowel['buttons']] == [False, False, True, False]
    assert trowel['rec'] == {'do': 'footage', 'label': 'Use footage', 'choice': 'use', 'reason': 'The film shows it whole and sharp from the side.'}
    assert trowel['tick'] == {'use': 'Tick at least one picture first.', 'set': 'Tick at least one picture first: the set is made from it.', 'fix': 'Tick at least one picture first: the set is made from it.'}
    # 2: only a "closest found" picture: Approve needs its tick
    assert fan['case'] == 'closest' and labels(fan) == ['No reference needed', 'Approve', 'Make a set'] and fan['tick'] == {'use': 'Tick the picture first, if that is it.'}
    assert fan['rec']['label'] == 'No reference needed' and fan['rec']['choice'] == 'ignore' and fan['own']['label'] == 'Upload my own'
    # 3: no picture, a thing: an optional small link for words
    assert brick['case'] == 'none' and labels(brick) == ['Make a set', 'No reference needed', 'Add words for the picture'] and choices(brick) == ['set', 'ignore', 'fix']
    assert brick['buttons'][2].get('small') is True and 'tick' not in brick and brick['rec']['label'] == 'Make a set'
    assert brick['search'] == {'text': 'Not in your footage.', 'why': 'The helper was stopped.'}
    # 4: a person the footage does not show: nothing to decide
    assert mason['case'] == 'auto' and labels(mason) == ['Add words for the picture'] and choices(mason) == ['fix'] and 'small' not in mason['buttons'][0]
    assert mason['search']['text'] == ('Not in your footage. A set will be made from the description when you say done in the chat. No answer is needed; '
                                       'you may add words or your own photo.')
    assert mason['kept'] == 'A set will be made' and mason['own']['label'] == 'Upload my own' and mason['own']['person'] is True
    for line in l.values():
        assert all(len(b['label'].split()) <= 5 and '(' not in b['label'] for b in line['buttons']), line['key']   # never a sentence inside a button
        if line['key'] != 'refs:proposals':
            assert (line['name'], line['kind']) and 'comment' not in line


def test_a_person_with_footage_pictures_and_a_thing_with_approved_drawings_have_no_approve(monkeypatch):
    film = Film(monkeypatch)
    film.change(lambda s: s['references'].update({'f-mason-1': {'id': 'f-mason-1', 'element_id': 'MASON', 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/f-mason-1.png",
                                                                'view': 'front', 'look': {'verdict': 'pass', 'seen': 'The mason, front.'}, 'weak': False}}))
    l = film.lines()
    assert l['ref:MASON']['case'] == 'footage' and labels(l['ref:MASON']) == ['Make a set', 'Make a set with words'] and 'tick' not in l['ref:MASON']   # a set is made of every person, with or without a tick
    assert l['ref:TILE']['case'] == 'footage' and labels(l['ref:TILE']) == ['Make a set', 'Make a set with words', 'No reference needed']                       # approved drawings: a set, never the bare footage


# ---------- the auto-answer: a person the footage does not show ----------

def test_a_person_not_in_the_footage_is_not_asked_and_gets_a_set_at_done_on_the_page(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    out = film.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:TROWEL'], 'use'), ans(l['ref:FAN'], 'ignore'))   # MASON is never answered
    assert not out['refused'] and 'ref:MASON' in out['recorded']
    verdicts = film.called('round_done')[0][0]
    assert verdicts['MASON'] == {'verdict': 'approve', 'words': ''} and verdicts['TROWEL']['verdict'] == 'approve' and verdicts['FAN']['verdict'] == 'ignore'


def test_a_person_not_in_the_footage_is_not_asked_in_the_chat_which_says_so_once(monkeypatch):
    film = Film(monkeypatch)
    first = film.next()['item']
    assert first['id'] == 'round1:all' and '1 person not in your footage gets a set from the description without being asked: The mason.' in first['summary']
    assert 'round1:MASON' not in [i['id'] for i in film.items(every=False)]
    film.decide('round1:all', 'accept_all')
    nxt = film.next()['item']
    assert nxt['id'] == 'round1:TROWEL' and 'summary' not in nxt                                                    # said once
    film.decide('round1:TROWEL', 'use')
    out = film.decide('round1:FAN', 'ignore')
    assert film.called('round_done') and film.called('round_done')[0][0]['MASON']['verdict'] == 'approve' and out['answered'] == 'round1:FAN'


def test_words_or_an_own_photo_for_that_person_replace_the_auto_answer(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    out = film.record(ans(l['ref:MASON'], 'fix'))
    assert out['refused'][0]['message'] == 'Write what should change first.'
    film.record(ans(film.lines()['ref:MASON'], 'fix', 'He wears a blue cap.'))
    kept = film.session()['chat_round']['MASON']
    assert (kept['verdict'], kept['words']) == ('approve', 'He wears a blue cap.') and film.lines()['ref:MASON']['kept'] == 'Add words for the picture'


# ---------- E: no cost anywhere at the two steps ----------

@pytest.mark.parametrize('state', ['1', 'making', 'looking', '2', 'rewrite'])
def test_no_cost_is_named_on_the_page_or_in_the_chat_at_the_two_steps(monkeypatch, state):
    film = Film(monkeypatch, state)
    film.changed.add('STREET')
    page = film.page()
    said = read(page) + ' ' + read([{k: v for k, v in i.items() if not k.startswith('_')} for i in film.items()])
    nxt = film.next()
    said += ' ' + read(nxt.get('item') or {})
    assert not MONEY.search(said), (state, MONEY.search(said).group(0), said[max(0, MONEY.search(said).start() - 80):MONEY.search(said).end() + 40])


def test_a_refusal_after_done_still_names_the_limit(monkeypatch):
    film = Film(monkeypatch)
    monkeypatch.setattr('app.visuals_stage._set_budget', lambda run, s, spend: (3700.0, F.CAP, F.SET_PRICE))
    l = film.lines()
    out = film.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:TROWEL'], 'use'), ans(l['ref:FAN'], 'ignore'))
    said = next(r['message'] for r in out['refused'] if r['key'] == 'references')
    assert said.startswith('These cannot be made now: the film has reached the limit its owner set.') and '₹' not in said and not film.called('round_done')
    assert out['page']['layout']['stopped'] == said and not MONEY.search(read(out['page']['lines']))


# ---------- C: what each button records ----------

def kept(film, eid):
    return {k: v for k, v in film.session()['chat_round'][eid].items() if k in ('verdict', 'words', 'pics')}


def test_approve_uses_the_ticked_footage_pictures_and_an_unticked_one_is_not_this_picture(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'use', pics={'f-trowel-use': 'not'}))
    assert out['kept'] == ['ref:TROWEL'] and film.called('not_this') == [('TROWEL', 'f-trowel-use', 'Approve')]
    assert kept(film, 'TROWEL') == {'verdict': 'approve', 'words': '', 'pics': {'f-trowel-use': 'not'}}
    assert film.lines()['ref:TROWEL']['kept'] == 'Approve'


def test_approve_with_no_picture_ticked_is_refused_on_its_line_and_marks_nothing(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'use', pics={'f-trowel-side': 'not', 'f-trowel-use': 'not'}))
    assert out['refused'] == [{'key': 'ref:TROWEL', 'message': 'Tick at least one picture first.'}] and not film.called('not_this') and 'chat_round' not in film.session()
    assert film.lines()['ref:TROWEL']['refused'] == 'Tick at least one picture first.'
    out = film.record(ans(film.lines()['ref:FAN'], 'use'))                                                           # the closest picture, not ticked
    assert out['refused'][0]['message'] == 'Tick the picture first, if that is it.' and not film.called('that_is_it')


def test_approve_on_a_ticked_closest_picture_takes_it_as_the_footage_picture(monkeypatch):
    film = Film(monkeypatch)
    film.record(ans(film.lines()['ref:FAN'], 'use', pics={'t0000000000c1': 'use'}))
    assert film.called('that_is_it') == [('FAN', 't0000000000c1', 'Approve')] and kept(film, 'FAN') == {'verdict': 'approve', 'words': '', 'pics': {'t0000000000c1': 'use'}}
    assert film.lines()['ref:FAN']['case'] == 'footage'


def test_make_a_set_is_a_clean_set_from_the_ticked_pictures_else_a_set_from_the_description(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    film.record(ans(l['ref:TROWEL'], 'set'), ans(l['ref:BRICK'], 'set', 'A wet brick.'), ans(l['ref:FAN'], 'set'))
    assert kept(film, 'TROWEL') == {'verdict': 'clean', 'words': '', 'pics': {}}                                    # from its footage pictures
    assert kept(film, 'BRICK') == {'verdict': 'approve', 'words': 'A wet brick.', 'pics': {}}                       # no picture: have a set made; "Add words" is the same with words
    assert kept(film, 'FAN') == {'verdict': 'approve', 'words': '', 'pics': {}} and not film.called('that_is_it')   # the closest picture left unticked: a set from the description
    out = film.record(ans(film.lines()['ref:TROWEL'], 'set', pics={'f-trowel-side': 'not', 'f-trowel-use': 'not'}))
    assert out['refused'][0]['message'] == 'Tick at least one picture first: the set is made from it.'


def test_minor_corrections_is_make_a_set_with_the_operators_words_which_are_required(monkeypatch):
    film = Film(monkeypatch)
    out = film.record(ans(film.lines()['ref:TROWEL'], 'fix'))
    assert out['refused'][0]['message'] == 'Write what should change first.' and 'chat_round' not in film.session()
    film.record(ans(film.lines()['ref:TROWEL'], 'fix', 'Keep it, but with a new handle.', pics={'f-trowel-use': 'not'}))
    assert kept(film, 'TROWEL') == {'verdict': 'clean', 'words': 'Keep it, but with a new handle.', 'pics': {'f-trowel-use': 'not'}}
    film2 = Film(monkeypatch)
    l = film2.lines()
    out = film2.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:TROWEL'], 'fix', 'A new handle.'), ans(l['ref:FAN'], 'ignore'))
    assert film2.called('round_done')[0][0]['TROWEL'] == {'verdict': 'clean', 'words': 'A new handle.'}             # the words reach the request as their words


def test_leave_out_is_ignore_and_names_the_shots_that_lose_the_thing(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    assert l['ref:TROWEL']['cost'] == 'These shots are then made with no reference of it: shot 1 of gap 2, shot 2 of gap 2.'
    film.record(ans(l['ref:TROWEL'], 'ignore', pics={'f-trowel-use': 'not'}))
    assert kept(film, 'TROWEL')['verdict'] == 'ignore'


def test_a_picture_that_comes_in_place_of_an_unticked_one_keeps_the_answer_and_asks_for_one_look(monkeypatch):
    """The review of 17 Nov, fault 2: the choice and the typed words were dropped, and the key was reported as recorded."""
    film = Film(monkeypatch)
    film.next_frame = {**F._frame('f-trowel-3', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a3')}
    out = film.record(ans(film.lines()['ref:TROWEL'], 'fix', 'Keep it, with a new handle.', pics={'f-trowel-use': 'not'}))
    assert out['kept'] == ['ref:TROWEL'] and 'ref:TROWEL' not in out['recorded'] and not out['refused']
    line = {x['key']: x for x in out['page']['lines']}['ref:TROWEL']
    assert line['note'] == 'A new picture was found for this thing. Look at it, then confirm or change your answer.'
    assert line['again'] == {'choice': 'fix', 'notes': 'Keep it, with a new handle.'} and 'kept' not in line and out['open'] >= 1   # still to answer: not counted, so "done" cannot close the step
    assert [(x['choice'], x.get('on', False)) for x in line['pics']] == [('not:f-trowel-side', True), ('not:f-trowel-3', True)]         # the new one starts ticked: the proposal uses the footage
    assert next(i for i in film.items() if i['id'] == 'round1:TROWEL')['text'].startswith('A new picture was found for this thing.')    # the chat says it too
    film.next_frame = None
    film.record(ans(line, 'fix', 'Keep it, with a new handle.'))                                                                    # confirmed, as it was
    assert kept(film, 'TROWEL') == {'verdict': 'clean', 'words': 'Keep it, with a new handle.', 'pics': {}} and 'note' not in film.lines()['ref:TROWEL']


def test_a_second_new_picture_does_not_ask_again_it_is_not_used_and_the_answer_stands(monkeypatch):
    """One look per thing: after the operator confirmed once, a picture that comes in place of another is left unticked, and the answer is kept."""
    film = Film(monkeypatch)
    film.next_frame = {**F._frame('f-trowel-3', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a3')}
    out = film.record(ans(film.lines()['ref:TROWEL'], 'use', pics={'f-trowel-use': 'not'}))
    film.next_frame = {**F._frame('f-trowel-4', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a2')}
    line = film.lines()['ref:TROWEL']
    out = film.record(ans(line, 'use', pics={'f-trowel-3': 'not'}))
    assert out['kept'] == ['ref:TROWEL'] and len(film.called('not_this')) == 2
    got = film.session()['chat_round']['TROWEL']
    assert got['verdict'] == 'approve' and 'confirm' not in got and got['pics']['f-trowel-4'] == 'off'
    line = film.lines()['ref:TROWEL']
    assert line['kept'] == 'Approve' and line['kept_how'] == 'from the 1 ticked picture' and 'note' not in line


def test_the_answers_of_the_page_before_this_layout_are_still_taken(monkeypatch):
    film = Film(monkeypatch)
    item = next(i for i in film.items() if i['id'] == 'round1:TROWEL')
    item['_run']('clean', 'Make a clean set from it', 'Sharper.')
    assert kept(film, 'TROWEL') == {'verdict': 'clean', 'words': 'Sharper.', 'pics': {}}


# ---------- D: the routine things, shown before they are accepted ----------

def test_the_proposals_line_lists_the_routine_things_for_show_the_n(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    prop = l['refs:proposals']
    assert prop['head'] == "Accept Claude's proposals for the 4 routine things" and prop['show'] == 'Show the 4' and labels(prop) == ['Accept all 4']
    assert prop['covers'] == ['ref:BRICK', 'ref:STREET', 'ref:T_LAY', 'ref:TILE']
    for key in prop['covers']:
        assert l[key]['group'] == G[0] and l[key]['rec']['reason'] and l[key]['rec']['label'] and l[key]['name'] and l[key]['kind']
    assert [p['label'] for p in l['ref:TILE']['pics']] == ['underside']                                             # its footage pictures, for the list
    assert prop['text'] == ('7 things have a proposal from Claude. Accepting the 4 routine ones asks for 4 sets, takes the footage pictures of 0 things as they are, and makes no reference for 0. '
                            'The first 3 sets are made to check the method; after you judge them, the others are made in one go. A set you ask to change is made again, at most 3 times. '
                            'A thing you answer yourself keeps your answer.')


def test_accept_all_keeps_an_answer_the_operator_gave_alone(monkeypatch):
    film = Film(monkeypatch)
    l = film.lines()
    film.record(ans(l['ref:BRICK'], 'ignore'), ans(l['refs:proposals'], 'accept_all'))
    held = film.session()['chat_round']
    assert held['BRICK']['verdict'] == 'ignore' and {e: held[e]['verdict'] for e in ('STREET', 'T_LAY', 'TILE')} == {'STREET': 'approve', 'T_LAY': 'approve', 'TILE': 'approve'}
    assert 'TROWEL' not in held and 'FAN' not in held and 'MASON' not in held                                       # never a thing outside the routine group


# ---------- F: the words ----------

def test_no_code_name_is_in_a_sentence_the_operator_reads(monkeypatch):
    film = Film(monkeypatch)
    p = film.page()
    said = read(p['lines']) + ' ' + p['summary'] + ' ' + read(film.next())
    codes = [e['id'] for e in F.plan()['elements']] + [g['gap_id'] for g in F.plan()['gaps']]
    plain = re.sub(r'\b(ref|round1|not|use):[\w-]+', '', said)                                                      # the keys and choices are not sentences
    assert not [c for c in codes if re.search(rf'\b{c}\b', plain)] and not re.search(r'G\d-S\d-SH\d', plain)
    trowel = film.lines()['ref:TROWEL']
    assert trowel['used'] == 'Used in 2 shots; the closest is a close-up (shot 2 of gap 2).' and trowel['shots'] == 'Used in 2 shots · closest: a close-up'
    assert trowel['desc'] == 'A pointed steel blade, a reddish-brown handle.' and (trowel['name'], trowel['kind']) == ("Mason's trowel", 'an object')
    assert 'was not searched' not in said and 'Not in your footage.' in said
    for word in ('character sheet', 'clean set', 'Have a set made'):
        assert word not in said, word                                                                               # one word, "set", for every kind of thing


def test_the_search_sentence_is_short_with_its_reason_behind_why(monkeypatch):
    l = Film(monkeypatch).lines()
    assert l['ref:FAN']['search'] == {'text': 'Not in your footage. The closest picture is shown.', 'why': 'Searched: 2 clips (C001.mp4, C002.mp4).'}
    assert l['ref:STREET']['search'] == {'text': 'Not in your footage.', 'why': 'Searched: 2 clips (C001.mp4, C002.mp4). Nothing close was seen.'}
    assert 'search' not in l['ref:TROWEL']


# ---------- the size of the round, and the older round ----------

def test_a_round_of_60_things_is_one_document_under_the_size_limit(monkeypatch):
    plan, s = F.plan(), F.session('1')
    long = 'A long description of the thing, as the plan gives it, with its form, colour, material and wear. ' * 3
    for n in range(60 - len(F.THINGS)):
        eid = f'EXTRA{n}'
        plan['elements'].append({'id': eid, 'name': f'Extra thing {n}', 'kind': 'object', 'identity': 'representative', 'requirements': '', 'required_views': [], 'size': [], 'description': long})
        plan['gaps'][0]['scenes'][0]['shots'][0]['element_ids'].append(eid)
        fids = [f'f-x{n}-{k}' for k in range(3)]
        for fid in fids:
            s['references'][fid] = {'id': fid, 'element_id': eid, 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/{fid}.png", 'view': 'whole and at rest, from the side',
                                    'look': {'verdict': 'weak', 'seen': long}, 'weak': True}
        s['round']['elements'][eid] = {**F._row('BRICK', fids), 'rec': 'footage', 'reason': long[:300], 'doubt': True}
        s['found'][eid] = F._found('found', ['C001'], long, fids)
    p = Film(monkeypatch, session=s, plan=plan).page()
    size = len(json.dumps(p['lines'], ensure_ascii=False).encode('utf-8'))
    assert len([l for l in p['lines'] if l['key'].startswith('ref:')]) == 60 and size < P.ROUND_BYTES, size
    assert p['lines'][0]['key'] == 'refs:proposals'                                                                 # nothing was held back for a later visit


def test_an_older_round_has_none_of_this(monkeypatch):
    from test_design211c_kit_pure import older_step1
    p = Film(monkeypatch, session=older_step1()).page()
    assert 'layout' not in p and not any(k in l for l in p['lines'] for k in ('case', 'group', 'tick', 'search', 'covers')) and '₹' in p['summary']
    assert [b['choice'] for b in p['lines'][0]['buttons']] == ['approve', 'ignore']


# ---------- the review of 17 Nov 2026: what a tick means ----------

def test_the_pictures_that_start_ticked_follow_the_proposal_not_the_weak_mark(monkeypatch):
    film, _things = vw24(monkeypatch)
    l = film.lines()
    on = lambda key: [bool(x.get('on')) for x in l[key]['pics']]
    assert on('ref:CONCRETE') == [True, True, True] and l['ref:CONCRETE']['pics'][0]['weak'] is True     # "use footage": every picture, weak or not
    assert on('ref:HELPER') == [False, False, False]                                                    # a person, a set proposed, only weak pictures: from the description
    assert on('ref:MASON') == [True, True, True]                                                        # a person, a set proposed, good pictures: from them
    assert on('ref:SITE_DECK') == [True, True, True]                                                    # a thing whose set can only come from its footage pictures
    assert on('ref:MORTAR') == [False, False]                                                           # proposed to leave out: none
    assert on('ref:TILEMAKER') == [False]                                                               # a "closest found" picture is never ticked for the operator


def test_a_picture_left_unticked_is_not_used_and_is_never_not_this_picture(monkeypatch):
    """The review of 17 Nov, fault 1: on VW-24's young site worker one click on "Make a set" wrote three "not this picture" marks."""
    film, _things = vw24(monkeypatch)
    out = film.record(ans(film.lines()['ref:HELPER'], 'set'))
    assert out['kept'] == ['ref:HELPER'] and film.called('not_this') == [] and film.called('that_is_it') == []
    line = film.lines()['ref:HELPER']
    assert len(line['pics']) == 3 and line['case'] == 'footage' and 'search' not in line               # the thing keeps its pictures on its line
    got = film.session()['chat_round']['HELPER']
    assert got['verdict'] == 'approve' and got['pics'] == {'f-HELPER-0': 'off', 'f-HELPER-1': 'off', 'f-HELPER-2': 'off'}
    assert line['kept'] == 'Make a set' and line['kept_how'] == 'from the description; the footage pictures are not used'


def test_a_default_pass_over_vw24_rejects_no_picture(monkeypatch):
    film, _things = vw24(monkeypatch)
    lines = [l for l in film.lines().values() if l['key'] != 'refs:proposals' and l['case'] != 'auto']
    out = film.record(*[ans(l, l['rec'].get('choice') or l['buttons'][0]['choice']) for l in lines if not l['buttons'][0].get('needs_words')])
    assert film.called('not_this') == [] and film.called('that_is_it') == []
    assert sorted(r['message'] for r in out['refused']) == ['Tick the picture first, if that is it.'] * len([l for l in lines if l['rec'].get('choice') == 'use' and l['case'] == 'closest'])


def test_a_picture_the_operator_ticked_themselves_is_used(monkeypatch):
    film, _things = vw24(monkeypatch)
    film.record(ans(film.lines()['ref:HELPER'], 'set', pics={'f-HELPER-1': 'on'}))
    got = film.session()['chat_round']['HELPER']
    assert got['pics'] == {'f-HELPER-0': 'off', 'f-HELPER-2': 'off'} and film.called('not_this') == []
    assert film.lines()['ref:HELPER']['kept_how'] == 'from the 1 ticked picture'


def test_the_chat_follows_the_same_ticks_and_accept_all_too(monkeypatch):
    film = Film(monkeypatch)
    film.change(lambda s: (s['references'].update({'f-mason-1': {'id': 'f-mason-1', 'element_id': 'MASON', 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/f-mason-1.png",
                                                                 'view': 'front', 'look': {'verdict': 'weak', 'seen': 'A man, far off.'}, 'weak': True}})))
    item = next(i for i in film.items() if i['id'] == 'round1:MASON')
    item['_run']('set', 'Make a set', '')                                                               # the chat has no ticks: the proposal's own
    assert film.session()['chat_round']['MASON']['pics'] == {'f-mason-1': 'off'} and film.called('not_this') == []
    film.record(ans(film.lines()['refs:proposals'], 'accept_all'))
    assert film.session()['chat_round']['TILE']['pics'] == {}                                           # its one good picture is used


def test_at_done_an_unticked_picture_is_set_aside_with_no_search_for_another(monkeypatch):
    from app import visuals_stage as VS
    film = Film(monkeypatch)
    film.change(lambda s: (s['references'].update({'f-mason-1': {'id': 'f-mason-1', 'element_id': 'MASON', 'kind': 'frame', 'status': 'candidate', 'key': f"{RUN['id']}/visuals/references/f-mason-1.png",
                                                                 'view': 'front', 'look': {'verdict': 'weak', 'seen': 'A man, far off.'}, 'weak': True}})))
    seen, real = {}, VS.round_done

    def done(store, user, run, outputs, verdicts, quote, conn=None):
        seen.update({k: (r['status'], (r.get('rejection') or {}).get('notes')) for k, r in film.session()['references'].items()})
        return real(store, user, run, outputs, verdicts, quote, conn=conn)
    monkeypatch.setattr(VS, 'round_done', done)
    l = film.lines()
    out = film.record(ans(l['refs:proposals'], 'accept_all'), ans(l['ref:MASON'], 'set'), ans(l['ref:TROWEL'], 'use'), ans(l['ref:FAN'], 'ignore'))
    assert not out['refused'] and film.called('round_done')[0][0]['MASON'] == {'verdict': 'approve', 'words': ''}
    assert seen['f-mason-1'] == ('rejected', 'not ticked by the operator: not used') and film.called('not_this') == []   # so the set is made from the description
    assert seen['f-trowel-side'][0] == 'candidate' and seen['f-trowel-use'][0] == 'candidate'                             # "use footage": both were ticked


def test_approve_with_only_unticked_pictures_is_refused_until_one_is_ticked(monkeypatch):
    film, _things = vw24(monkeypatch)
    l = film.lines()['ref:MORTAR']                                                                      # two pictures, proposed to leave out: none starts ticked
    out = film.record(ans(l, 'use'))
    assert out['refused'][0]['message'] == 'Tick at least one picture first.' and film.called('not_this') == []
    out = film.record(ans(film.lines()['ref:MORTAR'], 'use', pics={'f-MORTAR-0': 'on'}))
    assert out['kept'] == ['ref:MORTAR'] and film.session()['chat_round']['MORTAR']['pics'] == {'f-MORTAR-1': 'off'}


# ---------- the review: an answer in the shape of the page of before design/212 ----------

def test_an_answer_document_of_the_page_before_this_layout_is_still_taken(monkeypatch):
    """The review of 17 Nov, fault 3: `approve`, `clean`, `ignore` written by the 0.92.0 page were refused with "Not an answer to this line"."""
    film = Film(monkeypatch)
    l = film.lines()
    out = film.record(ans(l['ref:TROWEL'], 'clean', 'Sharper.', pics={'f-trowel-use': 'not'}), ans(l['ref:BRICK'], 'approve', 'A wet brick.'), ans(l['ref:FAN'], 'ignore'), ans(l['ref:TILE'], 'approve'))
    assert out['refused'] == [] and out['kept'] == ['ref:TROWEL', 'ref:BRICK', 'ref:FAN', 'ref:TILE']
    assert kept(film, 'TROWEL') == {'verdict': 'clean', 'words': 'Sharper.', 'pics': {'f-trowel-use': 'not'}} and film.session()['chat_round']['TROWEL']['quote'] == 'Make a clean set from it'
    assert kept(film, 'BRICK') == {'verdict': 'approve', 'words': 'A wet brick.', 'pics': {}} and kept(film, 'FAN')['verdict'] == 'ignore'
    out = film.record(ans(film.lines()['ref:STREET'], 'no_such_choice'))
    assert out['refused'][0]['message'].startswith("Not an answer to this line: 'no_such_choice'.")
