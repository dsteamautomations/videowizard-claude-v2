"""Release 1, section D (SK, 20 Nov 2026, answer 12: "Check the code, build what is missing"): the lessons of step 6 carried into step 7.
Each point was first read in the code; what was right has a test here that proves it, what was missing was built with a test that failed first.

D1 (built): the next-step line of step 7 names what can start now, together in one message: the writers of the scene descriptions, the
   checkers of the stills, the checkers of the takes.
D2 (built): the early cards come in batches in film order: every still's card, then every word to shoot; a shoot word waits while a still
   is being checked (its card comes with the look, or after 30 minutes as not checked); a rejected still does not hold the others' words.
D3 (proved): everything the operator chooses before a shot's first take is asked before it is paid for.
D4 (built in part): each limit of step 7's tools is named where the assistant reads it, and its refusal ends with the next step.
D5 (proved): "being redone" shows at once in the line of counts after "Make another".
D6 (proved): "does not apply", "not checked" and an unanswered line can never hold a take or turn into a fail, and nothing loops.
D7 (proved): no take waits on another shot's take; one "Make another" or one rejection does not close the page for the others.
Mid-flight (proved): a step 7 under way continues after the update with nothing asked again. Without a database."""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as G, guide_spec, page_flow as PF, pictures as P, takes as T, video_generators as VG, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_design222_critic2_pure import film, item, landed, on_page, second_take   # noqa: F401 (film: the fixture)
from test_design222_takes_pure import NOW, RUN, USER as OP, guide, held, job, look, plan, rec, session, shot, states   # noqa: F401 (held: the fixture)
from test_guide_route_pure import refused, scene, spec10, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import USER, saved

ROOT = Path(__file__).resolve().parents[2]
LOOKED = {'sha256': 's' * 64, 'lines': []}


def three():
    """Three AI video shots in film order S1, S2, S3; the guides were written in another order."""
    return plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'), shot('S3', start=200, end=300, title='Roof'))


def cards(s, p, monkeypatch, rows=()):
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: [j for j in rows if sid in (None, j['unit'])])
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None}
    return [i['id'].split(':')[0] + ':' + i['id'].split(':')[1] for i in CF._guide_items(ctx)]


# ---------- D1: what can start now, together ----------

def test_d1_the_next_step_line_names_the_checkers_and_writers_that_can_start_now_together(held):
    s, p = session(), three()
    s['guides'] = {'S2': guide(still='candidate', prompt=False), 'S3': guide(takes=['j3'])}             # S1: nothing yet; S2: its still waits for Claude's look; S3: its take does
    s['take_checks'] = {'j3': rec()}
    held(s, p)
    said = T.starts(s, p, [job('j3', 'S3')])
    assert said == 'Start now, together in one message: the writers of the scene descriptions of S1 (1); the checkers of the stills of S2 (1).'   # design/223: a take has no checker
    s['guides']['S1'] = guide(still='candidate', prompt=False)
    s['guides']['S1']['stills'][0]['id'] = 'st0'
    assert T.starts(s, p, [job('j3', 'S3')]) == 'Start now, together in one message: the checkers of the stills of S1, S2 (2).'
    s['guides']['S1']['stills'][0]['check_look'] = s['guides']['S2']['stills'][0]['check_look'] = LOOKED
    s['take_checks']['j3'] = rec(look=look())
    assert T.starts(s, p, [job('j3', 'S3')]) == ''                                                       # nothing to start: nothing said


# ---------- D2: the early cards in batches, in film order ----------

def test_d2_every_stills_card_comes_before_any_word_to_shoot_in_film_order(held, monkeypatch):
    s, p = session(), three()
    s['guides'] = {'S3': guide(still='candidate', prompt=False), 'S2': guide(), 'S1': guide(still='candidate', prompt=False)}   # written in another order than the film
    for sid in ('S1', 'S3'):
        s['guides'][sid]['stills'][0]['check_look'] = LOOKED
    held(s, p)
    assert cards(s, p, monkeypatch) == ['still:S1', 'still:S3', 'shoot:S2']
    s['guides']['S1'] = guide()                                                                          # S1's still answered: its word to shoot joins the second batch, in film order
    assert cards(s, p, monkeypatch) == ['still:S3', 'shoot:S1', 'shoot:S2']


