"""Text overlays (requirements version 3 of 28 Nov 2026, part E): one overlay as a HyperFrames page. Pure: it writes text, it renders nothing.

One template for each kind; the card, the motion, the font, the size and the place are its settings (SK, 28 Nov 2026: the operator chooses them).
The same page gives the still picture the operator approves on and the transparent clip, so the two cannot differ in look.
Carried over from the trial on VW-25 (26 Nov 2026): text is set as whole lines, never a box a word; sizes are a share of the frame's shorter side;
the server's own GSAP and font files only, nothing from the network. The motion timings follow HyperFrames' own skills (Apache 2.0, NOTICE.md)."""
import html

# Sizes as a share of the frame's shorter side, at "medium" (the trial's second round): (first line, the lines after it).
SHARE = {'callout': (0.057, 0.057), 'title': (0.043, 0.043), 'number': (0.13, 0.037), 'name': (0.043, 0.03), 'list': (0.039, 0.039)}
LIST_HEAD = 0.028
FACTOR = {'small': 0.8, 'medium': 1.0, 'large': 1.25}
WEIGHT = {'regular': 500, 'bold': 700}
EDGE, TOP, BOTTOM = 5, 6.5, 21   # per cent of the frame: the usual inset; "bottom" sits above the captions. A default only: a shift or a spot goes anywhere
ENTRY_S, EXIT_S = 0.4, 0.3       # an entry at most 0.8 s, an exit about three quarters of it
TICK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'   # Lucide "check" (ISC)


def _rgba(colour, opacity):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return f'rgba({r}, {g}, {b}, {opacity / 100:g})'


def _position(place, shift, width, height):
    """The style of the box that holds the card: where it sits. It is never animated, so a motion cannot move the place."""
    if isinstance(place, dict):
        css, tx, ty = f"left:{place['x']:g}%;top:{place['y']:g}%", '-50%', '-50%'
    else:
        col = 'left' if 'left' in place else 'right' if 'right' in place else 'mid'
        line = 'top' if 'top' in place else 'bottom' if 'bottom' in place else 'mid'
        css = {'left': f'left:{EDGE:g}%', 'right': f'right:{EDGE:g}%', 'mid': 'left:50%'}[col] + ';' + {'top': f'top:{TOP:g}%', 'bottom': f'bottom:{BOTTOM:g}%', 'mid': 'top:50%'}[line]
        tx, ty = ('-50%' if col == 'mid' else '0px'), ('-50%' if line == 'mid' else '0px')
    dx, dy = round((shift or {}).get('x', 0) / 100 * width), round((shift or {}).get('y', 0) / 100 * height)
    move = lambda base, px: base if not px else f'{px}px' if base == '0px' else f'calc({base} + {px}px)'
    return f'{css};transform:translate({move(tx, dx)}, {move(ty, dy)})'


def _line(text, px, weight, stress=None, extra=''):
    t = html.escape(text)
    if stress and html.escape(stress) in t:
        t = t.replace(html.escape(stress), f'<span class="em">{html.escape(stress)}</span>', 1)
    return f'<span class="ln" style="font-size:{px}px;font-weight:{weight};{extra}">{t}</span>'


def _side(place):
    """Which side a slide comes from: the side the overlay sits on."""
    return 1 if (isinstance(place, dict) and place['x'] > 50) or (isinstance(place, str) and 'right' in place) else -1


def still_at(row, fps):
    """Seconds into the overlay at which everything is in: the moment of the operator's still picture."""
    dur = (row['end_frame'] - row['start_frame']) / fps
    if row.get('item_frames'):
        return min((max(row['item_frames']) - row['start_frame']) / fps + 0.6, max(0.0, dur - EXIT_S - 0.1))
    return dur / 2


