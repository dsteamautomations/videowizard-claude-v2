"""Text stages: intake, brief, script. Each has prepare() (inputs + prompt for the model) and record() (validate the
model's proposal in out/<stage>.json, derive files, record the stage output). Ported rules from v1 intake.py / passages.py."""
import hashlib
import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from extraction import SUFFIXES, ExtractionError, extract

KINDS = {'scene_heading', 'timing', 'section_label', 'visual_note', 'production_note', 'other'}


class Refused(Exception):
    pass


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def stamp(ws, stage):
    """prepared_at for a stage (design/34 1.19): written by prepare, read back by record into the summary."""
    path = ws / 'work' / f'{stage}-prepared.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    at = now_iso()
    path.write_text(json.dumps({'prepared_at': at}), encoding='utf-8')
    return at


def stamps(ws, stage):
    try:
        prepared = json.loads((ws / 'work' / f'{stage}-prepared.json').read_text(encoding='utf-8')).get('prepared_at')
    except (OSError, ValueError):
        prepared = None
    return {'prepared_at': prepared, 'recorded_at': now_iso()}


def cleaned_script(ws, intake):
    """out/source.txt as recorded at intake (design/34 1.14): the local copy must match the recorded digest."""
    try:
        text = (ws / 'out' / 'source.txt').read_text(encoding='utf-8')
    except OSError:
        raise Refused('out/source.txt is missing on this machine; restore it with `vw pull` or revise intake.')
    expected = (intake.get('summary') or {}).get('source_digest')
    if expected and digest(text) != expected:
        raise Refused('The cleaned script on this machine (out/source.txt) differs from the recorded one; restore it with `vw pull` or revise intake.')
    return text


def numbered(source):
    return '\n'.join(f'{i}: {line.rstrip(chr(13))}' for i, line in enumerate(source.split('\n'), 1))


def remove_lines(source, removals):
    """v1 rule: the model names line numbers; the application removes them. Speech is never retyped."""
    if not isinstance(removals, list):
        raise Refused('Provide `remove` as a list (empty for a clean source).')
    lines = source.split('\n')
    seen = set()
    for item in removals:
        if not isinstance(item, dict) or set(item) != {'line', 'kind', 'why'}:
            raise Refused('Each removal needs exactly line, kind and why.')
        n = item['line']
        if type(n) is not int or not 1 <= n <= len(lines) or n in seen:
            raise Refused(f'Removal line {n!r} is not a unique line number of the current source (1–{len(lines)}).')
        if not lines[n - 1].strip():
            raise Refused(f'Blank source lines are preserved (line {n}).')
        if item['kind'] not in KINDS or not isinstance(item['why'], str) or not 1 <= len(item['why'].strip()) <= 500:
            raise Refused(f'Line {n}: use a supported kind and a short reason.')
        seen.add(n)
    return ''.join(line + ('\n' if i < len(lines) else '') for i, line in enumerate(lines, 1) if i not in seen)


def paragraphs(text):
    out, start = {}, 0
    spans = []
    for sep in re.finditer(r'\n\s*\n', text):
        if text[start:sep.start()].strip():
            spans.append((start, sep.start()))
        start = sep.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return {f'P{i:03d}': text[a:b].strip() for i, (a, b) in enumerate(spans, 1)}


def read_proposal(ws, stage):
    path = ws / 'out' / f'{stage}.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise Refused(f'Write the proposal to out/{stage}.json first ({exc.__class__.__name__}).')
    if not isinstance(data, dict):
        raise Refused(f'out/{stage}.json must be a JSON object.')
    return data


def need_text(data, keys, stage):
    for k in keys:
        if not isinstance(data.get(k), str) or not data[k].strip():
            raise Refused(f'out/{stage}.json: `{k}` must be a non-empty string.')


# ---------- intake ----------