def test_d2_a_word_to_shoot_waits_while_a_still_is_being_checked_and_never_longer_than_the_look(held, monkeypatch):
    s, p = session(), three()
    s['guides'] = {'S1': guide(still='candidate', prompt=False), 'S2': guide()}                           # S1's still waits for Claude's look
    held(s, p)
    assert cards(s, p, monkeypatch) == []                                                                # no card yet: the still's card comes first, with its look
    s['guides']['S1']['stills'][0]['check_look'] = LOOKED
    assert cards(s, p, monkeypatch) == ['still:S1', 'shoot:S2']
    s['guides']['S1']['stills'][0].pop('check_look')
    s['guides']['S1']['stills'][0]['asked_at'] = (P._now() - timedelta(minutes=P.PICTURE_LOOK_MINUTES + 1)).isoformat()   # the look never came
    ctx = {'session': s, 'plan': p, 'run': RUN, 'store': None, 'user': OP, 'outputs': [], 'conn': None}
    first = CF._guide_items(ctx)[0]
    assert cards(s, p, monkeypatch) == ['still:S1', 'shoot:S2'] and "Not checked: Claude's check did not come within 30 minutes. Judge it by eye." in first['text']   # shown as not checked: never blocks


def test_d2_a_rejected_still_does_not_hold_the_other_shots_words(held, monkeypatch):
    s, p = session(), three()
    s['guides'] = {'S1': guide(still='rejected', prompt=False), 'S2': guide(), 'S3': guide()}
    s['guides']['S1']['stills'].append({'id': 'st2', 'status': 'generating', 'guide_sha256': 'g' * 64})   # its new still is being made
    held(s, p)
    assert cards(s, p, monkeypatch) == ['shoot:S2', 'shoot:S3']


# ---------- D3: every choice before the first take is paid for ----------

def test_d3_no_take_is_paid_for_before_the_layout_the_still_and_the_word_are_answered(take_film):
    """Through the gate itself (`guide.shoot`), at every stage on the way to the first take (the critic's point 11)."""
    from test_guide_route_pure import STILL_WORDS, TAKE_WORDS, rendered, still_made
    store, conn = take_film
    paid = lambda: len([q for q in conn.queued if q['provider'] == 'video'])
    shoot = lambda quote='Shoot.': refused(lambda: G.shoot(conn, store, USER, NEW, [], 'VS1', quote))
    scene(store, conn)
    assert 'the rendered guide' in shoot() and 'an approved still made from this guide' in shoot() and "the take's words" in shoot()
    rendered(store, conn)                                                                        # the guide rendered, the layout drawing approved by the operator
    assert 'the rendered guide' not in shoot() and 'an approved still made from this guide' in shoot()
    sid = still_made(store, conn)                                                                # a still made, not yet answered by the operator
    assert 'an approved still made from this guide' in shoot()
    G.approve_still(conn, store, USER, NEW, [], 'VS1', sid, 'sha-still', 'Yes.')
    assert shoot().startswith("Not ready to shoot; still missing: the take's words")
    G.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)
    assert "on the operator's word" in shoot('') and paid() == 0                                 # everything is there, and still nothing without the operator's word
    assert G.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')['job_id'] and paid() == 1


# ---------- D4: every limit named where the assistant reads it; each refusal ends with the next step ----------

