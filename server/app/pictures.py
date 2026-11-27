"""design/217 (SK, 18 Nov 2026): step 6, "Pictures and drawn graphics", on the decisions page, and Claude's check of its pictures.

Two parts, one source each:
- Claude's check (C1-C7): a still, a step of a graphic, the style sheet, a component and a remade picture of a film whose reference round
  is v2 are no longer read by a model on the server. The server builds each picture's check list (`lines`), Claude answers every line
  (`looks_due`, `record_looks`), and a picture is offered to the operator only with its look recorded, or after PICTURE_LOOK_MINUTES as
  "not checked" (`offered`). The program's own measurements stay, as advice (`advice`).
- The lines of the step: one per item that waits (a question, the style sheet, a still, a graphic in steps, a drawn graphic), in the shape
  of design/217-contract.md section 3, built once here; the chat (`chat_flow._waiting_items`) says the same words from the same line.

Nothing here changes a film whose round is not v2: such a film's pictures keep the check of before and the chat.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from fractions import Fraction

from . import image_check, ref_find, visuals_stage as V

PICTURE_LOOK_MINUTES = 30   # C3: a picture whose look never comes is offered as "not checked" after this long; ponytail: one number, tune it on the first film
LOOK_KINDS = ('style', 'keyframe', 'state', 'component', 'isolated')   # the critic's point 7: an isolated picture is a made picture too: no made picture of steps 6 and 7 goes to the model
LOOK_SAY = 300   # a look's sentence, at most (ref_find.SEEN_CHARS)

# ---------- the words: the page and the chat say these ----------
W = {
    'step': 'Pictures and drawn graphics',
    'kind_question': 'A question about a picture already made', 'kind_style': 'The style sheet', 'kind_still': 'A still', 'kind_steps': 'A graphic in steps', 'kind_drawn': 'A drawn graphic',
    'kind_component': 'A component',
    'style_name': 'The look of the graphics',
    'style_sub': 'One picture that sets the colours, lines and lettering of every graphic in the film.',
    'q_from': 'The server asks this about a picture already made. Nothing is made until you answer.',
    'ask_style': 'Is this the right look for the graphics?', 'ask_still': 'Is this picture right for this shot?', 'ask_steps': 'Are these {n} steps of the graphic right?',
    'ask_drawn': 'Is this drawing right for the film?',
    'yes_style': 'Yes, use this look', 'yes_still': 'Yes, put it in the film', 'no': 'No, make another', 'correct': 'Correct it',
    'yes_steps': 'Yes, use all {n} steps', 'correct_step': 'Correct {n}', 'select': 'Select: use it in the film', 'reject': 'Reject', 'plain': 'Take the effect away',
    'say_style': 'Approved. The first picture of every graphic is made from it.', 'say_still': 'Approved and placed in the film at {at}.',
    'say_no_style': 'Rejected. Claude asks for a new style sheet.', 'say_no_still': 'Rejected. Claude asks for {which} picture for this shot.',
    'say_no_still_n': 'Rejected. Claude asks for {which} picture.',
    'say_fix_style': 'Rejected. Claude asks for a new one with your words: "{words}"', 'say_fix_still': 'Rejected. Claude asks for a new picture with your words: "{words}"',
    'say_steps': 'All {n} steps approved and placed in the film at {at}, played as a build.',
    'say_step': 'Step {k} is made again with your words: "{words}". {later} made again from it.', 'say_step_last': 'Step {k} is made again from step {p} with your words: "{words}".',
    'say_select': 'Selected. It goes in the film at {at}.',
    'say_reject': 'Rejected. Claude\'s helpers rebuild it with your words: "{words}"', 'say_plain': 'It is made again without the {finish}. You see it again here.',
    'say_answer': 'Your answer: {choice}. Claude acts on it.',
    'hint_style': 'What should change?', 'hint_still': 'What should change in this picture?', 'hint_step': 'What should change in step {n}?', 'hint_reject': 'What is wrong with it?',
    'go': 'Send these words',
    # release 1, B1 (SK, 20 Nov 2026): one click. The second box ("Use it all the same?", "Go back") and the typed reason of a held drawing are retired
    # (design/35 rows 275, 276): the warning is in view before the buttons, and Yes or Select records at once as approved against the check
    'against_note': "Used all the same: the operator's one click, with the warning in view.", 'log_against': 'approved against the check: {faults}',
    'log_against_drawn': 'selected against the check: {why}',
    'where': 'In the film at {start} to {end} ({secs} s) · {gap}', 'words_head': 'Voiceover:', 'no_voiceover': 'no voiceover under this shot',
    'gap_comment': 'A comment means something should change: the gap is then not recorded, whichever button you press.', 'try': 'Try {n}',
    'foot_still': 'Your footage: click one to see it beside the new picture', 'foot_still_try': 'Your footage and the earlier try: click one to see it beside the new picture',
    'foot_steps': 'Your footage: click one to see it beside the steps', 'foot_steps_try': 'Your footage and the earlier try: click one to see it beside the steps',
    'foot_drawn': 'Your footage: click one to see it beside the drawing',
    'strip_head': 'The steps, in order: click one to see it large',
    'before': 'Your footage before this shot', 'after': 'Your footage after this shot', 'new': 'The new picture',
    'earlier': 'Try {n}, not used', 'earlier_step': 'Step {s}, try {n}, not used', 'why': 'You said: {words}', 'why_none': 'You said no, with no words.',
    'step_cap': "Step {n}: on '{words}': {what}", 'step_cap_bare': 'Step {n}: {what}', 'step_label': 'Step {n}',
    'sheet': 'Its frames, in order', 'video': 'The drawing, playing', 'video_none': 'The video is not available here: these are its frames.',
    'finish': 'Added by the server: {finish}.',
    'held_fact': 'Its fact check did not pass. Select uses it all the same.', 'held_none': 'It has no fact check yet. Select uses it all the same.',
    'held_server': "The server's check did not pass it. Select uses it all the same.", 'held_unread': 'It was not checked. Select uses it all the same.',
    'held_short': 'It is shorter than its place in the film. Select uses it all the same.',
    # the check line (3.8)
    'pass': "Claude's check found nothing wrong", 'fail': "Claude's check found {problems}: {first}",
    'late': "Not checked: Claude's check did not come within {m} minutes. Judge it by eye.", 'unopened': 'Not checked: Claude could not open the picture. Judge it by eye.',
    'none': 'Not checked: no check was run on this picture. Judge it by eye.',
    # release 1, A5: the lines that did not apply, listed apart; a list where every line did not apply is not a check
    'na_head': '{n} lines did not apply', 'na_head_one': '1 line did not apply',
    'all_na': 'Not checked: every line of its list was answered "does not apply". Judge it by eye.',
    'all_na_rules': 'Not fact-checked: every rule was answered "does not apply". Judge it by eye.',
    # release 1, B3 (SK, 20 Nov 2026): the one short line of a check, for the closed box of the page and for the chat
    'short_pass': 'Passed', 'short_note': 'Passed, 1 note', 'short_notes': 'Passed, {n} notes', 'short_warn': '1 warning: {name}', 'short_warns': '{n} warnings: {name}',
    'by':'Claude looked at the picture against its list of {n} lines.', 'by_steps': 'Claude looked at each step against its list: {ns} lines.',
    'by_older': 'Gemini 3.8 Flash read the picture against its list of {n} lines.',
    # release 1, A2: who really checked. A picture the model checked before Claude's look took over keeps that check and says so: never "Claude's check" over a model's result
    # release 1, A7: "a real face" in Claude's list. The operator's permission for a person of the footage is the record of design/207 and 213 (visuals_stage.likeness)
    'face_when': 'no face that matches a real person in the footage pictures sent as references',
    'face_ok': ', other than {names}, whom the operator has permitted the film to show: a match with {names} is not a fault',
    'face_made': "; a face that matches the film's own made references is never a fault",
    'person_ask': ('{name} ({eid}) is a real person who speaks in the film, a made picture shows them, and the operator has not been asked: ask the operator once whether '
                   'they have this person\'s permission, and record their words (`vw visuals likeness --element {eid} --quote "<their words>"`; for a stand-in: add `--stand-in`).'),
    'face_ask': ('{name} ({eid}) is a person of the footage, a made picture shows them, and the operator has not been asked: ask the operator once whether made pictures may '
                 'show this person, and record their words (`vw visuals likeness --element {eid} --quote "<their words>"`; for No: add `--stand-in`). Until then a face '
                 'that matches them is a warning.'),
    'who_model': 'An earlier check by Gemini 3.8 Flash', 'who_mixed': 'The checks', 'check_head_step_model': "Gemini 3.8 Flash's check of step {n}:",
    'passed_head': 'The lines it passed', 'advice_head': 'Measured by the program, for you to judge', 'check_head': "Claude's check of this picture:", 'check_head_step': "Claude's check of step {n}:",
    'fact_pass': 'Fact check: passed. All {n} rules held, after {r}.', 'fact_fail': 'Fact check: not passed. {k} of {n} rules are still open after {r}:',
    'fact_none': 'Not fact-checked yet.', 'fact_stale': 'Fact check: not passed. The brief changed after its rules were written:',
    'fact_pass_notes': 'Passed, {k}. Every must rule held, after {r}. A note is not a fault: it needs no reason to select.', 'not_seen': 'Not seen yet ({need}): {rule}', 'fact_by': 'A Claude checker that never saw the build judged {n} rules on snapshots of the video.',
    'fact_passed_head': 'All {n} rules of the fact check (round {round})', 'fact_saw': 'What the checker saw', 'passed_rule': 'Passed: {rule}',
    'server_pass': "The server's check: passed.", 'server_fail': "The server's check: not passed. {k} lines are still open:", 'server_none': 'Not checked yet.',
    'alike': 'Steps {a} and {b} look almost the same: the change between them is small.',
    'size_ok': "Size: {seen}, the film's shape.", 'size_bad': 'Size: {seen}, not {want}.', 'parent_bad': 'Made from: a picture that was not approved ({seen}).',
    # the step's sentences
    'say_need': '{n} need your answer:', 'say_need_one': '1 thing needs your answer:', 'say_failed': '{n} could not be made: they are listed apart.',
    'say_failed_one': '1 could not be made: it is listed apart.', 'say_done': 'Then say done here.', 'say_nothing': 'Nothing waits for you on the page now.',
    'summary': '{n} to answer, {c} could not be made.', 'note': 'Answer each line, then say done in the chat.', 'nothing': 'Nothing waits for you now.',
    'failed': 'It could not be made. Claude tells you in the chat what happens to it.',
    'count': '{n} of {m} pictures and drawn graphics are on this page.', 'answered_note': 'Answered earlier, in the chat.',   # fix set (f), SK 20 Nov 2026
    'help': ['Each line on the left needs one answer. Answer them in any order, then say done in the chat.',
             'A still is a picture that fills one shot of the film. A graphic in steps is shown as it plays: step 1, then step 2. A drawn graphic is a short video; its frames are one click away.',
             'Your footage before and after the shot is shown so you can judge whether the new picture fits between them. It needs no answer.',
             'This page opens when everything of the step is made. Claude checked each picture and drawing first.'],
    # design/221 phase 4 (rows 18, 19): what step 6 must make, each thing's state, the line of counts, the page at the end
    'page_later': 'The page opens when everything of step 6 is made.',
    'page_now': ('Everything of step 6 is made: the operator answers it on the page, in one visit: run `vw visuals page` instead; ask here only where the page '
                 'cannot be shown. '),
    'shown': '{name}: made and checked, {notes}. You judge it on the page with the others.',
    'stills_due': ('{n} still shots have no picture asked for yet ({ids}): order them now, all of them in one call, beside the drawn graphics '   # fix set A2.1: the batch command, one helper
                   '(`vw visuals image --file out/images.json`, one row per still; one `vw-still-prompts` helper writes that file, started beside the parts helper); '
                   'they need nothing from the drawings.'),
    # fix set A2.2: a picture another picture is made from, asked early on one chat card: what its Yes carries
    'parent_card': 'Another picture is made from this one, so it is asked now, before the page. Yes also allows it as the parent of new pictures.',
    'parent_card_failed': ("Another picture is made from this one, so it is asked now, before the page. Claude's check failed a must line ({lines}): Yes approves it all the "
                           'same, and also allows it as the parent of new pictures.'),
    'stills_wait': '{n} still{s} wait{w} for the approved reference{r} of: {names}. {it} ordered when {that} approved; no order is taken before.',
    'supplied_due': ("{n} still shot{s} wait for the operator's own picture: {rows}. Place each now: `vw upload --stage visuals --file in/<name>`, then `vw visuals asset --shot S "
                     "--file in/<name> --kind still --made \"the operator's own picture\" --quote \"<their words>\"`. No picture is made for these shots."),
    'stills_due_one': ('1 still shot has no picture asked for yet ({ids}): order it now, beside the drawn graphics (`vw visuals image --shot S --element E '
                       '--kind keyframe --prompt "…"`); it needs nothing from the drawings.'),
    # design/221 (the critic's points 3, 4): a failed or stale render, said in the next step
    'render_failed': '{shot}: its render failed ({error}): render it again (`vw motion render --shot {shot}`).',
    'render_failed_twice': ('{shot}: its render failed twice on the same project ({error}): fix that fault in the project with a `vw-motion-shot` helper, '
                            'upload it, check it and render it again (`vw motion render --shot {shot}`).'),
    'render_stale_one': '1 drawn graphic must be rendered again (the plan or the shared parts changed): `vw motion render --shot {shot}`.',
    'render_stale': '{n} drawn graphics must be rendered again (the plan or the shared parts changed): `vw motion render --shot S` for each ({ids}).',
    # fix set phase 2 (19 Nov 2026), A1.2: a rule that compares with another drawing; A1.4: what can start now
    'compare_due': ("{shot}: its comparison with {other} is due ({other}'s still end-frame is approved): run `vw motion brief --shot {shot}` (it saves {other}'s frame in "
                    'work/motion/{shot}/with-{other}/), give a fresh vw-motion-check helper the rule{s} "{rule}" with that frame and {shot}\'s last frame, and send its '
                    'verdict with the same round ({round}): a fail is a failed must of {shot}.'),
    'compare_waits': "{shot}: its comparison with {other} waits until {other}'s still end-frame is approved ({n} rule{s}); {shot} is not held by it.",
    'compare_closed': '{shot}: its comparison with {other} is closed ({n} rule{s}): {other} is no drawn graphic of the plan now.',
    'start_now': 'Start now, together in one message: {what}.',
    'start_stills': 'the builders of the still end-frames of {ids} ({n})',
    'start_motion': 'the builders of the motion of {ids} ({n})',
    'start_checks': 'the checkers of {ids} ({n})',
    'motion_after': 'The motion of {ids} comes after the still end-frames.',
    'waits_on': 'Waiting on another drawing: {pairs}.',
    # release 2, section F (20 Nov 2026): F15, a clean drawing whose render the operator rejects; F12, a selected drawing a later comparison fails on
    'take_rejected': ('{shot}: the operator rejected this drawing{words}. Give these words to a new `vw-motion-shot` helper to build its motion again '
                      '(a new project, not a new render of this one), upload it and check it again from round 1.'),
    # release 2, the critic's point 5: the selection stands; one sentence for the operator, no "being redone", no promise (until then: "it is being redone … the new
    # drawing is asked on the page when it is made", which nothing did; design/35 row 295)
    'selected_failed': ('{shot}: its comparison with {other} failed after {shot} was selected: {words}. Tell the operator: they reject {shot} on the page or in the chat '
                        'to have it redrawn, or leave it as it is.'),
    'later_step': 'Made from a step that was corrected.',
    'still_failed': ("{name} ({ref}), a still, did not pass Claude's check: {lines} Make it again once now, without asking the operator, with a request that fixes "
                     "exactly that (`vw visuals image --shot {shot} --element {element} --kind keyframe …`); it is not shown meanwhile. If the next one fails too, it goes to the operator."),
    'start_failed': ("{name} ({shot}): the picture that starts the shot did not pass Claude's check: {lines} Make it again once now, without asking the operator, "
                     "with words that fix exactly that (`vw guide still --shot {shot} …`, or a masked repair of the wrong part); it is not shown meanwhile. "
                     "If the next one fails too, it goes to the operator."),
    'comp_failed': ("{name} ({ref}), a component, did not pass Claude's check: {lines} It stays out of the drawing: make it again with a new request that fixes "
                    'these lines (`vw visuals image --element {element} --kind component …`).'),
    'comp_unopened': 'Claude could not open it ({why}).',
    'comp_na': 'Claude answered "does not apply" on: {lines} A component is approved by the check alone, so every line must be judged.',
    'comp_all_na':'Claude answered every line of its list "does not apply": it is not checked.',
}
PAGE = {   # layout.words.pictures: the page's chrome
    'todo': 'Needs your answer', 'coming': 'Could not be made', 'waiting': 'Not being made now', 'recorded': 'Answered earlier', 'nothing': W['nothing'], 'against': 'Against the check',
    'done': {'answer': 'Answered', 'approve': 'Approved', 'again': 'Made again', 'fix': 'Made again, your words', 'select': 'Selected', 'reject': 'Rebuilt, your words', 'plain': 'Made again, no effect'},
    'undo': 'Undo', 'cancel': 'Cancel', 'details': 'Details', 'more': 'See all {n}', 'fewer': 'Show fewer', 'compare': 'Compare with the earlier try', 'stop': 'Stop comparing',
    'frames': 'Show its frames', 'video': 'Show the video', 'video_bad': 'The video could not be shown here; these are its frames.',
    'loading': 'Loading…', 'missing': 'Not available', 'no_large': 'The large picture is not available.', 'gate_wait': 'The buttons work when every picture has shown.',
    'gate_bad': 'A picture is missing: {pics}. This line cannot be answered here: tell the assistant in the chat.', 'words_need': 'Write what should change first.',
    'left_one': '1 answer still needed', 'left_many': '{n} answers still needed', 'left_note': 'Choose one from the list on the left.',
    'end_head': 'All answered', 'end_note': 'Go back to the chat and say done. This is what will happen then:', 'end_foot': 'Nothing is recorded or made before you say done.',
    'foot': '{n} of {m} answered.', 'foot_wait': 'When all are answered, say done in the chat. Nothing is made before that.', 'foot_done': 'Go back to the chat and say done.',
    'help': 'How this works', 'keys': 'Keys: the left and right arrows move between the things that need an answer. Escape closes what is open.', 'close': 'Close'}

# ---------- Claude's check: the refusals (design/214's sentences, said of pictures) ----------
PIC_LOOK_OPEN = ('{name}: the line "{check}" ({id}) has no answer: every line of the picture gets `pass`: true, false or "na" (does not apply here, with why in `seen`). '
                 'Answer it in its `lines` and send the file again (`vw visuals pictures --looks <file>`).')
# release 1, A3: "does not apply" with no reason
PIC_LOOK_NA = ('{name}: the line "{check}" ({id}) is answered "does not apply" with no reason: say in `seen`, in one sentence of at most {max} characters, why this view '
               'cannot show it or what other thing the line is about; or answer it pass or fail. Then send the file again (`vw visuals pictures --looks <file>`).')
PIC_LOOK_NA_JUDGED = ('{name}: the line "{check}" ({id}) failed on the picture this one was made again from, or is the line it was made again for, so this picture shows it: '
                      'answer it pass or fail, not "na", and send the file again (`vw visuals pictures --looks <file>`).')
PIC_LOOK_UNKNOWN ='{name}: {id} is not a line of this picture now: list the pictures again (`vw visuals pictures --looks`), answer the lines it gives and send the file again.'
PIC_LOOK_WORDS = ('{name}: the line "{check}" ({id}) needs one plain sentence of what was seen (`seen`, at most {max} characters): a fail always, and a pass of a line marked '
                  '`say`. Add it and send the file again (`vw visuals pictures --looks <file>`).')
PIC_LOOK_NOT_CHECKED = ('{name}: `not_checked` is only for a picture that could not be opened, and then it carries no `lines`. This one carries both: take `not_checked` out if '
                        'the picture was checked, or the lines if it was not, and send the file again (`vw visuals pictures --looks <file>`).')
PIC_LOOK_GONE = ('{name}: it is not a picture waiting for its check now (made again, answered, or changed): list the pictures again (`vw visuals pictures --looks`).')
PIC_LOOK_NONE = 'No picture of this film waits for Claude\'s check: its reference round is not of the new kind, so its pictures keep the check of before.'
LOOKS_DUE = "{n} picture(s) wait for Claude's check: run `vw visuals pictures --looks`."
LOOKS_THEN = ("Look at each picture against its lines, as `how` says, write work/visuals/pictures/looks.json and send it (`vw visuals pictures --looks work/visuals/pictures/looks.json`). "
              'Above 5 pictures, give them to vw-picture-look helpers, about 5 each, all started together, in one message.')
LOOKS_NONE = 'No picture waits for Claude\'s check now.'
COMPONENT_APPROVED = "Approved by Claude's check: a component is a part of a drawn graphic and is judged with it (design/217 D4)."
LOOK_HOW = {
    'judge': ["Answer every line of the picture's `lines`, pass or fail, from what you see in the picture, never from the request. A line's `pass_when` says what passes.",
              'Compare with the inputs where a line asks for it: a parent is what the picture was made from; `scene` pictures are the approved pictures of the same scene; '
              '`earlier` is the picture this one was made again from; `step before` is the previous step of a graphic.',
              'Exact words are read letter for letter. A face that matches a real person of the footage fails "a real face", unless its line names that person as permitted; '
              "a face that matches the film's own made references is never a fault. Anything the request did not ask for fails \"nothing extra\".",
              'Never pass a line you did not look at. A picture you could not open is `not_checked`, with why, and then has no lines.',
              'A row of kind `start` is the still an AI video shot starts from: its `overlay` input shows it under the red outlines of the layout, its `layout` input is the layout alone.',
              'The light, the fine detail and the size are measured by the program: they are not your lines.', V.NA_HOW],
    'file': {'by': 'assistant | helper',
             'pictures': [{'ref': '<the picture id>', 'sha10': '<the first 10 characters of its sha256, as listed>',
                           'lines': [{'id': '<a line id of its `lines`>', 'pass': 'true | false | "na"',
                                      'seen': '<with a fail, with "na" (why it does not apply) and with a line marked `say`: one plain sentence, at most 300 characters>'}],
                           'not_checked': '<only for a picture that could not be opened: why, one line; then no lines>'}]},
    'send': '`vw visuals pictures --looks <file>`. A refused picture is named with its reason: fix its row and send it again; the others are recorded.'}

ORDINAL = {2: 'a second', 3: 'a third', 4: 'a fourth', 5: 'a fifth'}


def _now():
    return datetime.now(timezone.utc)


def _say(check, words):
    words = ' '.join(str(words or '').split()).rstrip('.')
    return f'{check}: {words}.' if words else f'{check}.'


def _problems(n):
    return f"{n} problem{'' if n == 1 else 's'}"


def na_view(lines):
    """Release 1, A5: the lines that did not apply as the page and the chat get them, one field: {'na': {'head', 'lines'}}; nothing when there is none."""
    lines = list(lines)
    return {'na': {'head': W['na_head_one'] if len(lines) == 1 else W['na_head'].format(n=len(lines)), 'lines': lines}} if lines else {}


def all_na(look):
    """Release 1, A5: every line of this look was answered "does not apply": nothing was judged, so it is not a check."""
    rows = (look or {}).get('lines') or []
    return bool(rows) and all(l.get('pass') == V.NA for l in rows)


def _named(text, who):
    """Release 1, A2: a sentence of the check with who really checked: Claude (as written), the model before this release ('model'), or both ('mixed': the steps of one graphic)."""
    return str(text).replace("Claude's check", W['who_' + who]) if who else text


def _and(items):
    items = [str(x) for x in items]
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def _plain_cost(text):
    """D1: no amount of money on these sentences."""
    return re.sub(r'\s*\((?:about\s*)?(?:₹\s*)?[\d.,]+\s*(?:INR)?\)', '', str(text or '')).strip()


# ---------- which pictures Claude checks (C1) ----------

def video_shot(session, plan, ref):
    """True when the picture is a start or end picture, or is made for an AI video shot. (Until release 1 this kept a picture from Claude's
    check; every keyframe carries the role `start` or `end`, so it kept every still from it. Now it only says which question stays in the chat.)"""
    if ref.get('role') in ('start', 'end') or ref.get('pending_end'):
        return True
    shot = _scene_of(plan, session, ref)[1] if plan else None
    return bool(shot) and V.route_of(shot) == 'video'


def claude_checks(session, ref, plan=None):
    """C1: this picture is checked by Claude's look, not by a model on the server: a still, a step of a graphic, the style sheet, a component
    or a remade one of these, of a film whose round is v2. Never a picture of a set (design/214) or a footage picture.
    Release 1, A1 (SK, 20 Nov 2026): a start or end picture too: no picture of steps 6 and 7 goes to the model check. (`plan` is no longer read.)"""
    return bool(V.round_v2(session) and ref.get('kind') in LOOK_KINDS and not ref.get('set'))


def _line(check, pass_when, say=False):
    # the critic's point 9: "a real face" changes its words when a person's permission is recorded (`face_line`): its id is of its name alone, so a look in progress is not refused
    lid = hashlib.sha1((check if check == 'a real face' else f'{check}|{pass_when}').encode('utf-8')).hexdigest()[:8]
    return {'id': lid, 'check': check, 'pass_when': pass_when, **({'say': True} if say else {})}


def _scene_of(plan, session, ref):
    sid = V.made_for(session, ref)
    for gap in (plan or {}).get('gaps') or []:
        for sc in V.all_scenes(gap):
            if any(sh.get('id') == sid for sh in sc.get('shots') or []):
                return sc, next(sh for sh in sc['shots'] if sh.get('id') == sid)
    return None, None


def scene_pictures(session, plan, ref):
    """The approved pictures of the same scene, for the line on background figures (C5): the question the second model call asked after an approval."""
    scene, _ = _scene_of(plan, session, ref)
    sids = {s.get('id') for s in (scene or {}).get('shots') or []}
    return [r for r in session['references'].values() if r['id'] != ref['id'] and r.get('status') == 'approved' and r.get('kind') in ('keyframe', 'isolated')
            and V.made_for(session, r) in sids and r.get('key')]


def step_of(session, ref):
    """A step's number in its graphic (1-based), or None."""
    try:
        chain = V.state_chain(session, V.made_for(session, ref)) or []
    except ValueError:
        return None
    return next((n for n, r in enumerate(chain, 1) if r['id'] == ref['id']), None)


