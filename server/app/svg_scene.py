"""design/117 P2: the rules of an SVG scene. The planner writes the scene as one SVG document (data, never code); this module refuses what the
renderer must never see (scripts, foreign objects, animation, external links, unknown fonts, unreadable text) with the reason, reads the parts the
render and the check need (ids, groups, texts, pictures), and embeds the run's approved pictures as data URIs."""
import base64
import re
import xml.etree.ElementTree as ET

SVG_NS, XLINK_NS = 'http://www.w3.org/2000/svg', 'http://www.w3.org/1999/xlink'
ALLOWED = {'svg', 'g', 'defs', 'title', 'desc', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'path', 'text', 'tspan', 'image', 'use',
           'linearGradient', 'radialGradient', 'stop', 'clipPath', 'mask', 'pattern', 'filter', 'feGaussianBlur', 'feDropShadow', 'feOffset', 'feBlend',
           'feMerge', 'feMergeNode', 'feFlood', 'feComposite', 'feColorMatrix'}
LINKED = {'use', 'linearGradient', 'radialGradient', 'pattern', 'filter', 'clipPath', 'mask'}   # href="#id" inside the document
TEXT_MIN_SHARE, TEXT_MAX_WORDS, SAFE = 0.04, 8, 0.05   # design/91 N13; design/116 (the skill's rule); the inner 90 % of the frame
MAX_BYTES = 2_000_000
COLOUR = re.compile(r'^(none|currentColor|#[0-9A-Fa-f]{6}|url\(#[A-Za-z0-9_-]+\))$')
REF = re.compile(r'^ref:([A-Za-z0-9_-]+)$')
HREF_RE = re.compile(r'((?:xlink:)?href=")ref:([A-Za-z0-9_-]+)(")')


def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def parse(text):
    """The document's root, or a ValueError 'not an SVG document'."""
    if not text or len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('not an SVG document' if not text else f'the scene is over {MAX_BYTES // 1_000_000} MB: use <use> for repeats and components for things')
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError(f'not an SVG document (XML: {exc})') from None
    if local(root.tag) != 'svg':
        raise ValueError(f"not an SVG document (the root is <{local(root.tag)}>)")
    return root


def view_box(root):
    parts = (root.get('viewBox') or '').replace(',', ' ').split()
    if len(parts) != 4:
        return None
    try:
        x, y, w, h = (float(p) for p in parts)
    except ValueError:
        return None
    return (x, y, w, h) if w > 0 and h > 0 else None


def _style(el):
    out = {}
    for decl in (el.get('style') or '').split(';'):
        if ':' in decl:
            k, v = decl.split(':', 1)
            out[k.strip()] = v.strip()
    return out


def _attr(el, name, parents):
    """An attribute or style property of the element, else the nearest ancestor's (SVG inherits fill, stroke, font-size, font-family)."""
    for e in [el] + parents[::-1]:
        v = _style(e).get(name) or e.get(name)
        if v is not None:
            return v
    return None


def _walk(root):
    """(element, parents) for every element, depth first."""
    stack = [(root, [])]
    while stack:
        el, parents = stack.pop()
        yield el, parents
        stack.extend((c, parents + [el]) for c in reversed(list(el)))


def ids_of(root):
    return {el.get('id'): el for el, _ in _walk(root) if el.get('id')}


def children_of(root):
    """The ids of each group's direct children, in document order (a build steps through them)."""
    return {el.get('id'): [c.get('id') for c in el if c.get('id')] for el, _ in _walk(root) if local(el.tag) == 'g' and el.get('id')}


def members(root, ids):
    """The elements an action touches: a group stands for its children, in order; anything else for itself."""
    kids, out = children_of(root), []
    for i in ids:
        for j in (kids.get(i) or [i]):
            if j not in out:
                out.append(j)
    return out


def _text_of(el):
    return ' '.join(''.join(el.itertext()).split())


def texts_of(root):
    return [(el.get('id') or f'text-{n}', _text_of(el)) for n, (el, _) in enumerate(_walk(root), 1) if local(el.tag) == 'text' and _text_of(el)]


def _href(el):
    return el.get('href') or el.get(f'{{{XLINK_NS}}}href')


def image_refs(root):
    out = []
    for el, _ in _walk(root):
        if local(el.tag) == 'image':
            m = REF.match(_href(el) or '')
            if m and m.group(1) not in out:
                out.append(m.group(1))
    return out


