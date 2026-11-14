"""design/192 (Deepa, 13 Nov 2026; SK's yes to build, 14 Nov): instruction version 3, the stages intake, brief, script and voice, from the VW-23
stage reviews. Intake rows 2, 4-7; brief rows 1-5; script row 1; voice rows 2, 5, 6. Every anchor is found once (line breaks inside an anchor may
differ); run once: python scripts/d192_wording_v3.py"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
MARK = 'The document may be a bare script or a plan around one'   # present once the script has run

CATEGORY_BLOCK = (
    "THE FILM'S CATEGORY (recorded at intake)\n\n{category}\n\n"
    "The category sets the defaults you propose; the operator's words and the script come first.\n"
    "- documentary-explainer, training-education: the ending is what the viewer now understands or does next; no sales call to\n"
    "  action unless the script or the operator asks.\n"
    "- advertisement-product: the ending is an action for the viewer (buy, visit, book, call), with the directory's CTA when it has one.\n"
    "- social-ugc: the ending is short: the point, or one light invitation (follow, share, try it).\n"
    "- narrative-story: the ending is the story's own close; no call to action unless the script has one.\n"
    "- not recorded (a film started before categories): no sales call to action unless the script or the operator asks.\n"
    "Choose examples and wording that suit this category, never another's.\n\n")

INTAKE_PROMPT = [
    ('Clients rarely send a bare script. They send a plan: scene headings, durations, lists of visuals, section labels, notes to whoever makes the film. The spoken words are in there, wrapped in all of it.',
     'The document may be a bare script or a plan around one: scene headings, durations,\nlists of visuals, section labels, notes to whoever makes the film. In a plan the spoken\nwords are in there, wrapped in all of it.'),
    ('Your job is to say WHICH LINES ARE NOT THE SCRIPT.', 'Your job is to say which lines are not the script.'),
    ("YOU NEVER REWRITE A LINE. NOT ONE CHARACTER. You return line NUMBERS to remove. You do not return text, you do not correct spelling, you do not tidy anything. "
     "The tool removes the lines you name from the operator's own document and keeps every other line exactly as it is.",
     "You never rewrite a line. You return line numbers to remove; the tool removes those lines\nfrom the operator's own document and keeps every other line exactly as it is. "
     "A line that looks\nmistyped (a slip of spelling, a doubled word, a figure that contradicts another) is listed in `notes`\nwith its line number, for the operator to see; you do not change it."),
    ('"Scene 3: Why Choose CSEBs?"', '"Scene 3: Why it matters"'),
    ('a description of what is SEEN,', 'a description of what is seen,'),
    ('"Brick kilns emitting smoke", "Close-up of finished CSEB blocks"', '"Close-up of the finished product",\n                    "A customer opens the box"'),
    ('Anything that will be SPOKEN', 'Anything that will be spoken'),
    ('"Typically, the mixture contains: 50% sand, 20% clay"', '"The plan costs 499 a month and covers five users"'),
    ('A line you wrongly KEEP is', 'A line you wrongly keep is'),
    ('A line you wrongly REMOVE is', 'A line you wrongly remove is'),
    ('So the bar for removing is HIGH.', 'So the bar for removing is high.'),
    ('KEEP IT and let the human', 'keep it and let the human'),
    ('BLANK LINES STAY.', 'Blank lines stay.'),
    ('Name the SUBJECT and the DELIVERABLE - "Compressed Earth Blocks - Documentary Explainer". Never put in',
     'Name the subject and what the film is, for example "Rainwater Harvesting - Explainer",\n"Trail Running Shoe - Product Advertisement", "Forklift Safety - Training Film". '
     'The examples show the form only;\nnever copy their words. Never put in'),
]
INTAKE_STEPS = [
    ('`remove` by line number (never retype speech), `titles` (up to three, recommended first), notes.',
     '`remove` by line number, `titles` (up to three, recommended first), notes (with any line that looks mistyped, by its number).'),
    ('Ask one question: which title, and approve or corrections? They may pick one or give their own.',
     'Ask ONE question with the question tool, in three parts, each with your recommended answer first: (1) which title (they may give their own); '
     '(2) the cleaned script: approve, or corrections; (3) the video category (documentary-explainer, advertisement-product, training-education, social-ugc, narrative-story) '
     'with one line why; when the prepare prints `last_category` (what this client\'s last film recorded), recommend it unless the script plainly is another kind. '
     'The question tool shows at most four choices: the recommended one first, the others next; they can type another.'),
    ('run `vw stage intake record --title "<the title they chose>" --quote "<their reply>"`.',
     'run `vw stage intake record --title "<the title they chose>" --category <the category they chose> --quote "<their reply>"`.'),
    ('Once the script is recorded, name the video category it fits, with one line why (documentary-explainer, advertisement-product, training-education, social-ugc, narrative-story); '
     'ask the operator to confirm or change it, the five as choices, and record their answer: `vw category <name> --quote "<their words>"`. The brief waits for it; never assume one.',
     'The category is asked with the title (step 3) and recorded by the same command. `vw category <name> --quote "<their words>"` records it when it was left out, or changes it later. '
     'The brief waits for it; never assume one.'),
]
BRIEF_PROMPT = [
    ('An awareness-only conclusion is valid. Never add a sales call to action by default.',
     "An awareness-only conclusion is valid. The ending follows the film's category\n  (below) unless the operator says otherwise."),
    ('("why it matters" is not a chapter; "laying the first course" is)',
     '("why it matters" is not a chapter; a step of a process such as "fitting the filter" is,\nand so is a place or thing the camera shows, such as "the showroom floor")'),
    ("are the operator's words, asked on every film in one message; the list is in the steps.",
     "are the operator's words, asked in one message; for a client with a latest brief they come\nfilled in, for one approval (the steps say how)."),
    ('WHAT THE DOCUMENT SAID ABOUT ITS OWN LENGTH', CATEGORY_BLOCK + 'WHAT THE DOCUMENT SAID ABOUT ITS OWN LENGTH'),
]
BRIEF_STEPS = [
    ('Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none),',
     'For a client with no latest brief, ask the operator, in one message: the brand and safety rules (examples from several kinds of film: no competitor logos; '
     'protective gear required on site; nothing staged; no price claims; no children\'s faces; an empty list if none),'),
    ('named plainly in a few words ("Mixing the mortar", "Pointing the joints")',
     'named plainly in a few words (a step, such as "Fitting the filter"; or a place or thing, such as "The showroom floor")'),
    ('When the client has a latest brief, give its answers as the recommendation and ask once for the other production values: same as last time, or changes? Record exactly what they say.',
     'When the client has a latest brief, the prepare prints `same_as_last`: its production values filled in (brand and safety rules, speaker on camera, where it plays, target length). '
     'Put them in the proposal as they are, ask only for a value marked "not asked last time", and never ask the production values in a message of their own: '
     'they are shown in the one approval question of the next step. Record exactly what they say.'),
    ('then any consequential questions. Put each operator answer verbatim in `answers` by question id; required questions block record until answered. Ask one question: approve, or changes?',
     'then any consequential questions. Put each operator answer verbatim in `answers` by question id; required questions block record until answered. '
     'Ask one question with the question tool: approve, or changes? When the production values are last time\'s, the first answer to click is "Same as last time, approved": '
     'it approves the brief and those values together.'),
]
SCRIPT_STEPS = [
    ('When the assessment names figures or claims the message rests on, list them in `claims` (each {text, checked: true or false, source when checked});',
     'List in `claims` every number, quantity, duration, percentage or cost the narration speaks (in digits or in words), every safety or structural claim, '
     'and every comparison or saving a graphic will show (each {text, checked: true or false, source when checked}); never what the footage itself shows;'),
    ('When the assessment names a figure or claim that the message rests on, propose a web search: say "I am deviating from the usual procedure.',
     'Claim checks, by five rules: (a) always propose a check for any number, quantity, duration, percentage or cost, in digits or in words; '
     '(b) always for a safety claim or a claim that something holds, lasts or bears a load (structural); (c) for a comparison or a saving, when a graphic will show it; '
     '(d) never for what the footage itself shows; (e) one question for all the checks, with the question tool: the claims listed, a tick each (several may be ticked, none is an answer; '
     'the tool takes four choices a question and four questions a call, so more than four claims go in the same call). "Qualitative" is never a reason to leave out a claim under (a) or (b). '
     'A claim not ticked stays in `claims` with checked: false. For the ticked claims say once: "I am deviating from the usual procedure.'),
]
SPOKEN = 'will sound wrong when spoken'   # script row 2 (SK, 14 Nov: "Yes, add it"); its own mark, so the script adds it to a file the first part already changed
SCRIPT_PROMPT = [
    ('Avoid copy-editing for its own sake.',
     'Avoid copy-editing for its own sake. A line that will sound wrong when spoken (a slip\nwaiting to happen, a tongue-twister, a sentence too long for one breath) is a useful change:\npropose it as a normal before/after.'),
]
VOICE_STEPS = [
    ('the two lists (best_fit, experimental) and three test passages of 50 to 100 words; present the kind of film, each list as rows (first words, tag, reason) with the count of tagged sentences, '
     'one line on the experimental idea, and the three passages with why each tests a voice; ask one question: which list (best fit, experimental, none) and which test passage (1, 2 or 3).',
     'the two lists (best_fit, experimental) and ONE recommended test passage of 50 to 100 words; the kind of film is the run\'s category, as the prepare prints it. Present three lines: '
     'the kind of film, the best-fit register with the count of tagged sentences, the passage with why it tests a voice. Ask one question with the question tool whose first answer is '
     '"Best fit, passage 1" (recommended), then "Show the lists", "Experimental", "No direction". Show the lists as rows (first words, tag, reason), the experimental idea, '
     'or two more passages only when the operator asks; add the extra passages to the file then.'),
]
DIRECTION_PROMPT = [
    ('- The kind of film, which you state in one line before anything else: a documentary explainer, a promotional film, a social video, a testimonial, a training film, or another kind; '
     'from the brief and the script, never assumed. The kind sets the range: a documentary is measured and even; a promotional film builds and lands; a social video is quick and warm; '
     'a training film is clear and unhurried.',
     "- The kind of film: the run's category, printed by the prepare as `kind_of_film`. State it in one\n  line and never work it out again (only when the prepare prints none, name it from the brief and\n"
     "  the script). The kind sets the range: documentary-explainer is measured and even;\n  advertisement-product builds and lands; social-ugc is quick and warm; training-education is\n"
     "  clear and unhurried; narrative-story follows the turns of its story."),
    ('Propose three test passages from the script, each one contiguous, starting at a sentence start, 50 to 100 words, named by their first and last word numbers '
     '(the prepare prints every sentence with its word numbers). Each tests something different: a passage with a figure to land, a passage where the register turns, the close. '
     'Say in one line why each one tests a voice. The operator chooses one; every tryout reads it, with the tags of its sentences.',
     'Propose one test passage from the script (two more only when the operator asks): contiguous,\nstarting at a sentence start, 50 to 100 words, named by its first and last word numbers\n'
     '(the prepare prints every sentence with its word numbers). Choose the passage that tests a voice\nhardest: a figure to land, or the place where the register turns. Say in one line why. '
     'When more\nare asked for, each tests something different (the close, a list, a name). Every tryout reads the\nchosen passage, with the tags of its sentences.'),
    ("Present the kind of film in one line, the register of each list, then each list as rows: the sentence's first four or five words, the tag, the reason in a short phrase. "
     'Then the one line on the experimental idea. Ask: best fit, experimental, changes, or none.',
     'Present the kind of film in one line, the best-fit register with the count of tagged sentences,\nand the recommended passage. Ask one question whose first answer is "Best fit, passage 1".\n'
     "Show the lists (each as rows: the sentence's first four or five words, the tag, the reason in a\nshort phrase) and the one line on the experimental idea only when the operator asks. "
     'The answers:\nbest fit, experimental, changes, or none.'),
]


def swap(text, old, new, where):
    """Replace `old` (whitespace runs matched loosely) with `new`; it must be found exactly once."""
    pattern = r'\s+'.join(re.escape(tok) for tok in old.split())
    found = re.findall(pattern, text)
    if len(found) != 1:
        sys.exit(f'not applied: {where}: found {len(found)} times: {old[:70]}')
    return re.sub(pattern, lambda _: new, text, count=1)


def swap_all(text, pairs, where):
    for old, new in pairs:
        text = swap(text, old, new, where)
    return text


def swap_steps(steps, pairs, where):
    for old, new in pairs:
        pattern = r'\s+'.join(re.escape(tok) for tok in old.split())
        hits = [i for i, s in enumerate(steps) if re.search(pattern, s)]
        if len(hits) != 1:
            sys.exit(f'not applied: {where}: in {len(hits)} steps: {old[:70]}')
        steps[hits[0]] = swap(steps[hits[0]], old, new, where)
    return steps


def apply(d):
    st = {s['name']: s for s in d['stages']}
    changed = False
    if SPOKEN not in st['script']['prompt']:
        st['script']['prompt'] = swap_all(st['script']['prompt'], SCRIPT_PROMPT, 'script prompt')
        changed = True
    if MARK in st['intake']['prompt']:
        return changed
    st['intake']['prompt'] = swap_all(st['intake']['prompt'], INTAKE_PROMPT, 'intake prompt')
    swap_steps(st['intake']['steps'], INTAKE_STEPS, 'intake steps')
    st['brief']['prompt'] = swap_all(st['brief']['prompt'], BRIEF_PROMPT, 'brief prompt')
    swap_steps(st['brief']['steps'], BRIEF_STEPS, 'brief steps')
    swap_steps(st['script']['steps'], SCRIPT_STEPS, 'script steps')
    swap_steps(st['voice']['steps'], VOICE_STEPS, 'voice steps')
    st['voice']['direction_prompt'] = swap_all(st['voice']['direction_prompt'], DIRECTION_PROMPT, 'direction prompt')
    return True


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    if not apply(d):
        print('already applied')
        return
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('intake, brief, script and voice instructions: design/192 applied')


if __name__ == '__main__':
    main()
