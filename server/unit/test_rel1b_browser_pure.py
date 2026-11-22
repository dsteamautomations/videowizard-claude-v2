"""Release 1, B1 and B3 (SK, 20 Nov 2026), the page checks: `plugin/pages/decisions.html` in a headless browser with the frozen rounds of
steps 6 and 7 (rounds as the 0.118.0 server writes them) and with the same rounds as this server writes them (`as_now`).

B3: the check box is closed and shows one short line (green "Passed", "Passed, 1 note"; amber "N warnings: <name>"; or why it was not
checked); the line is a button with aria-expanded; a click, or Enter, opens the rest (the notes or warnings in full, the folded list of
the lines that did not apply, who checked); what is opened is remembered for that item only. The same box for a still, a graphic in
steps, a drawn graphic and an AI video take. A round of the older server (no `short`) shows its head on the closed line.
B1: "Yes, put it in the film" and "Select" record at once on a thing whose check has warnings: no second box, no typed reason; the answer
is marked "(Against the check)". A round of the older server keeps the box it was written with.
The fit: page areas of 1536 x 510 and 1900 x 830, light and dark, the box open: no scroll of the page or the main area, the buttons in view.
Skipped where Playwright or its browser is not installed."""
import pytest

pytest.importorskip('playwright.sync_api')

from test_design212_browser_pure import answers, browser   # noqa: F401 (`browser` is the fixture)
import test_design217_browser_pure as B6
import test_design222_browser_pure as B7

NA = {'head': '2 lines did not apply', 'lines': ['wear: A drawn graphic has no worn surface.', 'practitioner: No person is in this view.']}
SHORT6 = {'l02': 'Passed', 'l03': 'Passed', 'l04': '4 warnings: the start state', 'l05': '1 warning: step 3, exact text', 'l06': 'Passed', 'l07': '2 warnings: a rule', 'l08': None}


def now6(lines, d):
    """The round of step 6 as this server writes it: every check with its short line; no second box; Select with no typed reason."""
    for key, l in lines.items():
        c = l.get('check')
        if c:
            c['short'] = SHORT6[key] or c['head']
        for b in l['buttons']:
            if b.pop('sure', None):
                b['against'] = True
            if b['choice'] == 'select' and b.get('needs_words'):
                b.update(needs_words=False, against=True, say='Selected. It goes in the film at 2:10.4.')
                for k in ('hint', 'go', 'need', 'prefill'):
                    b.pop(k, None)
    lines['l04']['check']['na'] = NA
    lines['l06']['check'].update(short='Passed, 1 note', notes=['The shadow could be softer.'])
    lines['l07']['held'] = 'Its fact check did not pass. Select uses it all the same.'


def now7(lines, d):
    """The round of step 7 as this server writes it."""
    for l in lines.values():
        for t in l['takes']:
            c = t['check']
            c['short'] = 'Passed' if c['state'] == 'pass' else f"{len(c['faults'])} warning{'' if len(c['faults']) == 1 else 's'}: {c['faults'][0]['text'].split(': ')[0]}" if c['state'] == 'fail' else c['head']
        for b in l['buttons']:
            if b['act'] == 'select':
                bad = next(t for t in l['takes'] if t['n'] == b['take'])['check']['state'] != 'pass'
                b.update(needs_words=False, hint='', go='', need='', say=b['say'].split(' Your reason')[0], **({'against': True} if bad else {}))
    lines['l01']['takes'][1]['check']['na'] = NA


def box(pg):
    return pg.evaluate("""(() => { const c = document.querySelector('#pcheck'), b = c.querySelector('#pcheckb'), x = c.querySelector('#pcheckx');
        return {state: c.dataset.state, cls: c.className, line: (c.querySelector('b') || {}).textContent, button: !!b, open: b ? b.getAttribute('aria-expanded') : null,
                controls: b ? b.getAttribute('aria-controls') : null, more: x ? x.innerText : null, items: [...c.querySelectorAll('#pcheckx li')].map(e => e.textContent)}; })()""")


def quiet(pg):
    return pg.evaluate("(() => { const m = document.querySelector('#smain'), d = document.documentElement; return m.scrollHeight <= m.clientHeight + 1 && d.scrollHeight <= innerHeight + 1 && d.scrollWidth <= innerWidth; })()")


# ---------- B3, step 6 ----------

