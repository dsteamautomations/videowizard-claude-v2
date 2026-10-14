import math
from . import intake

def source_time(binding, local_s):
    values = [binding['original_start_s'], binding['duration_s'], local_s]
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values):
        raise ValueError('Clocks must be finite numbers.')
    start, duration, local = values
    if binding.get('speed', 1) != 1 or start < 0 or duration <= 0 or not 0 <= local < duration:
        raise ValueError('Invalid clip clock or unsupported retiming; no clamping.')
    return start + local

def map_verified_cut(root, binding, local_s):
    """Map a previously verified cut receipt; changed media invalidates its mapping."""
    for prefix in ('source', 'clip'):
        path = root / binding[prefix + '_path']
        if not path.is_file() or intake.hash_file(path) != binding[prefix + '_sha256']:
            raise ValueError('Cut mapping media changed or is missing.')
    duration = binding['source_duration_s']
    if (type(duration) not in (int, float) or not math.isfinite(duration)
            or binding['original_start_s'] + binding['duration_s'] > duration):
        raise ValueError('Cut extends beyond the original source.')
    return source_time(binding, local_s)

def bind_frame_results(manifest, result):
    rows = result['frames']; byid = {f['frame_id']: f for f in manifest['frames']}
    ids = [r['frame_id'] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(byid): raise ValueError('Missing, duplicate or unknown returned frame ID.')
    return [{**r, 'original_s': byid[r['frame_id']]['original_s'],
             'source_id': manifest['source_id'], 'timestamp_method': 'decoded_frame_manifest'} for r in rows]