def _people(plan, shot):
    """The people a shot shows, as the plan names them: {person element id: name}, in the shot's order."""
    names = V.people_of(plan) if plan else {}
    ids = list((shot or {}).get('element_ids') or []) + [s.get('element_id') for s in (shot or {}).get('subjects') or []]
    return {i: names[i] for i in dict.fromkeys(ids) if i in names}


def face_line(session, plan, shot):
    """Release 1, A7 (SK, 20 Nov 2026): "a real face" as Claude's list asks it of a picture made for this shot. A person of the shot for whom the
    operator's permission is recorded (`visuals_stage.likeness_of`: asked once, at step 1 of the references) is named: a match with them is not a
    fault, and only another real face from the footage is. With no permission (a stand-in, by the operator's No) the line is as it was for that
    person. A made character has no footage behind it: a match with the film's own made references is never a fault."""
    ok = [name for eid, name in _people(plan, shot).items() if V.likeness_of(session, eid)]
    return {'check': 'a real face', 'pass_when': W['face_when'] + (W['face_ok'].format(names=_and(ok)) if ok else '') + W['face_made']}


def faces_to_ask(session, plan):
    """Release 1, A7: the people of the footage whom a picture now waiting for its look shows and about whom the operator was never asked (a face
    frame is kept, and neither the permission nor a stand-in is recorded: `ref_sets.footage_person`): said in the next step, each once, with
    the command that records the answer. Normally none: step 1 of the references asks it before any picture is made.
    The critic's point 10c: asked before the picture is paid for: for every still and AI video shot of the plan, from the step's first next-step
    line; the stills of those shots are not named for ordering until it is answered (`ask_shots`), the other shots are not held."""
    from . import ref_sets
    people = {eid: name for sh in _made_shots(session, plan) for eid, name in _people(plan, sh).items()}
    asked = {eid: ref_sets.footage_person(session, plan, eid) for eid in people}
    return [W['face_ask' if asked[eid].get('faces', True) else 'person_ask'].format(name=name, eid=eid) for eid, name in people.items() if asked[eid].get('state') == 'ask']   # phase 2 part A: a real person the footage never shows


