"""design/108 D1-D4: a download streams to disk, skips what is already there, fetches a big file in parallel parts, and verifies the fingerprint."""
import hashlib
import os

import httpx
import pytest

import vw


class Redirect:
    """The server's file route: one redirect to the storage link (plugin: `api()`)."""
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, path, **kw):
        self.calls.append((path, kw))
        return httpx.Response(307, headers={'location': 'https://store/x'}, request=httpx.Request('GET', 'http://x' + path))


class Stream:
    def __init__(self, status, headers, body):
        self.status_code, self.headers, self._body = status, headers, body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_bytes(self, n):
        for i in range(0, len(self._body), n):
            yield self._body[i:i + n]


class Storage:
    """The storage link: whole or ranged GETs, with a failure script (plugin: `_storage_client()`)."""
    def __init__(self, data, failures=()):
        self.data, self.failures, self.ranges = data, list(failures), []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def stream(self, method, url, headers=None):
        rg = (headers or {}).get('Range')
        self.ranges.append(rg)
        if self.failures and self.failures.pop(0):
            raise httpx.ReadError('reset')
        if rg:
            a, b = (int(x) for x in rg[len('bytes='):].split('-'))
            return Stream(206, {'content-range': f'bytes {a}-{b}/{len(self.data)}'}, self.data[a:b + 1])
        return Stream(200, {'content-length': str(len(self.data))}, self.data)


def body(n):
    return bytes((i * 7 + i // 1000) % 256 for i in range(n))


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw.time, 'sleep', lambda s: slept.append(s))
    slept = []
    api = Redirect()
    monkeypatch.setattr(vw, 'api', lambda: api)

    def use(data, failures=()):
        st = Storage(data, failures)
        monkeypatch.setattr(vw, '_storage_client', lambda: st)
        return st
    return {'code': 'VW-9', 'run_id': 'run-1', 'files': []}, api, use, slept, tmp_path / 'runs' / 'VW-9'


def test_a_big_file_comes_in_four_parallel_parts_streamed_to_disk_and_verified(setup):
    m, api, use, slept, ws = setup
    data = body(vw.DOWNLOAD_PART_MIN + 1000)
    st = use(data)
    path = vw._download(m, 'k1', 'bundle/Media/C1.MP4', expect={'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    assert (ws / 'bundle/Media/C1.MP4').read_bytes() == data and path.endswith('C1.MP4') and not (ws / 'bundle/Media/C1.MP4.part').exists()
    assert len(st.ranges) == 4 and all(r and r.startswith('bytes=') for r in st.ranges)
    spans = sorted(tuple(int(x) for x in r[6:].split('-')) for r in st.ranges)
    assert spans[0][0] == 0 and spans[-1][1] == len(data) - 1 and all(spans[i][1] + 1 == spans[i + 1][0] for i in range(3))   # contiguous, the whole file
    assert api.calls[0][1] == {'follow_redirects': False}


def test_a_small_file_comes_in_one_request(setup):
    m, api, use, slept, ws = setup
    data = body(5_000_000)
    st = use(data)
    vw._download(m, 'k2', 'out/x.png', expect={'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    assert st.ranges == [None] and (ws / 'out/x.png').read_bytes() == data
    st = use(b'abc')
    vw._download(m, 'k3', 'out/y.bin')   # no manifest: one request, nothing to verify
    assert st.ranges == [None] and (ws / 'out/y.bin').read_bytes() == b'abc'


def test_a_file_already_on_disk_with_the_right_fingerprint_is_not_downloaded_again(setup):
    m, api, use, slept, ws = setup
    data = body(1000)
    (ws / 'bundle').mkdir(parents=True)
    (ws / 'bundle/C1.MP4').write_bytes(data)
    st = use(data)
    vw._download(m, 'k1', 'bundle/C1.MP4', expect={'bytes': 1000, 'sha256': hashlib.sha256(data).hexdigest()})
    assert st.ranges == [] and api.calls == []
    (ws / 'bundle/C1.MP4').write_bytes(data[:-1] + b'!')   # same size, wrong bytes: fetched again
    vw._download(m, 'k1', 'bundle/C1.MP4', expect={'bytes': 1000, 'sha256': hashlib.sha256(data).hexdigest()})
    assert st.ranges == [None] and (ws / 'bundle/C1.MP4').read_bytes() == data


def test_a_broken_part_is_fetched_again_after_the_usual_wait(setup):
    m, api, use, slept, ws = setup
    data = body(vw.DOWNLOAD_PART_MIN + 1)
    st = use(data, failures=[False, True, False, False])
    vw._download(m, 'k1', 'bundle/C1.MP4', expect={'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    assert (ws / 'bundle/C1.MP4').read_bytes() == data and len(st.ranges) == 5 and slept == [5]


def test_a_wrong_fingerprint_is_downloaded_once_more_then_named(setup, capsys):
    m, api, use, slept, ws = setup
    data = body(2000)
    use(data)
    with pytest.raises(SystemExit) as exc:
        vw._download(m, 'k1', 'bundle/C1.MP4', expect={'bytes': 2000, 'sha256': 'f' * 64})
    out = capsys.readouterr().out
    assert exc.value.code == 2 and 'C1.MP4' in out and 'fingerprint' in out and not (ws / 'bundle/C1.MP4').exists()


def test_the_bundle_passes_each_files_fingerprint(setup, monkeypatch):
    m, api, use, slept, ws = setup
    seen = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: seen.append((rel, expect and expect['sha256'])) or str(ws / rel))
    vw.download_bundle(m, {'files': [{'role': 'original', 'name': 'Media/Originals/C1.MP4', 'key': 'k1', 'bytes': 5, 'sha256': 'a' * 64}]})
    assert seen == [('bundle/Media/Originals/C1.MP4', 'a' * 64)]
