"""design/139 (SK's design/138 answers, 2 Nov 2026): instruction version 3, one exact replacement each. The old wording goes on RETIRED
(server/retired-sentences.json), which a test keeps out of v3.json for good.
Run once: python scripts/d139_wording_v3.py. c1_split_v3.py --check applies apply_visuals() for the visuals stage."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'

STAGES = [   # (stage, field, old, new); field 'prompt' or 'steps.N'
    ('brief', 'prompt', "Brand and safety rules,\nwhether the speaker may be seen on camera, the languages spoken in the footage, the\nnarration language, and where the film plays and its frame shape (production.format:\nframe 16:9, 9:16, 1:1 or 4:5) are the operator's words, asked on every film in one\nmessage; the list is in the steps.",
     "Brand and safety rules,\nwhether the speaker may be seen on camera and where the film plays (production.format)\nare the operator's words, asked on every film in one message; the list is in the steps.\nThe narration language is read from the script; the analysis detects the footage\nlanguages; the film's shape is asked after the clips are listed."),
    ('brief', 'steps.1', "brand_and_safety_rules, show_speaker_video, field_speech_languages, narration_language, and target_runtime_s only if the operator gives one. Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), the languages spoken in the footage (an empty list if nobody speaks or there is no footage), the narration language, whether the speaker may be seen on camera, and where the film plays and its frame shape (16:9, 9:16, 1:1 or 4:5; destinations such as YouTube or Instagram; watched muted or not; 16:9 and no destinations unless they say).",
     "brand_and_safety_rules, show_speaker_video, narration_language (the script's language as a code, read from it; tell the operator), industry (only when the client card has none: ask once), and target_runtime_s only if the operator gives one. Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), whether the speaker may be seen on camera, and where the film plays (destinations such as YouTube or Instagram; watched muted or not; none unless they say). Never ask the footage languages (the analysis detects them) or the film's shape (asked after the clips are listed)."),
    ('brief', 'steps.2', "a production block: field languages, narration language, speaker on camera,", "a production block: narration language (from the script), industry when asked, speaker on camera,"),
    ('brief', 'steps.2', "where it plays and the frame shape (16:9 unless they say; watched muted or not),", "where it plays (watched muted or not),"),
    ('options', 'prompt', " A real shot over 4 s needs hold_reason.", ""),
    ('options', 'prompt', "At least 3 s; no upper limit (the visuals stage splits long ones into shots of up to 30 s). A blank under 3 s is refused: hold a neighbouring shot longer, or give short_reason so the operator decides.",
     "Any length: the visuals stage fills it (a picture or a drawing for a second or two, AI video for 2 s or more, takes of up to 10 s)."),
    ('options', 'prompt', " E2 (a blank over 12 s, an AI-only scene included): a run of AI pictures that long reads as synthetic; find a footage cut-in, a B-roll clip or a frame that relates and split it, or say in intent why it must stay whole.", ""),
    ('options', 'steps.3', "(`act_on`: R5, B1, B2, rule 11, E1, E2, N17 (claims), N14;", "(`act_on`: R5, B1, B2, N17 (claims), N14;"),
    ('voice', 'prompt', "MODELS AND SETTINGS. Eleven v4 is the default: stability and similarity only,\nstart at 0.5 / 0.75 and adjust only for a specific listening concern. Multilingual\nv2 takes stability, similarity, style, speed and speaker boost; Eleven v3 takes\nstability 0, 0.5 or 1. Never switch the model silently or to get around a limit.",
     "MODELS AND SETTINGS. Eleven v4 only (v2 and v3 are retired): stability and similarity,\nstart at 0.5 / 0.75 and adjust only for a specific listening concern; the voices page\nshows both. A narration uses the settings of that voice's latest audition."),
    ('media', 'steps.1', "Confirm the list with the operator (names preserved, nothing analysed yet).",
     "Confirm the list with the operator (names preserved, nothing analysed yet). Then `vw shape` counts the horizontal and vertical clips and their frame rates: recommend the shape most clips have (horizontal or vertical) and the common rate, with the counts; the operator decides. Then ask the AI video shape, recommending the film's; record both before the analysis: `vw shape <horizontal|vertical> --video <horizontal|vertical> --fps <n> --quote \"<their words>\"`."),
    ('analysis', 'steps.1', "or a clip needs a decision.", "or a clip needs a decision. Then tell the operator the footage languages (`languages` in status); never assume English."),
]
INTAKE_STEP = ("Once the script is recorded, name the video category it fits, with one line why (documentary-explainer, advertisement-product, training-education, social-ugc, "
               "narrative-story); ask the operator to confirm or change it, the five as choices, and record their answer: `vw category <name> --quote \"<their words>\"`. "
               "The brief waits for it; never assume one.")
VISUALS_PROMPT = [
    ("The film has a cap of ₹5,000; only the builder changes it, on SK's word;",
     "At the start of the visuals stage tell the operator the estimate and the film's cap (₹5,000; only the builder changes it, on SK's word);"),
]
VISUALS_PARTS = [
    ('plan', "AI video 3 to 10 s (longer refused), 3–5 s in an AI run; over 12 s of AI video back to back in a gap is warned (`ai_run`), footage or not: break it with a frame, still or graphic.",
     "AI video 2 to 10 s on screen (made at 3 s and cut when shorter; under 2 s use a picture; longer refused); a picture or a drawing may be a second or two."),
    ('plan', "A graphic dissolves in and out over 8 frames and other cuts are hard, so AI scenes and footage read as one world; otherwise `transition_in` (`transition_out` on a gap's last shot only): cut, dissolve or match, with `transition_reason` (refused without).",
     "Name every join: `transition_in` on every shot (`transition_out` on a gap's last shot only): cut, dissolve or match; a dissolve or a match with `transition_reason`; refused without."),
    ('later', "the SVG keeps to a viewBox of the film's aspect (16:9),", "the SVG keeps to a viewBox of the film's shape (16:9 or 9:16),"),
    ('later', "the fonts Noto Sans or the run's brand font,", "the film's font (asked once before the first drawing, Noto Sans recommended: `vw font <name> --quote`) or the run's brand font,"),
    ('later', "(appear, build, move, highlight, fade;", "(appear, build, move, highlight with its `color` (#RRGGBB, chosen per drawing to stand out against the background and everything in the frame, the brand colours where they stand out), fade;"),
    ('later', "generated pictures follow the palette and guidelines, never show a competitor, and never generate a logo.",
     "generated pictures follow the palette and guidelines, never show a competitor, and never generate a logo. A card with no colours: ask the operator once which they prefer and record their words (`vw colours \"<their words>\" --quote`; \"no preference\" is an answer); a preferred colour is never forced where it would not stand out."),
]
RETIRED = ["A real shot over 4 s needs hold_reason", "A blank under 3 s is refused", "a run of AI pictures that long reads as synthetic", "3–5 s in an AI run",
           "over 12 s of AI video back to back in a gap is warned", "A graphic dissolves in and out over 8 frames and other cuts are hard",
           "takes stability, similarity, style, speed and speaker boost", "the languages spoken in the footage (an empty list if nobody speaks",
           "16:9 and no destinations unless they say", "the fonts Noto Sans or the run's brand font", "rule 11, E1, E2"]


def apply_visuals(prompt, parts):
    """For c1_split_v3.py --check (applied after design/134)."""
    for old, new in VISUALS_PROMPT:
        assert prompt.count(old) == 1, old[:60]
        prompt = prompt.replace(old, new)
    for name, old, new in VISUALS_PARTS:
        part = next(p for p in parts if p['name'] == name)
        assert part['text'].count(old) == 1, (name, old[:60])
        part['text'] = part['text'].replace(old, new)
    return prompt


def apply_stages(d):
    st = {s['name']: s for s in d['stages']}
    for name, field, old, new in STAGES:
        s = st[name]
        if field == 'prompt':
            assert s['prompt'].count(old) == 1, (name, old[:60])
            s['prompt'] = s['prompt'].replace(old, new)
        else:
            n = int(field.split('.')[1])
            assert s['steps'][n].count(old) == 1, (name, field, old[:60])
            s['steps'][n] = s['steps'][n].replace(old, new)
    if INTAKE_STEP not in st['intake']['steps']:
        st['intake']['steps'].append(INTAKE_STEP)
    prod = st['brief']['output_shape']['production']
    prod.pop('field_speech_languages', None)
    prod['narration_language'] = 'language code, read from the script'
    prod['industry'] = "only when the client card has none: the operator's answer"
    prod['format'].pop('frame', None)


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    vis = next(s for s in d['stages'] if s['name'] == 'visuals')
    try:
        vis['prompt'] = apply_visuals(vis['prompt'], vis['parts'])
        apply_stages(d)
    except AssertionError as exc:
        sys.exit(f'not applied: {exc}')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    r = json.loads(R.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied', len(STAGES) + len(VISUALS_PROMPT) + len(VISUALS_PARTS), 'replacements and the intake step')


if __name__ == '__main__':
    main()
