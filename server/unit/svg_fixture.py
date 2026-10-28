"""design/117: an SVG scene for the tests: a 16:9 canvas, a background, a title, a wall of three courses built one by one, a component picture, a
gradient and a filter, a label with a unit."""

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1600 900">
  <defs>
    <linearGradient id="warm"><stop offset="0" stop-color="#E8902A"/><stop offset="1" stop-color="#B5543A"/></linearGradient>
    <filter id="soft"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#2F2F2F" flood-opacity="0.3"/></filter>
  </defs>
  <rect id="bg" width="1600" height="900" fill="#F4EDE1"/>
  <text id="title" x="800" y="130" text-anchor="middle" font-family="Noto Sans" font-size="64" font-weight="700" fill="#2F2F2F">Bricks for the same wall</text>
  <g id="wall">
    <rect id="c1" x="300" y="700" width="400" height="60" fill="#B5543A" stroke="#2F2F2F" stroke-width="3"/>
    <rect id="c2" x="300" y="640" width="400" height="60" fill="#B5543A" stroke="#2F2F2F" stroke-width="3"/>
    <rect id="c3" x="300" y="580" width="400" height="60" fill="url(#warm)" stroke="#2F2F2F" stroke-width="3" filter="url(#soft)"/>
  </g>
  <image id="flame" href="ref:comp-1" x="1000" y="500" width="300" height="300"/>
  <path id="arrow" d="M 760 650 L 960 650 L 940 630 M 960 650 L 940 670" fill="none" stroke="#E8902A" stroke-width="8"/>
  <text id="pitch" x="300" y="820" font-family="Noto Sans" font-size="40" fill="#2F2F2F">course pitch 75 mm</text>
</svg>'''

ACTIONS = [{'kind': 'appear', 'ids': ['title'], 'at_s': 0},
           {'kind': 'build', 'ids': ['wall'], 'at_s': 0.5, 'every_s': 0.5},
           {'kind': 'move', 'ids': ['flame'], 'at_s': 2, 'path': [[1000, 500], [1000, 400]], 'seconds': 1},
           {'kind': 'highlight', 'ids': ['c3'], 'at_s': 2.5, 'seconds': 1},
           {'kind': 'fade', 'ids': ['arrow'], 'at_s': 3, 'seconds': 0.5}]

REFS = {'comp-1': {'status': 'approved', 'kind': 'component', 'key': 'run-1/visuals/references/comp-1.png'}}


def with_(svg=SVG, old='', new=''):
    assert old in svg, old
    return svg.replace(old, new, 1)
