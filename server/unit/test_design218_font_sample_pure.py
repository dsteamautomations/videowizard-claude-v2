"""design/218: the font question shows one sample picture first: one row per offered font, drawn in that font with the server's own files
(server/fonts), on the film's colours: a label of this film's drawn graphics, a line of numbers, and the film's other language or "English only".
Made by Chromium (Playwright), no AI. "Other" is not drawn; a sample that cannot be made says so in one line and never blocks the question.
Without a database. The render test runs where Playwright's Chromium is installed (it is on the builder's PC); the others test the rows and
the HTML the renderer is given."""
import json
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import film, font_sample as FS

ROOT = Path(__file__).resolve().parents[2]

try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as _p:
        _p.chromium.launch().close()
    CHROMIUM = True
except Exception:   # the package or the browser is missing on this machine
    CHROMIUM = False


def plan(*shots):
    return {'gaps': [{'gap_id': 'G01', 'scenes': [{'shots': list(shots)}]}]}


DRAWN = {'id': 'S1', 'visual_type': 'drawn', 'scene_motion': {'labels': ['Inlet pipe', 'நீர் உள்ளே']}, 'drawing_spec': {'label': 'Tank lid'}}
FOOTAGE = {'id': 'S2', 'visual_type': 'footage'}


def offer(scripts):
    return film.fonts_for('restrained', scripts)


# ---------- the labels ----------

def test_a_film_with_no_drawn_graphic_has_no_sample_and_is_not_asked():
    out = FS.sample(offer(set()), set(), plan(FOOTAGE), None, render=lambda html: pytest.fail('nothing is drawn'))
    assert out == {'available': False, 'asked': False, 'message': FS.NOT_ASKED}
    assert FS.sample(offer(set()), set(), None, None, render=lambda html: b'')['asked'] is False   # no plan yet


def test_the_labels_come_from_the_drawn_shots_then_their_specs_and_the_neutral_words_otherwise():
    labels = FS.drawn_labels(plan(FOOTAGE, DRAWN))
    assert labels == ['Inlet pipe', 'நீர் உள்ளே', 'Tank lid']
    assert FS.label_for(labels, 'latin') == 'Inlet pipe' and FS.label_for(labels, 'tamil') == 'நீர் உள்ளே'
    assert FS.label_for(labels, 'devanagari') == FS.NEUTRAL['devanagari']   # no Hindi label yet: the server's own words
    assert FS.label_for([], 'latin') == FS.NEUTRAL['latin']
    assert set(FS.NEUTRAL) == set(film.SCRIPT_NAMES)   # every language the offer supports has a neutral label
    for script, words in FS.NEUTRAL.items():
        assert film.scripts_of(words) == {script}, script


def test_a_film_with_one_language_has_two_lines_per_font():
    rows = FS.rows(offer(set()), set(), FS.drawn_labels(plan(DRAWN)))
    assert [r['name'] for r in rows] == [f['name'] for f in offer(set())]
    for r in rows:
        assert [ln['text'] for ln in r['lines']] == [r['name'], 'Inlet pipe', FS.NUMBERS] and not r['missing']


def test_a_film_with_two_languages_draws_its_other_language_where_the_font_holds_it_else_english_only():
    tamil = {'latin', 'tamil'}
    rows = FS.rows(offer(tamil), tamil, FS.drawn_labels(plan(DRAWN)))
    assert rows and all(r['lines'][-1]['text'] == 'நீர் உள்ளே' for r in rows)   # the offer holds only fonts with Tamil letters
    inter = [f for f in offer(set()) if f['name'] == 'Inter']   # a font the offer says has no Tamil (as the offer of an English film lists it)
    row = FS.rows(inter, tamil, [])[0]
    assert [ln['text'] for ln in row['lines']] == ['Inter', FS.NEUTRAL['latin'], FS.NUMBERS, 'English only']


