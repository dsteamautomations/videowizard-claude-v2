"""Text overlays (requirements version 3 of 28 Nov 2026, part C): the overlay list, the film's look and the refusals. Pure: no database, no provider.

SK, 28 Nov 2026: the assistant brings out options and suggests, the operator judges and approves; the assistant and the server are the enabler, not the
checker. So this module refuses only what cannot be made at all (a shot or a time that is not in the film, empty words, a font the application does not
have or one without the letters, a card, motion or place it does not know). The number of words, two overlays at once, an overlay on a drawn shot or over
the captions are all made as asked. The facts it works out ("runs over the cut") are text for the operator and hold nothing."""
import math
import re

from . import film as F

KINDS = ('callout', 'number', 'list', 'title', 'name')
MOTIONS = ('wipe', 'fade', 'rise', 'slide', 'cut')
SIZES = ('small', 'medium', 'large')
WEIGHTS = ('regular', 'bold')
CORNERS = ('square', 'rounded', 'pill')
PLACES = ('top left', 'top', 'top right', 'left', 'centre', 'right', 'bottom left', 'bottom', 'bottom right')
USUAL_PLACE = {'callout': 'bottom left', 'number': 'bottom left', 'list': 'left', 'title': 'top left', 'name': 'bottom left'}
# A card is its settings. `accent` None means the film's own accent colour; `border` None means no border.
CARDS = {'dark': {'ground': '#141414', 'opacity': 55, 'text': '#ffffff', 'accent': None, 'corner': 'rounded', 'border': None},
         'cream': {'ground': '#f6efe2', 'opacity': 94, 'text': '#2a2622', 'accent': None, 'corner': 'rounded', 'border': None},
         'bare': {'ground': '#000000', 'opacity': 0, 'text': '#ffffff', 'accent': None, 'corner': 'square', 'border': None},
         'bar': {'ground': '#141414', 'opacity': 0, 'text': '#ffffff', 'accent': None, 'corner': 'square', 'border': 'accent'}}
LOOK = {'card': 'dark', 'motion': 'wipe', 'size': 'medium', 'weight': 'bold', 'font': None}   # font None: the film's own
LOOK_KEYS = ('card', 'motion', 'size', 'weight', 'font')
ROW_KEYS = ('kind', 'lines', 'heading', 'word', 'item_words', 'all_at_once', 'shot', 'start_s', 'end_s', 'place', 'shift', 'stress', 'icon', 'why') + LOOK_KEYS
COLOUR = re.compile(r'^#[0-9a-fA-F]{6}$')
READ_BASE_S, READ_WORD_S, READ_MIN_S, EARLY_MAX_S = 1.0, 0.4, 1.5, 2.0   # decision 2 (SK, 27 Nov 2026)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _one_of(what, value, known, where, more=''):
    if not isinstance(value, str) or value not in known:
        return f"{where}{what} {value!r} is not one the application has. Write one of: {', '.join(known)}{more}"


def _card(value, where):
    """(settings, problem): a named card, or the default card with the operator's own settings."""
    if isinstance(value, str):
        p = _one_of('card', value, tuple(CARDS), where, ', or the settings of your own card')
        return (None, p) if p else (dict(CARDS[value]), None)
    if not isinstance(value, dict):
        return None, f"{where}card {value!r} is not one the application has. Write one of: {', '.join(CARDS)}, or the settings of your own card"
    unknown = [k for k in value if k not in CARDS['dark']]
    if unknown:
        return None, f"{where}the card has a setting the application does not have: {', '.join(unknown)}. A card may set: {', '.join(CARDS['dark'])}"
    for k in ('ground', 'text', 'accent', 'border'):
        v = value.get(k)
        if v is not None and not (isinstance(v, str) and (COLOUR.match(v) or (k == 'border' and v == 'accent'))):
            return None, f"{where}the card's {k} {v!r} is not a colour the application can read. Write it as #rrggbb"
    if 'opacity' in value and not (_num(value['opacity']) and 0 <= value['opacity'] <= 100):
        return None, f"{where}the card's opacity is a number from 0 to 100"
    if 'corner' in value:
        p = _one_of("the card's corner", value['corner'], CORNERS, where)
        if p:
            return None, p
    return {**CARDS[LOOK['card']], **value}, None


def _look(given, base, film, where, keys=LOOK_KEYS):
    """(look, problems): `base` with what `given` sets; the first fault of each setting."""
    out, problems = dict(base), []
    for k in keys:
        if given.get(k) is None:
            continue
        v = given[k]
        if k == 'card':
            card, p = _card(v, where)
            out['card'] = card or out['card']
        elif k == 'font':
            p = None if isinstance(v, str) and v in F.font_set() else f"{where}the font {v!r} is not in the application. The fonts are: {', '.join(F.font_set())}"
            out['font'] = v if not p else out['font']
        else:
            p = _one_of(k, v, {'motion': MOTIONS, 'size': SIZES, 'weight': WEIGHTS}[k], where)
            out[k] = v if not p else out[k]
        if p:
            problems.append(p)
    return out, problems