def intake_prepare(ws, procedure, prior, file=None, earlier_titles=None):
    files = sorted(p for p in (ws / 'in').iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES)
    if not files:
        raise Refused(f"Put the source script in {ws / 'in'} as TXT, MD, Fountain, DOCX or PDF, then run prepare again.")
    if file:
        source = ws / 'in' / file
        if source.name != file or source not in files:
            raise Refused(f"--file must name one document in {ws / 'in'} (TXT, MD, Fountain, DOCX or PDF); {file!r} is not one of: " + ', '.join(p.name for p in files) + '.')
    elif len(files) > 1:  # design/34 1.3: never pick silently
        raise Refused(f"{ws / 'in'} holds more than one document: " + ', '.join(p.name for p in files) + '. Ask the operator which one is the script and run prepare again with --file <name>.')
    else:
        source = files[0]
    data = source.read_bytes()
    try:
        result = extract(source.name, data)
    except ExtractionError as exc:
        raise Refused(str(exc))
    lines = numbered(result['text']).split('\n')
    (ws / 'work').mkdir(parents=True, exist_ok=True)
    # design/34 1.1: the numbered script goes to a file the assistant reads in parts; the prompt text itself is never written to disk
    (ws / 'work' / 'intake-numbered.md').write_text('\n'.join(textwrap.fill(line, 160, subsequent_indent='    ') if len(line) > 160 else line for line in lines) + '\n', encoding='utf-8')
    earlier = [{'code': r.get('code'), 'title': r.get('title')} for r in (earlier_titles or []) if r.get('title')]
    titles_text = '\n'.join(f"{r['code']}: {r['title']}" for r in earlier) or 'none'
    prompt = (procedure['prompt']
              .replace('{numbered_script}', f"(read work/intake-numbered.md in parts: {len(lines)} lines, {len(result['text'])} characters; it is not pasted here)")
              .replace('{earlier_titles}', titles_text))
    prepared_at = stamp(ws, 'intake')
    (ws / 'work' / 'intake-source.json').write_text(json.dumps({'file': source.name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                                                                   'prepared_at': prepared_at, **result}, indent=1), encoding='utf-8')
    return {'prompt': prompt, 'source_file': source.name, 'numbered_file': 'work/intake-numbered.md', 'lines': len(lines), 'characters': len(result['text']),
            'earlier_titles': earlier, 'warnings': result['warnings'], 'needs_readable_copy': result['needs_readable_copy'], 'prepared_at': prepared_at,
            'output_file': 'out/intake.json', 'output_shape': procedure['output_shape'], 'steps': procedure['steps']}


