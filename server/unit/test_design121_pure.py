"""design/121, SK's review of the visuals stage (29 Oct 2026): change 1 every searched thing ends with an answer, change 3 an action's target is on the list,
change 4 the operator's notes reach the sheet and its check, change 5 a stock search beside the plain one and the watermark line, change 6 a search per thing
on pass 1 with the pictures downloaded at once and Done running none."""
import io
import json
from fractions import Fraction
from pathlib import Path

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_design91_b1_pure import rest, subject, video
from test_design119_d_pure import sheet_store
from test_design111_f11_pure import image, put
from test_visuals_pure import GAPS as PGAPS, plan
from test_visuals_stage_pure import RUN, USER, g, plan_doc, ref, saved, session, shot, store_with

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (64, 48), (200, 80, 40)).save(buf, 'PNG')
    return buf.getvalue()


def rows(tag, n=3):
    return [{'n': i, 'thumbnail': f'https://t/{tag}{i}.jpg', 'image_url': f'https://i/{tag}{i}.jpg', 'page_url': 'https://p', 'site': 's', 'width': 8, 'height': 6, 'title': tag}
            for i in range(1, n + 1)]


def round_store(frames=False):
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [shot('VS1', 900, 1150, 'video')])
    doc['elements'] = [{'id': 'E1', 'name': 'Brick', 'kind': 'object', 'identity': 'representative', 'requirements': 'a red brick'},
                       {'id': 'E2', 'name': 'Yard', 'kind': 'place', 'identity': 'representative', 'requirements': 'a brick yard'}]
    refs = {'F2': {**ref('F2', 'candidate'), 'kind': 'frame', 'element_id': 'E2'}} if frames else {}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', references=refs)
    store = store_with(sess, doc)
    VS.round_start(store, USER, RUN, [], [{'element_id': 'E1', 'keywords': 'red clay brick India'}, {'element_id': 'E2', 'keywords': 'brick yard Tamil Nadu'}])
    return store


@pytest.fixture
def web(monkeypatch):
    """Apify and the picture downloads faked: every query and every download is recorded."""
    log = {'queries': [], 'downloads': []}
    monkeypatch.setattr(VS.apify, 'search_images', lambda kw, n=10: log['queries'].append(kw) or rows('s' if 'depositphotos' in kw else 'p'))
    monkeypatch.setattr(VS, 'fetch_image', lambda url: log['downloads'].append(url) or png())
    return log


def searched(store, eid, kw='red clay brick India', source='depositphotos'):
    found = VS.search_rows(store, RUN, kw, source)
    return VS.search(store, USER, RUN, [], eid, kw, '', source=source, found=found)


# ---------- change 5: two searches, the source outside the six words ----------

def test_the_source_word_adds_a_stock_search_and_does_not_count_in_the_six_words(web):
    store = round_store()
    VS.search_rows(store, RUN, 'red clay brick kiln worker India', 'depositphotos')
    assert web['queries'] == ['red clay brick kiln worker India', 'red clay brick kiln worker India depositphotos']
    web['queries'].clear()
    VS.search_rows(store, RUN, 'red clay brick', '')
    assert web['queries'] == ['red clay brick']                                    # an empty source box: the plain search alone
    with pytest.raises(Problem, match='two to six words'):
        g(lambda: VS.search(store, USER, RUN, [], 'E1', 'brick', '', source='depositphotos', found={}))


def test_a_search_in_the_round_keeps_both_searches_on_the_things_row(web):
    store = round_store()
    out = searched(store, 'E1')
    row = saved(store)['round']['elements']['E1']
    assert len(row['search_ids']) == 2 and row['search_id'] == row['search_ids'][0] == out['search_id'] and row['source'] == 'depositphotos'
    stock = saved(store)['searches'][row['search_ids'][1]]
    assert stock['source'] == 'depositphotos' and stock['keywords'] == 'red clay brick India' and stock['results'][0]['title'] == 's'


# ---------- change 6: every picture downloaded at the search; Save uses the stored file ----------

def test_the_search_downloads_every_picture_and_save_uses_the_stored_file(web, monkeypatch):
    store = round_store()
    searched(store, 'E1')
    assert len(web['downloads']) == 6                                              # 3 + 3 pictures, once each
    sid = saved(store)['round']['elements']['E1']['search_ids'][1]
    assert all(r['download'] == 'picture' for r in saved(store)['searches'][sid]['results'])
    monkeypatch.setattr(VS, 'fetch_image', lambda url: pytest.fail('downloaded again at Save'))
    out = VS.pick(store, USER, RUN, [], sid, [{'n': 2, 'note': 'colour only'}], '')
    assert out['references'] and out['references'][0]['source']['note'] == 'colour only'


