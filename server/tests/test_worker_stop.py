"""Graceful stop (design/25, approved 16 Oct 2026): SIGTERM finishes the current job, claims nothing new, and the parent
forwards the signal to its child workers and waits for them."""
import signal
import threading
import time

import pytest

from app import visual_workers, worker


@pytest.fixture(autouse=True)
def stop_flag():
    old = signal.getsignal(signal.SIGTERM)
    worker.STOP = False
    yield
    worker.STOP = False
    signal.signal(signal.SIGTERM, old)


def test_sigterm_mid_job_finishes_job_then_exits(monkeypatch):
    signal.signal(signal.SIGTERM, worker._stop)
    calls = []

    def tick():
        calls.append(1)
        signal.raise_signal(signal.SIGTERM)  # arrives while the job is running
        time.sleep(0.05)
        calls.append('finished')  # the job was not cut short
        return True

    monkeypatch.setattr(worker, 'tick', tick)
    worker.loop()
    assert calls == [1, 'finished']


def test_stop_while_idle_exits_within_about_a_second(monkeypatch):
    monkeypatch.setattr(worker, 'tick', lambda: False)  # idle: loop would sleep 10 s
    threading.Timer(0.3, lambda: setattr(worker, 'STOP', True)).start()
    start = time.monotonic()
    worker.loop()
    assert time.monotonic() - start < 2.5


def test_tick_claims_nothing_once_stopping(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('claimed a job after stop')
    from app import analysis_jobs
    from app.stage2 import render_jobs
    monkeypatch.setattr(worker, 'connect', boom)
    for mod in (analysis_jobs, visual_workers, render_jobs):
        monkeypatch.setattr(mod, 'tick', boom)
    worker.STOP = True
    assert worker.tick() is False


def test_visual_tick_skips_take_after_stop_during_image(monkeypatch):
    monkeypatch.setattr(visual_workers.jobs, 'claim', lambda conn, provider: {'id': 'img'})
    monkeypatch.setattr(visual_workers, 'process_image', lambda job: setattr(worker, 'STOP', True) or ('ready', {}, None, None, None))
    monkeypatch.setattr(visual_workers, 'finalize_image', lambda conn, job, *outcome: None)
    monkeypatch.setattr(visual_workers, 'claim_take', lambda conn: (_ for _ in ()).throw(AssertionError('claimed a take after stop')))
    assert visual_workers.tick() is True


class FakeChild:
    def __init__(self, *a, **k):
        self.signals, self.waited = [], False
        CHILDREN.append(self)

    def send_signal(self, sig):
        self.signals.append(sig)

    def terminate(self):
        self.signals.append(signal.SIGTERM)

    def wait(self, timeout=None):
        self.waited = True
        return 0


CHILDREN = []


def test_parent_forwards_sigterm_and_waits_for_children(monkeypatch):
    import subprocess
    CHILDREN.clear()
    monkeypatch.delenv('VW2_WORKER_CHILD', raising=False)
    monkeypatch.setattr(worker, 'settings', lambda: type('S', (), {'WORKERS': 3})())
    monkeypatch.setattr(subprocess, 'Popen', FakeChild)

    def loop():
        signal.raise_signal(signal.SIGTERM)
        time.sleep(0.05)
        assert worker.STOP

    monkeypatch.setattr(worker, 'loop', loop)
    worker.main()
    assert len(CHILDREN) == 2
    assert all(signal.SIGTERM in c.signals and c.waited for c in CHILDREN)