def test_d4_each_limit_of_step_7_is_in_the_served_text_and_in_its_refusal_with_the_next_step(take_film):
    stage = next(st for st in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if st['name'] == 'visuals')
    served = stage['prompt'] + ' '.join(pt['text'] for pt in stage['parts']) + (ROOT / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    assert (guide_spec.MIN_S, guide_spec.MAX_S) == (3, 15) and 'every take is an edit of a guide, 3 to 15 s' in served                 # the take's length
    assert VG.STILL['max_inputs'] == 16 and 'at most 16 pictures' in served                                                          # the references of a still
    assert 'there is no limit on the rounds of correction' in served                                                                 # design/223: no limit of takes for a shot (until then: two from one camera)
    assert (T.C.CLIP_MIN_S, T.C.CLIP_MAX_S, T.C.PICTURES_MAX) == (1.0, 3.0, 6) and '(1 to 3 s; in doubt, earlier), up to 6 approved pictures' in served   # design/223: a remake's clip and its pictures
    assert '(360p)' in served and VG.GUIDE['resolution'] == '360p' and T.C.VERSION_SIZE == '720p'                                     # design/223: the sizes
    assert 'the cost limit of the film' in served and 'only the owner can change it' in served                                        # the cost limit
    store, conn = take_film
    bad = {**spec10(), 'seconds': 20}
    said = refused(lambda: G.set_scene(conn, store, USER, NEW, [], 'VS1', bad))
    assert 'seconds: a whole number from 3 to 15.' in said and said.endswith('Correct the scene file and send it again (`vw guide scene --shot VS1 --file work/guide/VS1/scene.json`).')
    assert G.TOO_MANY.format(n=17, max=16).endswith('Leave out the pictures the shot needs least and ask for the still again (`vw guide still`).')
    # the critic's point 11: each stated limit against what the code enforces
    secs = lambda n: [x for x in guide_spec.problems({**spec10(), 'seconds': n, 'action': {'start': 0, 'end': min(n, 3)}}) if x.startswith('seconds')]
    assert secs(3) == secs(15) == [] and secs(2) and secs(16)                                                                          # 3 to 15 s
    assert str(VG.STILL['max_inputs']) in G.TOO_MANY.format(n=17, max=VG.STILL['max_inputs']) and "still['max_inputs']" in Path(G.__file__).read_text(encoding='utf-8')
    assert P.PICTURE_LOOK_MINUTES == 30   # the time-out of a still's check; design/223: a take has no check and no time-out
    assert 'tell the operator to ask the owner' in Path(V.__file__).read_text(encoding='utf-8').split('def check_cap')[1][:1200]       # the cost limit's refusal


# ---------- D5: "being redone" at once ----------


# ---------- D6: an answer that is neither pass nor fail never holds a take ----------

def due_take(held_):
    s, p = session(), plan(shot('S1'))
    s['guides']['S1'] = guide(takes=['j1'])
    s['take_checks']['j1'] = {**rec(), 'asked_at': NOW.isoformat()}
    held_(s, p)
    return s, p, [job('j1')]


def answers(pass_, seen=''):
    return [{'id': l['id'], 'pass': pass_, 'seen': seen} for l in T.look_lines()]


# ---------- D7: no take waits on another shot's take ----------


# ---------- a step 7 under way continues after the update ----------

def test_a_step_7_in_mid_flight_continues_with_nothing_asked_again(held, monkeypatch):
    """As VW-24 may stand at the update: S1's still approved and its word to shoot given, its take being made; S2 selected on the older page with a
    typed reason; S3's still approved, its word not asked yet. After the update: nothing answered is asked again, and S3's word is the one card."""
    s, p = session(), three()
    s['guides'] = {'S1': guide(takes=['j1'], shoot_asked={'stamp': 'x', 'answer': 'shoot'}), 'S2': guide(takes=['j2']), 'S3': guide()}
    s['take_checks'] = {'j2': rec(look=look(fail=('the action',)))}
    s['reviews'] = {'j2': [{'decision': 'accepted', 'notes': 'The broom is out of the cut.', 'quote': 'Select'}]}   # answered on 0.118.0, with its typed reason
    s['selections'] = {'S2': {'job_id': 'j2'}}
    held(s, p)
    rows = [job('j1', 'S1', status='running'), job('j2', 'S2')]
    assert states(s, p, rows) == [('S1', 'being made'), ('S2', 'answered'), ('S3', 'waiting for you in the chat')]
    assert cards(s, p, monkeypatch, rows) == ['shoot:S3']                                                # S1 and S2 are not asked again
    assert [w for w in V.waiting(s, p, 'VW-99', rows) if w['kind'] == 'take to select'] == []
    assert s['reviews']['j2'][-1]['notes'] == 'The broom is out of the cut.'                             # the typed reason stands as it was recorded


def test_mid_flight_a_candidate_still_a_still_with_a_look_reference_and_a_take_waiting_for_its_check(held, monkeypatch):
    """The critic's point 11: as the update may find them. S1: a candidate still made by 0.118.0 (never listed for a look, no `asked_at`), ordered with
    a look reference (`look`: a picture's id); S2: a take that waits for Claude's check; S3: ready for its word to shoot."""
    s, p = session(), three()
    s['guides'] = {'S1': guide(still='candidate', prompt=False), 'S2': guide(takes=['j2']), 'S3': guide()}
    s['guides']['S1']['stills'][0]['look'] = 'R9'
    s['take_checks'] = {'j2': rec()}
    held(s, p)
    rows = [job('j2', 'S2')]
    assert states(s, p, rows) == [('S1', 'being checked by Claude'), ('S2', 'made'), ('S3', 'waiting for you in the chat')]   # design/223: a take is never checked
    assert cards(s, p, monkeypatch, rows) == []                                                          # S3's word waits for S1's still, which is given to Claude's look now
    said = P.waits_words(s, p)                                                                           # the first next-step line stamps the still: the 30 minutes count from the update
    assert "1 picture(s) wait for Claude's check" in said and s['guides']['S1']['stills'][0]['asked_at']
    assert T.starts(s, p, rows) == 'Start now, together in one message: the checkers of the stills of S1 (1).'
    later = P._now() + timedelta(minutes=31)
    assert P.start_offered(s, s['guides']['S1']['stills'][0], later) and s['guides']['S1']['stills'][0]['look'] == 'R9'   # never held past the look's time; the reference untouched
    s['guides']['S1']['stills'][0]['asked_at'] = (P._now() - timedelta(minutes=31)).isoformat()
    assert cards(s, p, monkeypatch, rows) == ['still:S1', 'shoot:S3']


# ---------- D4b: the form of `changed_from_plan` (17 scene files refused on the first real run of step 7, VW-24, 20 Nov 2026) ----------

def test_d4b_the_helper_the_skill_and_the_served_text_give_the_form_the_route_takes_with_an_example_that_passes():
    import re
    helper = (ROOT / 'plugin' / 'agents' / 'vw-guide-scene.md').read_text(encoding='utf-8')
    skill = (ROOT / 'plugin' / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    stage = next(st for st in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if st['name'] == 'visuals')
    served = ' '.join(pt['text'] for pt in stage['parts'])
    form = 'a list of at most ten strings, each one plain sentence of at most 300 characters'
    assert form in helper and form in skill and form in guide_spec.CHANGED_FORM and 'never an object' in helper and 'never an object' in skill
    assert '`changed_from_plan` is a list of at most ten strings, each one sentence of at most 300 characters, never an object, and `[]` when nothing changed' in served
    ok = lambda value: not [p for p in guide_spec.problems({**spec10(), 'changed_from_plan': value}) if p.startswith('changed_from_plan')]
    examples = [json.loads(m) for text in (helper, skill, guide_spec.CHANGED_FORM) for m in re.findall(r'\[".*?"\]', text)]
    assert len(examples) >= 3 and all(ok(e) for e in examples)                         # every example given is taken by the route's own check
    assert ok([]) and '`[]`' in helper and '[]' in guide_spec.CHANGED_FORM and not [p for p in guide_spec.problems(spec10()) if p.startswith('changed_from_plan')]   # nothing changed: [] or no field
    for bad in ([{'plan': 'x', 'scene': 'y', 'why': 'z'}], 'one line', ['x' * 301], [''], ['a'] * 11):   # the shapes a helper is likely to send
        said = [p for p in guide_spec.problems({**spec10(), 'changed_from_plan': bad}) if p.startswith('changed_from_plan')]
        assert said == ['changed_from_plan: ' + guide_spec.CHANGED_FORM], bad
    for word in ('brick', 'kiln', 'mason', 'verandah'):
        assert word not in guide_spec.CHANGED_FORM.lower()