def _made_shots(session, plan):
    """The accepted shots a picture is made for: the still shots and the AI video shots."""
    return [sh for _, sh in V._accepted_shots(plan, session) if V.route_of(sh) in ('still', 'video')] if plan else []


def ask_shots(session, plan):
    """The critic's point 10c: the shots that show a person of the footage about whom the operator was never asked: their stills wait for the answer."""
    from . import ref_sets
    return {sh['id'] for sh in _made_shots(session, plan) if any(ref_sets.footage_person(session, plan, eid).get('state') == 'ask' for eid in _people(plan, sh))}


def lines(session, plan, ref):
    """C1, contract 5.3: the check list of one picture for Claude's look. The program's list for the picture (image_check.lines_of: the server's
    lines, the writer's checklist, the fixed lines), plus per kind: the background-figure line of a still (C5), the step line of a step, the
    style sheet's own lines, the original's list and two lines of a remade picture. Each line's id is made of its words.
    Release 1, A7: the fixed line "a real face" is asked as `face_line` says it for the picture's shot."""
    face = face_line(session, plan, _scene_of(plan, session, ref)[1])
    own = [face if l['check'] == 'a real face' else l for l in image_check.lines_of(ref)]
    kind = ref.get('kind')
    orig = session['references'].get(ref.get('fix_of') or '') if ref.get('fix_of') else None
    if orig:   # a remade picture is checked against its original's whole list, never a smaller one
        have = {l['check'] for l in own}
        own += [l for l in image_check.lines_of(orig) if l['check'] not in have]
    out = [_line(l['check'], l['pass_when'], l['check'].startswith('drawn fact: ')) for l in own]
    if kind == 'style':
        palette = str((((plan or {}).get('foundation') or {}).get('graphic_style') or {}).get('palette') or '').strip()
        if palette:
            out.append(_line('the palette', f'only the colours of the plan: {palette}'))
        out += [_line('sample labels readable', 'the sample labels read at film size, letter for letter'),
                _line('no scene', 'a sample of the drawing language (lines, fills, lettering), not a scene of the film')]
    elif kind == 'state':
        n = step_of(session, ref)
        if n and n > 1:
            _scene, shot = _scene_of(plan, session, ref)
            what = str((((shot or {}).get('states') or [{}] * n)[n - 1] or {}).get('what_appears') or '').strip() if shot and len(shot.get('states') or []) >= n else ''
            out.append(_line(f'step {n} adds its part', f"it adds what the plan's step {n} names" + (f' ({what})' if what else '') + f'; the rest is as step {n - 1}'))
    elif kind in ('keyframe', 'isolated') and scene_pictures(session, plan, ref):
        _scene, shot = _scene_of(plan, session, ref)
        if shot and V._has_figures(plan, shot):
            out.append(_line('no background figure repeated', 'no person or animal in it is the same individual as one in the approved pictures of this scene sent with it'))
    if orig:
        if ref.get('fix_for'):
            out.append(_line('the line it was made for', f"the line \"{ref['fix_for']}\" now passes"))
        out.append(_line('nothing else changed', 'nothing else changed against the earlier picture sent with it'))
        failed = {l.get('check') for l in (looked(orig) or {}).get('lines') or [] if l.get('pass') is False} | {ref.get('fix_for'), 'the line it was made for'}
        out = [{**l, 'judged': True} if l['check'] in failed else l for l in out]   # the critic's point 5a: a line the original failed, or the one the picture was made again for, is in view: never "na"
    seen = {}
    for l in out:
        seen.setdefault(l['id'], l)
    return list(seen.values())


# ---------- when a picture is offered (C3) ----------

def _at(ref, field):
    try:
        return datetime.fromisoformat(str(ref.get(field)))
    except ValueError:
        return None


START_LOOK = 'check_look'   # the critic's point 1: Claude's look of step 7's still has its own field: a guide's still keeps the id of its look reference in `look` (design/200, a string)


def looked(ref):
    """Claude's look of this picture as it is now (the same sha256), or None. A still of a guide (it carries `guide_sha256`) keeps it under `check_look`."""
    look = ref.get(START_LOOK if 'guide_sha256' in ref else 'look') or {}
    return look if look and look.get('sha256') == ref.get('sha256') else None


def older(ref):
    """A picture the model checked before the deploy (its record has the model's lines) and that the new worker never made: it keeps that check,
    is offered as before and is never given to Claude (the critic's review, 18 Nov). Only a picture still `check_pending` at the deploy is."""
    c = ref.get('check') or {}
    return bool(c.get('model') or c.get('lines')) and not ref.get('look') and not ref.get('ready_at') and not ref.get('check_pending')


def late(ref, now=None):
    """C3: the time-out counts from when Claude was first asked to check the picture (`asked_at`), never from when it was made: a film paused
    overnight does not offer its pictures as not checked."""
    at = _at(ref, 'asked_at')
    return bool(at) and (now or _now()) - at >= timedelta(minutes=PICTURE_LOOK_MINUTES)


def retry_due(session, ref, plan=None):
    """Release 1 of 27 Nov 2026, phase 2 part D (SK, 6.16): a still's picture that Claude's check failed is made again once before the operator
    sees anything: True for the first picture of a still shot whose look has a failed line. Never a second time (`still_retries`, written
    when the remake is ordered or given up), never on top of a picture the operator sent back, never for a look that could not open it.
    Retired: a still whose check failed waits for the operator before it is made again."""
    sid = V.made_for(session, ref)
    if (not sid or ref.get('kind') not in ('keyframe', 'isolated') or ref.get('status') != 'candidate' or ref.get('set') or 'guide_sha256' in ref
            or not claude_checks(session, ref, plan) or older(ref) or sid in (session.get('still_retries') or {})
            or ref.get('parent_wanted')):   # another picture was ordered from it: the operator is asked now, as before (fix set 3, A2.2)
        return False
    look = looked(ref)
    if not look or look.get('not_checked') or not _failed_lines(ref):
        return False
    if plan is not None and not any(sh['id'] == sid and V.route_of(sh) == 'still' for _, sh in V._accepted_shots(plan, session)):
        return False
    return not any(r is not ref and V.made_for(session, r) == sid and r.get('status') == 'rejected' and (r.get('rejection') or {}).get('by') != 'server'
                   for r in session['references'].values())   # the operator's own correction is the one try


def stills_failed(session, plan):
    """Part D: each still whose first picture failed Claude's check, said plainly with what failed: the assistant makes it again once."""
    return [W['still_failed'].format(name=name_of(session, plan, r), ref=r['id'], lines=' '.join(_failed_lines(r)), shot=V.made_for(session, r), element=r.get('element_id') or 'E')
            for r in session['references'].values() if retry_due(session, r, plan)]


def start_retry_due(session, shot_id, g, still):
    """Release 1 of 27 Nov 2026, phase 4 part A, rule 6 (SK: "yes, once"): the picture that starts an AI video shot is made again once by itself
    when Claude's check failed a line (the line "on the layout" included; an advice line never counts), before the operator sees anything:
    phase 2's rule for a still picture (`retry_due`), with the same count (`still_retries`, by shot). Never a second time, never when the check
    could not run, never on top of a still the operator sent back. Retired: such a still went to the operator at once."""
    look = looked(still)
    return bool(still.get('status') == 'candidate' and still.get('guide_sha256') == g.get('sha256') and shot_id not in (session.get('still_retries') or {})
                and look and not look.get('not_checked') and _failed_lines(still)
                and not any(s.get('status') == 'rejected' and (s.get('rejection') or {}).get('by') != 'server' for s in g.get('stills') or []))


def starts_failed(session, plan):
    """Part A rule 6: each start still whose first picture failed Claude's check, said plainly with what failed: the assistant makes it again once."""
    if not plan:
        return []
    from . import takes
    return [W['start_failed'].format(name=takes.name_of(gap, sh, n, of), shot=sh['id'], lines=' '.join(_failed_lines(st)))
            for gap, sh, n, of in takes.video_shots(plan, session) for g in [(session.get('guides') or {}).get(sh['id']) or {}]
            for st in g.get('stills') or [] if start_retry_due(session, sh['id'], g, st)]


def offered(session, ref, plan=None, now=None):
    """C3: a picture Claude checks is offered with its look recorded, or PICTURE_LOOK_MINUTES after Claude was asked (as not checked).
    A picture the model checked before the deploy, and any other picture: as before. Part D: never while it is made again by itself."""
    if not claude_checks(session, ref, plan) or older(ref):
        return True
    if retry_due(session, ref, plan):
        return False
    return bool(looked(ref)) or late(ref, now)


def due(session, plan, now=None):
    """The candidates that wait for Claude's look: checked by Claude, no look of their content yet. The ones past the time-out stay due: a look that comes before the operator's answer replaces "not checked"."""
    return [r for r in session['references'].values() if r.get('status') == 'candidate' and r.get('sha256') and claude_checks(session, r, plan) and not older(r) and not looked(r)]


def stamp(session, plan):
    """At the deploy and after: a candidate Claude checks that still waits for the model's check (`check_pending`) is due for a look from now.
    Returns True when the session changed (the caller saves it)."""
    changed = False
    for r in session['references'].values():
        if r.get('status') == 'candidate' and claude_checks(session, r, plan) and r.get('check_pending'):
            r.pop('check_pending', None)
            r.setdefault('ready_at', _now().isoformat())
            changed = True
    return changed


START_ON_LAYOUT = ('on the layout', "every person and thing sits where the layout puts it: on the overlay sent with it, on the red outlines of the guide's first frame. "
                   "Write what you see in words about the people and things of the picture (who stands where, what is missing): the operator reads it and never sees "
                   "the outlines, the overlay or the layout")   # release 1 of 27 Nov 2026, phase 4 part A: the still's card shows the still alone


START_WHO = ('who and what', 'each person, thing and place in it is the one of the pictures sent as `parent`: the same face, build and clothes, the same object, the same place')   # the critic's point 6


def start_lines(session, plan, shot, still):
    """Release 1, A1 (SK, 20 Nov 2026): the check list of step 7's still (the start picture of an AI video shot) for Claude's look. What it was
    judged on until now, by the operator alone on its overlay: every person and thing on the red outlines of the layout; the facts of the drawn
    things among its inputs (the request's "What must be true", guide._drawn_facts); then the fixed lines of every made picture."""
    from . import guide
    return ([_line(*START_ON_LAYOUT), _line(*START_WHO, True)] + [_line('drawn fact: ' + f, f'the picture shows it as the approved drawings do: {f}', True) for f in guide._drawn_facts(session, still.get('inputs') or [])]
            + [_line(l['check'], l['pass_when']) for l in (face_line(session, plan, shot) if l['check'] == 'a real face' else l for l in image_check.FIXED)])   # A7: the same face line as a still's


def starts_due(session, plan):
    """Release 1, A1: the stills of step 7 that wait for Claude's look: [(name, shot, the guide's entry, the still)]: a finished candidate made from
    the guide as it is, with no look of its content yet. Only on a film whose round is v2, as every picture Claude checks."""
    if not plan or not V.round_v2(session):
        return []
    from . import takes
    return [(takes.name_of(gap, sh, n, of), sh, g, st) for gap, sh, n, of in takes.video_shots(plan, session) for g in [(session.get('guides') or {}).get(sh['id']) or {}]
            for st in g.get('stills') or [] if st.get('status') == 'candidate' and st.get('key') and st.get('sha256') and st.get('guide_sha256') == g.get('sha256') and not looked(st)]


def start_offered(session, still, now=None):
    """Release 1, A1: step 7's still is shown to the operator with its look recorded, or PICTURE_LOOK_MINUTES after Claude was asked (as not
    checked): as a picture of step 6 (`offered`). On a film of the older round: at once, as before."""
    return not V.round_v2(session) or not still.get('sha256') or bool(looked(still)) or late(still, now)   # the critic's point 3: a still that `starts_due` can never list (no content mark) is never waited for


def asked(session, plan):
    """C3: the first time Claude is asked to check a picture (listed by `looks_due`, or said by `waits_words`), it gets `asked_at`. True when the session changed."""
    changed = False
    for r in due(session, plan) + [x[3] for x in starts_due(session, plan)]:
        if not r.get('asked_at'):
            r['asked_at'] = _now().isoformat()
            changed = True
    return changed


def _failed_lines(ref):
    look = looked(ref) or {}
    return [_say(l['check'], l.get('seen')) for l in look.get('lines') or [] if l.get('pass') is False] + \
        [_say(c.get('check'), c.get('seen')) for c in (ref.get('check') or {}).get('code') or [] if c.get('pass') is False and not c.get('advice')]


def _na_lines(ref):
    return [_say(l['check'], l.get('seen')) for l in (looked(ref) or {}).get('lines') or [] if l.get('pass') == V.NA]