def page(row, film):
    """index.html of one overlay. `row`: a row as overlays.check returns it. `film`: {'fps', 'width', 'height', 'accent' (a colour or None),
    'fonts': [{'family', 'file', 'bold'}] (the files of this overlay's font, placed under assets/fonts by the worker)}."""
    fps, width, height = film['fps'], film['width'], film['height']
    short, card, kind, motion = min(width, height), row['card'], row['kind'], row['motion']
    px = lambda share: round(short * share * FACTOR[row['size']])
    unit = short / 1080
    dur = (row['end_frame'] - row['start_frame']) / fps
    accent = card['accent'] or film.get('accent') or card['text']
    radius = {'square': 0, 'rounded': round(14 * unit), 'pill': 999}[card['corner']]
    border = '' if not card['border'] else f'border-left: {round(6 * unit)}px solid {accent};' if card['border'] == 'accent' else f"border: {max(1, round(2 * unit))}px solid {card['border']};"
    shadow = f'text-shadow: 0 {round(2 * unit)}px {round(8 * unit)}px rgba(0,0,0,0.75), 0 0 {round(2 * unit)}px rgba(0,0,0,0.6);' if card['opacity'] < 15 else ''
    families = list(dict.fromkeys(f['family'] for f in film['fonts']))
    bold_of = {f['family'] for f in film['fonts'] if f['bold']}
    faces = '\n'.join(f"@font-face {{ font-family: '{f['family']}'; src: url('assets/fonts/{f['file']}'); font-weight: {'700' if f['bold'] else '400' if f['family'] in bold_of else '100 900'}; }}"
                      for f in film['fonts'])
    stack = ', '.join(f"'{n}'" for n in families + ['Noto Sans']) + ', sans-serif'   # a sign the font lacks falls to Noto Sans, as in drawn shots
    weight = WEIGHT[row['weight']]
    first, rest = SHARE[kind]
    lines, js = row['lines'], []
    if kind == 'list':
        head = f'<div class="head" style="font-size:{px(LIST_HEAD)}px">{html.escape(row["heading"])}</div>' if row.get('heading') else ''
        items = ''.join(f'<div class="item" id="i{n}" style="font-size:{px(first)}px;font-weight:{weight}"><span class="tick">{TICK}</span>{html.escape(t)}</div>' for n, t in enumerate(lines))
        inner = head + items
        for n, frame in enumerate(row['item_frames']):
            at = max(0.25, (frame - row['start_frame']) / fps)   # never before the card is in
            js.append(f"tl.set('#i{n}', {{opacity: 1}}, {at:.3f});" if motion == 'cut' else
                      f"tl.fromTo('#i{n}', {{opacity: 0, x: {round(-16 * unit)}}}, {{opacity: 1, x: 0, duration: 0.35, ease: 'power2.out'}}, {at:.3f});")
    elif kind == 'number':
        inner = _line(lines[0], px(first), 800, row.get('stress'), 'line-height:1.05') + ''.join(_line(t, px(rest), weight, row.get('stress')) for t in lines[1:])
    else:
        inner = ''.join(_line(t, px(first if n == 0 else rest), weight, row.get('stress')) for n, t in enumerate(lines))
    entry = {'wipe': [f"tl.fromTo('#card', {{clipPath: 'inset(0 100% 0 0 round {radius}px)'}}, {{clipPath: 'inset(0 0% 0 0 round {radius}px)', duration: {ENTRY_S}, ease: 'power3.out'}}, 0);",
                      "tl.fromTo('.ln', {opacity: 0, y: 8}, {opacity: 1, y: 0, duration: 0.45, stagger: 0.25, ease: 'power2.out'}, 0.150);"],
             'fade': [f"tl.fromTo('#card', {{opacity: 0}}, {{opacity: 1, duration: {ENTRY_S}, ease: 'power2.out'}}, 0);"],
             'rise': ["tl.fromTo('#card', {opacity: 0, y: 24}, {opacity: 1, y: 0, duration: 0.45, ease: 'power2.out'}, 0);".replace('24', str(round(24 * unit)))],
             'slide': [f"tl.fromTo('#card', {{opacity: 0, x: {_side(row['place']) * round(width * 0.06)}}}, {{opacity: 1, x: 0, duration: 0.45, ease: 'power3.out'}}, 0);"],
             'cut': ["tl.set('#card', {opacity: 1}, 0);"]}[motion]
    leave = [] if motion == 'cut' else [f"tl.to('#card', {{opacity: 0, duration: {EXIT_S}, ease: 'power2.in'}}, {max(0.6, dur - EXIT_S - 0.02):.3f});"]
    code = '\n      '.join(entry + js + leave)
    css = f"""{faces}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {width}px; height: {height}px; overflow: hidden; background: transparent; font-family: {stack}; }}
#pos {{ position: absolute; }}
.card {{ background: {_rgba(card['ground'], card['opacity'])}; color: {card['text']}; border-radius: {radius}px; {border} padding: {round(26 * unit)}px {round(38 * unit)}px; overflow: hidden; {shadow} }}
.ln {{ display: block; white-space: nowrap; line-height: 1.25; }}
.em {{ color: {accent}; }}
.head {{ font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: {accent}; margin-bottom: {round(14 * unit)}px; }}
.item {{ line-height: 1.55; opacity: 0; display: flex; align-items: center; gap: {round(16 * unit)}px; white-space: nowrap; }}
.tick {{ width: {round(34 * unit)}px; height: {round(34 * unit)}px; flex: none; border-radius: 50%; background: {accent}; color: #fff; display: flex; align-items: center; justify-content: center; }}
.tick svg {{ width: 65%; height: 65%; }}"""
    return f"""<!doctype html>
<html><head><meta charset="UTF-8" /><meta name="viewport" content="width={width}, height={height}" />
<script src="assets/vendor/gsap.min.js"></script><style>
{css}
</style></head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-fps="{fps:g}" data-width="{width}" data-height="{height}">
    <div id="pos" style="{_position(row['place'], row.get('shift'), width, height)}"><div id="card" class="card">{inner}</div></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
      {code}
    window.__timelines["main"] = tl;
  </script>
</body></html>
"""