def test_the_check_box_of_step_6_is_closed_with_one_short_line_and_a_click_opens_the_rest(browser):
    pg = B6.page(browser, B6.doc(now6))
    B6.go(pg, B6.BUILDING)
    b = box(pg)
    assert b['line'] == 'Passed' and b['open'] == 'false' and b['more'] is None and 'bad' not in b['cls'] and b['controls'] == 'pcheckx'   # green, closed, a button
    assert B6.BUILDING['check']['by'] not in pg.locator('#pcheck').inner_text()
    B6.go(pg, B6.KILN)
    c, b = B6.KILN['check'], box(pg)
    assert b['line'] == '4 warnings: the start state' and 'bad' in b['cls'] and b['state'] == 'fail' and b['open'] == 'false' and b['items'] == []   # amber, one line, never hidden
    assert c['faults'][1] not in pg.locator('#pcheck').inner_text()
    pg.locator('#pcheckb').click()
    b = box(pg)
    assert b['open'] == 'true' and b['items'][:4] == c['faults'] and c['by'] in b['more']                    # the warnings in full, who checked and against how many lines
    assert pg.locator('#pna summary').text_content() == NA['head'] and not pg.locator('#pna').evaluate('e => e.open')   # the lines that did not apply: folded
    pg.locator('#pna summary').click()
    assert pg.locator('#pna li').all_text_contents() == NA['lines']
    B6.go(pg, B6.BUILDING)
    assert box(pg)['open'] == 'false'                                                                         # opened for that item only
    B6.go(pg, B6.KILN)
    assert box(pg)['open'] == 'true'                                                                          # and remembered for it
    pg.locator('#pcheckb').click()
    assert box(pg)['open'] == 'false' and box(pg)['more'] is None and pg.errors == []
    pg.close()


def test_the_same_box_for_a_graphic_in_steps_a_drawn_graphic_with_notes_and_a_picture_not_checked(browser):
    pg = B6.page(browser, B6.doc(now6))
    B6.go(pg, B6.STEPS)
    assert box(pg)['line'] == '1 warning: step 3, exact text' and 'bad' in box(pg)['cls']
    B6.go(pg, B6.CAVITIES)
    b = box(pg)
    assert b['line'] == 'Passed, 1 note' and 'bad' not in b['cls'] and 'doubt' not in b['cls'] and b['open'] == 'false'
    pg.locator('#pcheckb').focus()
    pg.keyboard.press('Enter')                                                                                # the line is a button: the keyboard opens it
    b = box(pg)
    assert b['open'] == 'true' and pg.locator('#pnotes li').all_text_contents() == ['The shadow could be softer.'] and B6.CAVITIES['check']['head'] in b['more'] and B6.CAVITIES['check']['by'] in b['more']
    assert pg.evaluate('document.activeElement.id') == 'pcheckb'                                             # the focus stays on the line after it opens
    B6.go(pg, B6.WALL)
    b = box(pg)
    assert b['line'] == '2 warnings: a rule' and b['open'] == 'false'
    pg.locator('#pcheckb').click()
    assert box(pg)['items'] == B6.WALL['check']['faults']                                                     # a drawn graphic's open rules in full, one click away
    B6.go(pg, B6.HOUSING)
    b = box(pg)
    assert b['state'] == 'not_checked' and b['line'] == B6.HOUSING['check']['head'] and 'doubt' in b['cls'] and not b['button']   # the sentence that says why; nothing more to open
    assert pg.errors == []
    pg.close()


def test_a_round_of_the_older_server_shows_its_head_on_the_closed_line_and_opens_the_same_way(browser):
    pg = B6.page(browser)                                                                                     # the frozen round of 0.118.0: no `short`
    B6.go(pg, B6.KILN)
    c, b = B6.KILN['check'], box(pg)
    assert b['line'] == c['head'] and b['open'] == 'false' and 'bad' in b['cls']
    pg.locator('#pcheckb').click()
    assert box(pg)['items'] == c['faults'] and pg.errors == []
    pg.close()


# ---------- B1, step 6 ----------