def components_failed(session, plan):
    """The critic's review (5): a component Claude's check failed (or could not open) stays a candidate and is never asked of the operator, so
    the assistant is told plainly, with what failed, to make it again: never silent."""
    out = []
    for r in session['references'].values():
        look = looked(r)
        if r.get('kind') == 'component' and r.get('status') == 'candidate' and look and claude_checks(session, r, plan):
            why = W['comp_unopened'].format(why=look['not_checked']) if look.get('not_checked') else W['comp_all_na'] if all_na(look) else ''
            fails = _failed_lines(r) or ([W['comp_na'].format(lines=' '.join(_na_lines(r)))] if _na_lines(r) else [])   # the critic's point 5b
            if why or fails:
                out.append(W['comp_failed'].format(name=name_of(session, plan, r), ref=r['id'], lines=why or ' '.join(fails), element=r.get('element_id') or 'E'))
    return out


def waits_words(session, plan):
    """The first thing `next` and `status` say while pictures wait for Claude's look (C2: the duty is never silent), then each failed component.
    Stamps `asked_at` on the pictures it reports (the caller saves the session)."""
    asked(session, plan)
    n = len(due(session, plan)) + len(starts_due(session, plan))   # release 1, A1: with the stills of step 7
    return ' '.join(([LOOKS_DUE.format(n=n)] if n else []) + faces_to_ask(session, plan) + components_failed(session, plan) + stills_failed(session, plan) + starts_failed(session, plan))   # release 1, A7: a person of the footage nobody was asked about


def _big(store, session, ref_id):
    from .page_flow import sized
    key, mark = ((session['references'].get(ref_id) or {}).get(k) for k in ('key', 'sha256'))
    try:
        return sized(store, key, 'zoom', mark) if key else None
    except Exception:   # a picture that cannot be shrunk is read at its full size
        return key


def name_of(session, plan, ref):
    if ref.get('kind') == 'style':
        return W['style_name']
    _scene, shot = _scene_of(plan, session, ref)
    title = str((shot or {}).get('title') or ref.get('name') or ref['id'])
    n = step_of(session, ref) if ref.get('kind') == 'state' else None
    return f'{title}, step {n}' if n else title


def looks_due(store, run, outputs, take_rows=None):
    """`GET /api/runs/{run_id}/visuals/pictures/looks`: {pictures: [{ref, sha10, kind, name, shot_id, n?, key, inputs: [{ref, role, key}],
    request, lines}], then, how}. The keys are the 1600 px copies. Stamps the pictures that waited for the model's check at the deploy.
    design/223 (SK, 22 Nov 2026): an AI video take is not in this list: nobody checks a take (until then: kind `take`, judged by `how_take`; design/35 row 317)."""
    session = V.session_of(store, run, outputs)
    if not V.round_v2(session):
        return {'pictures': [], 'then': PIC_LOOK_NONE, 'how': LOOK_HOW}
    plan = V.guarded(lambda: V.current_plan(store, session))
    if stamp(session, plan) | asked(session, plan):
        V.save_session(store, run, session)
    out = []
    for r in due(session, plan):
        inputs = [{'ref': p.get('id'), 'role': 'step before' if r.get('kind') == 'state' and (session['references'].get(p.get('id')) or {}).get('kind') == 'state' else
                   'scene' if (session['references'].get(p.get('id')) or {}).get('kind') == 'frame' else 'parent'} for p in (r.get('generation') or {}).get('parents') or [] if p.get('id')]
        if r.get('fix_of'):
            inputs.append({'ref': r['fix_of'], 'role': 'earlier'})
        if any(l['check'] == 'no background figure repeated' for l in lines(session, plan, r)):
            inputs += [{'ref': s['id'], 'role': 'scene'} for s in scene_pictures(session, plan, r)]
        out.append({'ref': r['id'], 'sha10': str(r['sha256'])[:10], 'kind': r.get('kind'), 'name': name_of(session, plan, r), 'shot_id': V.made_for(session, r),
                    **({'n': step_of(session, r)} if r.get('kind') == 'state' else {}), 'key': _big(store, session, r['id']),
                    'inputs': [{**i, 'key': _big(store, session, i['ref'])} for i in inputs], 'request': (r.get('generation') or {}).get('prompt') or '', 'lines': lines(session, plan, r)})
    made = {x['id']: x['key'] for gd in (session.get('guides') or {}).values() for x in gd.get('stills') or [] if x.get('status') == 'approved' and x.get('key')}   # the critic's point 6: a later still of a scene is made from the scene's approved stills, which are not references
    for name, sh, g, st in starts_due(session, plan):   # release 1, A1: step 7's still: the picture, its overlay on the layout, the layout alone, the pictures it was made from
        out.append({'ref': st['id'], 'sha10': str(st['sha256'])[:10], 'kind': 'start', 'name': name, 'shot_id': sh['id'], 'key': st['key'],
                    'inputs': [{'ref': role, 'role': role, 'key': k} for role, k in (('overlay', st.get('overlay_key')), ('layout', (g.get('render') or {}).get('frame1_key'))) if k]
                              + [{'ref': i['id'], 'role': 'parent', 'key': _big(store, session, i['id']) if i['id'] in session['references'] else made[i['id']]}
                                 for i in st.get('inputs') or [] if i.get('id') in session['references'] or i.get('id') in made],
                    'request': st.get('prompt') or '', 'lines': start_lines(session, plan, sh, st)})
    return {'pictures': out, 'then': LOOKS_THEN if out else LOOKS_NONE, 'how': LOOK_HOW}


def _fault(name, want, sent):
    """The first fault of one picture's row of a look against its list, as a refusal; None when every line is answered or it says why it was not opened."""
    one = lambda t: ' '.join(str(t or '').split())
    why = one(sent.get('not_checked'))
    if why:
        return PIC_LOOK_NOT_CHECKED.format(name=name) if sent.get('lines') else (PIC_LOOK_WORDS.format(name=name, check='not_checked', id='-', max=LOOK_SAY) if len(why) > LOOK_SAY else None)
    got = {a.get('id'): a for a in sent.get('lines') or [] if isinstance(a, dict)}
    unknown = [i for i in got if i not in {w['id'] for w in want}]
    if unknown:
        return PIC_LOOK_UNKNOWN.format(name=name, id=unknown[0])
    for w in want:
        a = got.get(w['id'])
        if not a or not (isinstance(a.get('pass'), bool) or a.get('pass') == V.NA):
            return PIC_LOOK_OPEN.format(name=name, check=w['check'], id=w['id'])
        words = one(a.get('seen'))
        if a['pass'] == V.NA and w.get('judged'):   # the critic's point 5a
            return PIC_LOOK_NA_JUDGED.format(name=name, check=w['check'], id=w['id'])
        if a['pass'] == V.NA and not words:   # release 1, A3: "does not apply" always says why
            return PIC_LOOK_NA.format(name=name, check=w['check'], id=w['id'], max=LOOK_SAY)
        if len(words) > LOOK_SAY or (not words and (a['pass'] is False or w.get('say'))):
            return PIC_LOOK_WORDS.format(name=name, check=w['check'], id=w['id'], max=LOOK_SAY)
    return None


def _look(sha, want, sent, who, at):
    """A picture's look as it is stored: who, when, the content it is of, and each line's answer by the list's own order; or why it was not opened."""
    why = ' '.join(str(sent.get('not_checked') or '').split())
    got = {a.get('id'): a for a in sent.get('lines') or [] if isinstance(a, dict)}
    return {'who': who, 'at': at, 'sha256': sha,
            **({'not_checked': why} if why else {'lines': [{'id': w['id'], 'check': w['check'], 'pass': got[w['id']]['pass'], 'seen': ' '.join(str(got[w['id']].get('seen') or '').split())} for w in want]})}


def na_said(name, look):
    """Release 1, A5: the lines of a look that did not apply, each with its reason, for the run's log."""
    return [f"{name}: {l['check']} ({l.get('seen') or ''})" for l in (look or {}).get('lines') or [] if l.get('pass') == V.NA]


def na_log(said):
    """The one log line of a step that recorded lines which did not apply; nothing when there is none."""
    return {'log': f"{W['na_head_one'] if len(said) == 1 else W['na_head'].format(n=len(said))}: " + '; '.join(said)} if said else {}


def record_looks(store, user, run, outputs, pictures, by, take_rows=None):
    """`POST /api/runs/{run_id}/visuals/pictures/looks`: each picture's look, line by line (contract 5.4, 5.5). A refused picture records
    nothing; the others record. Returns {recorded: [ref], refused: {ref: message}, left: [ref], then}, and `log` (release 1, A5: the lines
    that did not apply, kept in the run's log) when a recorded look has one."""
    session = V.session_of(store, run, outputs)
    V.need(V.round_v2(session), PIC_LOOK_NONE)
    plan = V.guarded(lambda: V.current_plan(store, session))
    stamp(session, plan)
    who, recorded, refused, at, na = by if by in ref_find.WHO else 'assistant', [], {}, _now().isoformat(), []
    for p in pictures or []:
        p = p if isinstance(p, dict) else {}
        rid = str(p.get('ref') or '')
        if rid not in session['references'] and any(str(j['id']) == rid for j in take_rows or []):   # design/223: a look sent for an AI video take is refused by name
            from . import takes
            refused[rid] = takes.W['look_retired']
            continue
        start = next((x for x in starts_due(session, plan) if x[3]['id'] == rid), None) if rid not in session['references'] else None
        if start:   # release 1, A1: the look of step 7's still, kept on the still
            name, sh, _g, st = start
            want = start_lines(session, plan, sh, st)
            fault = PIC_LOOK_GONE.format(name=name) if not p.get('sha10') or str(st['sha256'])[:10] != str(p['sha10'])[:10] else _fault(name, want, p)
            if fault:
                refused[rid] = fault
            else:
                st[START_LOOK] = _look(st['sha256'], want, p, who, at)
                recorded.append(rid)
                na += na_said(name, st[START_LOOK])
            continue
        r = session['references'].get(rid) or {}
        name = name_of(session, plan, r) if r else rid
        if not (r.get('status') == 'candidate' and r.get('sha256') and claude_checks(session, r, plan) and str(r['sha256'])[:10] == str(p.get('sha10') or '')[:10] and p.get('sha10')):
            refused[rid] = PIC_LOOK_GONE.format(name=name)
            continue
        want = lines(session, plan, r)
        fault = _fault(name, want, p)
        if fault:
            refused[rid] = fault
            continue
        why = ' '.join(str(p.get('not_checked') or '').split())
        r['look'] = _look(r['sha256'], want, p, who, at)
        recorded.append(rid)
        na += na_said(name, r['look'])
        if r.get('kind') == 'component' and not why and not _failed_lines(r) and not _na_lines(r):   # the critic's point 5b: any "does not apply" keeps it out of the approval nobody sees   # the program's advice lines (transparency, light) never decide it; release 1, A5: nor a list where nothing applied
            # D4: a component is a part of a drawn graphic, judged with it: it is approved when Claude's check and the program's lines pass, and never asked of the operator
            r.update(status='approved', approval={'by': user['id'], 'at': at, 'sha256': r['sha256'], 'quote': COMPONENT_APPROVED})
    V.save_session(store, run, session)
    left = [r['id'] for r in due(session, plan)] + [x[3]['id'] for x in starts_due(session, plan)]
    failed = components_failed(session, plan) + stills_failed(session, plan) + starts_failed(session, plan)   # the critic's review (5): a failed component is said, with its lines, never silent; phase 2 part D: a failed still too
    return {'recorded': recorded, 'refused': refused, 'left': left, **na_log(na),
            'then': ' '.join([LOOKS_DUE.format(n=len(left)) if left else LOOKS_NONE] + failed).strip()}


# ---------- the check as the page and the chat say it (F1, contract 3.8) ----------

def advice(ref):
    """C4, D2: the program's measured lines (size, parents, light, fine detail, transparency) as advice, never a fault."""
    out = []
    for c in ((ref.get('check') or {}).get('code') or []):
        name, seen = str(c.get('check') or ''), str(c.get('seen') or '')
        if name == 'size':
            if c.get('pass') is True:
                out.append(W['size_ok'].format(seen=seen))
            elif c.get('pass') is False:
                out.append(W['size_bad'].format(seen=seen, want=str(c.get('pass_when') or '').replace('the picture is ', '')))
        elif name == 'parent':
            if c.get('pass') is False:
                out.append(W['parent_bad'].format(seen=seen))
        elif seen:
            out.append(_say(name[:1].upper() + name[1:], seen))
    return out


def _name(text, cap=60):
    """A problem's short name: its words up to the first colon (the line's own name), cut at a word when long."""
    t = str(text).split(': ')[0].rstrip('.')
    return t if len(t) <= cap else t[:cap].rsplit(' ', 1)[0] + '…'


def short(state, head, faults=(), notes=(), names=None):
    """Release 1, B3 (SK, 20 Nov 2026): the one short line of a check, the same for a picture, a drawing and a take: "Passed", "Passed, 1 note",
    "2 warnings: <the first one's short name>", or the sentence that says why it was not checked (the head)."""
    if state == 'fail':
        name = (list(names) if names else [_name(f) for f in faults] or [''])[0]
        return (W['short_warn'] if len(faults) == 1 else W['short_warns']).format(n=len(faults), name=name)
    if state == 'pass':
        return W['short_pass'] if not notes else W['short_note'] if len(notes) == 1 else W['short_notes'].format(n=len(notes))
    return head


def marked(base, check, held=''):
    """The critic's point 2: an item's id with a mark of its check as shown (state, head, faults, why it is held), as `takes.item_id` does for a
    take: an answer given to an older view of the check is stale and asked again. Returns (the id, the id without the mark, whether an answer
    goes against the check): an id of a round written before the mark is taken only while nothing goes against the check."""
    check = check or {}
    mark = hashlib.sha1('|'.join([str(check.get('state')), str(check.get('head'))] + [str(f) for f in check.get('faults') or []] + [held]).encode('utf-8')).hexdigest()[:8]
    return f'{base}:{mark}', base, check.get('state') == 'fail' or bool(held)


