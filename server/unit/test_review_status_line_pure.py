"""SK, 15 Nov 2026 (VW-23 review): under the title the reviewer reads one line, large: where the review stands and what to do. The version, the
approval and the second-look record are kept, closed, behind Details; "2 fixes" read like something to approve and is now worded as what it is."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')


def test_one_status_line_for_each_state_of_the_review():
    for needle in ('Answer each shot. Your first answer approves these options.', 'The review film is not ready yet.', 'Answers closed. The master film is built.',
                   "'All '+d.of+' answered. The assistant builds the master film next.'", "esc(d.answered)+' of '+esc(d.of)+' answered.'+(wait.length?' '+left:'')"):   # 25 Nov 2026: what is left is named (below)
        assert needle in PAGE, needle
    assert '.rv .st{font-size:16px;font-weight:600' in PAGE and '<div class="st">' in PAGE


def test_an_open_defect_is_said_on_its_own_line_in_red():
    assert '<div class="st err">A defect is open on this run. Nothing can be recorded until it is fixed.</div>' in PAGE


def test_the_record_is_kept_behind_details_and_closed_by_default():
    assert 'let detOpen=false' in PAGE and "(detOpen?'':' hidden')" in PAGE and "(detOpen?'Hide details':'Details')" in PAGE
    for needle in ("'<div>Version '+esc(d.version)", 'Options approved by your first answer', 'Second look: ran ', "' · waiting: '"):
        assert needle in PAGE, needle
    assert "Version <strong>" not in PAGE and '<details>' not in PAGE


def test_a_fix_of_the_second_look_is_not_worded_as_something_to_approve():
    assert 'Changed by the second look, nothing to approve: ' in PAGE and "' fix'+" not in PAGE


# ---------- SK, 25 Nov 2026 (VW-25 issue 4, requirement R4): the missing answer is named and is a link ----------
# Older way retired: the bare "1 left" on the top line and the bare numbers after "waiting:" under Details.

def test_what_is_left_is_named_by_the_rows_own_titles_three_at_most_then_how_many_more():
    assert "const name=lab=>{const s=d.slides.find(x=>x.slide===lab);return s?s.title:'#'+lab;};" in PAGE
    assert "const names=(labs,most)=>labs.slice(0,most).map(l=>go(l,name(l))).join(', ')+(labs.length>most?' and '+(labs.length-most)+' more':'');" in PAGE
    assert "const left=wait.length+' left: '+names(wait,3);" in PAGE
    assert "(d.of-d.answered)+' left.'" not in PAGE
    assert "'Answer each shot. Your first answer approves these options.'+(wait.length?' '+left:'')" in PAGE    # a fresh page: three names and the rest counted
    assert "' · waiting: '+names(wait,wait.length)" in PAGE and "esc(d.waiting.join(', '))" not in PAGE       # under Details: the same names, every one


def test_each_name_is_a_link_that_scrolls_to_the_row_outlines_it_and_moves_the_film():
    assert "const go=(lab,text)=>'<a class=\"go\" href=\"#\" data-go=\"'+esc(lab)+'\">'+esc(text)+'</a>';" in PAGE   # a real link: Tab and Enter work
    assert "$('line').querySelectorAll('a.go').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();goTo(a.dataset.go);}));" in PAGE
    assert "el.scrollIntoView({block:'center'});seek(slide);" in PAGE                                        # the middle of the window; then the film, as a click on the row
    assert "function seek(slide){const c=cue(slide);if(!c||!filmKey)return;" in PAGE                         # no film yet: the film part is skipped


def test_the_count_and_the_red_scene_line_show_together_the_count_first_and_the_scene_is_a_link():
    assert "let line='<div class=\"st\">'+st+'<a id=\"more\"" in PAGE and "+'</a></div>'+red;" in PAGE
    assert "red='<div class=\"st err\">'+bal.slice(0,3).map(b=>go(String(b.scene),b.text)).join(' ')" in PAGE
    assert "' Fix it under the scene before the master film.</div>'" in PAGE
    assert "' scenes do not add up after a trim.'" not in PAGE                                               # retired: each scene is named
    assert "else if(d.of&&d.answered>=d.of&&!bal.length){st='All '+d.of+' answered. The assistant builds the master film next.';}" in PAGE   # never "build" while a scene does not add up