def test_a_long_label_is_shortened_at_a_word_with_an_ellipsis_never_cut_mid_word():
    long = 'The overflow pipe that carries the extra water from the top tank down to the garden drain'
    short = FS.shorten(long)
    assert short.endswith('…') and len(short) <= FS.MAX_LABEL + 1
    assert long.startswith(short[:-1].rstrip()) and long[len(short[:-1].rstrip())] == ' '   # ends at a whole word
    assert FS.shorten('Tank lid') == 'Tank lid'
    one = 'x' * 80
    assert FS.shorten(one) == 'x' * FS.MAX_LABEL + '…'   # one word longer than the row: cut, with the ellipsis
    row = FS.rows(offer(set())[:1], set(), [long])[0]
    assert row['lines'][1]['text'] == short


def test_a_font_the_server_lacks_says_so_and_the_others_are_drawn(monkeypatch):
    real = FS._have
    monkeypatch.setattr(FS, '_have', lambda file: file != 'Mukta-Regular.ttf' and real(file))
    rows = FS.rows(offer(set()), set(), [])
    mukta = next(r for r in rows if r['name'] == 'Mukta')
    assert mukta['missing'] and [ln['text'] for ln in mukta['lines']] == ['Mukta', FS.NOT_INSTALLED]
    assert all(not r['missing'] for r in rows if r['name'] != 'Mukta')
    html = FS.page(rows, '#FFFFFF', '#1A1A1A')
    assert 'Mukta-Bold.ttf' not in html and FS.NOT_INSTALLED in html and 'Inter-opsz-wght.ttf' in html


def test_other_is_never_drawn():
    rows = FS.rows([*offer(set())[:2], {'name': 'Other', 'languages': ['English']}], set(), [])
    assert [r['name'] for r in rows] == [f['name'] for f in offer(set())[:2]]


def test_the_page_uses_the_servers_font_files_and_the_films_colours():
    tamil = {'latin', 'tamil'}
    rows = FS.rows(offer(tamil)[:2], tamil, [])
    html = FS.page(rows, *FS.colours_of('navy and orange'))
    for r in rows:
        for face in film.font_faces(r['name'], tamil):
            assert (FS.FONTS / face['file']).as_uri() in html
    assert 'background:#000080' in html and 'color:#FFA500' in html
    assert FS.colours_of('#F5F0E6, #12324A') == ('#F5F0E6', '#12324A')
    assert FS.colours_of('no preference') == FS.colours_of(None) == (FS.BACKGROUND, FS.TEXT)
    assert FS.colours_of('white and yellow') == ('#FFFFFF', '#1A1A1A')   # yellow cannot be read on white: the readable dark instead
    assert '<script' not in html


def test_a_sample_that_cannot_be_made_says_one_line_and_never_blocks():
    def broken(html):
        raise RuntimeError('chromium did not start')
    out = FS.sample(offer(set()), set(), plan(DRAWN), None, render=broken)
    assert out['available'] is False and out['asked'] is True and out['message'] == FS.NOT_AVAILABLE == 'The font sample is not available.'
    out = FS.sample([], set(), plan(DRAWN), None, render=lambda html: b'png')
    assert out['available'] is False and out['message'] == FS.NOT_AVAILABLE   # nothing to draw


def test_the_question_and_the_command_say_to_show_the_sample_first():
    from app import visuals_stage as V
    with pytest.raises(ValueError) as e:
        V.need_font({'film': {}}, {})
    said = str(e.value)
    assert '`vw font --sample`' in said and FS.NOT_AVAILABLE in said and 'Other' in said
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert '/film/font-sample"' in vw and "add_argument('--sample'" in vw and 'font-sample.png' in vw
    main = (ROOT / 'server' / 'app' / 'main.py').read_text(encoding='utf-8')
    assert "@app.get('/api/runs/{run_id}/film/font-sample')" in main


