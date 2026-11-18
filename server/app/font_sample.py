"""design/218 (SK, 18 Nov 2026): the font question shows one sample picture first. One row per offered font, drawn in that font with the very
files the drawn graphics use (server/fonts): the font's name, a label of this film's drawn graphics, a line of numbers and units, and the
film's other language where the font holds it ("English only" where it does not). On the film's colours, 900 px wide. Drawn by headless
Chromium (Playwright, as the drawn-graphics route), no AI and no paid call. "Other" is not drawn. A sample that cannot be made is one line,
NOT_AVAILABLE, and the question is asked as before."""
import html as _html
import re
import tempfile
from pathlib import Path

from PIL import ImageColor

from . import film
from .drawn import FONTS

WIDTH = 900
MAX_LABEL = 40   # characters; a longer label is shortened at a word, with an ellipsis
NUMBERS = '230 x 110 x 75 mm'
NEUTRAL = {'latin': 'Water tank', 'devanagari': 'पानी की टंकी', 'tamil': 'தண்ணீர் தொட்டி', 'telugu': 'నీటి ట్యాంకు',
           'kannada': 'ನೀರಿನ ತೊಟ್ಟಿ', 'malayalam': 'വെള്ളത്തിന്റെ ടാങ്ക്'}   # the label when the film has none in that language yet
ENGLISH_ONLY, NOT_INSTALLED = 'English only', 'not installed on the server'
NOT_AVAILABLE = 'The font sample is not available.'
NOT_ASKED = 'This film has no drawn graphic: its font is not asked, so there is no sample.'
BACKGROUND, TEXT, LIGHT = '#FFFFFF', '#1A1A1A', '#FFFFFF'
CARD = 4   # the chat card holds four options (the question tool's limit; it adds "Other" itself): the offer's first four, in its order
ON_CARD, OTHERS = 'On the card', 'Others you can name'
TWO_COLUMNS = 10   # more others than this are drawn in two columns, smaller


def _shots(plan):
    for gap in (plan or {}).get('gaps') or []:
        scenes = gap.get('scenes') or [sc for c in gap.get('choices') or [] for sc in c.get('scenes') or []]
        for sc in scenes:
            yield from sc.get('shots') or []


def drawn_shots(plan):
    return [s for s in _shots(plan) if s.get('visual_type') == 'drawn']


def drawn_labels(plan):
    """The labels of the plan's drawn shots, in plan order: each shot's on-screen labels, then its spec's label."""
    out = []
    for s in drawn_shots(plan):
        for label in [*((s.get('scene_motion') or {}).get('labels') or []), (s.get('drawing_spec') or {}).get('label')]:
            label = str(label or '').strip()
            if label and label not in out:
                out.append(label)
    return out


def shorten(text, n=MAX_LABEL):
    """At most n characters, cut at a word with an ellipsis; one word longer than n is cut with the ellipsis."""
    text = ' '.join(str(text).split())
    if len(text) <= n:
        return text
    head = text[:n + 1].rsplit(' ', 1)[0] if ' ' in text[:n + 1] else text[:n]
    return head.rstrip(' ,;:-') + '…'


def label_for(labels, script):
    """The film's first label in that language (English: a label with English letters only), else the server's neutral words."""
    for label in labels:
        found = film.scripts_of(label)
        if (found == {'latin'}) if script == 'latin' else (script in found):
            return shorten(label)
    return NEUTRAL[script]


def _have(file):
    return (FONTS / file).is_file()


def rows(offer, scripts, labels):
    """One row per offered font (never "Other"): its faces (one file per script, as a drawing gets them) and its lines."""
    others = sorted(set(scripts or ()) - {'latin'})
    out = []
    for f in offer:
        if f['name'] == 'Other':
            continue
        faces = film.font_faces(f['name'], set(scripts or ()))
        if not faces or not all(_have(x['file']) for x in faces):
            out.append({'name': f['name'], 'faces': [], 'missing': True, 'lines': [{'kind': 'name', 'text': f['name']}, {'kind': 'note', 'text': NOT_INSTALLED}]})
            continue
        lines = [{'kind': 'name', 'text': f['name']}, {'kind': 'label', 'text': label_for(labels, 'latin')}, {'kind': 'numbers', 'text': NUMBERS}]
        for s in others:   # the offer says which languages each font holds
            held = film.SCRIPT_NAMES[s] in (f.get('languages') or [])
            lines.append({'kind': 'label' if held else 'note', 'text': label_for(labels, s) if held else ENGLISH_ONLY})
        out.append({'name': f['name'], 'faces': faces, 'missing': False, 'lines': lines})
    return out


