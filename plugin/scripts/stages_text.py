"""Text stages: intake, brief, script. Each has prepare() (inputs + prompt for the model) and record() (validate the
model's proposal in out/<stage>.json, derive files, record the stage output). Ported rules from v1 intake.py / passages.py."""
import hashlib
import json
import re
from pathlib import Path

from extraction import SUFFIXES, ExtractionError, extract

KINDS = {'scene_heading', 'timing', 'section_label', 'visual_note', 'production_note', 'other'}


class Refused(Exception):
    pass


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


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

def intake_prepare(ws, procedure, prior):
    files = sorted(p for p in (ws / 'in').iterdir() if p.is_file() and p.suffix.lower() in SUFFIXES)
    if not files:
        raise Refused(f"Put the source script in {ws / 'in'} as TXT, MD, Fountain, DOCX or PDF, then run prepare again.")
    source = files[0]
    try:
        result = extract(source.name, source.read_bytes())
    except ExtractionError as exc:
        raise Refused(str(exc))
    (ws / 'work' / 'intake-source.json').write_text(json.dumps({'file': source.name, **result}, indent=1), encoding='utf-8')
    return {'prompt': procedure['prompt'].replace('{numbered_script}', numbered(result['text'])),
            'source_file': source.name, 'warnings': result['warnings'], 'needs_readable_copy': result['needs_readable_copy'],
            'output_file': 'out/intake.json', 'output_shape': procedure['output_shape'], 'steps': procedure['steps']}


def intake_record(ws, procedure, prior, title=None, client=''):
    data = read_proposal(ws, 'intake')
    try:
        src = json.loads((ws / 'work' / 'intake-source.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw stage intake prepare` before record.')
    titles = data.get('titles')
    if not isinstance(titles, list) or not titles or not all(isinstance(t, str) and 8 <= len(t.strip()) <= 70 or t.strip() for t in titles):
        raise Refused('out/intake.json: `titles` must list at least one title (recommended first).')
    chosen = (title or '').strip() or titles[0].strip()
    if not 1 <= len(chosen) <= 160:
        raise Refused('The chosen title must be 1-160 characters (`--title`).')
    cleaned = remove_lines(src['text'], data.get('remove', []))
    if not cleaned.strip():
        raise Refused('Nothing would remain of the source; check the removals.')
    (ws / 'out' / 'source.txt').write_text(cleaned, encoding='utf-8')
    original = ws / 'in' / src['file']
    (ws / 'out' / ('original' + original.suffix.lower())).write_bytes(original.read_bytes())
    summary = {'title': chosen, 'titles': [t.strip() for t in titles], 'client': client, 'notes': data.get('notes', ''),
               'removed_lines': len(data.get('remove', [])), 'warnings': src['warnings'], 'source_digest': digest(cleaned)}
    return {'files': ['out/source.txt', 'out/original' + original.suffix.lower(), 'out/intake.json'], 'summary': summary, 'retain': True, 'upload': True}


# ---------- brief ----------

def brief_prepare(ws, procedure, prior):
    intake = prior('intake')
    return {'prompt': procedure['prompt'], 'inputs': {'title': intake['summary']['title'], 'client': intake['summary']['client'],
            'script': (ws / 'out' / 'source.txt').read_text(encoding='utf-8')},
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
    summary = {**body, 'questions': len(questions), 'source_intake': intake['summary']['source_digest'], 'content_digest': digest(json.dumps(body, sort_keys=True))}
    return {'files': ['out/brief.json'], 'summary': summary, 'retain': True, 'upload': True}


BLUEPRINT_DEFAULTS = {'target_runtime_s': None, 'process_stages': ['Stage_1_Setup', 'Stage_2_Preparation', 'Stage_3_Execution', 'Stage_4_Result'],
                      'brand_and_safety_rules': [],   # asked of the operator at brief; never filled with blueprint examples (VW-2, 15 Oct 2026)
                      'field_speech_languages': ['en', 'ta', 'hi'], 'narration_language': 'en', 'show_speaker_video': False}


def production_inputs(given):
    """Blueprint v3.2 project inputs (design/12 §A.1). Defaults apply only to keys the operator did not supply; nothing is invented per client."""
    out = {}
    for k, default in BLUEPRINT_DEFAULTS.items():
        v = given.get(k, default)
        if k == 'target_runtime_s':
            if v is not None and not (isinstance(v, (int, float)) and 0 < v <= 7200):
                raise Refused('out/brief.json: production.target_runtime_s must be seconds between 1 and 7200, or omitted (derived from the narration).')
        elif k == 'show_speaker_video':
            if not isinstance(v, bool):
                raise Refused('out/brief.json: production.show_speaker_video must be true or false.')
        elif k == 'narration_language':
            if not isinstance(v, str) or not v.strip():
                raise Refused('out/brief.json: production.narration_language must be a language code.')
        elif not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
            raise Refused(f'out/brief.json: production.{k} must be a list of strings (an empty list is allowed).')
        out[k] = v
    out['defaults_applied'] = sorted(k for k in BLUEPRINT_DEFAULTS if k not in given)
    return out


# ---------- script ----------

def script_prepare(ws, procedure, prior):
    intake, brief = prior('intake'), prior('brief')
    return {'prompt': procedure['prompt'], 'inputs': {'title': intake['summary']['title'], 'client': intake['summary']['client'],
            'script': (ws / 'out' / 'source.txt').read_text(encoding='utf-8'),
            'brief': {k: brief['summary'][k] for k in ('purpose', 'audience', 'message', 'tone', 'ending', 'constraints')}},
            'output_file': 'out/script.json', 'output_shape': procedure['output_shape'], 'steps': procedure['steps']}


def script_record(ws, procedure, prior):
    data = read_proposal(ws, 'script')
    need_text(data, ['spoken_text'], 'script')
    for c in data.get('changes') or []:
        if not isinstance(c, dict) or set(c) - {'before', 'after', 'reason'} or not str(c.get('reason', '')).strip():
            raise Refused('out/script.json: each change is {before, after, reason} with exact excerpts and a reason.')
    intake, brief = prior('intake'), prior('brief')
    text = data['spoken_text'].replace('\r\n', '\n').strip() + '\n'
    passages = paragraphs(text)
    if not passages:
        raise Refused('out/script.json: spoken_text has no passages.')
    beats = [{'beat_id': f'BEAT_{i + 1:02d}', 'passage_id': pid, 'text': t} for i, (pid, t) in enumerate(passages.items())]
    data.update({'spoken_text': text, 'passages': passages, 'beats': beats, 'content_digest': digest(text), 'parser': 'reference-paragraphs-v1'})
    (ws / 'out' / 'script.json').write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
    summary = {'content_digest': data['content_digest'], 'passages': len(passages), 'beats': len(beats), 'characters': len(text),
               'source_intake': intake['summary']['source_digest'], 'source_brief': brief['summary']['content_digest'],
               'assessment': data.get('assessment', ''), 'changes': len(data.get('changes') or [])}
    return {'files': ['out/script.json'], 'summary': summary, 'retain': True, 'upload': True}


STAGES = {'intake': (intake_prepare, intake_record), 'brief': (brief_prepare, brief_record), 'script': (script_prepare, script_record)}
