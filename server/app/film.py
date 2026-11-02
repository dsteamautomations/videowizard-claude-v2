"""design/137 and design/139: what the operator chose for this film, each with their words, in vw2_runs.film: the video category, the film's shape with the
AI video shape and the frame rate, the preferred colours and the drawing font. Nothing here is assumed for a new film; a step that needs a choice not yet
made is refused, naming the command. A run made before design/139 has film NULL: it keeps what it was made with (16:9 at 25, the documentary guidebooks,
Noto Sans), the older way kept until those films close (design/35)."""
import math
import re
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction

from psycopg.types.json import Json

from . import library
from .errors import Problem

SHAPES = {'horizontal': '16:9', 'vertical': '9:16'}
SIZES = {'16:9': (1920, 1080), '9:16': (1080, 1920)}
RETIRED_SHAPES = ('1:1', '4:5', 'square')   # SK, 2 Nov 2026 (design/138 A3): kept for a future update
RATES = (24, 25, 30, 50, 60)                # design/139 Q2: whole rates; 23.976, 29.97 and 59.94 are offered as 24, 30 and 60
FONTS = {'Noto Sans': 'NotoSans-Variable.ttf', 'Inter': 'Inter-Variable.ttf', 'Roboto': 'Roboto-Variable.ttf',
         'Montserrat': 'Montserrat-Variable.ttf', 'Lato': 'Lato-Regular.ttf'}   # design/139 Q4: files under server/fonts (renders have no network)
LOCKS = {'category': 'visuals', 'shape': 'analysis', 'colours': None, 'font': None}   # the stage whose first job fixes the choice
OLDER = {'category': library.DEFAULT_CATEGORY, 'frame': '16:9', 'fps': 25, 'font': 'Noto Sans'}


def choices(run):
    return (run or {}).get('film')


def older(run):
    return choices(run) is None


def _value(run, key):
    return ((choices(run) or {}).get(key) or {})


def category(run):
    return OLDER['category'] if older(run) else _value(run, 'category').get('value')


def frame(run, video=False):
    if older(run):
        return OLDER['frame']
    s = _value(run, 'shape')
    v = s.get('video' if video else 'value')
    return SHAPES.get(v)


def fps(run):
    return OLDER['fps'] if older(run) else _value(run, 'shape').get('fps')


def font(run):
    return OLDER['font'] if older(run) else _value(run, 'font').get('value')


def colours(run):
    """The operator's preferred colours as they said them, 'no preference', or None when not asked yet."""
    return None if older(run) else _value(run, 'colours').get('value')


def timeline(run):
    """The film's timeline; refused for a new film whose shape is not recorded yet."""
    f, r = frame(run), fps(run)
    if not f or not r:
        raise Problem(409, 'FILM_SHAPE', 'The film\'s shape is not recorded yet: show the operator `vw shape` (the clip count and the recommendation), ask the film\'s shape, '
                                         'then the AI video shape, and record both with `vw shape <horizontal|vertical> --video <horizontal|vertical> --fps <n> --quote "<their words>"`.')
    w, h = SIZES[f]
    return {'width': w, 'height': h, 'fps': r, 'aspect_ratio': f}


def need_category(run):
    c = category(run)
    if not c:
        raise Problem(409, 'FILM_CATEGORY', 'This film has no video category yet. Read the script, name the category it fits with one line why, ask the operator '
                                            f'({", ".join(library.CATEGORIES)}), and record their answer: `vw category <name> --quote "<their words>"`.')
    return c


def rate_of(value):
    """A clip's frame rate as the whole film rate it would be cut at: 29.97 → 30, 23.976 → 24, 59.94 → 60."""
    try:
        f = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        return None
    if not math.isfinite(f) or f <= 0:
        return None
    return min(RATES, key=lambda r: abs(r - f))


def _orientation(c):
    w, h = c.get('width') or 0, c.get('height') or 0
    if int(c.get('rotation_deg') or 0) % 180:
        w, h = h, w
    return 'square' if w == h else 'vertical' if h > w else 'horizontal'