def look_of(given, film):
    """The film's look as the templates read it: the defaults, the film's own font, and what the operator chose. Faults are left to `check`."""
    base = {**LOOK, 'card': dict(CARDS[LOOK['card']]), 'font': film.get('font')}
    return _look(given if isinstance(given, dict) else {}, base, film, '')[0]


def _reading_frames(words, fps):
    return math.ceil(round(max(READ_MIN_S, READ_BASE_S + READ_WORD_S * words) * fps, 6))   # rounded first: 2.2 s at 25 frames is 55, not 55.00000000000001


def _cut_at(cuts, frame):
    return next((c for c in cuts if c['start_frame'] <= frame < c['end_frame']), None)


def _crossed(cuts, start, end):
    """The facts for the operator: every cut the overlay runs over, by the shot it runs into."""
    first = _cut_at(cuts, start)
    return [f"runs over the cut into {c['name']}" for c in cuts if first and c['start_frame'] > start and c['start_frame'] < end]


def _seconds(v):
    return f'{v:g}'


def _moment(r, film, where, n_words):
    """(start_frame, end_frame, facts, item_frames, problem)."""
    fps, total, cuts, words = film['fps'], film['frames'], film['cuts'], film['words']
    word_frame = lambda n: words[n - 1]['start_frame']
    bad_word = lambda n: f"{where}word {n} is not in the voiceover (it has {len(words)} words)" if not (isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(words)) else None
    if r.get('shot') is not None and not any(c['name'] == r['shot'] for c in cuts):
        return None, None, [], None, f"{where}shot {r['shot']!r} is not a cut of the film. The cuts are: {', '.join(c['name'] for c in cuts)}"
    items = r.get('item_words')
    if items is not None:
        if not isinstance(items, list) or len(items) != len(r['lines']):
            return None, None, [], None, f'{where}"item_words" names one spoken word for each line ({len(r["lines"])} lines, {len(items) if isinstance(items, list) else 0} words)'
        for n in items:
            if bad_word(n):
                return None, None, [], None, bad_word(n)
    if r.get('start_s') is not None or r.get('end_s') is not None:   # times given: kept exactly
        a, b = r.get('start_s'), r.get('end_s')
        if a is None or b is None:
            return None, None, [], None, f'{where}"start_s" and "end_s" come together'
        if not (_num(a) and _num(b)):
            return None, None, [], None, f'{where}"start_s" and "end_s" are numbers, in seconds of the film'
        if b <= a:
            return None, None, [], None, f'{where}the end ({_seconds(b)} s) is not after the start ({_seconds(a)} s)'
        start, end = round(a * fps), round(b * fps)
        if a < 0 or end > total:
            return None, None, [], None, f'{where}the time {_seconds(a if a < 0 else b)} s is outside the film ({_seconds(round(total / fps, 2))} s long)'
        frames = [min(max(word_frame(n), start), end) for n in items] if items and not r.get('all_at_once') else None
        return start, end, _crossed(cuts, start, end), frames or ([start] * len(r['lines']) if r['kind'] == 'list' else None), None
    first = items[0] if items else r.get('word')
    if first is None:
        return None, None, [], None, f'{where}no moment. Write "word": the number of the spoken word, or "start_s" and "end_s" in seconds of the film'
    if bad_word(first):
        return None, None, [], None, bad_word(first)
    start = word_frame(first)
    cut = _cut_at(cuts, start)
    if r.get('shot') is not None and cut and cut['name'] != r['shot']:
        return None, None, [], None, f"{where}word {first} is spoken in {cut['name']}, not in {r['shot']}. Name {cut['name']}, or leave the shot out"
    need = _reading_frames(n_words, fps)
    if r['kind'] == 'list':   # a list may run over cuts: each item on its own word, the last one long enough to read
        frames = [start] * len(r['lines']) if r.get('all_at_once') or not items else [word_frame(n) for n in items]
        end = min(total, max(start + need, max(frames) + _reading_frames(len(r['lines'][-1].split()), fps)))
        return start, end, _crossed(cuts, start, end), frames, None
    facts = []
    if cut and start + need > cut['end_frame']:
        earlier = max(cut['start_frame'], cut['end_frame'] - need)
        if cut['end_frame'] - earlier >= need and start - earlier <= EARLY_MAX_S * fps:   # decision 2: up to 2 seconds before its word, to stay inside its shot
            facts.append(f"starts {_seconds(round((start - earlier) / fps, 1))} s before its word")
            start = earlier
    end = start + need
    if end > total:   # never past the end of the film
        start, end = max(0, total - need), total
    return start, end, facts + _crossed(cuts, start, end), None, None