def check(text, aspect=(16, 9), fonts=('Noto Sans',), refs=None):
    """Every rule the file breaks, each with its reason; [] when the scene may be rendered. refs: the run's references by id (status read)."""
    try:
        root = parse(text)
    except ValueError as exc:
        return [str(exc)]
    out = []
    vb = view_box(root)
    if not vb:
        return ['the scene needs viewBox="0 0 W H" with the film\'s aspect']
    want = aspect[0] / aspect[1]
    if abs(vb[2] / vb[3] - want) > want * 0.01:
        out.append(f'the viewBox is {vb[2]:g}:{vb[3]:g}; the film is {aspect[0]}:{aspect[1]}')
    for k in ('width', 'height'):
        v = root.get(k)
        if v and re.sub(r'px$', '', v) not in (f'{vb[2]:g}', f'{vb[3]:g}'):
            out.append(f'the root {k}="{v}" differs from the viewBox; leave width and height out')
    ids, allowed_fonts = {}, {f.lower() for f in fonts} | {'sans-serif', 'serif', 'monospace'}
    for el, parents in _walk(root):
        tag = local(el.tag)
        if tag not in ALLOWED:
            out.append(f'<{tag}> is not allowed in a scene')
            continue
        if el.get('id'):
            if el.get('id') in ids:
                out.append(f"id '{el.get('id')}' twice")
            ids[el.get('id')] = el
        for a, v in el.attrib.items():
            name = local(a)
            if name.lower().startswith('on'):
                out.append(f"<{tag}> has {name}=: no event attributes")
            if re.search(r'url\((?!#)', v) or '@import' in v:
                out.append(f"<{tag}> {name}= has url( or @import: only url(#id) inside the document")
        href = _href(el)
        if href is not None:
            if tag == 'image':
                m = REF.match(href)
                if not m:
                    out.append(f'<image> href must be ref:<id> of an approved picture of the run, not "{href[:60]}"')
                else:
                    r = (refs or {}).get(m.group(1))
                    if not r:
                        out.append(f"<image> names ref:{m.group(1)}, which is not a picture of this run")
                    elif r.get('status') != 'approved':
                        out.append(f"<image> names ref:{m.group(1)}, which is {r.get('status')}, not approved")
            elif tag in LINKED:
                if not href.startswith('#'):
                    out.append(f'<{tag}> href must be #id inside the document, not "{href[:60]}"')
            else:
                out.append(f'<{tag}> may not carry href')
        for name in ('fill', 'stroke', 'stop-color', 'flood-color'):
            v = _style(el).get(name) or el.get(name)
            if v is not None and not COLOUR.match(v.strip()):
                out.append(f'<{tag}> {name}="{v}": give #RRGGBB, none, or url(#id)')
        if tag == 'text':
            fam = _attr(el, 'font-family', parents)
            if fam:
                bad = [f.strip().strip('\'"') for f in fam.split(',') if f.strip().strip('\'"').lower() not in allowed_fonts]
                if bad:
                    out.append(f"text '{el.get('id') or _text_of(el)[:30]}' uses the font {', '.join(bad)}: the run's fonts are {', '.join(fonts)}")
            size = _attr(el, 'font-size', parents)
            try:
                px = float(re.sub(r'px$', '', size or ''))
            except ValueError:
                px = None
            if px is None or px < TEXT_MIN_SHARE * vb[3]:
                out.append(f"text '{_text_of(el)[:40]}' is {size or 'without'} font-size: at least {TEXT_MIN_SHARE * 100:g} % of the frame height ({TEXT_MIN_SHARE * vb[3]:g}) (design/91 N13)")
            words = len(_text_of(el).split())
            if words > TEXT_MAX_WORDS:
                out.append(f"text '{_text_of(el)[:40]}…' has {words} words: at most eight words on screen at once (design/116)")
    for el, _ in _walk(root):   # second pass: internal links resolve
        href = _href(el)
        if href and href.startswith('#') and href[1:] not in ids:
            out.append(f"<{local(el.tag)}> names {href}, which is not in the document")
        for name in ('fill', 'stroke', 'filter', 'clip-path', 'mask'):
            v = _style(el).get(name) or el.get(name) or ''
            m = re.match(r'url\(#([A-Za-z0-9_-]+)\)', v.strip())
            if m and m.group(1) not in ids:
                out.append(f"<{local(el.tag)}> {name}= names #{m.group(1)}, which is not in the document")
    return out


def action_problems(actions, root):
    ids = ids_of(root)
    out = []
    for n, a in enumerate(actions or [], 1):
        for i in a.get('ids') or []:
            if i not in ids:
                out.append(f"action {n} names '{i}', which is not an element of the scene")
    return out


def _dim_key(d):
    return f"{d.get('part', '')} {d.get('measure', '')}".strip().lower()


def spec_problems(root, spec):
    """design/117 P2: every known size of the spec appears in the scene's text with its unit; an unknown size shows no figure (design/106 D6)."""
    text = ' '.join(t for _, t in texts_of(root)).lower()
    out = []
    for d in (spec or {}).get('dimensions') or []:
        if d.get('status') == 'unknown' or d.get('value') is None:
            part = str(d.get('part') or '').lower()
            for _, t in texts_of(root):
                if part and part in t.lower() and re.search(r'\d', t):
                    out.append(f"text '{t}' gives a figure for the {_dim_key(d)}, which is unknown: no figure (design/106 D6)")
            continue
        figure = f"{d['value']:g} {d.get('unit') or ''}".strip().lower()
        if figure not in text and f"{d['value']:g}{d.get('unit') or ''}".lower() not in text:
            out.append(f"the spec's {_dim_key(d)} ({figure}) is not written in the scene: every known size is a label with its unit")
    return out


def embed(text, images):
    """The scene with every ref:<id> picture inlined as a data URI. images: {ref id: (mime, bytes)}; a picture not given is a ValueError."""
    def sub(m):
        rid = m.group(2)
        if rid not in images:
            raise ValueError(f'picture {rid} is not loaded')
        mime, data = images[rid]
        return f'{m.group(1)}data:{mime};base64,{base64.b64encode(data).decode("ascii")}{m.group(3)}'
    return HREF_RE.sub(sub, text)
