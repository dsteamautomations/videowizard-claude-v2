"""design/186 (SK, 12 Nov 2026): a drawn shot may carry a finish (motion blur, film grain, a soft vignette from the HyperFrames library): a layer the
server adds, never the helper, on a drawing that is complete without it, and that the user can have taken away."""
import json

import pytest

from app import motion as M
from app import visual_workers as W

INDEX = b'<html><body><div id="root" data-composition-id="main" data-duration="4" data-fps="25" data-width="1920" data-height="1080"><div data-hf-motion-blur></div></div></body></html>'


def files(finish=None, index=INDEX):
    out = {'index.html': index}
    if finish is not None:
        out['finish.json'] = finish if isinstance(finish, bytes) else json.dumps(finish).encode()
    return out


# ---- what the helper asks for ----

def test_no_finish_file_is_no_finish():
    assert M.finish_of(files()) == ([], [])


def test_the_file_names_the_effects_as_a_list_or_under_effects():
    assert M.finish_of(files(['grain', 'blur'])) == (['blur', 'grain'], [])            # kept in the server's own order
    assert M.finish_of(files({'effects': ['vignette', 'vignette']})) == (['vignette'], [])
    assert M.finish_of(files([])) == ([], [])


@pytest.mark.parametrize('bad', [['glow'], {'effects': ['blur', 'halftone']}, {'effects': 'blur'}, 'blur', 7, b'{not json'])
def test_an_unknown_effect_or_an_unreadable_file_is_refused_naming_the_three(bad):
    effects, problems = M.finish_of(files(bad))
    assert effects == [] and len(problems) == 1 and 'blur, grain, vignette' in problems[0] and problems[0].startswith('finish.json')


def test_the_upload_check_reports_a_bad_finish_file():
    out = M.problems(files(['glow']), refs={}, fonts=[], frames=100, fps='25', width=1920, height=1080)
    assert any(p.startswith('finish.json') for p in out)
    assert not any(p.startswith('finish.json') for p in M.problems(files(['blur']), refs={}, fonts=[], frames=100, fps='25', width=1920, height=1080))


def test_blur_asked_with_nothing_marked_is_said_and_a_mark_without_blur_is_ignored():
    plain = b'<html><body><div id="root"></div></body></html>'
    assert 'nothing is marked' in M.finish_note(files(['blur', 'grain'], index=plain), ['blur', 'grain'])
    assert M.finish_note(files(['blur']), ['blur']) == ''
    assert M.finish_note(files(['grain']), ['grain']) == ''          # the mark in INDEX is simply not used


# ---- on and off ----

def test_the_finish_in_force_is_what_the_project_asks_unless_it_was_taken_off():
    assert M.finish_in_force(['blur', 'grain'], off=False) == ['blur', 'grain']
    assert M.finish_in_force(['blur', 'grain'], off=True) == []
    assert M.finish_in_force([], off=False) == []


def test_the_plain_words_for_the_user():
    assert M.finish_words(['blur', 'grain']) == ('This drawing has an added effect on top: a soft blur on the moving parts and a film grain. '
                                                 "If you don't like it, it can be taken away.")
    assert 'a film grain and a soft darkening of the corners' in M.finish_words(['grain', 'vignette'])
    assert 'a soft blur on the moving parts, a film grain and a soft darkening of the corners' in M.finish_words(['blur', 'grain', 'vignette'])
    assert M.finish_words([]) == ''


# ---- the layer, added by the server ----

def test_the_layer_goes_in_once_at_the_end_of_the_page_with_only_the_effects_asked(tmp_path):
    (tmp_path / 'index.html').write_bytes(INDEX)
    M.apply_finish(tmp_path, ['grain'])
    text = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert text.count('id="vw-finish"') == 1 and 'grain-overlay' in text and 'hf-vignette' not in text and 'data-hf-motion-blur]' not in text.split('id="vw-finish"')[1][:200]
    assert text.index('id="vw-finish"') > text.index('id="root"') and text.rstrip().endswith('</body></html>')
    M.apply_finish(tmp_path, ['grain'])                               # asked twice: still one layer
    assert (tmp_path / 'index.html').read_text(encoding='utf-8').count('id="vw-finish"') == 1