def _view(state, head, by='', faults=(), passed=(), adv=(), show='first', passed_head=None, advice_head=None, na=(), notes=(), names=None):
    return {'state': state, 'head': head, 'short': short(state, head, faults, notes, names), 'by': by, 'show': show, 'faults': list(faults),
            'passed_head': (W['passed_head'] if passed else '') if passed_head is None else passed_head,
            'passed': list(passed), 'advice_head': (W['advice_head'] if adv else '') if advice_head is None else advice_head, 'advice': list(adv), **na_view(na),
            **({'notes': list(notes)} if notes else {})}


def look_view(ref, adv=(), now=None):
    """The check of a picture Claude looks at, from its look as it is now: a failed line is a problem; a line that does not apply (release 1, A5) is
    neither a problem nor passed and is listed apart (`na`); a list where every line does not apply is not a check."""
    look = looked(ref)
    if look and look.get('not_checked'):
        return _view('not_checked', W['unopened'], adv=adv)
    if not look:
        return _view('not_checked', W['late'].format(m=PICTURE_LOOK_MINUTES) if late(ref, now) else W['none'], adv=adv)
    rows = look.get('lines') or []
    fails = [_say(l['check'], l.get('seen')) for l in rows if l.get('pass') is False]
    passed = [_say(l['check'], l.get('seen') or l['check']) for l in rows if l.get('pass') is True]
    na = [_say(l['check'], l.get('seen')) for l in rows if l.get('pass') == V.NA]
    if all_na(look):
        return _view('not_checked', W['all_na'], W['by'].format(n=len(rows)), adv=adv, na=na)
    return _view('fail' if fails else 'pass', W['fail'].format(problems=_problems(len(fails)), first=fails[0]) if fails else W['pass'],
                 W['by'].format(n=len(rows)), fails, passed, adv, na=na)


def check_view(session, ref, plan=None, now=None):
    """F1: one picture's check, from Claude's look (`ref.look`) and the program's lines (`ref.check.code`); never from `ref.checklist`.
    A film of before (round not v2) keeps its model's lines (`ref.check.lines`). States: pass, fail, not_checked, none."""
    adv = advice(ref)
    if claude_checks(session, ref, plan) and not older(ref):   # a picture the model checked before the deploy keeps that check
        return look_view(ref, adv, now)
    rows =[l for l in ((ref.get('check') or {}).get('lines') or []) if isinstance(l, dict)]
    if not rows:
        return _view('none', W['none'], adv=adv)
    fails = [_say(l.get('check'), l.get('seen')) for l in rows if l.get('pass') is False and (l.get('weight') or 'must') == 'must' and l.get('check') != 'light and colour']
    passed = [_say(l.get('check'), l.get('seen') or l.get('check')) for l in rows if l.get('pass') is True]
    head = _named(W['fail'].format(problems=_problems(len(fails)), first=fails[0]) if fails else W['pass'], 'model')   # release 1, A2: the heading names the model, as the small line does
    return {**_view('fail' if fails else 'pass', head, W['by_older'].format(n=len(rows)), fails, passed, adv), 'who': 'model'}


def steps_view(store, session, chain, plan=None, now=None):
    """The check of a graphic in steps: each step's own view, one line for all; two steps alike measured by the program is advice (R3)."""
    views = [check_view(session, r, plan, now) for r in chain]
    fails = [f'Step {n}: {f}' for n, v in enumerate(views, 1) for f in v['faults']]
    passed = [f'Step {n}: {p}' for n, v in enumerate(views, 1) for p in v['passed']]
    alike = alike_steps(store, chain)
    adv = list(dict.fromkeys([W['alike'].format(a=a, b=b) for a, b in alike] + [x for v in views for x in v['advice']]))
    state = 'fail' if fails else 'not_checked' if any(v['state'] in ('not_checked', 'none') for v in views) else 'pass'
    head = (W['fail'].format(problems=_problems(len(fails)), first=fails[0][0].lower() + fails[0][1:]) if fails else
            next((v['head'] for v in views if v['state'] in ('not_checked', 'none')), W['pass']) if state == 'not_checked' else W['pass'])
    counts = [len((looked(r) or {}).get('lines') or []) for r in chain]
    by = W['by_steps'].format(ns=_and(counts)) if any(counts) else ''
    na = [f'Step {n}: {x}' for n, v in enumerate(views, 1) for x in (v.get('na') or {}).get('lines') or []]   # release 1, A5
    whos = {v.get('who') or 'claude' for v in views if v['state'] in ('pass', 'fail')}   # release 1, A2: who checked the steps: Claude, the model before this release, or both
    who = 'model' if whos == {'model'} else 'mixed' if 'model' in whos else ''
    if who:
        head, by = _named(head, who), ' '.join(f"Step {n}: {v['by']}" for n, v in enumerate(views, 1) if v['by'])
    names = [f'step {n}, {_name(f)}' for n, v in enumerate(views, 1) for f in v['faults']]   # release 1, B3: the short line names the step; two steps alike is a note
    return {**_view(state, head, by, fails, passed, adv, na=na, notes=[W['alike'].format(a=a, b=b) for a, b in alike], names=names), **({'who': who} if who else {}), '_views': views, '_alike': alike}


def alike_steps(store, chain):
    """R3: the neighbouring steps the program measures as almost the same (the fingerprint the old refusal used), as (n, n+1) pairs."""
    from . import lookalike
    prints = []
    for r in chain:
        try:
            prints.append((V._fingerprints(store, r['key']) or {}).get('graphic'))
        except Exception:
            prints.append(None)
    return [(i, i + 1) for i in range(1, len(chain)) if prints[i - 1] is not None and prints[i] is not None and lookalike.distance(prints[i - 1], prints[i]) <= lookalike.BITS_GRAPHIC]


def rule_id(text):
    """C6: a rule of a drawing's brief, known by its words (as `ref_sets.check_lines`)."""
    return hashlib.sha1(' '.join(str(text or '').split()).lower().encode('utf-8')).hexdigest()[:8]


_MARK = r'(?:(still|motion)|with\s+([A-Za-z0-9_-]+))?'   # release 2, F13: the two pieces of a mark, in either order, with a comma or a semicolon
RULE_CLASS = re.compile(r'[*_]*(must|should)[*_]*\s*(?:\(\s*' + _MARK + r'\s*[,;]?\s*' + _MARK + r'\s*\))?[*_]*\s*:\s*[*_]*\s*', re.I)
# F13: a class, brackets and a colon left at the start of a rule's words: a mark that was not read. The critic's point 7: only when the brackets hold a
# mark word (`still`, `motion`, `with`); other words in brackets ("must (per the spec): …") are the rule's own words, as before F13.
RULE_MARKED = re.compile(r'[*_]*(must|should)[*_]*\s*\([^)]*\b(still|motion|with)\b[^)]*\)[*_]*\s*:', re.I)


def rules_of(text):
    """C6: the rules of a drawing (`work/motion/<shot>/rules.md`) as the server keeps them: every list line, numbered or bulleted, with its id.
    design/221 row 11: a rule starts with `must:` or `should:`; the class is kept beside the rule, never in its words or its id; no class is a must.
    Fix set B3 (19 Nov 2026): after the class the rule writer marks what shows the rule, `must (still):` (the finished picture, standing still) or
    `must (motion):` (only the moving drawing); kept as `shows`. A rule with no mark (a list written before) has no `shows`.
    Fix set A1.2: a rule that compares with another drawing names it in the mark, `must (still, with D1):`; kept as `with`."""
    out = {}
    for raw in str(text or '').splitlines():
        m = re.match(r'\s*(?:[-*]|\d+[.)])\s+(.*\S)', raw)
        if m:
            c = RULE_CLASS.match(m.group(1))
            if c and ((c.group(2) and c.group(4)) or (c.group(3) and c.group(5))):
                c = None   # the critic's point 7: both `still` and `motion` (or two drawings) in one mark is no mark the server reads: left in the words, refused at the upload
            words = ' '.join(m.group(1)[c.end() if c else 0:].split())
            shows, other = (c.group(2) or c.group(4), c.group(3) or c.group(5)) if c else (None, None)
            out.setdefault(rule_id(words), {'id': rule_id(words), 'rule': words, 'class': c.group(1).lower() if c else 'must', **({'shows': shows.lower()} if shows else {}),
                                           **({'with': other} if other else {})})
    return list(out.values())


NOTE_HEAD = re.compile(r'(questions?|notes?|colou?rs? to add)\b', re.I)   # the critic's A3: at the start of the heading only ("Corner note and labels:" is a heading of rules)
LIST_LINE = re.compile(r'(\s*)(?:[-*]|\d+[.)])\s+(\S.*)')


def notes_in(text):
    """design/221 row 15: the lines of a rules text that are not rules (they belong in questions.md): the list lines under a heading that starts with
    Question(s), Note(s) or Colours to add, and a list line that is such a heading itself ("- Questions for the operator:") with the lines indented under it."""
    out, under, bullet = [], False, None   # bullet: the indent of a list line that heads a list of questions or notes
    words = lambda raw: re.sub(r'^[\s#*_>-]+|[\s*_:]+$', '', raw)
    for raw in str(text or '').splitlines():
        m = LIST_LINE.match(raw)
        if m:
            indent = len(m.group(1).expandtabs(4))
            if bullet is not None and indent > bullet:
                out.append(raw.strip())
                continue
            bullet = None
            if m.group(2).rstrip().rstrip('*_').endswith(':') and NOTE_HEAD.match(words(m.group(2))):
                out.append(raw.strip())
                bullet = indent
            elif under:
                out.append(raw.strip())
        elif re.match(r'\s*(?:#+\s|\*\*|__)', raw) or raw.rstrip().rstrip('*_').endswith(':'):   # a heading: '# …', '**…**' or a line ending in a colon
            bullet, under = None, bool(NOTE_HEAD.match(words(raw)))
    return out


def fact_view(session, store, job, shot_id, brief_now=None):
    """F3, C6: a motion drawing's fact check, from the verdicts of the project it was rendered from (as `select_take` reads them): passed, not
    passed with its open rules in full, or none yet. N is the number of rules the server holds for the project (else the verdict's).
    design/221 (the critic's A2): brief_now(shot_id) gives the shot's brief lines now; a project whose brief changed since its rules were written
    reads as not passed, in the words of the verdict's refusal."""
    try:
        sha = (V.load_json(store, job['request']['request_key']) or {}).get('sha256')
    except Exception:   # the request file cannot be read: no fact check is known
        sha = None
    rounds = V.motion_rounds(session, shot_id, sha) if sha else []   # design/221 (the critic's A1): a verdict on other rules is ignored
    if not rounds:
        return _view('none', W['fact_none'], show='all')
    last = rounds[-1]
    rules = last.get('rules') or []
    n = len(((session.get('motion_projects') or {}).get(sha) or {}).get('rules') or []) or len(rules)
    open_ = ([str(r.get('rule')) for r in rules if r.get('pass') is False and r.get('class') != 'should']   # design/221 row 11: a failed must; no class is a must
             + [W['not_seen'].format(need=r.get('need'), rule=r.get('rule')) for r in rules if r.get('pass') == V.NOT_SEEN] + [str(x) for x in last.get('label_musts') or []])   # rows 12, 17
    notes = [str(r.get('rule')) for r in rules if r.get('pass') is False and r.get('class') == 'should']
    na = [_say(str(r.get('rule')).rstrip('.'), r.get('why')) for r in rules if r.get('pass') == V.NA]   # release 1, A5: a rule that does not apply: no fault, not counted as held, listed apart
    if na and len(na) == len(rules) and not last.get('label_musts'):   # nothing was judged: never "passed"
        return _view('not_checked', W['all_na_rules'], W['fact_by'].format(n=n), show='all', na=na)
    n -= len(na)
    redo = max(int(last.get('round') or 1) - 1, 0)
    r = f"{redo} redo round{'' if redo == 1 else 's'}"
    changed = V.stale_brief(store, None, None, session, sha, shot_id, now=brief_now) if brief_now else []
    if changed:
        return _view('fail', W['fact_stale'], W['fact_by'].format(n=n), [V.MOTION_BRIEF_CHANGED.format(shot=shot_id, names=', '.join(f'"{k}"' for k in changed))],
                     show='all')
    head = (W['fact_fail'].format(k=len(open_), n=n, r=r) if open_ else
            W['fact_pass_notes'].format(k=f"{len(notes)} note{'' if len(notes) == 1 else 's'}", r=r) if notes else W['fact_pass'].format(n=n, r=r))
    return _view('fail' if open_ else 'pass', head, W['fact_by'].format(n=n), open_,
                 [W['passed_rule'].format(rule=x.get('rule')) for x in rules if x.get('pass') is True], [str(x) for x in last.get('stranger') or []], 'all',
                 W['fact_passed_head'].format(n=n, round=int(last.get('round') or 1)), W['fact_saw'], na=na, notes=notes)   # design/221 row 11: the notes, as data for the page


def server_view(check):
    """An older drawing (the svg route): the server's own checks, as before."""
    if not check:
        return _view('none', W['server_none'], show='all')
    open_ = list(dict.fromkeys([str(c.get('check')) for c in check.get('must_failed') or []] + [str(l.get('line')) for l in check.get('scorecard') or [] if l.get('state') == 'Fail']))
    return _view('fail' if open_ else 'pass', W['server_fail'].format(k=len(open_)) if open_ else W['server_pass'], faults=open_, show='all')


# ---------- the context of a line ----------

def _t(frames, fps):
    s = frames / fps
    return f'{int(s // 60)}:{s % 60:04.1f}'


def where(session, plan, shot_id):
    """The film-time line of a shot, its gap, and the words under it."""
    fps = float(Fraction(str((V._fps(session) if session.get('source') else None) or 25)))   # a card's heading never fails for the film's frame rate
    name = V.coded(V.shot_names(plan, session), shot_id)   # VW-25 issue 7: the shot in words, its code last
    for gap, sh in V._accepted_shots(plan, session):
        if sh['id'] == shot_id:
            gap_words = f"Gap {gap['gap_id']}" + (f", {gap['title']}" if gap.get('title') else '')
            return {'where': W['where'].format(start=_t(sh['start_frame'], fps), end=_t(sh['end_frame'], fps), secs=f"{(sh['end_frame'] - sh['start_frame']) / fps:.1f}", gap=gap_words),
                    'at': _t(sh['start_frame'], fps), 'words': str(sh.get('narration') or ''), 'shot': sh, 'gap': gap, 'name': name}
    return {'where': '', 'at': '', 'words': '', 'shot': None, 'gap': None, 'name': name}