def _row(r, i, look, film):
    where = f'row {i}: '
    if not isinstance(r, dict):
        return None, [where + 'a row is an object']
    unknown = [k for k in r if k not in ROW_KEYS]
    if unknown:
        return None, [f"{where}a field the application does not know: {', '.join(unknown)}. A row may hold: {', '.join(ROW_KEYS)}"]
    p = _one_of('kind', r.get('kind'), KINDS, where)
    if p:
        return None, [p]
    lines = r.get('lines')
    if not isinstance(lines, list) or not all(isinstance(t, str) for t in lines):
        return None, [where + '"lines" is a list of lines of text']
    if not any(t.strip() for t in lines):
        return None, [where + 'the words are empty. Write "lines": one or more lines of text']
    own, problems = _look(r, look, film, where)
    text = [t for t in ([r['heading']] if isinstance(r.get('heading'), str) else []) + lines if t.strip()]
    if not problems and own['font']:
        missing = F.missing_letters(own['font'], text)
        if missing:
            letters = ''.join(dict.fromkeys(ch for m in missing for ch in m['letters']))
            have = [n for n in F.font_set() if not F.missing_letters(n, text)]
            problems.append(f"{where}the font {own['font']!r} has no letter for {letters}. Fonts that have them: {', '.join(have) or 'none'}")
    place = r.get('place') if r.get('place') is not None else USUAL_PLACE[r['kind']]
    if isinstance(place, dict):
        if not (set(place) == {'x', 'y'} and all(_num(v) and 0 <= v <= 100 for v in place.values())):
            problems.append(where + 'the spot is outside the frame. "x" and "y" are shares of the width and the height, from 0 to 100')
    else:
        p = _one_of('place', place, PLACES, where)
        if p:
            problems.append(p)
    shift = r.get('shift')
    if shift is not None and not (isinstance(shift, dict) and shift and set(shift) <= {'x', 'y'} and all(_num(v) and -100 <= v <= 100 for v in shift.values())):
        problems.append(where + 'the shift is "x" and "y" in shares of the frame, from -100 to 100')
    start, end, facts, item_frames, p = _moment({**r, 'lines': lines}, film, where, sum(len(t.split()) for t in text))
    if p:
        problems.append(p)
    if problems:
        return None, problems[:1]   # one fault a row: the first, with what to write
    out = {'kind': r['kind'], 'lines': lines, **own, 'place': place, 'start_frame': start, 'end_frame': end, 'facts': facts,
           **{k: r[k] for k in ('heading', 'shift', 'stress', 'icon', 'why') if r.get(k) is not None},
           **({'item_frames': item_frames} if item_frames is not None else {})}
    return out, []


def check(doc, film):
    """The one check of an overlay list. `film`: {'fps', 'frames', 'cuts': [{'name', 'start_frame', 'end_frame'}], 'words': [{'start_frame', 'text'}], 'font'}.
    Returns {'look', 'rows', 'problems'}: every fault named by its row with what to write; rows are the overlays as the templates read them, with their frames."""
    if not isinstance(doc, dict):
        return {'look': None, 'rows': [], 'problems': ['the overlay list must be an object: {"look": {…}, "overlays": [ … ]}']}
    unknown = [k for k in doc if k not in ('look', 'overlays')]
    if unknown:
        return {'look': None, 'rows': [], 'problems': [f"the list has a field it does not know: {', '.join(unknown)}. It holds \"look\" and \"overlays\""]}
    given = doc.get('look') if doc.get('look') is not None else {}
    if not isinstance(given, dict):
        return {'look': None, 'rows': [], 'problems': ['"look" must be an object: the film\'s card, motion, size, weight and font']}
    if not isinstance(doc.get('overlays'), list):
        return {'look': None, 'rows': [], 'problems': ['"overlays" must be a list of rows']}
    problems = [f"the film's look: a field the application does not know: {', '.join(k for k in given if k not in LOOK_KEYS)}. The look may hold: {', '.join(LOOK_KEYS)}"] \
        if any(k not in LOOK_KEYS for k in given) else []
    base = {**LOOK, 'card': dict(CARDS[LOOK['card']]), 'font': film.get('font')}
    look, faults = _look(given, base, film, "the film's look: ")
    problems += faults
    rows = []
    for i, r in enumerate(doc['overlays'], 1):
        row, faults = _row(r, i, look, film)
        problems += faults
        if row:
            rows.append(row)
    return {'look': look, 'rows': rows, 'problems': problems}
