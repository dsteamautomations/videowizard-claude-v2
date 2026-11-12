"""design/137 and design/139: what the operator chose for this film, each with their words, in vw2_runs.film: the video category, the film's shape with the
AI video shape and the frame rate, the preferred colours and the drawing font. Nothing here is assumed for a new film; a step that needs a choice not yet
made is refused, naming the command. A run made before design/139 has film NULL: it keeps what it was made with (16:9 at 25, the documentary guidebooks,
Noto Sans), the older way kept until those films close (design/35)."""
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

from psycopg.types.json import Json

from . import library
from .errors import Problem

SHAPES = {'horizontal': '16:9', 'vertical': '9:16'}
SIZES = {'16:9': (1920, 1080), '9:16': (1080, 1920)}
RETIRED_SHAPES = ('1:1', '4:5', 'square')   # SK, 2 Nov 2026 (design/138 A3): kept for a future update
RATES = (24, 25, 30, 50, 60)                # design/139 Q2: whole rates; 23.976, 29.97 and 59.94 are offered as 24, 30 and 60
FONTS = {'Noto Sans': 'NotoSans-Variable.ttf', 'Inter': 'Inter-Variable.ttf', 'Roboto': 'Roboto-Variable.ttf',
         'Montserrat': 'Montserrat-Variable.ttf', 'Lato': 'Lato-Regular.ttf'}   # design/139 Q4: files under server/fonts (renders have no network)
LOCKS = {'category': 'visuals', 'shape': 'analysis', 'colours': None, 'font': None, 'motion': None}   # the stage whose first job fixes the choice
OLDER = {'category': library.DEFAULT_CATEGORY, 'frame': '16:9', 'fps': 25, 'font': 'Noto Sans'}


# Motion style per film and the font set (SK, 11-12 Nov 2026; design/179). A style is a file under server/motion_styles (adding a style is adding a file);
# the fonts are files under server/fonts, described by fonts.json (written by scripts/fetch_fonts.py from the files themselves). FONTS above is the older
# way: a film that recorded one of those five keeps it; Roboto and Lato are no longer offered to a new film.
STYLE_DIR = Path(__file__).resolve().parents[1] / 'motion_styles'
FONT_DIR = Path(__file__).resolve().parents[1] / 'fonts'
DEFAULT_STYLE = 'restrained'
STYLE_ORDER = ('restrained', 'lively', 'bold', 'technical', 'editorial', 'playful', 'data-led', 'product')
OLDER_STYLE = ('Calm, eased, technical: arrivals on long ease-outs (`power3.out`, `expo.out`), a build in sequence (staggered, never all at once), '
               'a label that lands and holds dead still, a slow push-in only when the brief asks. Flat, clean, technical.')   # the one style every film had before; kept for films without a recorded style
SCRIPT_RANGES = {'latin': [(0x41, 0x5A), (0x61, 0x7A), (0xC0, 0xD6), (0xD8, 0xF6), (0xF8, 0x24F)], 'devanagari': [(0x0900, 0x097F)], 'tamil': [(0x0B80, 0x0BFF)], 'telugu': [(0x0C00, 0x0C7F)],
                 'kannada': [(0x0C80, 0x0CFF)], 'malayalam': [(0x0D00, 0x0D7F)]}
SCRIPT_NAMES = {'latin': 'English', 'devanagari': 'Hindi', 'tamil': 'Tamil', 'telugu': 'Telugu', 'kannada': 'Kannada', 'malayalam': 'Malayalam'}


@lru_cache(maxsize=1)
def styles():
    """{name: {title, for, first: [categories it is recommended first for], also: [...], text}}; a file that is empty or has no text is left out (E3)."""
    out = {}
    for path in sorted(STYLE_DIR.glob('*.md')):
        head, _, text = path.read_text(encoding='utf-8').partition('\n\n')
        meta = dict((k.strip(), v.strip()) for k, v in (line.split(':', 1) for line in head.splitlines() if ':' in line))
        if text.strip() and meta.get('title'):
            cats = lambda key: [c.strip() for c in meta.get(key, '').split(',') if c.strip()]
            out[path.stem] = {'title': meta['title'], 'for': meta.get('for', ''), 'first': cats('first'), 'also': cats('also'), 'text': text.strip()}
    return out