VOICEOVER_MAX = 400   # characters of a shot's voiceover on a card; longer is cut at a sentence end


def voiceover(words):
    """Release 1 of 27 Nov 2026, part H: the narration spoken during a shot, whole; a long one is cut at the last sentence end inside
    VOICEOVER_MAX (at a word when it has none), with "…". Any script is shown as written."""
    text = ' '.join(str(words or '').split())
    if len(text) <= VOICEOVER_MAX:
        return text
    head = text[:VOICEOVER_MAX]
    ends = [m.end() for m in re.finditer(r'[.!?।။。](?=\s)', head)]
    return (head[:ends[-1]] if ends else head[:head.rfind(' ')] if ' ' in head else head) + ' …'


def heading(session, plan, shot_id):
    """Part H (SK, 27 Nov 2026: a code tells the operator nothing; the voiceover does): the one heading of a shot, for every card and page line:
    its name in words with the code last, and the voiceover spoken during it ("no voiceover under this shot" when there is none)."""
    w = where(session, plan, shot_id)
    return {'name': w['name'], 'voiceover': voiceover(w['words']) or W['no_voiceover']}


def heading_text(session, plan, shot_ids, most=None):
    """The heading as a card's text. One shot: its voiceover (the card's question begins with its name). Several: each shot's name and
    voiceover, in the order given; with `most`, the first `most` and then how many more."""
    ids = list(shot_ids or [])
    if not ids:
        return ''
    head = W['words_head']
    if len(ids) == 1:
        return f"{head} {heading(session, plan, ids[0])['voiceover']}"
    shown = ids[:most] if most else ids
    rows = [f"- {h['name']}\n  {head} {h['voiceover']}" for h in (heading(session, plan, sid) for sid in shown)]
    left = len(ids) - len(shown)
    return '\n'.join(rows + ([f"and {left} more shot{'' if left == 1 else 's'}."] if left else []))


def shot_picture(session, shot_id):
    """Part H: the picture that stands for a shot on a card, where one exists: the still placed in the film, else the chosen video's frame
    sheet (or the video), else the approved still of its AI video, else its newest made picture. {key, name} or None; nothing is made for it."""
    refs = session.get('references') or {}
    asset = (session.get('assets') or {}).get(shot_id) or {}
    ref = refs.get(asset.get('reference_id') or '')
    if ref and ref.get('key'):
        return {'key': ref['key'], 'name': f'{shot_id}.png'}
    sel = (session.get('selections') or {}).get(shot_id) or {}
    if sel:
        sheet = ((session.get('take_checks') or {}).get(str(sel.get('job_id'))) or {}).get('sheet_key')
        if sheet:
            return {'key': sheet, 'name': f'{shot_id}-frames.jpg'}
        if (sel.get('take') or {}).get('key'):
            return {'key': sel['take']['key'], 'name': f'{shot_id}.mp4'}
    still = next((st for st in reversed(((session.get('guides') or {}).get(shot_id) or {}).get('stills') or []) if st.get('status') == 'approved' and st.get('key')), None)
    if still:
        return {'key': still['key'], 'name': f'{shot_id}-still.png'}
    mine = [r for r in refs.values() if r.get('key') and r.get('status') in ('approved', 'candidate') and V.made_for(session, r) == shot_id]
    best = next((r for r in reversed(mine) if r.get('status') == 'approved'), mine[-1] if mine else None)
    return {'key': best['key'], 'name': f'{shot_id}.png'} if best else None


def footage(session, gap):
    """Your footage before and after the shot's gap: an approved footage picture of the clip just before and just after it (none at the film's
    start or end). ponytail: a picture of the neighbouring clip, not the exact frame at the cut; the master's in and out points if that matters."""
    beside = (session.get('gap_neighbours') or {}).get((gap or {}).get('gap_id')) or {}
    frames = [r for r in session['references'].values() if r.get('kind') == 'frame' and r.get('status') == 'approved' and r.get('key')]
    pick = lambda clip: next((r for r in frames if clip and (r.get('source') or {}).get('media_id') == clip), None)
    return pick(beside.get('before')), pick(beside.get('after'))


def _pic(ref, label, role, **extra):
    return {'_key': ref.get('key'), '_mark': str(ref.get('sha256') or ''), 'label': label, 'role': role, **extra}


def _foot_pics(session, gap):
    before, after = footage(session, gap)
    return ([_pic(before, W['before'], 'before', cmp_cap=W['before'])] if before else []), ([_pic(after, W['after'], 'after', cmp_cap=W['after'])] if after else [])


def earlier_tries(session, ref):
    """The rejected pictures of the same place as this one (V._slot), newest first."""
    try:
        slot = V._slot(session, ref)
    except Exception:
        return []
    out = []
    for r in session['references'].values():
        if r.get('status') == 'rejected' and r['id'] != ref['id'] and r.get('kind') == ref.get('kind') and r.get('key'):
            try:
                if V._slot(session, r) == slot:
                    out.append(r)
            except Exception:
                continue
    return sorted(out, key=lambda r: str((r.get('rejection') or {}).get('at') or ''), reverse=True)


def _why(r):
    rej = r.get('rejection') or {}
    notes = str(rej.get('notes') or '').strip()
    return W['why'].format(words=notes) if notes else rej['cause'] if rej.get('cause') else W['why_none']


def _details(ref, made_from=None):
    gen = ref.get('generation') or {}
    rows = [['How it was asked for', [str(gen.get('prompt') or '')[:1200]]]] if gen.get('prompt') else []
    if made_from:
        rows.append(['The approved looks it was made from', made_from])
    how = [f"Picture AI: {'an edit of earlier pictures' if gen.get('parents') else 'a new picture'}"] + ([f"Size: {ref['width']}x{ref['height']}"] if ref.get('width') else [])
    return rows + [['How it was made', how]]


def _made_from(session, plan, ref):
    names = {e['id']: e.get('name') or e['id'] for e in (plan or {}).get('elements') or []}
    out = []
    for p in (ref.get('generation') or {}).get('parents') or []:
        r = session['references'].get(p.get('id')) or {}
        if r.get('kind') in ('sheet', 'frame', 'supplied'):
            n = names.get(r.get('element_id')) or r.get('element_id')
            if n and n not in out:
                out.append(n)
    return out


def _fix_button(which, hint, faults, say):
    return {'label': W['correct'] if which == 'correct' else which, 'choice': 'correct', 'act': 'fix', 'needs_words': True, 'hint': hint, 'go': W['go'],
            'prefill': ' '.join(faults), 'say': say}


def picture_line(store, session, plan, ref, style=False, now=None):
    """Kind `style` or `still` (contract 3.4, 3.5): the picture, its footage before and after, its earlier tries, its check, three answers."""
    check = check_view(session, ref, plan, now)
    tries = earlier_tries(session, ref)
    kind = 'style' if style else 'still'
    w = where(session, plan, V.made_for(session, ref)) if not style else {'where': '', 'at': '', 'words': '', 'gap': None}
    before, after = _foot_pics(session, w['gap']) if not style else ([], [])
    main = _pic(ref, W['style_name'] if style else W['new'], 'main')   # its failed lines are the check's, said once (`check.faults`); a new try says so in `try` only
    earlier = [_pic(t, W['earlier'].format(n=len(tries) - i), 'earlier', cmp_cap=W['earlier'].format(n=len(tries) - i), why=_why(t)) for i, t in enumerate(tries)]
    which = ORDINAL.get(len(tries) + 1, 'a new') if tries else 'a new'
    yes = {'label': W['yes_' + kind], 'choice': 'yes', 'act': 'approve', 'needs_words': False, 'say': W['say_style'] if style else W['say_still'].format(at=w['at']),
           **({'against': True} if check['state'] == 'fail' else {})}   # release 1, B1: one click; the page and the log say it went against the check
    no = {'label': W['no'], 'choice': 'no', 'act': 'again', 'needs_words': False,
          'say': W['say_no_style'] if style else (W['say_no_still_n'].format(which=which) if tries else W['say_no_still'].format(which=which))}
    fix = _fix_button('correct', W['hint_style' if style else 'hint_still'], check['faults'], W['say_fix_' + kind])
    line = {'kind': kind, 'name': W['style_name'] if style else name_of(session, plan, ref), 'kind_words': W['kind_' + kind], 'ask': W['ask_' + kind],
            'pics': before + [main] + after + earlier, 'check': check, 'buttons': [yes, no, fix], 'details': _details(ref, None if style else _made_from(session, plan, ref))}
    if style:
        line['sub'] = W['style_sub']
    else:
        line.update(where=w['where'], film_at=w['at'], words_head=W['words_head'], words=w['words'], **{'try': W['try'].format(n=len(tries) + 1) if tries else ''},
                    foot_head=W['foot_still_try' if tries else 'foot_still'])
    return line


def steps_line(store, session, plan, shot_id, chain, now=None):
    """Kind `steps` (contract 3.6): every step side by side with what appears on which words, one check, "Yes, use all N steps" and one
    "Correct step n" per step (F2). Two steps alike is advice and asks once (R3)."""
    n = len(chain)
    check = steps_view(store, session, chain, plan, now)
    views, alike = check.pop('_views'), check.pop('_alike')
    w = where(session, plan, shot_id)
    states = (w['shot'] or {}).get('states') or []
    before, after = _foot_pics(session, w['gap'])
    cap = lambda i: (W['step_cap'].format(n=i + 1, words=states[i]['words'], what=states[i].get('what_appears') or '') if i < len(states) and states[i].get('words') else
                     W['step_cap_bare'].format(n=i + 1, what=(states[i] if i < len(states) else {}).get('what_appears') or ''))
    steps = [_pic(r, W['step_label'].format(n=i + 1), 'step', n=i + 1, caption=cap(i), faults=views[i]['faults'],
                  **({'check_head': W['check_head_step_model' if views[i].get('who') else 'check_head_step'].format(n=i + 1)} if views[i]['faults'] else {})) for i, r in enumerate(chain)]
    tries = [t for r in chain for t in earlier_tries(session, r)]
    earlier = [_pic(t, W['earlier_step'].format(s=step_of(session, t) or '?', n=1), 'earlier', cmp_cap=W['earlier_step'].format(s=step_of(session, t) or '?', n=1), why=_why(t)) for t in tries]
    buttons = [{'label': W['yes_steps'].format(n=n), 'choice': 'yes', 'act': 'approve', 'needs_words': False, 'say': W['say_steps'].format(n=n, at=w['at']),
                **({'against': True} if check['state'] == 'fail' else {})}]   # release 1, B1: one click; two steps alike is a note of the check (B3), not a question
    for k in range(1, n + 1):
        later = list(range(k + 1, n + 1))
        say = (W['say_step'].format(k=k, words='{words}', later=(f'Step {later[0]} is' if len(later) == 1 else f'Steps {_and(later)} are')) if later else
               W['say_step_last'].format(k=k, p=k - 1, words='{words}'))
        b = _fix_button(W['correct_step'].format(n=k), W['hint_step'].format(n=k), views[k - 1]['faults'], say)
        buttons.append({**b, 'choice': f'correct:{k}'})
    return {'kind': 'steps', 'name': w['name'], 'kind_words': W['kind_steps'], 'ask': W['ask_steps'].format(n=n), 'where': w['where'], 'film_at': w['at'],
            'words_head': W['words_head'], 'words': w['words'], 'try': W['try'].format(n=2) if tries else '', 'strip_head': W['strip_head'],
            'foot_head': W['foot_steps_try' if tries else 'foot_steps'], 'pics': before + steps + after + earlier, 'check': check, 'buttons': buttons,
            'details': _details(chain[0]) if chain else []}


def finish_listed(fin):
    from . import motion
    parts = [motion.FINISH_PHRASE[n] for n in motion.FINISH if n in (fin or [])]
    return _and(parts) if parts else ''


def _drawn_here(plan, shot_id):
    from .font_sample import drawn_shots
    return plan is None or any(s['id'] == shot_id for s in drawn_shots(plan))   # design/218b: a shot a revision took out shows no note


def colour_notes(session, shot_id, plan=None):
    """design/218 A: the colours added for a thing this drawing shows, said without asking (by Claude, or with the operator's words)."""
    if not _drawn_here(plan, shot_id):
        return []
    return [f"Added {'by Claude' if r['by'] == 'claude' else 'with your words'}: {r['words']} for the {r['thing']}, because {r['reason']}."
            for r in (session.get('added_colours') or {}).values() if shot_id in r['shots']]


def drawing_notes(session, shot_id, plan=None):
    """design/218b: the plain lines Claude recorded for this drawing (a part seen from another direction), said without asking."""
    if not _drawn_here(plan, shot_id):
        return []
    return [n['text'] for n in session.get('drawing_notes') or [] if shot_id in n['shots']]


