"""SK, 15 Nov 2026 (VW-23 review): scrolling the review page cut the top of the film, because the film stuck 64px from the top while the page's own
top block is taller. The film and the rows now keep clear of the top block and the footer at their measured heights."""
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')


def test_the_film_sticks_below_the_top_block_at_its_measured_height():
    assert '.rv .left{position:sticky;top:calc(var(--top-h) + 10px)}' in PAGE and 'top:64px' not in PAGE
    assert "setProperty('--top-h',a.querySelector('.top').offsetHeight+'px')" in PAGE and "setProperty('--foot-h',a.querySelector('.foot').offsetHeight+'px')" in PAGE
    assert 'calc(100vh - var(--top-h) - var(--foot-h) - 140px)' in PAGE   # the film never grows past the space between the two


def test_the_height_is_measured_again_whenever_it_can_change():
    for needle in ("$('line').innerHTML=line;fit();", 'draw();fit();', "addEventListener('toggle',fit,true)", "window.addEventListener('resize',fit)", 'new ResizeObserver(fit)'):
        assert needle in PAGE, needle


def test_a_row_brought_into_view_stays_clear_of_the_top_block_and_the_footer():
    assert '.rv .row,.rv .head{scroll-margin-top:calc(var(--top-h) + 10px);scroll-margin-bottom:calc(var(--foot-h) + 10px)}' in PAGE