@lru_cache(maxsize=1)
def font_set():
    return json.loads((FONT_DIR / 'fonts.json').read_text(encoding='utf-8'))['fonts']


def recommend_styles(category_):
    """S3: the style filed first for the category, then those filed also for it, then the rest; Restrained first when none is filed (E1)."""
    st = styles()
    order = [n for n in STYLE_ORDER if n in st] + [n for n in st if n not in STYLE_ORDER]
    first = [n for n in order if category_ in st[n]['first']] or [n for n in order if n == DEFAULT_STYLE]
    also = [n for n in order if category_ in st[n]['also'] and n not in first]
    return first + also + [n for n in order if n not in first and n not in also]


def motion(run):
    """The film's motion style, or None: not asked yet, or a film from before (it keeps the older fixed style)."""
    return None if older(run) else _value(run, 'motion').get('value')


def style_part(run):
    """S4: the 'Motion style' part of a drawn shot's brief."""
    name = motion(run)
    if name and name in styles():
        return f"Motion style ({styles()[name]['title']}): how things move and appear in this film. It never changes the facts, the labels, the colours, the font or the timing above.\n{styles()[name]['text']}"
    return f'Motion style (the older fixed style, kept for this film): {OLDER_STYLE}'


def need_motion(run):
    """S3: asked once, at the treatment, with the style recommended for the film's category; a film from before is not asked."""
    if older(run) or motion(run):
        return
    st, order = styles(), recommend_styles(category(run))
    raise Problem(409, 'FILM_MOTION', f"This film has no motion style yet. Recommend {st[order[0]]['title']} ({st[order[0]]['for']}) for this film's category, name the others in a line "
                                      f"({'; '.join(st[n]['title'] + ': ' + st[n]['for'] for n in order[1:])}), ask the operator once, and record their answer: "
                                      '`vw motion-style <name> --quote "<their words>"`. A look none of these gives: record the nearest and tell the builder what was asked for.')


def scripts_of(text_):
    """S8: the scripts a text is written in, read from its letters (figures, signs and spaces say nothing)."""
    found = set()
    for ch in str(text_ or ''):
        c = ord(ch)
        for name, ranges in SCRIPT_RANGES.items():
            if any(lo <= c <= hi for lo, hi in ranges):
                found.add(name)
    return found


def _holds(name, scripts):
    f = font_set().get(name)
    return bool(f) and set(scripts) <= set(f['scripts'])


def fonts_for(style, scripts, last=None):
    """S6, S7: the fonts offered to a film, in the order to recommend them: the client's last font first, then the style's fonts, then the other
    fonts that hold the film's scripts (E5). A font without one of the scripts is not in the list (E4, E6)."""
    scripts, fs = set(scripts or ()) | {'latin'}, font_set()
    rows = [{'name': n, 'character': f['character'], 'fits': style in f['styles'], 'last': n == last, 'kept': False,
             'languages': [SCRIPT_NAMES[s] for s in f['scripts']]} for n, f in fs.items() if _holds(n, scripts)]
    if last and last in FONTS and last not in fs and scripts == {'latin'}:   # E8: the client's font from before the set, kept for them
        rows.append({'name': last, 'character': 'used on this client\'s last film', 'fits': False, 'last': True, 'kept': True, 'languages': ['English']})
    return sorted(rows, key=lambda r: (not r['last'], not r['fits']))


def font_faces(name, scripts):
    """The files a film's font brings into a drawing: one family per script the film is written in, English always (labels hold figures and Latin words)."""
    f = font_set().get(name)
    if not f:
        return [{'family': name, 'file': FONTS[name], 'bold': False}] if name in FONTS else []
    out = []
    for sc in ['latin'] + [s for s in f['scripts'] if s != 'latin' and s in set(scripts or ())]:
        out += [{'family': f['scripts'][sc]['family'], 'file': x['file'], 'bold': x['bold']} for x in f['scripts'][sc]['files']
                if not any(o['file'] == x['file'] for o in out)]
    return out