def recommend(clips):
    """design/139 R1: the shape most clips have and the rate most share, with the counts; None on a tie or with no clips (asked plainly)."""
    counts = Counter({'horizontal': 0, 'vertical': 0, 'square': 0})
    counts.update(_orientation(c) for c in clips or [] if c.get('width') and c.get('height'))
    h, v = counts['horizontal'], counts['vertical']
    rates = Counter(r for r in (rate_of(c.get('fps')) for c in clips or []) if r)
    top = rates.most_common(2)
    return {'counts': dict(counts), 'shape': 'horizontal' if h > v else 'vertical' if v > h else None,
            'fps_counts': dict(rates.most_common()), 'fps': top[0][0] if top and (len(top) == 1 or top[0][1] > top[1][1]) else None}


def check(key, value, video=None, fps=None):
    """The choice as it is stored, or a refusal naming what is allowed."""
    value = str(value or '').strip()
    if key == 'category':
        if value not in library.CATEGORIES:
            raise Problem(422, 'FILM_CHOICE', f'{value!r} is not a category; use one of: {", ".join(library.CATEGORIES)}.')
        return {'value': value}
    if key == 'shape':
        for v in (value, video):
            if v in RETIRED_SHAPES:
                raise Problem(422, 'FILM_CHOICE', 'Square and 4:5 are kept for a future update (SK, 2 Nov 2026); a film is horizontal or vertical.')
            if v not in SHAPES:
                raise Problem(422, 'FILM_CHOICE', 'Give the film\'s shape and the AI video shape, each horizontal or vertical (--video).')
        if fps not in RATES:
            raise Problem(422, 'FILM_CHOICE', f'Give the frame rate as one of {", ".join(map(str, RATES))} (--fps); 29.97 is cut at 30, 23.976 at 24, 59.94 at 60.')
        return {'value': value, 'video': video, 'fps': fps}
    if key == 'colours':
        if not value or len(value) > 300:
            raise Problem(422, 'FILM_CHOICE', 'Give the colours as the operator said them (for example "navy and orange" or "#123456, #FF8800"), or "no preference".')
        return {'value': value}
    if key == 'font':
        if value not in FONTS:
            raise Problem(422, 'FILM_CHOICE', f'{value!r} is not a font the server holds; offer: {", ".join(FONTS)} (Noto Sans recommended).')
        return {'value': value}
    raise Problem(422, 'FILM_CHOICE', f'unknown choice {key!r}')


def locked_by(key):
    return LOCKS[key]


def record(conn, user, run, key, value, quote, video=None, fps=None):
    """Record one choice with the operator's words; a choice is fixed once the stage that reads it has started (LOCKS)."""
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    if older(run):
        raise Problem(409, 'FILM_CHOICE', 'This film was started before these choices were asked; it keeps what it was made with.')
    quote = str(quote or '').strip()
    if not quote:
        raise Problem(422, 'FILM_CHOICE', 'Pass the operator\'s own words with --quote.')
    doc = check(key, value, video, fps)
    stage = LOCKS[key]
    if stage and conn.execute('select 1 from vw2_jobs where run_id=%s and stage=%s limit 1', (run['id'], stage)).fetchone():
        why = {'analysis': 'the analysis has started and judged the crops against the shape recorded; to change it, run the analysis again (`vw analysis --again`) after recording',
               'visuals': 'the visuals stage has started and its guidebooks were written for the category recorded'}[stage]
        if key == 'shape':
            raise Problem(409, 'FILM_LOCKED', f'The shape cannot change now: {why}. Ask the builder if the film must change shape.')
        raise Problem(409, 'FILM_LOCKED', f'The {key} cannot change now: {why}.')
    doc = {**doc, 'quote': quote, 'by': user.get('name') or user.get('id'), 'at': datetime.now(timezone.utc).isoformat()}
    row = conn.execute("update vw2_runs set film = coalesce(film, '{}'::jsonb) || jsonb_build_object(%s::text, %s::jsonb) where id=%s returning film",
                       (key, Json(doc), run['id'])).fetchone()
    return row['film']
