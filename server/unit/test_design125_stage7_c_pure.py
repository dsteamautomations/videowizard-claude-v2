"""design/125 stage 7, builder C: the version 3 wording of the options, master, first-cut and visuals stages.
P2 labels; P7 one chapter a scene; P9 rule 3; P13 an AI-only scene is one blank; O7 two parts of one clip in a scene; O1-O3 scene numbers and
second choices; O4-O6 the second look by helpers; O9 the plan's named helper; P14 the first slide answer approves; the first-cut record retired.
Every stage's words the same or fewer (scripts/d125_stage7_wording_v3.py)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))['stages']}
V3 = {s['name']: s for s in json.loads((ROOT / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']}
BEFORE = {'options': 1963, 'master': 478, 'first_cut': 53, 'analysis': 329, 'visuals': 19576}   # release 4 (+37, SK 20 Nov): the guide's first frame first, its video behind it; each still ordered as soon as its first frame is ready; the video needed only for the take. Before: 19539: release 2, the critic's points 2 and 8 (+46, 20 Nov): one verdict for each scene; a layout whose third check in a row fails is held and the operator is asked. Before: 19493: release 2, B4 and B4b (+67, SK 20 Nov): several still end-frames or layout drawings ready together come as a group, side by side in one message, one question for each. Before: 19426: release 1, a layout is checked before its card is shown (+33, SK 20 Nov): the operator is asked about a layout only after a fresh checker passed it, the checkers of the layouts started together, only layouts that passed are shown. Before: 19393: release 1, the critic's point 10 (+10, 20 Nov): a held drawing and `select` are one click, "No finished take is asked one by one". Before: 19383: release 1, B1 and D (+154, SK 20 Nov): one click against the check (no second question, no typed reason), the checkers started together, the cards of step 7 in two batches, a still's 16 pictures and the cost limit, the form of `changed_from_plan` (D4b). Before: 19229: release 1, section A (+77, SK 20 Nov): a rule or a line answered "na" (it does not apply, with why), recorded once; step 7's still checked by Claude before its card. Before: 19152: fix set, the page (+68, SK 20 Nov): the page's link given only when `vw visuals page --shown` prints it, a page of an older tool published again as soon as the tool says so, a publish that fails or goes to another link never a new page. Before that: fix set, the critic's points (+94, 19 Nov): a shot whose only text is the corner note or a logo has carries_text false (the sentence "is not asked for labels" replaced); the round's list also names the musts that passed; the still of a drawing that continues another started once the earlier still is approved, with that still beside the brief. Before that: fix set phase 3 (+107, SK 19 Nov): the stills ordered in one call from the file one helper writes, shown with every field as text; a still another picture is made from; the frame limit of a snapshot call; the corner note and a logo are no carried text. Before that: fix set phase 2 (+411, SK 19 Nov):the helpers started together, the stills first in the order of the film, a rule that compares with another drawing (a note until there is something to compare with, due later), the round's rule list, every shape that repeats and its counts, the parts helper's open choices, a still with no rule a still can show. Before that: design/222 (+175, SK 19 Nov): step 7 on the page: Claude checks each take from frames, the takes answered on the page once all are made and checked, "Make another" is the word for a second take. Before that: design/221 phase 4, rows 18 and 19 (+299, SK 19 Nov): step 6 answered on the page once everything is made; the line of counts said as it is, asking nothing; a finished drawn graphic shown once in the chat; each drawing rendered as soon as it passes; the held drawing a chat card (select with a reason, reject, one more round once); the stills ordered at the start. Before: design/221 phase 3c, row 3 (+224, SK 19 Nov): every drawn shot built first as a still end-frame, checked on the musts a still can show, approved in the chat before the motion. Before: design/221 phase 3c, row 1 (+198, SK 19 Nov): the shared parts of a film with two or more drawn graphics drawn once by one helper and approved in the chat before any brief; a changed part rendered again, not rebuilt. Before: design/221 phase 3b (+62, SK 19 Nov): shots of one diagram built in order, the others side by side; the earlier drawing's passed project and last frame beside a continuing shot's brief. Before: design/221, the critic's seven points on phase 2 (+111, SK 19 Nov): the labels and cues of every drawn shot in the plan with the plan, before the first brief; a clean verdict binds the passed project, no plan revision per drawing. Before: design/221 phase 3a (+341, SK 19 Nov): one camera flow per drawn shot, by what the explanation is doing; the shared look recorded once before the first brief, a choice with a fact asked once with the others; the film's motions binding, with one send-back. Before: design/221 phase 2 (+221, SK 19 Nov): the same set of frames for every check and the last frame of the shot a drawing continues from; must and should, only a failed must sends a drawing back; "not seen" answered by the same checker in the same round; rounds 2 and 3 answer what failed and what the fix touched; a short label of this shot only is a must; the corner note drawn by the server, never in the labels. Before: design/221 phase 1 (+221, SK 19 Nov): the progression in seconds from the shot's start; step 6 and step 7 named apart; the font first, no brief before it; the rule writer's questions in questions.md, decided by Claude, a question about a fact asked once before the first build; a verdict on rules from an older brief refused, naming the line; the operator's answers logged as theirs. Before: design/220 (+81, SK 19 Nov): when the look says use for every first set the server orders the others itself, else they wait for the operator's word and that set is shown first. Before: design/218b (+192, 18 Nov): the spec wins over a note or an added colour, a note withdrawn with --remove; a part seen from another direction is the same part, never asked, recorded with `vw motion note`; only two approved specs that truly contradict are asked. Before: design/218 (+227, 18 Nov): a missing neutral colour chosen by Claude and recorded (`vw motion colour`), never asked; the font question shows `vw font --sample` first; step 6 answered on the page, a chat card only for a question the server asks there; a graphic sequence reviewed at step 6. Before: design/217 (+281, 18 Nov): Claude checks the step-6 pictures (`vw visuals pictures --looks`, helpers above five, not checked after 30 minutes), step 6 answered on the page, the fix round retired for Correct it, a component approved by the check, the style sheet only with a graphic in steps, repeated background figures a line of the check, a fact check answering every rule the server holds. Before: design/216b (+99, 18 Nov): for a place, `things` with the proposal and `vw visuals round --things`. Before: design/216 (+39, 18 Nov): the page's `say` posted with the link unchanged, and `preparing` said before `vw visuals page --fetch`. Before: design/215 (+312, 18 Nov): the references fix set: the three labels for "Leave out", how the making goes, no cost word (also in a reason), an unticked picture, one order of authority, the corrections kept per thing, the search record, the older rules that do not read a set, the look and an object in use by category. Before: design/214 (+80, 18 Nov): Claude checks the sets: the look answers each picture's check list from what it sees, a drawn fact against the drawing sheet, "not checked" for a picture it could not open; no model checks a set; design/213 (+382, 17 Nov): the sets screen in the new layout and the corrections of step 5; design/212 (+134, 17 Nov): step 1 of the references in its new layout: the five groups in their order, the buttons by the case of the thing, a Keep tick on each footage picture, a person the footage does not show not asked, and no cost shown at the references (the sentences on a price on a button are replaced); design/211, the review (+269, 17 Nov): the step list names the rebuilt way (the digest, the looks, each row a proposal), the views by kind (a material's own; a way of working as the action or the change, hands and a tool allowed, never required; a default view the plan already shows left out), the order of authority in a request, what a helper is given (its group, its ids, the run folder's path, the tool's command line), the judging points and the file's shape with the listing, the proposals saying which sets are made first, a make with no picture not counted, a round file sent again bringing back only what is new or changed, no set by the image command; design/211 (+722, 17 Nov): the references step rebuilt: the footage searched by looks (the digest, trial frames, the helpers, the server's frame rule), each row of the round a proposal with its reason, the views by kind, the first three sets and then the others, the looks at the made sets, the rewrite after No or Correct it (three makes at most), the proposals and the doubtful things first on the page, an older round named; the design/210 wording review (+74, 16 Nov): each step sent to where it is answered (the page, then the chat), the picture search in the order it is done, the wait between the round's two steps, Done on step 1 not undone, an offered choice left to the operator; design/210 part 2 (+170, SK 16 Nov): the reference round's two steps answered on the page, each in one visit, a paid answer with its price on its button, the operator's own picture given on the page, the chat where the page cannot be shown; design/210 (+102, SK 16 Nov): the reference drawings approved on the page with their pictures, which `vw visuals page` also sends, the chat where the page cannot be shown; design/209 (+99, SK 16 Nov): the drawings and the materials approved on the page after the plan, in one visit, each size asked once, the chat where the page cannot be shown; the review of design/207 (+53, 16 Nov): no link to the server's visuals page, who sets the cost limit, the permission after the plan is proposed, people who read alike named at the check, "not to scale" with every size known, a refusal the server does not make removed; design/207 (+1,031, SK 16 Nov): the visuals rules after SK's review: any kind of AI video with the known weak cases, clothes over time, own likeness or a stand-in, the world rule, ten named people, the same set-up not twice and a reuse kept without the operator, a drawing to scale, framing as instructions, the check's checklist, the page for the treatment and the plan, the cost limit by length, examples for every kind of film; design/206 (+99, SK 16 Nov): the plan answered on the page in one visit, the card where it cannot be shown; design/205 (+108, SK 15 Nov): the Direction alone first, the motion style on the page, a still that must be read, beats by the film's turns; design/204 (+86): the treatment answered on a page, the card where it cannot be shown; design/203 (+206): the Direction in six parts and a second Direction that differs in kind; design/202 (+150): the narration alone, action first, the two reasons of every shot, words on the picture by category;   # design/200 accurate images (+292): a thing drawn before the round, the shot's drawing before the still, the look reference; words read by the assistant; design/127 added round 2 (B-roll), alternatives and the shot answers (SK); design/189 the answers file's shape (+77), design/193 each piece's own lines and two rules (+90), the model's name (+1), design/195 a flagged piece may be used (+54, SK 14 Nov); visuals: design/188 the decisions in the chat, design/190 the card, design/191 the shared change asked once (+384); design/130 added section 11, the HyperFrames route and its fact check, 261 words (SK approved design/130), and §12 the motion default, 27 words (SK, 1 Nov); design/148 A3 the helper's file as proof, 21 words (SK, 3 Nov); design/149 Set B (B1, B2, B4-B7, B9), 250 words, and B10, 80 words (SK, 3 Nov); design/150 Set C (treatment limits, one clip per gap), 50 words (SK, 3 Nov)


def texts(stage):
    s = V3[stage]
    return [s.get('prompt') or '', *(s.get('steps') or []), *(p['text'] for p in s.get('parts') or [])]


def words(stage):
    return sum(len(t.split()) for t in texts(stage))


def rule(n):
    p = V3['options']['prompt']
    return p[p.index(f'\n{n}. ') + 1:p.index(f'\n{n + 1}. ')]


def test_every_stage_is_the_same_length_or_shorter():
    for stage, before in BEFORE.items():
        assert words(stage) <= before, (stage, words(stage), before)


def test_p2_no_change_history_labels_and_the_rule_codes_kept():
    for stage in ('options', 'master', 'first_cut'):
        assert all('design/' not in t for t in texts(stage)), stage
    o = '\n'.join(texts('options'))
    for code in ('R1', 'R5', 'B1', 'N14', 'N17'):   # design/139 R9: E1, E2 and rule 11 are gone
        assert code in o, code


def test_p7_retired_by_design126_op2_a_scene_lists_every_chapter():
    assert 'a scene covers one chapter' not in V3['options']['steps'][1]
    assert 'list every chapter the paragraph covers; split a paragraph only when the operator asks' in V3['options']['steps'][1]


def test_p9_rule_3_an_abstract_idea_has_nothing_to_show_and_is_no_longer():
    r3 = rule(3)
    assert 'have no exact match: a blank, or round 2 B-roll only where the words make no specific claim' in r3 and 'camera can see is matched like any other' in r3   # design/127: B-roll moved to round 2
    old = V2['options']['prompt']
    old3 = old[old.index('\n3. ') + 1:old.index('\n4. ')]
    assert len(r3.split()) <= len(old3.split())


def test_p13_an_ai_only_scene_is_one_blank_and_a_declared_gap_is_refused():
    p = V3['options']['prompt']
    assert "one blank of the scene's length" in p and 'declaring a gap is refused' in p and 'declared in `gaps`' not in p


def test_o7_a_later_part_of_the_same_clip_in_the_same_scene():
    r4 = rule(4)
    assert 'same scene' in r4 and 'not overlapping' in r4 and 'side by side at the same shot size' in r4 and 'note of kind reuse' in r4
    assert 'including another part of the same clip' not in r4


def test_o4_o6_the_second_look_between_check_and_propose():
    s = V3['options']['steps'][3]
    for needle in ('`vw options second-look`', 'work/options/scenes/', '`vw-scene-review`', 'out/second-look/', '`vw options join-second-look`'):
        assert needle in s, needle
    assert s.index('until valid') < s.index('second look') < s.index('vw options propose')


def test_o9_the_plan_names_its_helper():
    plan = next(p for p in V3['visuals']['parts'] if p['name'] == 'plan')['text']
    assert '`vw-plan-gaps` helper' in plan and 'your own agents' not in plan


def test_p14_the_first_slide_answer_approves_and_the_explicit_record_is_gone():
    o = '\n'.join(texts('options'))
    assert 'remains for an explicit approval' not in o and 'record with their yes' not in o and 'vw options record' not in o
    assert 'the first answer approves the options' in V3['options']['steps'][4] and 'the first answer approves the options' in V3['master']['steps'][0].lower()


def test_the_first_cut_record_is_retired_in_one_line():
    (step,) = V3['first_cut']['steps']
    assert 'vw first-cut record' not in step and 'retired' in step and '`vw master record`' in step and len(step.split()) <= 20


def test_p3_the_steps_name_the_pieces_by_scene():
    s0 = V3['options']['steps'][0]
    assert 'pieces-' in s0 and 'cards-1.json' not in s0 and 'sub-clips-1.json' not in s0 and '`vw options show --sub' in s0
    assert 'cards-N.json' not in V3['options']['steps'][3]


def test_version_2_is_untouched():
    assert '`vw options record --quote "<their yes>"` remains for an explicit approval' in V2['options']['steps'][4]
    assert 'design/44' in V2['first_cut']['steps'][0] and 'between 2 and 3' in V2['master']['steps'][0]