def missing_letters(name, labels):
    """E7: for each label, the letters no file of the film's font holds; [] for a font from before the set (not judged)."""
    f = font_set().get(name)
    if not f:
        return []
    cover = [r for sc in f['scripts'].values() for x in sc['files'] for r in x['cover']]
    has = lambda c: any(lo <= c <= hi for lo, hi in cover)
    out = []
    for label in labels or []:
        miss = [ch for ch in dict.fromkeys(str(label)) if unicodedata.category(ch)[0] in 'LM' and ord(ch) < 0x3000 and not has(ord(ch))]   # letters and their marks; a sign the font lacks falls to Noto Sans
        if miss:
            out.append({'label': label, 'letters': miss})
    return out


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


def font_scripts(run):
    """The scripts the film was written in when its font was recorded (S8); none for a film from before."""
    return set() if older(run) else set(_value(run, 'font').get('scripts') or ())


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


def check(key, value, video=None, fps=None, scripts=None):
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
        if value not in font_set() and value not in FONTS:
            raise Problem(422, 'FILM_CHOICE', f'{value!r} is not a font the server holds; offer: {", ".join(font_set())}.')
        lacks = [s for s in sorted(scripts or ()) if value in font_set() and s not in font_set()[value]['scripts']] or [s for s in sorted(scripts or ()) if value not in font_set() and s != 'latin']
        if lacks:   # S6: never a font for a film whose language it lacks
            have = [n for n in font_set() if _holds(n, scripts)]
            raise Problem(422, 'FILM_CHOICE', f"{value} has no {' or '.join(SCRIPT_NAMES[s] for s in lacks)} letters, and this film is written in {', '.join(SCRIPT_NAMES[s] for s in sorted(scripts))}; offer: {', '.join(have)}.")
        return {'value': value}
    if key == 'motion':
        name = value.lower()
        if name not in styles():
            raise Problem(422, 'FILM_CHOICE', f'{value!r} is not a motion style; the styles are: {", ".join(recommend_styles(None))}.')
        return {'value': name}
    raise Problem(422, 'FILM_CHOICE', f'unknown choice {key!r}')


def locked_by(key):
    return LOCKS[key]


def record(conn, user, run, key, value, quote, video=None, fps=None, scripts=None):
    """Record one choice with the operator's words; a choice is fixed once the stage that reads it has started (LOCKS)."""
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    if older(run):
        raise Problem(409, 'FILM_CHOICE', 'This film was started before these choices were asked; it keeps what it was made with.')
    quote = str(quote or '').strip()
    if not quote:
        raise Problem(422, 'FILM_CHOICE', 'Pass the operator\'s own words with --quote.')
    doc = check(key, value, video, fps, scripts)
    stage = LOCKS[key]
    if stage and conn.execute('select 1 from vw2_jobs where run_id=%s and stage=%s limit 1', (run['id'], stage)).fetchone():
        why = {'analysis': 'the analysis has started and judged the crops against the shape recorded; to change it, run the analysis again (`vw analysis --again`) after recording',
               'visuals': 'the visuals stage has started and its guidebooks were written for the category recorded'}[stage]
        if key == 'shape':
            raise Problem(409, 'FILM_LOCKED', f'The shape cannot change now: {why}. Ask the builder if the film must change shape.')
        raise Problem(409, 'FILM_LOCKED', f'The {key} cannot change now: {why}.')
    doc = {**doc, **({'scripts': sorted(scripts)} if key == 'font' and scripts else {}), 'quote': quote, 'by': user.get('name') or user.get('id'), 'at': datetime.now(timezone.utc).isoformat()}
    row = conn.execute("update vw2_runs set film = coalesce(film, '{}'::jsonb) || jsonb_build_object(%s::text, %s::jsonb) where id=%s returning film",
                       (key, Json(doc), run['id'])).fetchone()
    return row['film']
