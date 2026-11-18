"""design/213's page check of step 1 (the things layout, design/212), kept when its sets screen was replaced (design/216): a person the footage
shows is asked the permission only (`#tlikeness`), and the writer's added words are said openly (`#tdiffers`). Restored from
test_design213_browser_pure at the critic's word, 18 Nov 2026. Skipped where Playwright or its browser is not installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser, gone, saved, show   # noqa: F401 (`browser` is the fixture)
from test_design216_browser_pure import clean


def test_step_1_asks_the_permission_of_a_person_the_footage_shows_and_says_the_writers_words(monkeypatch, browser):
    """design/213, on the screen of step 1: the one question of a person whose kept footage picture shows the face, its two answers, the
    words box of the permission, what each answer will do in the server's own sentence; and the writer's added words, said openly."""
    from test_design212_browser_pure import doc as doc1, thing
    from test_design213_layout_pure import person_film
    film, _said = person_film(monkeypatch)
    film.change(lambda s: s['round']['elements']['TROWEL'].update(prompt='The look from the footage, the place from the plan.'))
    page = film.page()
    by = {l['key']: l for l in page['lines']}
    mason, permit, standin = by['ref:MASON'], by['ref:MASON']['buttons'][0], by['ref:MASON']['buttons'][1]
    pg = show(browser, doc1(page))
    pg.locator('#tauto').uncheck()
    thing(pg, mason['name'])
    assert pg.locator('#tlikeness').text_content() == mason['likeness']['ask'] and pg.locator('#tlikeness').is_visible()
    pg.wait_for_function("![...document.querySelectorAll('#tmain .tbar button')].some(b => b.disabled)")
    assert [' '.join(x.split()) for x in pg.locator('#tmain .tbar button').all_text_contents()] == [permit['label'], standin['label'], mason['own']['label']]
    pg.locator('#tmain [data-act="permit"]').click()
    assert pg.locator('#tpanel label').text_content() == permit['hint']
    pg.locator('#tfixsend').click()
    assert mason['line'] not in answers(pg) and pg.locator('#tmsg').text_content() == permit['hint']              # their own words are required
    pg.locator('#tfix').fill('He agreed on site.')
    pg.locator('#tfixsend').click()
    assert saved(pg, mason['line'], 'permit')['notes'] == 'He agreed on site.'
    assert pg.locator('#tanswer p').text_content() == 'Your answer: ' + permit['say'].replace('{words}', 'He agreed on site.').replace('{pictures}', '1 ticked picture')   # design/213 review: which pictures go
    pg.locator('#tundo').click()
    gone(pg, mason['line'])
    pg.locator('#tmain [data-act="standin"]').click()
    saved(pg, mason['line'], 'standin')
    assert pg.locator('#tanswer p').text_content() == 'Your answer: ' + standin['say'] and 'will differ from the person in your clips' in standin['say']
    thing(pg, by['ref:TROWEL']['name'])
    assert pg.locator('#tdiffers').is_visible() and pg.locator('#tdiffers').text_content() == by['ref:TROWEL']['differs']
    clean(pg)
    pg.close()
