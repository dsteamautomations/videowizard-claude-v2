"""Stage 1.5: deterministic crop solver and eligibility (verbatim port of the blueprint solver via model-test/solve_stage15.py)
plus the design/12 additions. Policy, aspect and resolution are inputs, so a change re-runs this only, never the paid call."""
import math
from fractions import Fraction

ELIGIBLE = ('ELIGIBLE_AS_IS', 'ELIGIBLE_WITH_CROP', 'ELIGIBLE_A_ROLL_SPEAKER', 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', 'REJECT_ALL')
SHOT_SIZES = ['EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU']
STABILIZE_ZOOM = 1.08


TRIM = 0.10   # design/125 P6: each edge of the must-keep box may lose up to 10 % of its width (left, right) or height (top, bottom)


def _clipped(x_min, y_min, w, h, preserve_box):
    px, py, pw, ph = preserve_box
    tx, ty = TRIM * pw + 1e-6, TRIM * ph + 1e-6
    return x_min - px > tx or (px + pw) - (x_min + w) > tx or y_min - py > ty or (py + ph) - (y_min + h) > ty


def compute_davinci_crop(exclude_box, preserve_box, source_w, source_h, timeline_w, timeline_h, max_safe_zoom, rotation_deg=0.0, stabilize=False, head_box=None):
    """The blueprint's side crop (ported verbatim, with P6's trim); when it fails and the head box is given, design/125 P5: a crop
    from the top (window starts below the head) or the bottom (window ends above it), same aspect and zoom limit. The feasible
    one with the least zoom wins; when none is, the side crop's answer stands."""
    arf = (timeline_w / timeline_h) / (source_w / source_h)
    side = _crop(_side_window(exclude_box, preserve_box, arf), preserve_box, timeline_w, timeline_h, max_safe_zoom, rotation_deg, stabilize, arf)
    if side['feasible'] or not head_box:
        return side
    hx, hy, hw, hh = head_box
    top = round(hy + hh + 0.02, 2)
    ok = [s for s in (_crop(_vertical_window(top, round(1.0 - top, 2), preserve_box, arf), preserve_box, timeline_w, timeline_h, max_safe_zoom, rotation_deg, stabilize, arf),
                      _crop(_vertical_window(0.0, round(hy - 0.02, 2), preserve_box, arf), preserve_box, timeline_w, timeline_h, max_safe_zoom, rotation_deg, stabilize, arf))
          if s['feasible']]
    return min(ok, key=lambda s: s['total_cumulative_zoom']) if ok else side


def _side_window(exclude_box, preserve_box, arf):
    ex, ey, ew, eh = exclude_box
    px, py, pw, ph = preserve_box
    if ex + ew <= px:
        x_min = round(ex + ew + 0.02, 2); max_w = round(1.0 - x_min, 2)
    elif px + pw <= ex:
        x_min = 0.0; max_w = round(ex - 0.02, 2)
    else:
        return 'Speaker horizontally overlaps must_preserve_action_box'
    w = max_w; h = round(w / arf, 2)
    p_cy = py + ph / 2.0
    return x_min, round(max(0.0, min(1.0 - h, p_cy - h / 2.0)), 2), w, h


def _vertical_window(y_min, h, preserve_box, arf):
    if h <= 0 or y_min >= 1.0:
        return 'Speaker head leaves no room above or below must_preserve_action_box'
    w = round(h * arf, 2)
    if w > 1.0:
        w = 1.0; h = round(w / arf, 2)
    px, py, pw, ph = preserve_box
    return round(max(0.0, min(1.0 - w, px + pw / 2.0 - w / 2.0)), 2), y_min, w, h


def _crop(window, preserve_box, timeline_w, timeline_h, max_safe_zoom, rotation_deg, stabilize, arf):
    if isinstance(window, str):
        return {'feasible': False, 'reason': window}
    x_min, y_min, w, h = window
    if _clipped(x_min, y_min, w, h, preserve_box):
        return {'feasible': False, 'reason': 'Action box clipped by aspect-locked crop window'}
    fit = max(arf, 1.0 / arf)
    crop_zoom = round((1.0 / w) * fit, 2)
    cx = x_min + w / 2.0; cy = y_min + h / 2.0
    theta = math.radians(abs(rotation_deg))
    rot_zoom = (math.cos(theta) + (timeline_w / timeline_h) * math.sin(theta)) if rotation_deg else 1.0
    total = round(crop_zoom * rot_zoom * (STABILIZE_ZOOM if stabilize else 1.0), 2)
    return {'feasible': total <= max_safe_zoom, 'crop_rect': [x_min, y_min, w, h], 'zoom_x': crop_zoom, 'zoom_y': crop_zoom,
            'position_x': round((0.5 - cx) * timeline_w * crop_zoom, 1), 'position_y': round((cy - 0.5) * timeline_h * crop_zoom, 1),
            'total_cumulative_zoom': total, 'within_safe_zoom_limit': total <= max_safe_zoom,
            'reason': None if total <= max_safe_zoom else f'Cumulative zoom {total} exceeds max_safe_zoom_limit {max_safe_zoom}'}


def valid_box(b):
    return isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in b) and 0 <= b[0] <= 1 and 0 <= b[1] <= 1 and 0 < b[2] <= 1 and 0 < b[3] <= 1 and b[0] + b[2] <= 1.0001 and b[1] + b[3] <= 1.0001


