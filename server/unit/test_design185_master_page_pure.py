"""design/185: the master page (view only). The page's state from the built master, its render record and a storage check."""
from pathlib import Path

from app.stage2 import stage as S

APP = Path(__file__).resolve().parents[1] / 'app'
M = {'version': 2, 'digest': 'd2'}
READY = {'status': 'ready', 'digest': 'd2', 'error': None,
         'result': {'key': 'run-1/stage2/master-v2-d2.mp4', 'duration_s': 118.72, 'record': {'mix': {'integrated_lufs': -16.3, 'true_peak_dbfs': -2.4}}}}
yes, no = (lambda k: True), (lambda k: False)


def test_no_master_built():
    assert S.master_state(None, None, yes) == {'state': 'none'}
    assert S.master_state(None, READY, yes) == {'state': 'none'}   # a revise dropped the master: an old render is not shown


def test_built_but_not_rendered_or_the_render_is_of_another_build():
    assert S.master_state(M, None, yes) == {'version': 2, 'state': 'not_rendered'}
    assert S.master_state(M, {**READY, 'digest': 'd1'}, yes)['state'] == 'not_rendered'


def test_queued_and_running_are_rendering():
    for status in ('queued', 'running'):
        assert S.master_state(M, {'status': status, 'digest': 'd2'}, yes) == {'version': 2, 'state': 'rendering'}


def test_a_failed_render_carries_its_error():
    assert S.master_state(M, {'status': 'failed', 'digest': 'd2', 'error': 'ffmpeg exit 1'}, yes) == {'version': 2, 'state': 'failed', 'error': 'ffmpeg exit 1'}
    assert S.master_state(M, {'status': 'ready', 'digest': 'd2', 'result': {}}, yes)['state'] == 'failed'   # ready with no file key


def test_the_file_missing_in_storage():
    assert S.master_state(M, READY, no) == {'version': 2, 'state': 'missing'}


def test_ready_gives_the_key_the_length_and_the_loudness():
    assert S.master_state(M, READY, yes) == {'version': 2, 'state': 'ready', 'key': 'run-1/stage2/master-v2-d2.mp4', 'duration_s': 118.72,
                                             'mix': {'integrated_lufs': -16.3, 'true_peak_dbfs': -2.4}}


def test_the_page_has_no_button_and_plays_through_the_film_route():
    html = (APP / 'templates' / 'master.html').read_text(encoding='utf-8')
    assert '<button' not in html and '<form' not in html and '/film/{{ view.key }}' in html
    assert "'/runs/{code}/master'" in (APP / 'web.py').read_text(encoding='utf-8')
    assert '/runs/{{ run.code }}/master' in (APP / 'templates' / 'run.html').read_text(encoding='utf-8')