def drawn_line(store, session, plan, job, check, fin, motion_take, brief_now=None):
    """Kind `drawn` (contract 3.7): the video (its page copy) with the frame sheet one click away, the fact check with every open rule in full,
    select (release 1, B1: one click also when it is held; `held` says why, in view before the buttons), reject, and "Take the effect away" when it has a finish (no confirmation, D8)."""
    res, shot_id = job.get('result') or {}, job['unit']
    view = fact_view(session, store, job, shot_id, brief_now) if motion_take else server_view(check)
    w = where(session, plan, shot_id)
    ev = res.get('evidence') or {}
    held = (W['held_fact'] if view['state'] == 'fail' and motion_take else W['held_none'] if view['state'] == 'none' and motion_take else
            W['held_server'] if view['state'] == 'fail' else W['held_unread'] if check.get('not_read') else W['held_short'] if ev.get('timing_matches_placement') is False else '')
    listed = finish_listed(fin)
    before, after = _foot_pics(session, w['gap'])
    sheet_key = res.get('sheet_key') or check.get('sheet_key')
    pics = before + ([{'_key': sheet_key, '_mark': str(res.get('sha256') or ''), 'label': W['sheet'], 'role': 'sheet'}] if sheet_key else []) + after
    select = {'label': W['select'], 'choice': 'select', 'act': 'select', 'needs_words': False, 'say': W['say_select'].format(at=w['at']),
              **({'against': True} if held else {})}   # release 1, B1: one click, no typed reason; `held` says why above the buttons
    buttons = [select, {'label': W['reject'], 'choice': 'reject', 'act': 'reject', 'needs_words': True, 'hint': W['hint_reject'], 'go': W['go'],
                        'prefill': ' '.join(view['faults']) if view['state'] == 'fail' else '', 'say': W['say_reject']}]
    if listed:
        buttons.append({'label': W['plain'], 'choice': 'plain', 'act': 'plain', 'needs_words': False, 'say': W['say_plain'].format(finish=listed)})
    secs = ev.get('exact_seconds') or ((job.get('request') or {}).get('duration_seconds'))
    return {'kind': 'drawn', 'name': w['name'], 'kind_words': W['kind_drawn'], 'ask': W['ask_drawn'], 'where': w['where'], 'film_at': w['at'],
            'words_head': W['words_head'], 'words': w['words'], 'try': '', 'foot_head': W['foot_drawn'],
            'video': {'_key': res.get('key') or '', '_mark': str(res.get('sha256') or ''), 'code': '', 'label': W['video'], 'none': W['video_none']},
            'finish': W['finish'].format(finish=listed) if listed else '', 'held': held, 'pics': pics, 'check': view, 'buttons': buttons,
            'details': [['How it was made', ['Built as a web animation by Claude helpers on the laptop, rendered to video by the server. No picture AI.' if motion_take else 'Drawn by the server from the scene file.']
                         + ([f'Length: {float(secs):.2f} s.'] if secs else [])]] + ([['Colours', colour_notes(session, shot_id, plan)]] if colour_notes(session, shot_id, plan) else [])
                + ([['Notes', drawing_notes(session, shot_id, plan)]] if drawing_notes(session, shot_id, plan) else [])}   # design/218 A, 218b


def question_line(session, plan, item, q, ref):
    """Kind `question` (contract 3.3): the server's question in plain words (no reference ids, no amounts), one button per choice."""
    choices = [str(c) for c in q.get('choices') or []]
    plain = lambda t: _plain_cost(re.sub(r'\b[0-9a-f]{8}(?:-[0-9a-f-]{4,})?(?:…|\.\.\.)?', 'this picture', str(t or '')))
    labels = [plain(c)[:1].upper() + plain(c)[1:] for c in choices]
    return {'kind': 'question', 'name': (name_of(session, plan, ref) if ref else str(item)), 'kind_words': W['kind_question'], 'ask': plain(q.get('question')), 'from': W['q_from'],
            'pics': [_pic(ref, name_of(session, plan, ref), 'main')] if ref and ref.get('sha256') and ref.get('key') else [],
            'buttons': [{'label': l[:60], 'choice': f'c{i}', 'act': 'answer', 'needs_words': False, 'say': W['say_answer'].format(choice=l)} for i, l in enumerate(labels, 1)][:4],
            'details': []}


def chat_text(line):
    """One flow, two front ends: what the chat shows of a page line: the check line, its faults, the measured advice, the place, the finish, why it is held."""
    c = line.get('check') or {}
    na = c.get('na') or {}   # release 1, A5: the lines that did not apply, one row: never among the faults
    said = c.get('short') or c.get('head')   # release 1, B3: the short line, a warning in full, the count of the lines that did not apply (the chat has no fold); a line with no short line says its head
    rows = ([line['where']] if line.get('where') else []) + ([said] if said else []) + (c.get('faults') or [])[1 if c.get('state') == 'fail' and c.get('show') != 'all' and not c.get('short') else 0:6] \
        + ([na['head']] if na else []) + ([c['by']] if c.get('who') and c.get('by') and c.get('short') else []) \
        + (c.get('advice') or [])[:4] + ([line['finish']] if line.get('finish') else []) + ([line['held']] if line.get('held') else [])
    return '\n'.join('- ' + r for r in rows if r)


# ---------- design/221 phase 4: what step 6 must make, and each thing's state ----------

STATE = {'none': 'not started', 'making': 'being made', 'checking': 'being checked by Claude', 'redo': 'being redone', 'done': 'made and checked',
         'held': 'held (needs a decision)', 'answered': 'answered', 'failed': 'could not be made',
         'stale': 'must be rendered again (the plan or the shared parts changed)'}   # design/221 (the critic's point 4)
ORDER = ('done', 'answered', 'checking', 'making', 'stale', 'redo', 'held', 'failed', 'none')   # the order of the counts in the line
GROUPS = (('drawn', 'Drawn graphics'), ('still', 'Stills'), ('steps', 'Graphics in steps'), ('component', 'Components'))
COMPLETE = (STATE['done'], STATE['answered'], STATE['failed'])   # a thing that could not be made never keeps the page closed
KIND_WORDS = {'drawn': 'kind_drawn', 'still': 'kind_still', 'steps': 'kind_steps', 'component': 'kind_component'}


def _pictures_state(session, plan, mine, now, need=1):
    """A still's (or a graphic in steps') state from the pictures made for its shot, in the order they were asked."""
    live = [r for r in mine if r.get('status') in ('generating', 'candidate', 'approved')]
    if any(r['status'] == 'generating' for r in live):
        return 'redo' if any(r.get('status') in ('rejected', 'failed') for r in mine) else 'making'
    made = [r for r in live if r['status'] == 'candidate' and r.get('sha256')]
    if any(retry_due(session, r, plan) for r in made):
        return 'redo'   # phase 2 part D: its check failed: made again once before the operator sees it
    if any(not offered(session, r, plan, now) for r in made):
        return 'checking'
    if live:
        return ('done' if made else 'answered') if len(live) >= need else 'making'   # some steps of a graphic made: the others come
    return ('failed' if mine[-1].get('status') == 'failed' else 'redo') if mine else 'none'   # only rejected tries: another is asked


def _component_state(rs):
    """A component (a part a drawn graphic places): approved by Claude's check, never asked of the operator."""
    live = [r for r in rs if r.get('status') in ('generating', 'candidate', 'approved')]
    if not live:
        return 'failed' if rs[-1].get('status') == 'failed' else None   # rejected and replaced: not counted
    if any(r['status'] == 'generating' for r in live):
        return 'redo' if len(rs) > len(live) else 'making'
    if any(r['status'] == 'approved' for r in live):
        return 'done'
    look = looked(live[-1])
    return 'redo' if look and (look.get('not_checked') or _failed_lines(live[-1]) or _na_lines(live[-1])) else 'checking'   # a failed one is made again by the assistant


def _ts(v):
    """A time from the database (datetime) or the session (ISO text), else None."""
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _stale(session, plan, job):
    """A render Select would refuse (`visuals_stage.select_gate`, release 1 of 27 Nov 2026, part B: the one gate): its own shot is not as it was
    when it was rendered, the shared parts it placed are not the approved ones now, or it carries no stamp of its shot (made before the release).
    Retired: the page's own rule (the plan version looked up, the parts compared here)."""
    return bool(V.select_gate(session, plan, job.get('unit'), job.get('request') or {}, job))


def _failed_render(session, sid, rows, last):
    """design/221 (the critic's point 3): a failed render is redone while it can be asked again or anything newer of the shot exists (a project,
    a verdict, a still); it could not be made when the same project's render failed twice and nothing newer exists. (state, the next step)."""
    at = _ts(last.get('created_at'))
    seen = [p.get('at') for p in (session.get('motion_projects') or {}).values() if p.get('shot_id') == sid] \
        + [c.get('at') for c in (session.get('motion_checks') or {}).get(sid) or []] + [((session.get('motion_stills') or {}).get(sid) or {}).get('at')]
    if at and any(t and t > at for t in map(_ts, seen)):
        return 'redo', ''
    mark = lambda j: (j.get('request') or {}).get('sha256') or (j.get('request') or {}).get('preparation_id')
    err = str(last.get('error') or 'no reason given')[:300]
    if mark(last) and sum(1 for j in rows if j['status'] == 'failed' and mark(j) == mark(last)) >= 2:
        return 'failed', W['render_failed_twice'].format(shot=sid, error=err)
    return 'redo', W['render_failed'].format(shot=sid, error=err)


def _by_other(rows):
    """Fix set A1.2: a drawing's comparing rules by the drawing they compare with, {other: [the rules' words]}."""
    out = {}
    for c in rows:
        out.setdefault(c['with'], []).append(c['rule'])
    return out


def _compare_said(sid, cmp):
    """Fix set A1.2: what stands with a drawing's comparisons (`visuals_stage.compared`), as the sentences of the next-step line."""
    return ' '.join(W['compare_' + k].format(shot=sid, other=o, n=len(rs), s='' if len(rs) == 1 else 's', rule=rs[0], round=cmp['round']) for k in ('due', 'waits', 'closed')
                    for o, rs in _by_other(cmp.get(k) or []).items())


def _rejected_take(session, sid, take_rows):
    """Release 2, F15 (20 Nov 2026): the operator's review of the shot's newest render when it rejects it and no project of the shot was uploaded
    since: the drawing itself is refused, so it is built again with their words (a new render of the same project would be the same drawing).
    None when a newer render exists (made again without the effect) or a rebuild is already uploaded."""
    rows = [j for j in take_rows or [] if j.get('provider') == 'drawn' and j.get('unit') == sid]
    review = ((session.get('reviews') or {}).get(str(rows[-1]['id'])) or [{}])[-1] if rows else {}
    made = _ts(rows[-1].get('created_at')) if rows else None
    newer = any(t and made and t > made for t in (_ts(p.get('at')) for p in (session.get('motion_projects') or {}).values() if p.get('shot_id') == sid))
    return review if review.get('decision') == 'rejected' and not newer else None


def _selected_state(session, plan, sid, take_rows):
    """Release 2, F12: (state, the next step) of a drawn shot the operator selected. 'answered', unless a comparison with another drawing came due
    afterwards (that drawing's still end-frame was approved or replaced): then it is being checked until the comparison is judged. A comparison
    that fails on it after the selected render leaves it answered, with one sentence for the operator (the critic's point 5: the selection is
    theirs; only their Reject has it redrawn)."""
    cmp = V.compared(session, plan, sid)
    if cmp.get('due'):
        return 'checking', _compare_said(sid, cmp)
    job = next((j for j in take_rows or [] if str(j['id']) == str(session['selections'][sid].get('job_id'))), None)
    made = _ts((job or {}).get('created_at'))
    after = [c for c in (session.get('motion_checks') or {}).get(sid) or [] if not c.get('still') and made and (_ts(c.get('at')) or made) > made]   # the verdicts since the selected render
    bad = next((r for c in after for r in c.get('rules') or [] if r.get('with_png') and r.get('pass') is False and r.get('class') != 'should'), None)
    if not bad or not V.open_rules(after[-1]):   # until a later verdict of the drawing is clean
        return 'answered', ''
    held = ((session.get('motion_projects') or {}).get(after[-1].get('sha256') or '') or {}).get('rules') or []
    other = next((x['with'] for x in held if x.get('with') and rule_id(x.get('rule')) == rule_id(bad.get('rule'))), 'another drawing')
    return 'answered', W['selected_failed'].format(shot=sid, other=other, words=str(bad.get('where') or bad.get('fix') or bad.get('rule') or '').rstrip('.'))


def _drawn_state(session, sh, take_rows, plan=None):
    """(state, the render job shown, the next step) of a drawn shot, from what the server knows: the render jobs, the held verdict, the verdicts,
    the uploads, the still end-frame. 'made and checked' only once its render is ready and not stale."""
    sid = sh['id']
    rows = [j for j in take_rows or [] if j.get('provider') == 'drawn' and j.get('unit') == sid
            and ((session.get('reviews') or {}).get(str(j['id'])) or [{}])[-1].get('decision') != 'rejected']
    last = rows[-1] if rows else None
    if V.held_drawing(session, sid):
        return 'held', last, ''
    checks = [c for c in (session.get('motion_checks') or {}).get(sid) or [] if not c.get('still')]
    cmp = V.compared(session, plan, sid) if plan else {}   # fix set A1.2: its rules that compare with another drawing
    said = _compare_said(sid, cmp)
    if cmp.get('due'):
        return 'checking', None, said   # a comparison that came due is a must not yet judged: never dropped, and the page waits for it
    if last and last['status'] == 'ready':
        made, judged = _ts(last.get('created_at')), _ts(checks[-1].get('at')) if checks else None
        if made and judged and judged > made and V.held_rules(checks[-1]):
            return 'redo', None, said   # a verdict after the render failed a must (a comparison that came due): the old render is not the drawing any more
        redrawn = [t for t in (_ts(p.get('at')) for p in (session.get('motion_projects') or {}).values() if p.get('shot_id') == sid) if t]
        if made and sid not in (session.get('motion_bound') or {}) and any(t > made for t in redrawn):
            return 'redo', None, said   # fix set A3.5: a new still uploaded after the render (set_motion unbound the shot): being redone at once. Release 2, F8: a new animated project too
        was = (last.get('request') or {}).get('sha256')
        if was and (session.get('motion_bound') or {}).get(sid) not in (None, was):
            return 'making', None, said   # the redrawn project passed and is the bound one: this render is of the project before; its own render comes next
        return ('stale', None, said) if plan and _stale(session, plan, last) else ('done', last, said)
    if last and last['status'] in ('queued', 'running', 'storage_pending'):
        return 'making', None, said
    if last:
        state, due = _failed_render(session, sid, rows, last)
        return state, None, due
    if checks:
        gone = None if V.open_rules(checks[-1]) else _rejected_take(session, sid, take_rows)   # release 2, F15: clean, and the operator rejected its render: built again
        if gone:
            words = str(gone.get('notes') or '').strip()
            return 'redo', None, ' '.join(x for x in (W['take_rejected'].format(shot=sid, words=f': "{words}"' if words else ''), said) if x)
        return ('redo' if V.held_rules(checks[-1]) else 'checking' if V.open_rules(checks[-1]) else 'making'), None, said   # clean: its render comes next
    if any(p.get('shot_id') == sid and not p.get('still') for p in (session.get('motion_projects') or {}).values()):
        return 'checking', None, ''
    started = (session.get('motion_stills') or {}).get(sid) or (session.get('motion_checks') or {}).get(sid) or any(p.get('shot_id') == sid for p in (session.get('motion_projects') or {}).values())
    return ('making' if started else 'none'), None, ''