def head_inside_body(head, body):
    """design/11 §6.2 sanity rule: the head box lies inside the body box and the body is under 0.6 of the frame width."""
    return head[0] >= body[0] - 0.01 and head[1] >= body[1] - 0.01 and head[0] + head[2] <= body[0] + body[2] + 0.01 and head[1] + head[3] <= body[1] + body[3] + 0.01 and body[2] < 0.6


def max_safe_zoom(source_w, source_h, timeline_w, timeline_h, model_value):
    """Server override from resolution (design/12 §A.2): 2.0 for 4K→1080p, 1.35 for 1080p; the model's value is kept when it is stricter."""
    ratio = min(source_w / timeline_w, source_h / timeline_h) if source_w and source_h else 1.0
    base = 2.0 if ratio >= 1.9 else 1.35
    return min(base, model_value) if isinstance(model_value, (int, float)) and model_value > 0 else base


def effective_post_crop_shot_size(native, zoom):
    """One step tighter per ~1.3x of crop zoom (design/12 §A.5)."""
    if native not in SHOT_SIZES or not zoom or zoom <= 1.0:
        return native
    steps = int(math.log(zoom) / math.log(1.3) + 1e-9)
    return SHOT_SIZES[min(len(SHOT_SIZES) - 1, SHOT_SIZES.index(native) + steps)]


def ui_path(sol):
    return (f"Inspector > Video > Transform: Zoom X/Y {sol['zoom_x']}, Position X {sol['position_x']}, Position Y {sol['position_y']} "
            f"(crop rect x={sol['crop_rect'][0]} y={sol['crop_rect'][1]} w={sol['crop_rect'][2]} h={sol['crop_rect'][3]})") if sol and sol.get('crop_rect') else None


def waived(flag, waivers):
    f = str(flag).lower()
    return any(w and w.lower() in f for w in waivers or [])


def client_safety(sub, policy):
    """The model judges client safety against the brief's rules; the operator may waive a rule for a client afterwards (e.g. PPE on a
    rural training film). A sub-clip marked unsafe becomes safe when every one of its risk flags is waived. Returns (safe, kept_flags, waived_flags)."""
    flags = sub.get('risk_flags') or []
    waivers = policy.get('waived_risk_flags') or []
    kept = [f for f in flags if not waived(f, waivers)]
    gone = [f for f in flags if waived(f, waivers)]
    if sub['client_safe']:
        return True, kept, gone
    return bool(flags) and not kept, kept, gone


