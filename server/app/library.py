"""design/68: SK's image prompt library, read from files under server/library/<version>/ and never written by the server.
The step map mirrors VW-MAP.md of the bundle; the job form follows FIELD-SOURCES.md with what the server has; the answer lint checks
what a machine can check of the library's answer form."""
import hashlib
import json
import math
import re
from pathlib import Path

from .errors import Problem
from .video_generators import DEFAULT as DEFAULT_GENERATOR

ROOT = Path(__file__).resolve().parents[1] / 'library'
ALWAYS = ('library/RULEBOOK.md', 'library/forms/answer-form.videowizard.md', 'library/agency/deterministic-checks.md')   # design/71 F1: the VideoWizard cut of the form
SIZES = {'16:9': '1536x864', '9:16': '1088x1936'}   # design/71 P3: GPT Image sizes per frame (the sheet's working values; 1080x1920 fails the multiple-of-16 rule)
MODEL_WORDS = ('gpt-image', 'sunburst', 'flare', 'omni', 'kling', 'seedance')   # design/71 F2 (the library's lint rule 8)
COMPLIANCE = 'library/agency/compliance-checklist.md'
GPT = 'library/models/gpt-image/FACT-SHEET.md'
MODEL_SHEETS = {'gemini-omni-1.1-flash': ('library/video/models/gemini-omni-1-1/FACT-SHEET.md',),
                'kling-video/v3.0/std/image-to-video': ('library/video/models/kling/FACT-SHEET.md', 'library/video/models/higgsfield/NOTES.md'),
                'bytedance/seedance-2.5/image-to-video': ('library/video/models/seedance/FACT-SHEET.md', 'library/video/models/higgsfield/NOTES.md')}
ALL_SHEETS = tuple(dict.fromkeys(p for sheets in MODEL_SHEETS.values() for p in sheets))
VIDEO_FRAME = 'library/playbooks/video-frame.md'
STEPS = {
    'reference': {'task': 'continuity-kit', 'playbook': 'video-frame', 'files': (VIDEO_FRAME, GPT, 'library/video/consistent-character-frames.md'),
                  'when': 'a generated reference of a person, object or place (`vw visuals image --kind isolated|sheet`); consistent-character-frames for a person'},
    'frame': {'task': None, 'playbook': None, 'files': ('library/video/gap-fill.md',), 'when': 'choosing a frame from a clip (`vw visuals frame`): gap-fill section 3; no prompt is written'},
    'still-scene': {'task': 'keyframe', 'playbook': 'video-frame', 'files': (VIDEO_FRAME, GPT, 'library/video/craft/animatic-keyframes.md', 'library/video/gap-fill.md', 'library/00-method/de-slop.md'),
                    'when': 'an AI still for an image shot (`image --kind keyframe`, then `still`); de-slop for a photographic look'},
    'still-diagram': {'task': 'process-explainer', 'playbook': 'web-app', 'files': ('library/playbooks/web-app.md', GPT, 'library/00-method/craft.md', 'library/prompts/05-information.md'),
                      'when': 'a diagram, chart or labelled picture for a diagram shot (`image`, then `still`); craft section 5 for the diagram grammar'},
    'state': {'task': 'graphic-states', 'playbook': 'diagram-in-states', 'files': ('library/video/diagram-in-states.md', GPT, 'library/00-method/craft.md'),
              'when': 'a state of a graphic sequence (`image --kind state --parents R`, then `sequence`)'},
    'start': {'task': 'keyframe', 'playbook': 'video-frame', 'files': (VIDEO_FRAME, GPT, 'library/video/craft/animatic-keyframes.md', 'library/video/gap-fill.md', 'library/video/consistent-character-frames.md'),
              'when': "the start image of a video shot (`image --kind keyframe`); the generator's sheet for its accepted size"},
    'end': {'task': 'first-last-frame', 'playbook': 'video-frame', 'files': (VIDEO_FRAME, GPT, 'library/video/gap-fill.md'),
            'when': 'the end image of a video shot (`image --kind keyframe --parents <start>`): gap-fill section 3'},
    'take': {'task': 'clip-from-frame', 'playbook': 'video-clip',
             'files': ('library/playbooks/video-clip.md', 'library/video/craft/camera-lighting-vocabulary.md', 'library/video/gap-fill.md', 'library/video/still-to-motion-pipeline.md') + ALL_SHEETS,
             'when': "a video take (`prepare-take`, `take`): the sheet of the shot's generator; still-to-motion for a faceless explainer"},
}