def test_a_picture_that_will_not_download_is_marked_before_it_is_ticked(web, monkeypatch):
    def fetch(url):
        if url in ('https://i/p2.jpg', 'https://i/p3.jpg', 'https://t/p3.jpg'):
            raise ValueError('HTTP 403 from i')
        return png()
    monkeypatch.setattr(VS, 'fetch_image', fetch)
    store = round_store()
    searched(store, 'E1', source='')
    res = saved(store)['searches'][saved(store)['round']['elements']['E1']['search_id']]['results']
    assert [r['download'] for r in res[:2]] == ['picture', 'thumbnail'] and res[2]['download'].startswith('failed: ') and '403' in res[2]['download']


# ---------- change 6: Done on pass 1 runs no search and waits for every Search button ----------

def test_done_on_pass_1_waits_for_every_thing_set_to_google_and_runs_no_search(web, monkeypatch):
    store = round_store(frames=True)
    with pytest.raises(Problem, match=r'not searched yet: E1'):
        g(lambda: VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'search'}, 'E2': {'verdict': 'approve'}}, ''))
    searched(store, 'E1')
    monkeypatch.setattr(VS.apify, 'search_images', lambda *a, **k: pytest.fail('Done searched'))
    out = VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'search'}, 'E2': {'verdict': 'approve'}}, '')
    assert out['pass'] == 2 and out['searched'] == ['E1'] and saved(store)['references']['F2']['status'] == 'approved'


def test_ignore_this_on_pass_1_needs_no_search_and_a_round_of_ignores_completes():
    store = round_store()
    out = VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'ignore'}, 'E2': {'verdict': 'ignore'}}, '')
    assert out['pass'] == 'complete' and saved(store)['round']['elements']['E1']['ignored'] is True


def test_a_failed_search_is_recorded_on_the_row_and_the_thing_still_waits(monkeypatch):
    def down(kw, n=10):
        raise Problem(502, 'SEARCH', 'Apify answered HTTP 500 to the image search.')
    monkeypatch.setattr(VS.apify, 'search_images', down)
    store = round_store()
    found = VS.search_rows(store, RUN, 'red clay brick India', 'depositphotos')
    with pytest.raises(Problem, match='HTTP 500'):
        g(lambda: VS.search(store, USER, RUN, [], 'E1', 'red clay brick India', '', source='depositphotos', found=found))
    assert 'HTTP 500' in saved(store)['round']['elements']['E1']['error']
    with pytest.raises(Problem, match='not searched yet: E1'):
        g(lambda: VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'search'}, 'E2': {'verdict': 'ignore'}}, ''))


# ---------- change 1: pass 2 waits until every searched thing has a tick, a saved pick or Ignore this ----------

def pass2(web):
    store = round_store()
    searched(store, 'E1')
    searched(store, 'E2', kw='brick yard Tamil Nadu')
    VS.round_done(store, USER, RUN, [], {'E1': {'verdict': 'search'}, 'E2': {'verdict': 'search'}}, '')
    return store


def test_pass_2_is_refused_while_a_searched_thing_has_no_answer(web):
    store = pass2(web)
    e1 = saved(store)['round']['elements']['E1']['search_ids']
    with pytest.raises(Problem, match=r'still need an answer: E2'):
        g(lambda: VS.round_picks(store, USER, RUN, [], {e1[0]: [{'n': 1}]}, ''))
    assert saved(store)['round']['pass'] == 2


def test_a_tick_from_the_stock_search_and_ignore_this_complete_pass_2(web):
    store = pass2(web)
    stock = saved(store)['round']['elements']['E1']['search_ids'][1]
    out = VS.round_picks(store, USER, RUN, [], {stock: [{'n': 1, 'note': 'the colour'}]}, '', ignore=['E2'])
    rd = saved(store)['round']
    assert out['complete'] is True and rd['pass'] == 'complete' and rd['elements']['E2']['ignored'] is True and rd['elements']['E1']['ignored'] is False


def test_search_again_on_pass_2_replaces_the_things_searches_and_its_ticks_count(web):
    store = pass2(web)
    old = saved(store)['round']['elements']['E1']['search_ids']
    searched(store, 'E1', kw='wire cut brick Chennai')
    new = saved(store)['round']['elements']['E1']['search_ids']
    assert set(new).isdisjoint(old) and saved(store)['round']['pass'] == 2
    out = VS.round_picks(store, USER, RUN, [], {new[0]: [{'n': 3}]}, '', ignore=['E2'])
    assert out['complete'] is True


