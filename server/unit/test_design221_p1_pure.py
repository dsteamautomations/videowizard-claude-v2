"""design/221 phase 1 (SK, 19 Nov 2026): the brief of a drawn shot tells the truth. S1: no brief before the film's motion style and font (an older
film passes as before). Row 14: nothing empty or defaulted printed as a fact (no "None", no "-", no "(given)"), the palette said approved or not yet,
the letter size for labels, each subject rule with its source; S3: the brief kept line by line beside the rules at upload, and a verdict on rules
written from an older brief refused with the changed line named. Row 4: the sizes confirmed on the shot's things in its brief; a diagram of a real
thing approved only with a proportion or a known size. Row 6: the brief's order. Row 15: a note or a question is not a rule. Rows 20-22: the font
first, step 6 and step 7 named apart, the log says what failed. Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import chat_flow as C, pictures as P, runlog as L, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import MRUN, motion_shot, motion_store, project, zipped
from test_visuals_stage_pure import USER, accepted, g

ROOT = Path(__file__).resolve().parents[2]
PLAN = 'run-1/visuals/plan-v1.json'
RULES = '# Rules\n1. The course is solid at sill level.\n2. The two leaves are the same thickness.\n'


def run_with(**choices):
    return {**MRUN, 'film': {k: {'value': v} for k, v in choices.items()}}


NEW = run_with(motion='lively', font='Noto Sans')


def edit_plan(store, fn):
    doc = json.loads(store.files[PLAN])
    fn(doc['document'])
    store.files[PLAN] = json.dumps(doc).encode('utf-8')
    edit_session(store, lambda s: s.update(accepted=accepted(doc['document'])))   # the changed plan accepted again, as the operator would


def edit_session(store, fn):
    s = json.loads(store.files['run-1/visuals/session.json'])
    fn(s)
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


def brief(store=None, run=NEW):
    return VS.motion_brief(store or motion_store(), run, [], 'MO1')['brief']


def upload(store, run=NEW, rules=RULES):
    return VS.set_motion(store, USER, run, [], 'MO1', 'shot.zip', zipped(project()), rules)


def verdict(sha, run=NEW, store=None):
    return VS.motion_verdict(store, USER, run, [], {'shot_id': 'MO1', 'sha256': sha, 'round': 1,
                                                     'rules': [{'rule': r['rule'], 'pass': True} for r in P.rules_of(RULES)]})


# ---------- S1: no brief before the motion style and the font ----------

def test_no_brief_while_the_font_is_not_chosen_and_the_refusal_says_how_to_ask():
    with pytest.raises((Problem, ValueError)) as e:
        g(lambda: brief(run=run_with(motion='lively')))
    assert 'This film has no font yet' in str(e.value) and '`vw visuals next`' in str(e.value)   # release 1 of 27 Nov 2026, phase 3 part A: the font is asked by the server's card; "Other" is retired


def test_no_brief_while_the_motion_style_is_not_chosen():
    with pytest.raises(Problem, match='no motion style yet'):
        g(lambda: brief(run=run_with(font='Noto Sans')))


def test_a_film_with_both_choices_and_an_older_film_get_their_brief():
    assert brief(run=NEW).startswith('# Brief: drawn shot MO1')
    assert brief(run=MRUN).startswith('# Brief: drawn shot MO1')   # a film without a film record passes as today


# ---------- row 14: nothing empty or defaulted printed as a fact ----------

def test_empty_values_are_left_out_never_printed_as_none_or_a_dash():
    store = motion_store(sh=motion_shot(depicts='', purpose='', framing=None, appearance='', message='', information_progression='',
                                        drawing_spec={'parts': ['inner leaf'], 'dimensions': [{'part': 'leaf', 'measure': 'thickness', 'value': 110, 'unit': 'mm', 'source': 's', 'status': ''}],
                                                      'relationships': [], 'proportions': [], 'label': ''}))
    edit_plan(store, lambda d: d['foundation'].pop('appearance'))
    b = brief(store)
    assert 'None' not in b and ' -' not in b and '-;' not in b and '(given)' not in b
    for word in ('Shows:', 'Framing:', 'Appearance:', 'Message:', 'Progression:', 'relationships', 'proportions', 'label "'):
        assert word not in b, word
    assert 'sizes leaf thickness 110 mm.' in b   # a size with no status gets no word


def test_an_unknown_size_says_so_with_no_number():
    b = brief()
    assert 'cavity width unknown (no figure)' in b and 'leaf thickness 110 mm (confirmed)' in b and 'None' not in b


def test_the_palette_is_said_approved_only_once_a_gap_was_accepted():
    assert 'Palette (approved): terracotta #B5543A, paper #F4EDE1.' in brief(motion_store())
    doc = {'foundation': {'graphic_style': {'palette': 'terracotta #B5543A'}}, 'gaps': []}
    assert VS.palette_line(doc, {'accepted': {}}, 'MO1') == 'Palette (not yet approved): terracotta #B5543A.'   # a brief needs an accepted gap, so only the line itself shows it
    assert VS.palette_line(doc, {'accepted': {}, 'shared_pending': {'G1': {}}}, 'MO1') == 'Palette (approved): terracotta #B5543A.'


def test_the_letter_size_is_for_labels_in_the_brief_and_the_skill():
    b = brief()
    assert 'every label at least 2.6 % of the frame height, inside the inner 90 %' in b and 'text at least 2.6 %' not in b
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'every label at least 2.6 % of the frame height' in skill and 'text at least 2.6 %' not in skill


def test_each_subject_rule_names_where_it_comes_from():
    store = motion_store(sh=motion_shot(narration='In rat-trap bond, providing a solid course at sill level improves strength.'))
    store.files['subject-rules/rat-trap-bond.json'] = json.dumps([{'rule': 'A window opening has a lintel bearing on both sides.', 'run': 'VW-12'},
                                                                  {'rule': 'Header bricks show their short face.'}]).encode('utf-8')
    b = brief(store)
    assert 'Subject rules (rat-trap-bond), from the subject file rat-trap-bond.md: every one holds in this drawing.' in b
    assert 'Subject rules (rat-trap-bond), added on film VW-12: every one holds in this drawing.\n- A window opening has a lintel bearing on both sides.' in b
    assert 'Subject rules (rat-trap-bond), added by an operator: every one holds in this drawing.\n- Header bricks show their short face.' in b


# ---------- row 4: the confirmed sizes of the shot's things; a real thing needs a proportion or a known size ----------

TILE = {'id': 'E2', 'name': 'Tile', 'kind': 'material', 'identity': 'representative', 'requirements': 'a clay tile',
        'material_spec': {'parts': ['tile'], 'laid': 'flat', 'pattern': 'single', 'proportions': ['length about twice the width'],
                          'dimensions': [{'part': 'tile', 'measure': 'length', 'value': 410, 'unit': 'mm', 'source': 'maker sheet', 'status': 'confirmed'},
                                         {'part': 'tile', 'measure': 'depth', 'value': None, 'unit': 'mm', 'status': 'unknown', 'tried': 'x'}]}}


def test_the_brief_prints_the_sizes_confirmed_on_the_things_it_shows_before_the_spec():
    store = motion_store(sh=motion_shot(element_ids=['E1', 'E2']))
    edit_plan(store, lambda d: d['elements'].append(TILE))
    b = brief(store)
    line = 'Confirmed for the things in this shot: Tile: sizes tile length 410 mm (confirmed); proportions length about twice the width'
    assert line in b and 'tile depth' not in b   # only confirmed or measured sizes
    assert b.index('Confirmed for the things in this shot') < b.index('Drawing spec, view')
    assert 'Confirmed for the things' not in brief()   # a shot whose things have no spec: no line


def test_a_diagram_of_a_real_thing_needs_a_proportion_or_a_known_size():
    bare = VC.DrawingSpec.model_validate({'parts': ['tile'], 'dimensions': [{'part': 'tile', 'measure': 'length', 'value': None, 'unit': 'mm', 'status': 'unknown', 'tried': 'x'}],
                                          'illustrative': True, 'label': 'illustrative, not to scale'})
    with pytest.raises(ValueError, match='has no proportion and no known size. Add the proportions that matter'):
        VC.spec_research_needs('shot D1', bare, real_thing=True)
    VC.spec_research_needs('shot D1', bare)   # not a real thing: as before
    VC.spec_research_needs('shot D1', bare.model_copy(update={'proportions': ['about 2 : 1']}), real_thing=True)
    plan = {'elements': [TILE, {'id': 'E1', 'kind': 'graphic'}]}
    assert VS.draws_real_thing(plan, {'graphic_kind': 'diagram', 'element_ids': ['E2']})
    assert not VS.draws_real_thing(plan, {'graphic_kind': 'chart', 'element_ids': ['E2']}) and not VS.draws_real_thing(plan, {'graphic_kind': 'diagram', 'element_ids': ['E1']})
    src = Path(VS.__file__).read_text(encoding='utf-8')
    assert src.count('real_thing=draws_real_thing(plan, ') == 2   # both approval paths: one spec, and all specs at once


# ---------- row 6: the order ----------

def test_the_brief_reads_what_it_shows_then_facts_text_timings_pictures_fonts_rules_style():
    store = motion_store(sh=motion_shot(narration='In rat-trap bond, providing a solid course at sill level improves strength.'))
    b = brief(store)
    heads = ['Shows:', 'Claims (', 'Drawing spec, view', 'Text on screen', 'Length: exactly', 'Narration (', "Each word's start", 'Progression:',
             'Pictures you may place', 'Palette (', 'Fonts:', 'Rules: GSAP', 'Motion style (', 'Subject rules (']
    at = [b.index(h) for h in heads]
    assert at == sorted(at), [h for h, a, n in zip(heads, at, at[1:] + [10 ** 9]) if a > n]


# ---------- S3: the brief the rules were written from ----------

def test_the_upload_keeps_one_fingerprint_per_brief_line_beside_the_rules():
    store = motion_store()
    sha = upload(store)['sha256']
    row = VS.session_of(store, NEW, [])['motion_projects'][sha]
    assert {'Fonts', 'Palette', 'Drawing spec', 'Motion style', 'Rules', 'Text on screen'} <= set(row['brief']) and len(row['rules']) == 2
    assert row['brief'] == VS.motion_brief(store, NEW, [], 'MO1')['lines']


def test_a_verdict_on_rules_from_an_older_brief_is_refused_and_names_the_line():
    store = motion_store()
    sha = upload(store)['sha256']
    later = run_with(motion='lively', font='Inter')   # the font changed after the rules were written
    with pytest.raises((Problem, ValueError)) as e:
        g(lambda: verdict(sha, run=later, store=store))
    assert 'the brief changed after these rules were written, in the line(s): "Fonts"' in str(e.value)
    assert 'Read the rules of this drawing again against the new brief' in str(e.value) and '`vw motion upload --shot MO1`' in str(e.value)
    edit_session(store, lambda s: s.update(added_colours={'walls': {'thing': 'walls', 'colour': '#5A524C', 'words': 'dark warm grey', 'shots': ['MO1']}}))
    with pytest.raises((Problem, ValueError), match='"Palette"'):
        g(lambda: verdict(sha, store=store))
    upload(store)   # the same project uploaded again with its rules: the brief is stamped again, no new command
    assert verdict(sha, store=store)['failed'] == []


def test_brief_changed_names_changed_added_and_removed_lines_in_order():
    assert VS.brief_changed({'A': '1', 'B': '2', 'C': '3'}, {'A': '1', 'B': '9', 'D': '4'}) == ['B', 'D', 'C']
    assert VS.brief_changed({'A': '1'}, {'A': '1'}) == []


# ---------- row 15: a note or a question is not a rule ----------

def test_list_lines_under_a_questions_or_notes_heading_are_found():
    text = ('# Rules\n1. The course is solid.\n  the note sits low (a wrapped line, not a heading)\n2. The leaves match.\n\n'
            '## Questions for the operator\n- Is the sill 230 mm?\n**Notes**\n* The client said tiles.\nColours to add:\n- walls #5A524C\n')
    assert P.notes_in(text) == ['- Is the sill 230 mm?', '* The client said tiles.', '- walls #5A524C']   # the critic's A3 (test_design221_p1b_pure): "Colours to add" too
    assert P.notes_in(RULES) == [] and P.notes_in('Note: one line\n1. a rule') == []   # a line that is no heading changes nothing


def test_an_upload_with_a_question_in_its_rules_is_refused():
    with pytest.raises((Problem, ValueError), match='A note or a question is not a rule: move these lines to questions.md'):
        g(lambda: upload(motion_store(), rules=RULES + '\n## Questions\n- Is the sill 230 mm?\n'))


# ---------- rows 20, 21, 15, 14 (S3), 22: the texts ----------

def visuals():
    return next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')


def test_the_wording_script_is_applied_once_and_says_each_change():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221_wording_v3 as W
    import fixset2_wording as FIX2   # fix set phase 2: sentences added inside this script's sentences, and one replaced
    import rel27nov_wording as R27   # release 1 of 27 Nov 2026, phase 3 part A: the font sentence of this script is replaced (the server's card asks the font)
    stage = FIX2.before(R27.before(visuals()))
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and olds[where].count(old) == 1, old[:50]
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(new) == 1, file
    later, common = texts['later'], texts['common']
    assert "never in frame numbers of the whole film" in common                                   # row 6
    assert '"Step 6, pictures and drawn graphics"' in later and '"Step 7, AI video (in the chat)"' in later   # row 21
    assert 'the font comes first: run `vw font` before any brief' in later                       # row 20
    assert 'questions.md' in later and 'a question about a fact is put to the operator once' in later   # row 15
    assert 'the refusal names the changed line' in later                                         # S3
    assert '`vw log --kind answer "<their words>"`' in later and 'logged as theirs (kind `answer`)' in later   # row 22
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    for old in (W.FONT_OLD[:70], 'when the brief leaves a fact open, show the operator rules.md', 'list it at the end under "Questions for the operator"'):
        assert any(r in old or old in r for r in retired), old


def test_the_rule_writer_writes_no_rule_the_server_checks_and_its_questions_apart():
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert "the font, the frame size, the length, the frame rate, the sound, the second each cued element appears, a label's wording and the letter size" in rules
    assert 'Write no "no colour outside the palette" rule while the brief marks the palette "not yet approved"' in rules
    assert 'carries no number the brief does not give' in rules and "a chart's bars start from zero" in rules and 'masonry' not in rules
    assert 'work/motion/<shot>/questions.md' in rules and 'Questions for the operator' not in rules
    shot = (ROOT / 'plugin' / 'agents' / 'vw-motion-shot.md').read_text(encoding='utf-8')
    assert 'read `rules.md`' in shot and 'read `brief.md`' in shot   # the builder's agent file agrees with the skill
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert '`questions.md` beside them' in skill and 'a question about a fact goes to the operator once' in skill


def test_the_chats_ai_video_items_say_step_7():
    src = Path(C.__file__).read_text(encoding='utf-8')
    assert "'Step 7, AI video: the still'" in src and "'Step 7, AI video: the take'" in src and "'Step 7, AI video: a layout that did not pass its check'" not in src   # release 1 of 27 Nov 2026, phase 4 part A: the held-layout card is retired too
    assert "'Step 7, AI video: the layout drawing of the shot'" not in src   # A1 (25 Nov 2026): that card is retired; the held layout's card is the layout card left
    assert "'AI video, the" not in src


def test_a_verdicts_log_line_carries_the_round_the_counts_and_the_failed_rules():
    store = motion_store()
    sha = upload(store, run=MRUN)['sha256']
    rules = [{'rule': r['rule'], 'pass': i == 0, 'where': 'left'} for i, r in enumerate(P.rules_of(RULES))]
    out = VS.motion_verdict(store, USER, MRUN, [], {'shot_id': 'MO1', 'sha256': sha, 'round': 2, 'rules': rules})
    assert out['log'] == 'round 2: 1 of 2 rules failed: "The two leaves are the same thickness."'
    e = L.entry_from('/api/runs/' + '0' * 36 + '/visuals/motion/verdict', {'shot_id': 'MO1'}, 200, out)
    assert e['entry'] == 'visuals/motion/verdict: round 2: 1 of 2 rules failed: "The two leaves are the same thickness."' and 'shot_id MO1' in e['about']


def test_a_refusal_by_the_form_check_keeps_its_reason_in_the_log():
    detail = {'detail': [{'type': 'too_long', 'loc': ['body', 'at'], 'msg': 'List should have at most 12 items after validation, not 14'},
                         {'type': 'too_long', 'loc': ['body', 'crops'], 'msg': 'List should have at most 6 items after validation, not 8'}]}
    e = L.entry_from('/api/runs/' + '0' * 36 + '/visuals/motion/tool', {'shot_id': 'MO1'}, 422, detail)
    assert e['kind'] == 'refusal' and e['rule'] == '422'
    assert e['entry'] == ('visuals/motion/tool refused: at: List should have at most 12 items after validation, not 14; '
                          'crops: List should have at most 6 items after validation, not 8')
    assert L.entry_from('/api/runs/' + '0' * 36 + '/visuals/x', {}, 409, {'code': 'C', 'message': 'Because.'})['entry'] == 'visuals/x refused: Because.'


def test_the_operators_answers_in_the_visuals_stage_are_logged_as_theirs():
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "TEXT_STAGES = ('intake', 'brief', 'script', 'visuals')" in vw
    assert L.assistant_entry('r', 'visuals', {'text': 'Use the tile', 'kind': 'answer'})['by_kind'] == 'operator'
