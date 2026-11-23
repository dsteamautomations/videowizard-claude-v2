"""SK, 15 Nov 2026 (VW-24 voices page). The bottom bar covered the page and could not be closed; "narrate again" looked like a label and one click
sent a paid narration. The bar now closes to a small tab, and every button that makes a full narration looks like a button and sends on a second click."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'voices2.html').read_text(encoding='utf-8')


def test_the_bottom_bar_closes_to_a_tab_and_opens_again():
    for needle in ('<button class="x" id="foot-x" type="button" aria-label="Minimise this bar"', '<button class="foottab" id="foot-tab" type="button" hidden>',
                   '.v2 .foot.min{display:none}', '.v2.footmin .spacer{height:56px}', "function setFoot(min)", "$('foot-x').addEventListener('click',()=>setFoot(true))",
                   "$('foot-tab').addEventListener('click',()=>setFoot(false))"):
        assert needle in PAGE, needle


def test_the_bar_opens_by_itself_for_an_error_and_for_a_play_only():
    assert "if(err)setFoot(false);" in PAGE                                   # in msg(): an error is never hidden
    assert "const pl=$('pl');setFoot(false);$('player').hidden=false;" in PAGE   # in play(): the player the user asked for
    assert PAGE.count('setFoot(false)') == 3                                 # those two and the tab itself


def test_the_tab_says_what_matters():
    for needle in ("'Playing: '", "'Pick the final narration'", "'Player and actions'"):
        assert needle in PAGE, needle


def test_a_full_narration_is_sent_on_the_second_click():
    assert 'function paid(btn,run)' in PAGE and "'Confirm: send'" in PAGE and "c.textContent='Cancel'" in PAGE
    assert PAGE.count('paid(') == 4   # the helper, and its three uses: narrate again, narrate again with the final words, narrate the ticked voices
    for old in ("forEach(b=>b.addEventListener('click',async()=>{const box=b.closest('details')", "rb.addEventListener('click',async()=>{busy(rb", "if(b)b.addEventListener('click',async()=>{busy(b,'Submitting…');msg('Submitting '+chosen.length+' full narrations"):
        assert old not in PAGE, old   # no full narration is wired to a single click any more


def test_narrate_again_reads_as_a_paid_button_without_the_character_count():
    assert '<button class="tw-go paid" type="button" data-v="${esc(n.voice_id)}" disabled>Narrate again (paid)</button>' in PAGE
    assert 'This makes another full narration and is charged again.' in PAGE
    assert 'narrate again — paid, ~' not in PAGE and "again with the final words · paid, ~" not in PAGE
    assert '.v2 button.paid{' in PAGE and '.v2 button.armed,.v2 .foot .go.armed{' in PAGE   # 23 Nov 2026: every armed button turns red, also the bar's Narrate


def test_the_button_is_off_without_a_tag_and_while_a_narration_is_being_made():
    assert "box.querySelector('.tw-t').addEventListener('input'" in PAGE
    assert 'A narration is being made' in PAGE and 'function making()' in PAGE
