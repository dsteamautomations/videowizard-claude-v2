"""design/88: the footage character is measured, not asked.

Per clip: the camera from the maker and model tags, else the file name, else the codec, bit depth and bit rate; the support from the analysis's
movement type per sub-clip; the look from the colour transfer and the analysis's contrast profile. Every value carries its evidence. The film
summary is the value most clips share, or mixed with the counts. The operator's correction, with their words, wins over the measurement."""
import re
from collections import Counter

CAMERAS = ('cinema', 'mirrorless', 'phone', 'drone', 'mixed')   # what the operator may correct to
SUPPORTS = ('handheld', 'tripod', 'gimbal', 'mixed')
LOOKS = ('natural', 'graded', 'log')

PRO_CODECS = ('prores', 'dnxhd', 'dnxhr', 'cineform', 'braw', 'v210')
PHONE_MAKERS = ('apple', 'samsung', 'google', 'xiaomi', 'redmi', 'poco', 'oneplus', 'oppo', 'vivo', 'realme', 'motorola', 'huawei', 'honor', 'nokia', 'nothing')
CINEMA_MAKERS = ('blackmagic', 'arri', 'red digital', 'kinefinity', 'z cam')
CAMERA_MAKERS = ('sony', 'canon', 'nikon', 'panasonic', 'fujifilm', 'olympus', 'om digital', 'leica', 'sigma', 'ricoh', 'pentax')
NAME_HINTS = ((r'^DJI_', 'DJI', 'drone'), (r'^C\d{4}', 'Sony', 'mirrorless'), (r'^MVI_', 'Canon', 'mirrorless'), (r'^DSC_?\d', 'Nikon or Sony', 'mirrorless'),
              (r'^P\d{7}', 'Panasonic', 'mirrorless'), (r'^(PXL|IMG|VID)_?\d', 'a phone', 'phone'))
SUPPORT_OF_MOVE = {'Static': 'tripod', 'Pan': 'tripod', 'Tilt': 'tripod', 'Handheld': 'handheld', 'Gimbal': 'gimbal', 'Dolly': 'gimbal'}
CAMERA_WORDS = {'cinema': 'cinema camera', 'mirrorless': 'mirrorless camera', 'phone': 'phone', 'drone': 'drone', 'professional': 'professional camera (cinema or mirrorless)',
                'unknown': 'camera not known'}


def _pro(clip):
    ten_bit = bool(re.search(r'p1[0-6](le|be)?$', clip.get('pix_fmt') or ''))   # yuv422p10le, not the 20 of yuv420p
    return (clip.get('codec') or '').lower().startswith(PRO_CODECS) or ten_bit or (clip.get('bit_rate') or 0) >= 50_000_000


def camera_of(clip):
    """(value, evidence): the maker and model tags, else the file name, else the codec rule; 'unknown' when a run recorded before design/88 has none of them."""
    make, model = str(clip.get('make') or '').strip(), str(clip.get('model') or '').strip()
    tag = ' '.join(x for x in (make, model) if x)
    low = make.lower()
    if low:
        if any(m in low for m in CINEMA_MAKERS):
            return 'cinema', tag
        if any(m in low for m in PHONE_MAKERS):
            return 'phone', tag
        if 'dji' in low:
            return 'drone', tag
        if any(m in low for m in CAMERA_MAKERS):
            return ('cinema' if _pro(clip) and (clip.get('bit_rate') or 0) >= 100_000_000 else 'mirrorless'), tag
    for pattern, who, value in NAME_HINTS:
        if re.match(pattern, clip.get('name') or '', re.I):
            return value, f"file name {clip.get('name')} ({who})"
    if clip.get('codec') or clip.get('bit_rate'):
        bits = f"{clip.get('codec') or '?'}, {clip.get('pix_fmt') or '?'}, {(clip.get('bit_rate') or 0) / 1e6:.0f} Mbit/s"
        return ('professional', bits) if _pro(clip) else ('phone', bits)
    return 'unknown', 'no maker tag, name pattern or codec on record'