def test_the_wording_is_in_once_retired_by_name_and_registered():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d218_wording_v3 as W
    stage = next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    part = {p['name']: p['text'] for p in stage['parts']}
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    for where, old, new in W.PAIRS:
        text = stage['prompt'] if where == 'common' else part[where]
        assert text.count(new) == 1, old[:60]
        was = before['prompt'] if where == 'common' else next(p['text'] for p in before['parts'] if p['name'] == where)
        assert was.count(old) == 1, old[:60]
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    everything = stage['prompt'] + ''.join(part.values())
    assert all(s in retired and s not in everything for s in W.RETIRED)
    cmd = (ROOT / 'plugin' / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert all(new in cmd for _, new in W.COMMANDS) and '`vw font --sample`' in cmd
    assert FS.NOT_AVAILABLE in part['later'] and 'Step 6, the pictures and drawn graphics, is answered on the page too' in stage['prompt']
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d217(prompt, parts)') < split.index('d218(prompt, parts)')


def test_the_cards_fonts_come_first_under_their_heading_then_the_others():
    rows = FS.rows(offer(set()), set(), [])
    assert len(rows) > FS.CARD + 10   # an English film: every font fits
    html = FS.page(rows, '#FFFFFF', '#1A1A1A')
    card, others = html.index(FS.ON_CARD), html.index(FS.OTHERS)
    assert FS.ON_CARD == 'On the card' and FS.OTHERS == 'Others you can name' and card < others
    names = [f['name'] for f in offer(set())]
    for n in names[:FS.CARD]:
        assert card < html.index(f'>{n}<') < others, n   # the card's fonts are the offer's first, in its order
    for n in names[FS.CARD:]:
        assert html.index(f'>{n}<') > others, n
    assert 'class="cols"' in html   # more than ten others: two columns
    few = FS.page(rows[:FS.CARD + 3], '#FFFFFF', '#1A1A1A')
    assert FS.OTHERS in few and 'class="cols"' not in few
    assert FS.OTHERS not in FS.page(rows[:FS.CARD], '#FFFFFF', '#1A1A1A')
    out = FS.sample(offer(set()), set(), plan(DRAWN), None, render=lambda html: b'PNG')
    assert out['on_card'] == names[:FS.CARD]
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "out.get('on_card')" in vw


def test_the_route_gives_the_picture_as_base64_json_and_never_raises(monkeypatch):
    import base64
    from app import main as M
    monkeypatch.setattr(M.core, 'load_run', lambda conn, user, rid: {'id': 'r1', 'film': {}})
    monkeypatch.setattr(M.core, 'current_outputs', lambda conn, rid: [])
    monkeypatch.setattr(M, '_font_offer', lambda conn, run, outputs: (set(), [], offer(set())[:2]))
    monkeypatch.setattr(M.visuals_stage, 'session_of', lambda *a, **k: {})
    monkeypatch.setattr(M.visuals_stage, 'current_plan', lambda store, s: plan(DRAWN))
    monkeypatch.setattr(M, 'storage', lambda: None)
    monkeypatch.setattr(FS, 'render', lambda html: b'PNG')
    monkeypatch.setattr(FS.sample, '__defaults__', (FS.render,))
    body = json.loads(M.get_font_sample('r1', None, None).body)
    assert base64.b64decode(body['base64']) == b'PNG' and body['file'] == 'font-sample.png' and 'png' not in body and body['fonts'] == [f['name'] for f in offer(set())[:2]]
    monkeypatch.setattr(M.visuals_stage, 'current_plan', lambda store, s: (_ for _ in ()).throw(ValueError('Propose a visual plan first.')))
    body = json.loads(M.get_font_sample('r1', None, None).body)
    assert body['available'] is False and body['message'] == FS.NOT_ASKED


def test_the_versions():
    from app.config import Settings
    assert Settings.model_fields['SERVER_VERSION'].default == '0.116.0' and Settings.model_fields['PLUGIN_MIN_VERSION'].default == '0.100.0'
    assert json.loads((ROOT / 'plugin' / '.claude-plugin' / 'plugin.json').read_text(encoding='utf-8'))['version'] == '0.100.0'


@pytest.mark.skipif(not CHROMIUM, reason='Playwright Chromium is not installed on this machine (playwright install chromium)')
def test_the_sample_is_drawn_by_chromium_with_the_repos_fonts():
    tamil = {'latin', 'tamil'}
    out = FS.sample(offer(tamil)[:3], tamil, plan(DRAWN), 'navy and orange')
    assert out['available'] is True and [r['name'] for r in out['rows']] == [f['name'] for f in offer(tamil)[:3]]
    img = Image.open(BytesIO(out['png']))
    assert img.size[0] == FS.WIDTH and img.size[1] > 300
    assert img.convert('RGB').getpixel((2, 2)) == (0, 0, 128)   # the film's background
