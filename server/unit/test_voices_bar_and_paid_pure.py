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
    assert '<button class="tw-go paid" type="button" data-v="${esc(n.voice_id)}" disabled>Narrate again with this tag (paid)</button>' in PAGE
    assert "${n.behind?'Also uses the approved words (list '+esc(data.words.version)+'). ':''}One narration, charged once." in PAGE   # one call carries both
    assert 'narrate again — paid, ~' not in PAGE and "again with the final words · paid, ~" not in PAGE
    assert '.v2 button.paid{' in PAGE and '.v2 button.armed,.v2 .foot .go.armed{' in PAGE   # 23 Nov 2026: every armed button turns red, also the bar's Narrate


def test_the_button_is_off_without_a_tag_and_while_a_narration_is_being_made():
    assert "box.querySelector('.tw-t').addEventListener('input'" in PAGE
    assert 'A narration is being made' in PAGE and 'function making()' in PAGE


def test_each_narrate_again_button_says_what_one_narration_carries():
    """SK, 23 Nov: the two buttons name their action, and each says the other change travels in the same single narration."""
    assert "Narrate again with the approved words (paid)</button>" in PAGE and "Keeps this narration's sentence tags. One narration, charged once." in PAGE
    assert 'Narrate again (paid)' not in PAGE and 'charged again' not in PAGE   # older way retired: the bare label and the two "charged again" notes
    web = (Path(__file__).resolve().parents[1] / 'app' / 'web.py').read_text(encoding='utf-8')
    assert "user, run, outputs, body['voice_id'], rid, 'page', list(body.get('tweaks') or []) or None)" in web   # no tags sent: the stored ones are kept


def test_a_tag_already_in_force_names_the_words_button_when_the_words_are_newer():
    from app import voices
    plain = voices.tag_in_force('[reassuring]', False)
    assert plain == 'This sentence is already read as [reassuring]; pick a different tag. Nothing was narrated.'
    assert voices.tag_in_force('[reassuring]', True) == plain + " To get the approved words, press 'Narrate again with the approved words'."


def test_the_done_message_is_not_covered_by_the_script_box():
    """SK, 23 Nov: the open directed script sat in the sticky top and covered the Final step's box."""
    top = PAGE.split('<div class="top">', 1)[1].split('<div class="msg" id="msg">', 1)[0]
    assert top.index('</div>\n<details id="scriptbox"') > top.index('id="dir"')   # the script box follows the top bar, outside it
    assert "$('scriptbox').hidden=true;go('final');window.scrollTo(0,0);" in PAGE   # after the final: closed, and the box at the top is in view
    assert '<b class="donehere">' in PAGE and "what is next for '+esc(code)+'</code></b> <button data-copy=" in PAGE and 'copyBind(tray)' in PAGE
