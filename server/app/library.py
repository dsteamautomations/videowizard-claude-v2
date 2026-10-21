"""design/68: SK's image prompt library, read from files under server/library/<version>/ and never written by the server.
The step map mirrors VW-MAP.md of the bundle; the job form follows FIELD-SOURCES.md with what the server has; the answer lint checks
what a machine can check of the library's answer form."""
import hashlib
import json
import math
from pathlib import Path

from .errors import Problem
from .video_generators import DEFAULT as DEFAULT_GENERATOR

ROOT = Path(__file__).resolve().parents[1] / 'library'
ALWAYS = ('library/RULEBOOK.md', 'library/forms/answer-form.md', 'library/agency/deterministic-checks.md')
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