def eligibility(sub, policy, max_zoom, src_w, src_h, timeline_w, timeline_h):
    """Returns (eligibility, crop_solution_or_None, notes[])."""
    p = sub['people_and_speaker_analysis']
    qc = sub.get('technical_qc_and_remediation') or sub.get('technical_qc') or {}
    notes = []
    safe, _, gone = client_safety(sub, policy)
    if gone and safe and not sub['client_safe']:
        notes.append('client-safe after operator waiver of: ' + ', '.join(gone))
    if sub['usability_grade'] == 'REJECT' or not safe:
        return 'REJECT_ALL', None, notes
    talking = bool(p.get('looking_at_lens') or (p.get('mouth_visible') and p.get('speech_translation_block')))   # design/125 P4
    if not talking:
        return 'ELIGIBLE_AS_IS', None, notes            # silent worker (no speech heard) / hidden lips rule
    if policy.get('show_speaker_video'):
        return 'ELIGIBLE_A_ROLL_SPEAKER', None, notes
    m = p.get('speaker_crop_module')
    if not m:
        return 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', {'feasible': False, 'reason': 'speaker visible but no crop boxes logged'}, notes
    boxes = (m.get('speaker_head_mouth_box'), m.get('speaker_full_body_box'), m.get('must_preserve_action_box'))
    if not all(valid_box(b) for b in boxes):
        return 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', {'feasible': False, 'reason': 'crop boxes are outside 0-1 or have zero size'}, notes + ['invalid crop boxes']
    if not head_inside_body(boxes[0], boxes[1]):
        notes.append('head box not inside body box, or body wider than 0.6 of the frame: NEEDS_BOUNDARY_CHECK')
    try:
        sol = compute_davinci_crop(boxes[1], boxes[2], src_w, src_h, timeline_w, timeline_h, max_zoom,
                                   float(qc.get('horizon_rotation_deg') or 0.0), bool(qc.get('stabilization_needed')), head_box=boxes[0])
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        return 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', {'feasible': False, 'reason': f'solver error: {exc.__class__.__name__}'}, notes + ['solver error']
    if sol['feasible'] and m.get('sharp_in_crop_zone', True):
        return 'ELIGIBLE_WITH_CROP', sol, notes
    if sol['feasible'] and not m.get('sharp_in_crop_zone', True):
        sol['reason'] = 'crop zone is not sharp'
    return 'REJECT_VIDEO_KEEP_AUDIO_CONTEXT', sol, notes


def solve(log, policy, clip, timeline):
    """Mutates every sub_clip in `log` with a `stage15` block. clip: media record (width/height/fps); timeline: {'width','height','fps'}."""
    src_w, src_h = clip.get('width') or timeline['width'], clip.get('height') or timeline['height']
    try:
        source_fps = float(Fraction(str(clip.get('fps') or timeline['fps'])))
    except (ValueError, ZeroDivisionError):
        source_fps = float(timeline['fps'])
    zoom_cap = max_safe_zoom(src_w, src_h, timeline['width'], timeline['height'], log.get('max_safe_zoom_limit'))
    log['max_safe_zoom_limit_applied'] = zoom_cap
    for sub in log.get('sub_clips') or []:
        elig, sol, notes = eligibility(sub, policy, zoom_cap, src_w, src_h, timeline['width'], timeline['height'])
        cam = sub.get('camera_and_optics') or {}
        pacing = sub.get('pacing_and_flow') or {}
        options = [o for o in pacing.get('time_manipulation_options') or [] if not (o == 'SLOW_MO_ELIGIBLE' and source_fps < 50)]
        if options != (pacing.get('time_manipulation_options') or []):
            notes.append('SLOW_MO_ELIGIBLE removed: source fps under 50')
        if notes and any('NEEDS_BOUNDARY_CHECK' in n for n in notes):
            sub['tc_confidence'] = 'NEEDS_BOUNDARY_CHECK'
        zoom = (sol or {}).get('zoom_x') if elig == 'ELIGIBLE_WITH_CROP' else None
        safe, kept_flags, waived_flags = client_safety(sub, policy)
        sub['stage15'] = {'visual_eligibility': elig, 'crop_solution': sol, 'client_safe_effective': safe, 'risk_flags_effective': kept_flags, 'risk_flags_waived': waived_flags,
                          'still_frame_dynamic_zoom_eligible': not cam.get('has_3d_parallax') and not cam.get('has_internal_scene_motion'),
                          'effective_post_crop_shot_size': effective_post_crop_shot_size(cam.get('native_shot_size'), zoom),
                          'time_manipulation_options': options, 'ui_path': ui_path(sol) if elig == 'ELIGIBLE_WITH_CROP' else None,
                          'policy': {'allow_speaker_audio': bool(policy.get('allow_speaker_audio')), 'show_speaker_video': bool(policy.get('show_speaker_video')),
                                     'waived_risk_flags': list(policy.get('waived_risk_flags') or [])},
                          'timeline': dict(timeline), 'notes': notes}
    return log