def test_yes_on_a_still_with_warnings_records_at_once_with_no_second_box(browser):
    pg = B6.page(browser, B6.doc(now6))
    B6.go(pg, B6.KILN)
    assert 'bad' in box(pg)['cls'] and pg.locator('#pcheck').bounding_box()['y'] < pg.locator('#pbar').bounding_box()['y']   # the warning is in view above the buttons
    pg.locator('#pbar [data-choice="yes"]').click()
    assert B6.saved(pg, 'l04', 'yes')['notes'] == '' and pg.locator('#ssure').count() == 0 and pg.locator('#sback').count() == 0
    assert pg.locator('#sanswer').text_content().count('(' + B6.W['against'] + ')') == 1                      # said in the item's own view
    B6.go(pg, B6.STEPS)
    pg.locator('#pbar [data-choice="yes"]').click()
    assert B6.saved(pg, 'l05', 'yes') and pg.locator('#spanel').count() == 0 and pg.errors == []
    pg.close()


def test_select_on_a_drawn_graphic_whose_check_did_not_pass_records_at_once_and_says_why_above_the_buttons(browser):
    pg = B6.page(browser, B6.doc(now6))
    B6.go(pg, B6.WALL)
    held = pg.locator('#pheld')
    assert held.text_content() == 'Its fact check did not pass. Select uses it all the same.' and held.bounding_box()['y'] < pg.locator('#pbar').bounding_box()['y']
    pg.locator('#pbar [data-choice="select"]').click()
    assert B6.saved(pg, 'l07', 'select')['notes'] == '' and pg.locator('#sfix').count() == 0                  # no typed reason
    assert '(' + B6.W['against'] + ')' in pg.locator('#sanswer').text_content()
    pg.locator('#sundo').click()
    pg.locator('#pbar [data-choice="reject"]').click()
    assert pg.locator('#sfix').count() == 1 and 'l07' not in answers(pg)                                      # rejecting still needs words
    assert pg.errors == []
    pg.close()


def test_a_round_of_the_older_server_keeps_the_second_box_it_was_written_with(browser):
    pg = B6.page(browser)
    B6.go(pg, B6.KILN)
    pg.locator('#pbar [data-choice="yes"]').click()
    assert pg.locator('#ssure').count() == 1 and answers(pg) == {}
    pg.locator('#ssure').click()
    assert B6.saved(pg, 'l04', 'yes') and '(' + B6.W['against'] + ')' in pg.locator('#sanswer').text_content() and pg.errors == []
    pg.close()


# ---------- B3 and B1, step 7 ----------


def test_a_step_7_round_of_the_older_server_shows_check_and_its_first_fault_and_keeps_its_typed_reason(browser):
    pg = B7.page(browser)
    B7.go(pg, B7.TWO)
    k, b = B7.TWO['takes'][1]['check'], box(pg)
    assert b['line'] == k['head'] + ' ' + k['faults'][0]['text'] and b['open'] == 'false'
    pg.locator('#pbar [data-choice="select"]').click()
    assert pg.locator('#sfix').count() == 1 and answers(pg) == {} and pg.errors == []                         # as that round was written
    pg.close()


# ---------- the fit ----------

@pytest.mark.parametrize('scheme', ['light', 'dark'])
@pytest.mark.parametrize('size', ['fit-small', 'fit-large'])
def test_the_box_closed_and_open_fits_both_page_areas_with_no_scroll(browser, size, scheme):
    pg = B6.page(browser, B6.doc(now6), size=size, scheme=scheme)
    for l in (B6.KILN, B6.STEPS, B6.CAVITIES, B6.WALL):
        B6.go(pg, l)
        closed = pg.locator('#pcheck').bounding_box()['height']
        assert closed <= 64, (l['name'], closed)                                                              # one short line
        for opened in (False, True):
            if opened:
                pg.locator('#pcheckb').click()
            assert quiet(pg), (l['name'], size, opened)
            B6.inside(pg, '#pcheckb')
            for i in range(pg.locator('#pbar button').count()):
                B6.inside(pg, f'#pbar button >> nth={i}')                                                     # the buttons stay in view with the box open
    pg.close()
    pg = B7.page(browser, B7.doc(now7), size=size, scheme=scheme)
    B7.go(pg, B7.TWO)
    for opened in (False, True):
        if opened:
            pg.locator('#pcheckb').click()
        assert quiet(pg), (size, opened)
        B7.inside(pg, '#pcheckb')
        for i in range(pg.locator('#pbar button').count()):
            B7.inside(pg, f'#pbar button >> nth={i}')
    assert pg.errors == []
    pg.close()