def expected(session, plan, take_rows, now=None):
    """Every thing step 6 must make, from the accepted plan and the session, in film order, then the components: [{kind, id, name, state, job?}];
    kind still, steps, drawn or component; the state in plain words (STATE)."""
    out, refs = [], list(session['references'].values())
    shots, names = {sh['id']: sh for _, sh in V._accepted_shots(plan, session)}, V.shot_names(plan, session)
    wait = None   # release 2, F11: what the builders of the drawn graphics wait for, worked out once
    for gap, sh in V._accepted_shots(plan, session):
        kind = {'still': 'still', 'graphic_sequence': 'steps', 'drawn': 'drawn'}.get(V.route_of(sh))
        if not kind:
            continue
        sid, job, due, turn = sh['id'], None, '', ('', '')
        held = V.refs_waited(session, plan, sh) if kind == 'still' else []
        if sid in (session.get('selections') or {}) or sid in (session.get('assets') or {}):
            state, due = _selected_state(session, plan, sid, take_rows) if kind == 'drawn' and sid in (session.get('selections') or {}) else ('answered', '')   # F12
        elif kind == 'drawn':
            state, job, due = _drawn_state(session, sh, take_rows, plan)
            if state != 'held' and V.base_changed(session, plan, gap, sh):   # release 2, F1, F6: built on a still that was replaced: made again from its still
                state, job = 'redo', None
        else:
            mine = [r for r in refs if r.get('kind') in (('keyframe', 'isolated') if kind == 'still' else ('state',)) and V.made_for(session, r) == sid and not r.get('set')]
            state = _pictures_state(session, plan, mine, now, len(sh.get('states') or []) if kind == 'steps' else 1)
        if kind == 'drawn' and state in ('none', 'making', 'checking', 'redo'):
            turn = V.drawn_turn(session, plan, gap, sh, shots)   # fix set A1.4: whose turn it is
            if state == 'redo' and turn == ('', '') and _rejected_take(session, sid, take_rows):
                turn = ('motion', '')   # F15: the operator rejected its render: its builder
            wait = V.parts_wait(plan, session) if wait is None else wait
            if wait and not turn[0].startswith('check'):   # F11: the shared parts are not the approved ones: no builder is named, and the line says what is waited for
                turn, due = ('', ''), ' '.join(x for x in (due, wait if turn[0] else '') if x)
        stuck = None
        if STATE[state] not in COMPLETE:   # phase 4 part D (SK's second decision): the 30 minutes hold for step 6 too
            made = [r for r in refs if V.made_for(session, r) == sid]
            busy = any(r.get('status') == 'generating' for r in made) or any(j.get('unit') == sid and j.get('status') in JOB_OPEN for j in take_rows or [])
            stuck = stuck_of(session, sid, STUCK['supplied' if kind == 'still' and sh.get('supplied') and state == 'none' else 'refs' if held and state == 'none' else state], made,
                             [j for j in take_rows or [] if j.get('unit') == sid], busy, now)
        out.append({'kind': kind, 'id': sid, 'name': V.coded(names, sid), 'state': STATE[state], **({'job': job} if job else {}), **({'due': due} if due else {}), **({'stuck': stuck} if stuck else {}),
                    **({'supplied': sh['supplied']} if kind == 'still' and sh.get('supplied') else {}),   # release 3 (N4): it waits for the operator's own picture
                    **({'waits_for': [e.get('name') or e['id'] for e in held]} if held else {}),   # phase 2 part C: the things whose approved reference it waits for
                    **({'turn': turn[0]} if turn[0] else {}), **({'waits_on': turn[1]} if turn[1] else {})})
    names = {e['id']: e.get('name') or e['id'] for e in plan.get('elements') or []}
    by = {}
    for r in refs:
        if r.get('kind') == 'component':
            by.setdefault(r.get('element_id') or r['id'], []).append(r)
    for eid, rs in by.items():
        state = _component_state(rs)
        if state:
            stuck = None if STATE[state] in COMPLETE else stuck_of(session, eid, STUCK[state], rs, [], any(r.get('status') == 'generating' for r in rs), now)
            out.append({'kind': 'component', 'id': eid, 'name': str(names.get(eid) or eid), 'state': STATE[state], **({'stuck': stuck} if stuck else {})})
    return out


# ---------- release 1 of 27 Nov 2026, phase 4 part D (SK): a thing that is stuck does not keep the page closed ----------

STUCK_MINUTES = 30   # one number (SK, 27 Nov 2026), for the page of step 7 and, by his second decision, the page of step 6
JOB_OPEN = ('queued', 'running', 'submitted', 'storage_pending', 'submission_unknown')
STUCK = {   # what a stuck thing waits for, one sentence for each state that is not complete
    'none': 'Nothing has been ordered for it since {since}. Ask the assistant why.',
    'making': 'Nothing is being made for it since {since}. Ask the assistant why.',
    'checking': "It waits for Claude's check since {since}. Ask the assistant why.",
    'redo': 'It is to be made again; nothing has happened since {since}. Ask the assistant why.',
    'held': 'It waits for your decision in the chat since {since}.',
    'stale': 'It must be rendered again; nothing has happened since {since}. Ask the assistant why.',
    'supplied': 'It waits for your own picture since {since}.',
    'refs': 'It waits for the approved references of what it shows since {since}.',
}
STUCK_LEAD = f'Not moving for {STUCK_MINUTES} minutes or more: '


def _marks(o):
    """Every time recorded in a record: the values of `at` and of the keys that end in `_at`, at any depth."""
    if isinstance(o, dict):
        for k, v in o.items():
            if (k == 'at' or str(k).endswith('_at')) and isinstance(v, (str, datetime)):
                try:
                    d = v if isinstance(v, datetime) else datetime.fromisoformat(v)
                except ValueError:
                    continue
                yield d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            else:
                yield from _marks(v)
    elif isinstance(o, (list, tuple)):
        for x in o:
            yield from _marks(x)


def stuck_of(session, ident, sentence, refs, rows, busy, now=None):
    """Part D, rule 1: the one test of "stuck", for a shot of step 7 and a thing of step 6: nothing is queued or running for it (`busy`, said by
    the caller) and nothing has happened for it for STUCK_MINUTES. None, or {'since', 'waits'}: since when, and what it waits for in one
    sentence. "Since when" is the newest time recorded on the thing: in its own records of the session (any record filed under its id), on its
    pictures (`refs`) and on its jobs (`rows`); a thing with no time at all counts from the plan's last version or acceptance.
    Why: on VW-25 eleven paid takes waited about 25 hours for one shot. Retired: one unfinished thing keeping the page closed with no time limit."""
    if busy:
        return None
    own = [v[ident] for v in session.values() if isinstance(v, dict) and ident in v]
    at = max(_marks([own, list(refs), [dict(j) for j in rows]]), default=None) or max(_marks([session.get('versions'), session.get('accepted')]), default=None)
    now = now or _now()
    if at is None or now - at < timedelta(minutes=STUCK_MINUTES):
        return None
    since = at.strftime('%H:%M UTC') if at.date() == now.date() else f"{at.day} {at.strftime('%b, %H:%M UTC')}"
    return {'since': at.isoformat(), 'waits': sentence.format(since=since)}


def settled(items):
    """Nothing of the step is still moving: every thing is complete or stuck."""
    return all(i['state'] in COMPLETE or i.get('stuck') for i in items)


def complete(items):
    """The page of step 6 opens: every thing is made and checked, answered, or could not be made (a held drawing waits for its card).
    Part D: a stuck thing does not keep it closed; with a stuck thing the page opens only when something waits for an answer on it."""
    return settled(items) and (not any(i.get('stuck') for i in items) or any(i['state'] == STATE['done'] for i in items))


def stuck_due(items):
    """Part D, rule 4: the sentence of each stuck thing, the same in the status line, the next-step line and on the page. '' when none."""
    same = {}
    for i in items:
        if i.get('stuck'):
            same.setdefault(i['stuck']['waits'], []).append(i['name'])
    return STUCK_LEAD + ' '.join(f"{'; '.join(names)}: {waits}" for waits, names in same.items()) if same else ''


def waiting_rows(session, plan, items):
    """layout.waiting: the stuck things, listed apart on the page: the name, the voiceover, what it waits for and since when."""
    shots = {sh['id'] for _, sh in V._accepted_shots(plan, session)} if plan else set()
    return [{'name': i['name'], 'kind_words': heading_text(session, plan, [i['id']]) if i['id'] in shots else '', 'state': 'stuck', 'note': i['stuck']['waits']} for i in items if i.get('stuck')]


def status_line(items):
    """One short line of counts: 'Drawn graphics: 5 made and checked, 3 being redone, 1 held (needs a decision). Stills: 9 made and checked.'"""
    out = []
    for kind, head in GROUPS:
        mine = [i['state'] for i in items if i['kind'] == kind]
        if mine:
            out.append(f"{head}: " + ', '.join(f'{mine.count(STATE[s])} {STATE[s]}' for s in ORDER if STATE[s] in mine) + '.')
    return ' '.join(out)


def stills_due(items, hold=()):
    """design/221 row 19: the still shots with no picture asked for yet, said in the tool's next-step line until each is ordered.
    The critic's point 10c: `hold` (`ask_shots`): the shots whose person the operator must be asked about first are not named."""
    ids = [i['id'] for i in items if i['kind'] == 'still' and i['state'] == STATE['none'] and i['id'] not in hold and not i.get('supplied') and not i.get('waits_for')]   # phase 2 part C: only the stills that are due
    return (W['stills_due_one'] if len(ids) == 1 else W['stills_due']).format(n=len(ids), ids=', '.join(ids)) if ids else ''


def stills_wait(items):
    """Release 1 of 27 Nov 2026, phase 2 part C: the stills that wait for the references of what they show, counted, each thing named once."""
    rows = [i for i in items if i['kind'] == 'still' and i['state'] == STATE['none'] and i.get('waits_for') and not i.get('supplied')]
    names = list(dict.fromkeys(n for i in rows for n in i['waits_for']))
    one, ref1 = len(rows) == 1, len(names) == 1
    return W['stills_wait'].format(n=len(rows), s='' if one else 's', w='s' if one else '', r='' if ref1 else 's', names=', '.join(names), it='It is' if one else 'They are',
                                   that='that is' if ref1 else 'those are') if rows else ''


def supplied_due(items):
    """SK, 23 Nov 2026 (release 3, N4): the still shots that wait for the operator's own picture, said as that, never as "no picture asked for"."""
    rows = [f"{i['id']} ({i['supplied']})" for i in items if i['kind'] == 'still' and i['state'] == STATE['none'] and i.get('supplied')]
    return W['supplied_due'].format(n=len(rows), s='' if len(rows) == 1 else 's', rows=', '.join(rows)) if rows else ''


def drawn_due(items):
    """design/221 (the critic's points 3, 4): what the assistant does next for the drawn graphics whose render went stale or failed."""
    stale = [i['id'] for i in items if i['kind'] == 'drawn' and i['state'] == STATE['stale']]
    out = [W['render_stale_one'].format(shot=stale[0]) if len(stale) == 1 else W['render_stale'].format(n=len(stale), ids=', '.join(stale))] if stale else []
    return ' '.join(dict.fromkeys(out + [i['due'] for i in items if i['kind'] == 'drawn' and i.get('due')]))   # release 2, F11: what several drawings wait for is said once


def starts(items):
    """Fix set A1.4, A1.3 (19 Nov 2026): the helpers of the drawn graphics that can start now, to be started together in one message, and which
    drawing waits on which; the motion is named only when no still end-frame is left to build or check (the stills come first)."""
    of = lambda *turns: [i['id'] for i in items if i['kind'] == 'drawn' and i.get('turn') in turns]
    stills, motion, checks = of('still'), of('motion'), of('check-still', 'check')
    first = stills or of('check-still')
    what = [W[k].format(ids=', '.join(ids), n=len(ids)) for k, ids in (('start_stills', stills), ('start_motion', [] if first else motion), ('start_checks', checks)) if ids]
    waits = [f"{i['id']} on {i['waits_on']}" for i in items if i['kind'] == 'drawn' and i.get('waits_on')]
    return ' '.join(x for x in (W['start_now'].format(what='; '.join(what)) if what else '', W['motion_after'].format(ids=', '.join(motion)) if first and motion else '',
                                W['waits_on'].format(pairs='; '.join(waits)) if waits else '') if x)


def coming(items):
    """layout.coming: the things that could not be made, shown apart on the page (nothing is listed there while it is being made: the page opens at the end)."""
    return [{'name': i['name'], 'kind_words': W[KIND_WORDS[i['kind']]], 'state': 'failed', 'note': W['failed']} for i in items if i['state'] == STATE['failed']]


def say(lines, rows):
    """The one message the assistant posts with the link (contract 2.4)."""
    more = (W['say_failed_one'] if len(rows) == 1 else W['say_failed'].format(n=len(rows))) if rows else ''
    if not lines:
        return ' '.join(x for x in (W['say_nothing'], more) if x)
    head = W['say_need_one'] if len(lines) == 1 else W['say_need'].format(n=f'{len(lines)} things')
    return head + ''.join('\n- ' + l['name'] for l in lines) + '\n' + ' '.join(x for x in (more, W['say_done']) if x)