def test_the_layer_is_sized_to_the_film_and_softer_than_the_librarys_defaults(tmp_path):
    (tmp_path / 'index.html').write_bytes(INDEX)
    M.apply_finish(tmp_path, ['blur', 'grain', 'vignette'], width=1280, height=720)
    text = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert 'width:1280px;height:720px' in text
    assert 'opacity: 0.15' not in text and 'rgba(0, 0, 0, 0.7)) var(' not in text      # the library's grain and vignette strengths are not used as they come
    assert 'attachMotionBlur' in text or 'data-hf-motion-blur' in text


def test_no_effects_leaves_the_page_untouched_and_a_page_with_no_body_end_still_gets_the_layer(tmp_path):
    (tmp_path / 'index.html').write_bytes(INDEX)
    M.apply_finish(tmp_path, [])
    assert (tmp_path / 'index.html').read_bytes() == INDEX
    (tmp_path / 'index.html').write_bytes(b'<div id="root"></div>')
    M.apply_finish(tmp_path, ['vignette'])
    assert 'id="vw-finish"' in (tmp_path / 'index.html').read_text(encoding='utf-8')


def test_the_servers_three_parts_carry_no_web_address():
    for name in M.FINISH:
        text = (M.FINISH_DIR / f'{name}.html').read_text(encoding='utf-8')
        assert not M.EXTERNAL.search(text), name


# ---- the render: a finish never stops a film ----

class Renderer:
    """Stand-ins for HyperFrames: what each call was given, and what it answers."""
    def __init__(self, snaps=(b'a', b'a'), fail_with_finish=False):
        self.snaps, self.fail, self.calls = list(snaps), fail_with_finish, []

    def build(self, effects):
        self.calls.append(('build', tuple(effects)))
        return tuple(effects)

    def twice(self, project):
        self.calls.append(('twice', project))
        return self.snaps[0] == self.snaps[1]

    def render(self, project):
        self.calls.append(('render', project))
        if project and self.fail:
            raise RuntimeError('render failed: timeout')
        return 'movie-with' if project else 'movie-plain'


def test_a_finish_that_draws_the_same_twice_is_rendered():
    r = Renderer()
    assert W.render_with_finish(['blur'], r.build, r.twice, r.render) == ('movie-with', ['blur'], '')
    assert [c[0] for c in r.calls] == ['build', 'twice', 'render']


def test_no_finish_is_one_plain_render_with_no_extra_work():
    r = Renderer()
    assert W.render_with_finish([], r.build, r.twice, r.render) == ('movie-plain', [], '')
    assert [c[0] for c in r.calls] == ['build', 'render']


def test_a_finish_that_draws_differently_twice_is_left_off_and_the_shot_still_renders():
    r = Renderer(snaps=(b'a', b'b'))
    movie, used, why = W.render_with_finish(['grain'], r.build, r.twice, r.render)
    assert (movie, used) == ('movie-plain', []) and 'differently' in why


def test_a_finish_that_breaks_the_render_is_left_off_and_the_shot_still_renders():
    r = Renderer(fail_with_finish=True)
    movie, used, why = W.render_with_finish(['blur', 'grain'], r.build, r.twice, r.render)
    assert (movie, used) == ('movie-plain', []) and 'timeout' in why
    assert r.calls[-2:] == [('build', ()), ('render', ())]


def test_a_plain_render_that_fails_is_raised_as_before():
    def render(project):
        raise RuntimeError('render failed: no chrome')
    with pytest.raises(RuntimeError, match='no chrome'):
        W.render_with_finish([], lambda e: tuple(e), lambda p: True, render)