def test_undo_from_pass_2_still_works_with_two_searches_per_thing(web):
    store = pass2(web)
    assert VS.round_undo(store, USER, RUN, [], '')['pass'] == 1


# ---------- change 4: the notes reach the sheet's prompt and its check; a late note marks the sheet ----------

def test_the_sheet_carries_each_notes_line_and_a_must_line_per_note():
    store = sheet_store()
    s = saved(store)
    s['references']['W3']['source'] = {'note': 'use this brick colour, ignore the wall'}
    put(store, s)
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'],
                prompt='Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.')
    r = saved(store)['references'][out['reference_id']]
    assert "The operator's note on Image 1: use this brick colour, ignore the wall." in r['generation']['prompt'] and 'note on Image 2' not in r['generation']['prompt']
    line = next(l for l in r['server_checklist'] if l['check'] == 'operator note on Image 1')
    assert line['weight'] == 'must' and 'use this brick colour, ignore the wall' in line['pass_when']


def test_a_note_after_the_sheet_is_saved_and_marks_the_sheet_sources_changed():
    store = sheet_store()
    s = saved(store)
    s['references']['SH3'] = {**ref('SH3', 'approved'), 'kind': 'sheet', 'element_id': 'E3', 'generation': {'op': 'edit', 'parents': [{'id': 'W3'}]}}
    put(store, s)
    out = VS.note_reference(store, USER, RUN, [], 'W3', 'keep the handle short')
    assert saved(store)['references']['W3']['source']['note'] == 'keep the handle short' and saved(store)['references']['SH3']['sources_changed'] is True
    assert 'sources changed' in out['next']


# ---------- change 5: a web picture's watermark is never copied ----------

def test_a_web_parent_gets_the_watermark_line_and_the_check_a_must_line():
    store = sheet_store()
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'],
                prompt='Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.')
    r = saved(store)['references'][out['reference_id']]
    assert "Image 1 may carry a watermark or a stock site's lettering: ignore it, never copy it." in r['generation']['prompt'] and 'Image 2 may carry' not in r['generation']['prompt']
    assert any(l['check'] == 'no watermark' and l['weight'] == 'must' for l in r['server_checklist'])


def test_no_web_parent_no_watermark_line():
    store = sheet_store()
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['U3'], prompt='Image 1 is the supplied picture: take its binding.')
    r = saved(store)['references'][out['reference_id']]
    assert 'watermark' not in r['generation']['prompt'] and not any(l['check'] == 'no watermark' for l in r['server_checklist'])


# ---------- change 3: what an action heads for is a landmark or a thing of the shot ----------

def with_target(target, element_ids=('E1',)):
    sub = subject((0, 100, 3), (100, 200, 3))
    for b in sub['beats']:
        b['target'] = target
    doc = plan([video('VS1', 0, 200, [], changes=[{'what': 'two bricks laid', 'beat_id': 'B1'}]) | {'subjects': [sub], 'element_ids': list(element_ids)}] + rest())
    doc['elements'].append({'id': 'E9', 'name': 'Cement mixer', 'kind': 'object', 'identity': 'representative', 'requirements': 'a drum mixer'})
    return doc


def test_an_actions_target_is_a_landmark_or_a_thing_listed_in_the_shot():
    VC.validate_plan(with_target('L1'), PGAPS, Fraction(25))                       # the table, a landmark of the scene
    VC.validate_plan(with_target('E9', ('E1', 'E9')), PGAPS, Fraction(25))         # the mixer, listed in the shot
    with pytest.raises(ValueError, match="'the cement mixer' is neither"):
        VC.validate_plan(with_target('the cement mixer'), PGAPS, Fraction(25))
    with pytest.raises(ValueError, match='not in the shot'):
        VC.validate_plan(with_target('E9'), PGAPS, Fraction(25))                   # on the list, but not in this shot: it would miss the start picture


# ---------- the page ----------

def test_the_page_has_a_search_per_thing_a_source_box_ignore_this_and_no_false_promise():
    assert 'data-a="round-search"' in PAGE and 'class="src"' in PAGE and 'value="ignore"' in PAGE and 'data-a="ignore"' in PAGE
    assert 'the assistant searches again' not in PAGE
    assert 'still need an answer' in PAGE and 'not searched yet' in PAGE