def _luminance(rgb):
    c = [v / 255 for v in rgb]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    la, lb = sorted((_luminance(ImageColor.getrgb(a)), _luminance(ImageColor.getrgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colours_of(words):
    """(background, text) from the film record's colours as the operator said them: the first colour named (#RRGGBB or a colour word) is the
    background, the most readable other one the text, else a readable dark or white. ponytail: the first colour as the background is a guess;
    the film record has no field for which is which."""
    found = []
    for tok in re.findall(r'#[0-9A-Fa-f]{6}\b|[A-Za-z]+', str(words or '')):
        try:
            hexed = '#%02X%02X%02X' % ImageColor.getrgb(tok)[:3]
        except ValueError:
            continue
        if hexed not in found:
            found.append(hexed)
    if not found:
        return BACKGROUND, TEXT
    bg = found[0]
    best = max(found[1:], key=lambda c: _contrast(bg, c), default=None)
    if best and _contrast(bg, best) >= 4.5:
        return bg, best
    return bg, max((TEXT, LIGHT), key=lambda c: _contrast(bg, c))


def page(rows_, bg, fg):
    """The HTML Chromium draws: the card's fonts first, then the others; each row's faces as @font-face from the server's files."""
    faces = [f"@font-face{{font-family:'vwnoto';src:url('{(FONTS / 'NotoSans-Variable.ttf').as_uri()}') format('truetype');font-weight:100 900}}"]
    blocks = []
    for i, r in enumerate(rows_):
        fams = []
        for j, x in enumerate(r['faces']):
            fam = f'vw{i}f{j}'
            static = any(y['bold'] for y in r['faces'] if y['family'] == x['family'])
            weight = (700 if x['bold'] else 400) if static else '100 900'
            faces.append(f"@font-face{{font-family:'{fam}';src:url('{(FONTS / x['file']).as_uri()}') format('truetype');font-weight:{weight}}}")
            fams.append(fam)
        family = ','.join(f"'{f}'" for f in fams) if fams else "'vwnoto'"
        lines = ''.join(f'<div class="{ln["kind"]}">{_html.escape(ln["text"])}</div>' for ln in r['lines'])
        blocks.append(f'<div class="row" style="font-family:{family}">{lines}</div>')
    card, rest = blocks[:CARD], blocks[CARD:]
    body = f'<h2>{ON_CARD}</h2>' + ''.join(card)
    if rest:
        body += f'<h2>{OTHERS}</h2>' + (f'<div class="cols">{"".join(rest)}</div>' if len(rest) > TWO_COLUMNS else ''.join(rest))
    css = (f"html,body{{margin:0;padding:0;width:{WIDTH}px;background:{bg};color:{fg}}}"
           "body{padding:8px 32px 16px;box-sizing:border-box}h2{font-family:'vwnoto';font-size:18px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;"
           'margin:18px 0 2px;opacity:.75}.row{padding:12px 0;border-top:2px solid;border-color:currentColor}'
           '.name{font-size:20px;opacity:.7}.label{font-size:36px;font-weight:600;line-height:1.35}'
           '.numbers{font-size:30px;font-weight:400;line-height:1.35}.note{font-size:24px;font-style:italic;opacity:.8}'
           '.cols{display:grid;grid-template-columns:1fr 1fr;column-gap:28px}.cols .label{font-size:26px}.cols .numbers{font-size:22px}'
           '.cols .name{font-size:17px}.cols .note{font-size:19px}')
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{"".join(faces)}{css}</style></head><body>{body}</body></html>'


def render(html):
    """The picture, by headless Chromium (Playwright). ponytail: a Chromium of its own per sample (a second or two), since the API's threads
    cannot share the worker's; keep it so unless the question is asked often."""
    from playwright.sync_api import sync_playwright
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'sample.html'
        path.write_text(html, encoding='utf-8')
        with sync_playwright() as p:
            b = p.chromium.launch(args=['--disable-gpu', '--force-color-profile=srgb', '--font-render-hinting=none', '--allow-file-access-from-files'])
            try:
                pg = b.new_page(viewport={'width': WIDTH, 'height': 600}, device_scale_factor=1)
                pg.goto(path.as_uri(), wait_until='load')
                pg.evaluate('() => document.fonts.ready.then(() => true)')
                return pg.screenshot(type='png', full_page=True)
            finally:
                b.close()


def sample(offer, scripts, plan, colours_words, render=render):
    """{'available', 'asked', 'message', 'png'?, 'rows'?}: never raises; a film with no drawn graphic is not asked."""
    if not drawn_shots(plan):
        return {'available': False, 'asked': False, 'message': NOT_ASKED}
    rs = rows(offer, scripts, drawn_labels(plan))
    if not any(not r['missing'] for r in rs):
        return {'available': False, 'asked': True, 'message': NOT_AVAILABLE}
    try:
        png = render(page(rs, *colours_of(colours_words)))
    except Exception as exc:   # the renderer missing or failing: the question goes on without the picture
        return {'available': False, 'asked': True, 'message': NOT_AVAILABLE, 'reason': f'{exc.__class__.__name__}: {exc}'[:300]}
    return {'available': True, 'asked': True, 'message': '', 'png': png, 'rows': [{'name': r['name'], 'missing': r['missing']} for r in rs],
            'on_card': [r['name'] for r in rs[:CARD]]}