def versions():
    if not ROOT.is_dir():
        return []
    return sorted(p.name for p in ROOT.iterdir() if (p / 'MANIFEST.json').is_file())


def latest():
    found = versions()
    if not found:
        raise Problem(503, 'LIBRARY_MISSING', 'No image prompt library is installed on the server (server/library/<version>/).')
    return found[-1]


def manifest(version):
    path = ROOT / str(version) / 'MANIFEST.json'
    if not version or '/' in str(version) or not path.is_file():
        raise Problem(422, 'LIBRARY_VERSION', f'Unknown library version {version!r}; installed: {", ".join(versions()) or "none"}.')
    return json.loads(path.read_text(encoding='utf-8'))


def verify(version):
    """Every manifest file present with its sha256; the problems, or an empty list."""
    problems = []
    for entry in manifest(version)['files']:
        path = ROOT / version / entry['path']
        if not path.is_file():
            problems.append(f"{entry['path']}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            problems.append(f"{entry['path']}: sha256 differs")
    return problems


def text(version, path):
    manifest(version)
    file = ROOT / version / path
    if not file.is_file():
        raise Problem(500, 'LIBRARY_FILE', f'Library file {path} is missing from {version}.')
    return file.read_text(encoding='utf-8')


def steps(version):
    """What the plugin writes per step at prepare (design/68 L4): the always-open files, each step's files with their text, the compliance checklist, the two maps."""
    def files(paths):
        return [{'path': p, 'text': text(version, p)} for p in paths]
    return {'version': version, 'always': files(ALWAYS),
            'steps': {name: {'task': s['task'], 'playbook': s['playbook'], 'when': s['when'], 'files': files(s['files'])} for name, s in STEPS.items()},
            'compliance': {'path': COMPLIANCE, 'text': text(version, COMPLIANCE)},
            'map': text(version, 'VW-MAP.md'), 'field_sources': text(version, 'FIELD-SOURCES.md')}


def steps_of(shot):
    """The library steps a shot goes through, by its route."""
    vt = shot['visual_type']
    return ['start', 'end', 'take'] if vt == 'video' else ['state'] if vt == 'animation' else ['still-diagram'] if vt == 'diagram' else ['still-scene']


def step_files(step, generator=None):
    """The step's files, with the sheet of the shot's generator where a generator matters."""
    paths = [p for p in STEPS[step]['files'] if p not in ALL_SHEETS]
    if step in ('start', 'take'):
        paths += list(MODEL_SHEETS.get((generator or DEFAULT_GENERATOR).get('model')) or ())
    return paths


def _texts(rules):
    return [(r.get('statement') or r.get('text') or r.get('rule') or json.dumps(r, ensure_ascii=False)) if isinstance(r, dict) else str(r) for r in rules or []]


def job_form(step, *, run, plan, gap, scene, shot, refs, generator, brief, card, rules, fps=25, round_=1):
    """The library's job form for one picture or take, filled from the run as FIELD-SOURCES.md says, with what the server has (design/68 §4)."""
    spec = STEPS.get(step)
    if not spec or spec['task'] is None:
        raise ValueError(f'unknown library step {step!r}')
    from .visuals_stage import IMAGE_MODELS   # late: visuals_stage imports this module
    foundation = plan.get('foundation') or {}
    frame = (((brief or {}).get('production') or {}).get('format') or {}).get('frame') or '16:9'
    elements = {e['id']: e for e in plan.get('elements') or []}
    images = [{'id': r['reference_id'], 'tag': 'scene' if r.get('kind') == 'frame' else 'approved', 'element_id': r['element_id'],
               'keep': (elements.get(r['element_id']) or {}).get('requirements') or ''} for r in refs or []]
    mode = 'edit-with-identity' if step == 'end' else 'edit' if step == 'state' else 'multi-reference' if len(images) > 1 else 'edit' if images else 'generate'
    if step == 'state':
        copy = [{'role': 'label', 'text': s['what_appears']} for s in shot.get('states') or []]
    else:
        progression = (shot.get('information_progression') or '').strip()
        copy = [{'role': 'body', 'text': progression}] if progression else 'none'
    brand = [(label, (card or {}).get(col)) for label, col in (('Colours', 'color_palette'), ('Type', 'typography_fonts'), ('Guidelines', 'client_brand_guidelines'), ('Trademarks', 'trademark_patterns'))]
    preamble = '\n'.join(f'{label}: {value}' for label, value in brand if value)
    model = ((generator or DEFAULT_GENERATOR).get('model')) if step == 'take' else IMAGE_MODELS['generate' if mode == 'generate' else 'edit']
    form = {'job_id': f"{run.get('code')}-{shot['id']}-{round_}", 'client_code': run.get('client_id') or '', 'requested_by': {'kind': 'agent', 'id': 'vw-operator-assistant'}, 'round': round_,
            'playbook': spec['playbook'], 'task': spec['task'], 'mode': mode, 'industry': (card or {}).get('industry') or 'other',
            'placement': frame, 'video_aspect': frame,
            'request': {'words': shot.get('narration') or '', 'purpose': shot.get('purpose') or ''},
            'purpose': {'intent': gap.get('intent') or '', 'treatment_fit': gap.get('treatment_fit') or ''},
            'audience': (brief or {}).get('audience') or 'general',
            'style_direction': {'foundation': foundation.get('appearance') or '', 'shot': shot.get('appearance') or ''},
            'copy': copy, 'text_mode': 'rendered', 'mandatory_text': 'none', 'logo': 'none', 'images': images,
            'brand_kit_id': run.get('client_id') or '', 'brand_preamble': preamble or 'none',
            'hard_constraints': _texts(foundation.get('exclusions')) + [str(r) for r in rules or []],
            'avoid': _texts(foundation.get('editing_constraints')),
            'model': model, 'finish': 'final', 'variants': 1, 'checked_by': 'person', 'trial': False}
    if step == 'take':
        form['video_seconds'] = math.ceil((shot['end_frame'] - shot['start_frame']) / float(fps))
    return form


def check_answer(answer, prompt):
    """The answer-form lint a machine can run (design/68 L5): ready, the prompt sent, a must line, the exact text present."""
    if not isinstance(answer, dict):
        raise ValueError("The answer form is an object (the library's answer-form.md).")
    status = answer.get('status')
    if status != 'ready':
        raise ValueError(f"The answer's status is {status or 'missing'}: nothing is sent; settle a needs_input in chat, or drop the picture on a refused.")
    if (answer.get('prompt') or '') != prompt:
        raise ValueError("The answer's prompt differs from the prompt sent: send the answer's prompt, or fix the answer.")
    checklist = answer.get('checklist')
    if not isinstance(checklist, list) or not any(isinstance(c, dict) and c.get('weight') == 'must' for c in checklist):
        raise ValueError('The checklist needs at least one must line.')
    for s in answer.get('exact_text') or []:
        if str(s) not in prompt:
            raise ValueError(f'The exact text {str(s)!r} is not in the prompt.')
    return answer


def check_prompt(prompt):
    """design/71 F2: the library's lint rules 3 and 8 as the server's own refusals, on every prompt. A logo is refused unless the sentence
    says no to it (the standing line "do not add unrelated logos" stays); a model name, a pixel size or a resolution is refused with the word."""
    text = str(prompt or '')
    for sentence in re.split(r'(?<=[.;:!?\n])\s+', text):
        if re.search(r'\blogos?\b', sentence, re.I) and not re.search(r"\b(no|not|never|without|don't|unrelated)\b", sentence, re.I):
            raise ValueError(f'The prompt asks for a logo ({sentence.strip()[:80]!r}): a logo is never generated; the editor places it.')
    for word in MODEL_WORDS:
        if re.search(r'(?<!lens )\b' + re.escape(word) + r'\b', text, re.I):
            raise ValueError(f'The prompt names a model ({word!r}): the server chooses the model; describe the picture only.')
    m = re.search(r'\b\d{3,4}\s?[x×]\s?\d{3,4}\b', text)
    if m:
        raise ValueError(f'The prompt names a pixel size ({m.group(0)!r}): the server sets the size; describe the picture only.')
    m = re.search(r'\b(720p|1080p|2160p)\b', text, re.I)
    if m:
        raise ValueError(f'The prompt names a resolution ({m.group(0)!r}): the server sets it; describe the picture only.')
    for sentence in re.split(r'(?<=[.;:!?\n])\s+', text):   # design/110 F2: a place is a landmark and a measured distance, never 'the centre' alone
        m = re.search(r'\b(centre|center|middle|nearby|closer|further)\b', sentence, re.I)
        if m and not re.search(r'\d|\b(one|two|three|four|five|six|half|bricks?|paces?|body-lengths?|arm-lengths?|hands?|doorways?|courses?|metres?|meters?)\b', sentence, re.I):
            raise ValueError(f'The prompt places something at {m.group(1)!r} with no landmark and measured distance ({sentence.strip()[:80]!r}): say the landmark and how far from it, '
                             'in a unit the picture shows (bricks, paces, a hand, a doorway) (design/110 F2).')
    m = re.search(r'\b(as before|facing each other|sit as before|the parents as before)\b', text, re.I)   # design/111 F7: a look is a target, a head turn and a mouth
    if m:
        raise ValueError(f'{m.group(0)!r} says nothing a picture can show: write where each person\'s eyes are (a landmark or a named person), the head turn and the mouth (design/111 F7).')
    m = re.search(r'Change only:(.*?)(?:\n\s*(?:Keep|Constraints|Render only)\b|$)', text, re.S | re.I)   # design/86 K5: an edit makes one change, two at most
    if m:
        changes = [s for s in re.split(r'(?<=[.;])\s+', m.group(1).strip()) if s.strip()]
        if len(changes) > 2:
            raise ValueError(f'The edit names {len(changes)} changes under "Change only": one change per edit, two at most; make the rest in a second edit of the result.')
    return None


MATERIAL_UNITS = r'(bricks?|tiles?|blocks?|planks?|pavers?|stones?|units?|slabs?|boards?)'


def check_material_prompt(prompt):
    """design/111 F10: a prompt that shows a repeating material says its sizes in numbers (the server pastes the spec); relative words are refused."""
    text = str(prompt or '')
    m = (re.search(r'\b(short|long|small|large|big|thin|thick)\s+' + MATERIAL_UNITS + r'\b', text, re.I) or re.search(r'\babout\s+\d+(?:\.\d+)?\s*:\s*\d+', text, re.I)
         or re.search(r'\b(roughly|approximately|typical|standard)\b', text, re.I))
    if m:
        raise ValueError(f'The prompt describes the material in relative words ({m.group(0)!r}): the material spec gives the numbers and the server pastes them; take the words out (design/111 F10).')


def image_names_missing(prompt, n):
    """design/96 C1 (the course's C03-2): the numbers of the n pictures an edit sends that its prompt does not name as Image k; a range
    ("images 2–4") and "images 2 onward" count."""
    text, named = str(prompt or ''), set()
    for a, b in re.findall(r'\bimages?\s+(\d+)\s*(?:-|–|to)\s*(\d+)', text, re.I):
        named.update(range(int(a), int(b) + 1))
    for a in re.findall(r'\bimages?\s+(\d+)\s+onwards?\b', text, re.I):
        named.update(range(int(a), n + 1))
    named.update(int(a) for a in re.findall(r'\bimages?\s+(\d+)\b', text, re.I))
    return [k for k in range(1, n + 1) if k not in named]


def default_size(frame):
    """design/71 P3: the image size for the brief's frame."""
    return SIZES.get(frame or '16:9') or SIZES['16:9']


def edit_size(width, height, frame):
    """design/71 P3: an edit keeps its first parent's size when both sides are multiples of 16, else the frame's default."""
    if width and height and width % 16 == 0 and height % 16 == 0:
        return f'{int(width)}x{int(height)}'
    return default_size(frame)
