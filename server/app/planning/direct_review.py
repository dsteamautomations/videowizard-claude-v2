from copy import deepcopy
import math
from . import intake as executor
from .gemini_edit_inputs import passage_windows
Error=ValueError

def subset_context(context, passage_ids):
    """Cut only a contiguous, frame-aligned baseline passage window, retaining source audio."""
    all_ids = context['passage_ids']
    if not passage_ids or any(p not in all_ids for p in passage_ids):
        raise Error('Alternative passage IDs must resolve in the baseline context.')
    first = all_ids.index(passage_ids[0])
    if all_ids[first:first + len(passage_ids)] != passage_ids:
        raise Error('Alternative passages must be unique, contiguous and in narration order.')
    windows = passage_windows(context)
    start, end = windows[first]['timeline_start_s'], windows[first + len(passage_ids)-1]['timeline_end_s']
    fps = context['fps']
    if any(not math.isclose(t * fps, round(t * fps), abs_tol=1e-7) for t in (start, end)):
        raise Error('Alternative passage boundaries must align exactly to output frames; no rounding is allowed.')
    words = deepcopy([w for w in context['mapped_words'] if w['passage_id'] in passage_ids])
    for word in context['mapped_words']:
        if any(word['timeline_start_s'] < t - 1e-8 < word['timeline_end_s'] - 1e-8 for t in (start, end)):
            raise Error('Alternative boundary would cut a narration word.')
    segments = []
    for source in context['audio_segments']:
        lo = source['timeline_start_s']
        hi = lo + source['source_end_s'] - source['source_start_s']
        a, b = max(start, lo), min(end, hi)
        if b > a + 1e-9:
            segments.append({**deepcopy(source), 'source_start_s': source['source_start_s'] + a-lo,
                'source_end_s': source['source_start_s'] + b-lo,
                'timeline_start_s': a-start, 'timeline_end_s': b-start})
    if not segments:
        raise Error('Alternative has no source narration.')
    for word in words:
        word['timeline_start_s'] -= start
        word['timeline_end_s'] -= start
    result = deepcopy(context)
    result.update(passage_ids=deepcopy(passage_ids), mapped_words=words, audio_segments=segments,
        expected_audio_segments_sha256=executor._digest(segments),
        narration_source_start_s=segments[0]['source_start_s'], narration_source_end_s=segments[-1]['source_end_s'],
        duration_frames=round((end-start)*fps), section_start_s=context.get('section_start_s', 0)+start,
        section_end_s=context.get('section_start_s', 0)+end,
        review_baseline_window={'timeline_start_s': start, 'timeline_end_s': end})
    return result

def _plan(sequence, bundle):
    result = {key: deepcopy(sequence[key]) for key in ('duration_frames', 'shots', 'narration_pauses',
        'sequence_reason', 'unresolved')} | {'contract': 'direct-gemini-edit-v2',
        'experiment_id': bundle['experiment_id'], 'fps': bundle['fps']}
    if 'source_audio_segments' in sequence:
        result['source_audio_segments'] = deepcopy(sequence['source_audio_segments'])
    return result
