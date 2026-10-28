"""design/117 P5: the page shows the sheet and the server's passes on a drawn card and says when a drawing is held; the procedure says the new route;
the API carries the scene routes and the meta flag."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
PROC = json.dumps(json.load(open(ROOT / 'procedures' / 'v2.json', encoding='utf-8')), ensure_ascii=False)
MAIN = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')


def test_the_page_shows_the_sheet_and_the_passes_and_the_hold():
    assert 'k.sheet_url' in PAGE and 'img class="sheet"' in PAGE and 'function drawnPasses(c)' in PAGE and 'drawnPasses(k.check)' in PAGE
    assert "Held: a line still failed after the server" in PAGE and 'still failed' in PAGE and 'Server passes' in PAGE
    assert 'Rendering the drawing' in PAGE   # the waiting state stays


def test_the_procedure_says_the_route_the_scene_the_component_and_the_hold():
    for words in ('design/117', 'vw visuals scene --shot S --file scene.svg', '`scene_svg`', 'ref:<id>', '--kind component', 'transparent background', 'contact sheet of every frame',
                  'is held', 'scene --shot S --download', 'what must be exact', 'never shapes standing for things', 'at most eight words'):
        assert words in PROC, words
    assert 'scene_drawn' not in PROC and 'the server places the spec' not in PROC


def test_the_api_has_the_scene_routes_and_the_meta_flag():
    assert "@app.post('/api/runs/{run_id}/visuals/scene')" in MAIN and "@app.get('/api/runs/{run_id}/visuals/scene/{shot_id}')" in MAIN and "'chromium':" in MAIN
    assert "'component'" in MAIN   # ImageGenerate takes the kind