def intake_record(ws, procedure, prior, title=None, client=''):
    data = read_proposal(ws, 'intake')
    try:
        src = json.loads((ws / 'work' / 'intake-source.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw stage intake prepare` before record.')
    original = ws / 'in' / src['file']
    if src.get('sha256'):  # design/34 1.8: the file record copies must be the one prepare extracted
        if not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != src['sha256']:
            raise Refused(f"The source file {src['file']} changed or is missing since prepare; run `vw stage intake prepare` again.")
    titles = data.get('titles')
    if not isinstance(titles, list) or not titles or not all(isinstance(t, str) and t.strip() for t in titles):  # design/34 1.4
        raise Refused('out/intake.json: `titles` must list at least one non-empty title (recommended first).')
    titles = [t.strip() for t in titles]
    chosen = (title or '').strip()
    if not chosen:  # design/34 1.2: the operator chooses; the tool never picks for them
        raise Refused("Pass the operator's chosen title with --title; record does not pick one for them.")
    if len(chosen) > 160:
        raise Refused('The chosen title must be 1-160 characters (`--title`).')
    cleaned = remove_lines(src['text'], data.get('remove', []))
    if not cleaned.strip():
        raise Refused('Nothing would remain of the source; check the removals.')
    (ws / 'out').mkdir(parents=True, exist_ok=True)
    (ws / 'out' / 'source.txt').write_text(cleaned, encoding='utf-8')
    (ws / 'out' / ('original' + original.suffix.lower())).write_bytes(original.read_bytes())
    summary = {'title': chosen, 'title_source': 'suggested' if chosen in titles else 'typed', 'titles': titles, 'client': client, 'notes': data.get('notes', ''),
               'removed_lines': len(data.get('remove', [])), 'kept_lines': sum(1 for line in cleaned.split('\n') if line.strip()),
               'warnings': src['warnings'], 'source_digest': digest(cleaned), 'source_file': src['file'], 'source_sha256': src.get('sha256'), **stamps(ws, 'intake')}
    return {'files': ['out/source.txt', 'out/original' + original.suffix.lower(), 'out/intake.json'], 'summary': summary, 'retain': True, 'upload': True}


# ---------- brief ----------

def last_brief_text(lb):
    """What this client said at their latest brief (design/37 2.2): shown to the model as recommendations, never as answers."""
    if not lb:
        return 'none'
    prod = lb.get('production') or {}
    lines = [f"from run {lb.get('run')}:"]
    for k in ('process_stages', 'field_speech_languages', 'narration_language', 'show_speaker_video', 'brand_and_safety_rules', 'target_runtime_s'):
        if k in prod:
            v = prod[k]
            shown = 'none' if v in (None, [], '') else (', '.join(str(x) for x in v) if isinstance(v, list) else str(v))
            lines.append(f'  {k}: {shown}')
    questions = {q.get('id'): q.get('question') for q in lb.get('questions') or [] if isinstance(q, dict)}
    for qid, words in (lb.get('answers') or {}).items():
        lines.append(f'  answer to {qid}' + (f' ({questions[qid]})' if questions.get(qid) else '') + f': {words}')
    return '\n'.join(lines)


def client_rules_text(rules):
    return '\n'.join(f"- {r.get('rule')} (from {r.get('source_run')})" for r in rules or [] if r.get('rule')) or 'none'


def brief_prepare(ws, procedure, prior, last_brief=None, client_rules=None):
    intake = prior('intake')
    prompt = procedure['prompt'].replace('{last_brief}', last_brief_text(last_brief)).replace('{client_rules}', client_rules_text(client_rules))
    return {'prompt': prompt, 'inputs': {'title': intake['summary']['title'], 'client': intake['summary']['client'],
            'script': cleaned_script(ws, intake), 'last_brief': last_brief, 'client_rules': client_rules or []}, 'prepared_at': stamp(ws, 'brief'),
            'output_file': 'out/brief.json', 'output_shape': procedure['output_shape'], 'steps': procedure['steps']}


def brief_record(ws, procedure, prior):
    data = read_proposal(ws, 'brief')
    need_text(data, ['purpose', 'audience', 'message', 'tone', 'ending'], 'brief')
    intake = prior('intake')
    questions = data.get('questions') or []
    answers = data.get('answers') or {}
    if not isinstance(questions, list) or not isinstance(answers, dict):
        raise Refused('out/brief.json: `questions` is a list and `answers` a map of question id → the operator\'s exact words.')
    for q in questions:
        if not isinstance(q, dict) or not str(q.get('id', '')).strip():
            raise Refused('out/brief.json: every question needs an id.')
        if q.get('required') and not str(answers.get(q['id'], '')).strip():
            raise Refused(f"out/brief.json: question {q['id']} is required; ask the operator and store their exact answer in `answers`.")
    body = {k: data.get(k, '') for k in ('purpose', 'audience', 'message', 'tone', 'ending', 'constraints')}
    body['answers'] = {k: str(v) for k, v in answers.items()}
    body['production'] = production_inputs(data.get('production') or {})
    summary = {**body, 'questions': len(questions), 'source_intake': intake['summary']['source_digest'], 'content_digest': digest(json.dumps(body, sort_keys=True)), **stamps(ws, 'brief')}
    return {'files': ['out/brief.json'], 'summary': summary, 'retain': True, 'upload': True}


GENERIC_STAGES = ['Stage_1_Setup', 'Stage_2_Preparation', 'Stage_3_Execution', 'Stage_4_Result']   # the old default: not allowed (design/37 2.1)
BLUEPRINT_DEFAULTS = {'target_runtime_s': None, 'process_stages': [],   # the chapters of the film, from the script, or empty
                      'brand_and_safety_rules': [],   # asked of the operator at brief; never filled with blueprint examples (VW-2, 15 Oct 2026)
                      'show_speaker_video': False}
ASKED_EVERY_FILM = ('field_speech_languages', 'narration_language')   # no default: the operator answers on every film (design/37 2.8)


def production_inputs(given):
    """Blueprint v3.2 project inputs (design/12 §A.1). Defaults apply only to keys the operator did not supply; nothing is invented per client."""
    out = {}
    missing = [k for k in ASKED_EVERY_FILM if not given.get(k)]
    if missing:
        raise Refused('out/brief.json: production.field_speech_languages (languages spoken in the footage) and production.narration_language are asked of the operator on every film; '
                      'record their answers (missing: ' + ', '.join(missing) + ').')
    langs, narration = given['field_speech_languages'], given['narration_language']
    if not isinstance(langs, list) or not all(isinstance(x, str) and x.strip() for x in langs):
        raise Refused('out/brief.json: production.field_speech_languages must be a list of language codes.')
    if not isinstance(narration, str) or not narration.strip():
        raise Refused('out/brief.json: production.narration_language must be a language code.')
    out['field_speech_languages'], out['narration_language'] = langs, narration
    for k, default in BLUEPRINT_DEFAULTS.items():
        v = given.get(k, default)
        if k == 'target_runtime_s':
            if v is not None and not (isinstance(v, (int, float)) and 0 < v <= 7200):
                raise Refused('out/brief.json: production.target_runtime_s must be seconds between 1 and 7200, or omitted (derived from the narration).')
        elif k == 'show_speaker_video':
            if not isinstance(v, bool):
                raise Refused('out/brief.json: production.show_speaker_video must be true or false.')
        elif not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
            raise Refused(f'out/brief.json: production.{k} must be a list of strings (an empty list is allowed).')
        out[k] = v
    if out['process_stages'] == GENERIC_STAGES:
        raise Refused('out/brief.json: production.process_stages must be the chapters of the film, from the script, or empty; the generic names are not allowed.')
    out['defaults_applied'] = sorted(k for k in BLUEPRINT_DEFAULTS if k not in given)
    return out


# ---------- script ----------

DECISIONS = ('accepted', 'rejected', 'reworded')
V4_REQUEST_LIMIT = 10000   # Eleven v4 characters per request (server/app/elevenlabs.py); narration segmentation is a later piece of work (design/39 4.3)


def normalise(text):
    """Whitespace is not wording: collapse runs and drop spaces before punctuation (a deletion may leave one)."""
    return re.sub(r'\s+([.,;:!?])', r'\1', ' '.join(str(text or '').split()))


def sentences(text):
    return [t.strip() for t in re.split(r'(?<=[.!?])\s+', normalise(text)) if t.strip()]


def first_difference(a, b):
    """The first sentence that differs between two texts, as (a's, b's); None when they match up to whitespace."""
    sa, sb = sentences(a), sentences(b)
    for x, y in zip(sa, sb):
        if x != y:
            return x, y
    if len(sa) != len(sb):
        return (sa[len(sb)] if len(sa) > len(sb) else '(end of text)'), (sb[len(sa)] if len(sb) > len(sa) else '(end of text)')
    return None


def apply_changes(source, changes, spoken_text):
    """design/38 3.1: rebuild the wording from the cleaned script plus the accepted changes. Returns (rebuilt, expected), both whitespace-
    normalised: expected is the submitted text with insertions removed. Raises Refused for a change that cannot be applied."""
    working, expected = normalise(source), normalise(spoken_text)
    for i, c in enumerate(changes, 1):
        decision = c.get('decision')
        if decision not in DECISIONS:
            raise Refused(f"out/script.json: change {i} needs the operator's decision (accepted, rejected or reworded) before record.")
        if decision == 'rejected':
            continue
        after = c.get('operator_wording') if decision == 'reworded' else c.get('after', '')
        if decision == 'reworded' and not normalise(after):
            raise Refused(f'out/script.json: change {i} is reworded: give the operator_wording.')
        before, after = normalise(c.get('before', '')), normalise(after)
        if before:
            n = working.count(before)
            if n == 0:
                raise Refused(f'out/script.json: change {i}: before not found in the current wording; quote it exactly.')
            if n > 1:
                raise Refused(f'out/script.json: change {i}: before occurs {n} times; quote more words so it occurs once.')
            working = normalise(working.replace(before, after, 1))
        else:
            if not after:
                raise Refused(f'out/script.json: change {i}: an insertion needs after text.')
            n = expected.count(after)
            if n != 1:
                raise Refused(f'out/script.json: change {i}: the inserted wording must occur exactly once in spoken_text (found {n}); anchor it on a short before excerpt instead.')
            expected = normalise(expected.replace(after, ' ', 1))
    return working, expected


def script_prepare(ws, procedure, prior):
    intake, brief = prior('intake'), prior('brief')
    production = brief['summary'].get('production') or {}
    return {'prompt': procedure['prompt'], 'inputs': {'title': intake['summary']['title'], 'client': intake['summary']['client'],
            'script': cleaned_script(ws, intake),
            'brief': {k: brief['summary'].get(k, '') for k in ('purpose', 'audience', 'message', 'tone', 'ending', 'constraints')},
            'answers': brief['summary'].get('answers') or {}, 'narration_language': production.get('narration_language'),   # design/38 3.4
            'brand_and_safety_rules': production.get('brand_and_safety_rules') or [], 'chapters': production.get('process_stages') or []},
            'prepared_at': stamp(ws, 'script'),
            'output_file': 'out/script.json', 'output_shape': procedure['output_shape'], 'steps': procedure['steps']}


def script_record(ws, procedure, prior):
    data = read_proposal(ws, 'script')
    need_text(data, ['spoken_text'], 'script')
    changes = data.get('changes') or []
    for c in changes:
        if not isinstance(c, dict) or set(c) - {'before', 'after', 'reason', 'decision', 'operator_wording'} or not str(c.get('reason', '')).strip():
            raise Refused('out/script.json: each change is {before, after, reason, decision[, operator_wording]} with exact excerpts and a reason.')
    intake, brief = prior('intake'), prior('brief')
    text = data['spoken_text'].replace('\r\n', '\n').strip() + '\n'
    rebuilt, expected = apply_changes(cleaned_script(ws, intake), changes, text)   # design/38 3.1: the text is the source plus the accepted changes
    if rebuilt != expected:
        diff = first_difference(rebuilt, expected) or ('', '')
        raise Refused('out/script.json: spoken_text is not the cleaned script plus the accepted changes. First difference, expected: '
                      f'{diff[0]!r}; submitted: {diff[1]!r}. List every edit as a change with an exact before.')
    accepted = sum(1 for c in changes if c.get('decision') in ('accepted', 'reworded'))
    passages = paragraphs(text)
    if not passages:
        raise Refused('out/script.json: spoken_text has no passages.')
    beats = [{'beat_id': f'BEAT_{i + 1:02d}', 'passage_id': pid, 'text': t} for i, (pid, t) in enumerate(passages.items())]
    data.update({'spoken_text': text, 'passages': passages, 'beats': beats, 'content_digest': digest(text), 'parser': 'reference-paragraphs-v1'})
    (ws / 'out' / 'script.json').write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
    summary = {'content_digest': data['content_digest'], 'passages': len(passages), 'beats': len(beats), 'characters': len(text),
               **({'length_warning': f'The script has {len(text):,} characters; Eleven v4 narrates at most 10,000 per request and segmentation is not built yet. '
                                     'Shorten or split the film before voice.'} if len(text) > V4_REQUEST_LIMIT else {}),
               'source_intake': intake['summary']['source_digest'], 'source_brief': brief['summary']['content_digest'],
               'assessment': data.get('assessment', ''), 'changes': accepted, 'changes_proposed': len(changes), 'changes_accepted': accepted,
               'changes_rejected': sum(1 for c in changes if c.get('decision') == 'rejected'), **stamps(ws, 'script')}   # design/38 3.2
    return {'files': ['out/script.json'], 'summary': summary, 'retain': True, 'upload': True}


STAGES = {'intake': (intake_prepare, intake_record), 'brief': (brief_prepare, brief_record), 'script': (script_prepare, script_record)}