def support_of(sub_clips, camera):
    """(value, evidence) from the analysis's movement type per sub-clip; stabilisation needed counts toward handheld."""
    votes = Counter()
    for s in sub_clips or []:
        move = ((s.get('camera_and_optics') or {}).get('movement_type'))
        if move in SUPPORT_OF_MOVE:
            votes[SUPPORT_OF_MOVE[move]] += 1
        if (s.get('technical_qc_and_remediation') or {}).get('stabilization_needed'):
            votes['handheld'] += 1
    if not votes:
        return ('gimbal', 'a drone, no analysis yet') if camera == 'drone' else ('unknown', 'no analysis of its movement yet')
    value, n = votes.most_common(1)[0]
    return value, ', '.join(f'{k} {v}' for k, v in votes.most_common())


def look_of(clip, log):
    transfer = str(clip.get('color_transfer') or '').lower()
    contrast = (log or {}).get('contrast_profile')
    if 'log' in transfer or transfer == 'arib-std-b67':
        return 'log', f'colour transfer {transfer}'
    if contrast == 'Flat_Low_Contrast':
        return 'log', 'flat, low contrast in the analysis'
    return 'natural', f"contrast {contrast or 'not analysed'}, transfer {transfer or 'untagged'}"


def per_clip(clip, log):
    camera, ce = camera_of(clip)
    support, se = support_of((log or {}).get('sub_clips'), camera)
    look, le = look_of(clip, log)
    return {'name': clip.get('name'), 'camera': camera, 'support': support, 'look': look, 'evidence': {'camera': ce, 'support': se, 'look': le}}


def _field(values):
    """The value most clips share (two thirds or more), else mixed; unknowns do not vote. Always with the counts."""
    counts = Counter(v for v in values if v != 'unknown')
    if not counts:
        return 'unknown', {}
    top, n = counts.most_common(1)[0]
    return (top if n * 3 >= sum(counts.values()) * 2 else 'mixed'), dict(counts.most_common())


def measure(clips, logs):
    """clips: the media record's clips; logs: {clip_id: clip log}. Returns {'per_clip', 'summary'}."""
    rows = {c['id']: per_clip(c, (logs or {}).get(c['id'])) for c in clips or [] if c.get('id')}
    summary = {}
    for f in ('camera', 'support', 'look'):
        summary[f], summary[f + '_counts'] = _field([r[f] for r in rows.values()])
    return {'per_clip': rows, 'summary': summary}


def apply_correction(measured, correction):
    """The operator's words win, field by field, for the summary and every clip; the measurement is kept beside it."""
    out = {'per_clip': {k: dict(v) for k, v in (measured or {}).get('per_clip', {}).items()}, 'summary': dict((measured or {}).get('summary') or {})}
    if correction:
        for f in ('camera', 'support', 'look'):
            if correction.get(f):
                out['summary'][f] = correction[f]
                for row in out['per_clip'].values():
                    row[f] = correction[f]
        out['summary']['corrected'] = {k: correction.get(k) for k in ('quote', 'by', 'at', 'from') if correction.get(k)}
    return out


def line(summary):
    """One line for the operator: told, not asked."""
    s = summary or {}

    def word(f, v):
        if v == 'mixed':
            return 'mixed ' + {'camera': 'cameras', 'support': 'support', 'look': 'looks'}[f] + ' (' + ', '.join(f'{n} {k}' for k, n in (s.get(f + '_counts') or {}).items()) + ')'
        return {'camera': CAMERA_WORDS, 'support': {'unknown': 'support not known'}, 'look': {'unknown': 'look not known'}}[f].get(v, v + (' look' if f == 'look' else ''))
    text = 'Your footage: ' + ', '.join(word(f, s.get(f) or 'unknown') for f in ('camera', 'support', 'look'))
    return text + (' (your correction)' if s.get('corrected') else ' (measured from the clips)')
