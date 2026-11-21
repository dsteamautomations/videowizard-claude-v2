"""Hotfix (SK, 21 Nov 2026, "Yes, hotfix"): the same Gemini key for every call of the same take.

Each call of a take took the next key of the pool (five keys), but only the key that sent a take can read it: the other four answer 404
"Requested entity was not found". The worker read that as "could not be confirmed" and tried again later with whichever key came up, so a
finished take waited minutes to an hour "being stored" (VW-24: BEAT_13-B1_S4's take, sent 08:47 UTC and finished at the provider, was still
not fetched at 09:45; keys 1, 2, 4, 5 answered 404 and key 3 answered 200). Now the sending key's number is kept beside the take's saved
answer and used for every later call; a take saved before this (no number), or whose key answers 404, is looked for once with each other key
of the pool, and the key that finds it is kept. Each test failed first. Without a database, without the network."""
import json

import pytest

from app import video_providers as VP, visual_workers as VW
from app.errors import Problem

KEYS = ['k0', 'k1', 'k2', 'k3', 'k4']
REMOTE = 'v1_abc'


def provider(index, monkeypatch, owner='k2', other=404):
    """A provider on key `index` whose requests succeed only with the owner's key; the rest answer `other`."""
    monkeypatch.setattr(VP, 'pool_keys', lambda: list(KEYS))
    p = VP.Provider.__new__(VP.Provider)
    p.name, p.key, p.key_index, p.asked = 'google', KEYS[index], index, []

    def request(method, url, body=None, identity=None, paid=False):
        p.asked.append(p.key)
        if p.key != owner:
            raise Problem(502, 'VIDEO_PROVIDER', 'Provider request was not accepted or could not be confirmed.', http_status=other)
        return {'id': REMOTE, 'status': 'completed'}
    p.request = request
    return p


def test_a_take_another_key_sent_is_looked_for_with_each_key_once_and_the_finder_is_kept(monkeypatch):
    p = provider(0, monkeypatch)
    assert p.poll(REMOTE) == {'id': REMOTE, 'status': 'completed'}
    assert p.asked == ['k0', 'k1', 'k2'] and (p.key, p.key_index) == ('k2', 2)                  # stops at the key that finds it
    assert p.poll(REMOTE)['status'] == 'completed' and p.asked == ['k0', 'k1', 'k2', 'k2']      # and stays on it


def test_the_sending_key_is_asked_alone(monkeypatch):
    p = provider(2, monkeypatch)
    assert p.poll(REMOTE)['status'] == 'completed' and p.asked == ['k2']


def test_no_key_finds_it_the_same_error_as_before_and_the_first_key_is_kept(monkeypatch):
    p = provider(1, monkeypatch, owner='nobody')
    with pytest.raises(Problem) as e:
        p.poll(REMOTE)
    assert e.value.code == 'VIDEO_PROVIDER' and sorted(p.asked) == sorted(KEYS) and (p.key, p.key_index) == ('k1', 1)


def test_an_answer_other_than_not_found_is_not_searched(monkeypatch):
    for status in (500, 429, 403, None):
        p = provider(0, monkeypatch, other=status)
        with pytest.raises(Problem):
            p.poll(REMOTE)
        assert p.asked == ['k0'], status


def test_one_key_only_nothing_to_search(monkeypatch):
    p = provider(0, monkeypatch, owner='nobody')
    monkeypatch.setattr(VP, 'pool_keys', lambda: ['k0'])
    with pytest.raises(Problem):
        p.poll(REMOTE)
    assert p.asked == ['k0']


def test_a_provider_is_made_on_the_key_asked_for_else_on_the_next_of_the_pool(monkeypatch):
    monkeypatch.setattr(VP, 'pool_keys', lambda: list(KEYS))

    def nxt(name):
        nxt.last_index = 4
        return 'k4'
    monkeypatch.setattr(VP, 'configured', nxt)
    p = VP.Provider('google', key_index=2)
    assert (p.key, p.key_index) == ('k2', 2)
    for gone in (None, 9, -1, 'x'):                                                             # no number, or one the pool no longer has
        p = VP.Provider('google', key_index=gone) if gone is not None else VP.Provider('google')
        assert (p.key, p.key_index) == ('k4', 4), gone


def test_a_refused_request_carries_the_providers_http_status(monkeypatch):
    class Response:
        is_success, status_code = False, 404

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(VP.httpx, 'stream', lambda *a, **k: Response())
    p = VP.Provider.__new__(VP.Provider)
    p.name, p.key, p.key_index = 'google', 'k0', 0
    with pytest.raises(Problem) as e:
        p.request('GET', 'https://example.invalid/x')
    assert e.value.extra.get('http_status') == 404 and e.value.code == 'VIDEO_PROVIDER'


# ---------- the take's job keeps its key ----------

class Store:
    def __init__(self, snapshot):
        self.files = {'req': json.dumps(snapshot).encode()}

    def get(self, k):
        return self.files[k]

    def put(self, k, data, mime):
        self.files[k] = data


class Fake:
    """A provider that sends, and reports the take as still being made."""
    made, found = [], None   # found: the key a search ends on, when the test says one

    def __init__(self, name, key_index=None):
        self.key_index = 3 if key_index is None else key_index
        Fake.made.append(key_index)

    def build(self, snapshot, store):
        return {}

    def submit(self, wire, jid):
        return {'id': REMOTE, 'status': 'in_progress'}

    def identity(self, result):
        return result['id']

    def state(self, result):
        return 'in_progress' if result.get('status') == 'in_progress' else result['status']

    def poll(self, remote):
        if Fake.found is not None:
            self.key_index = Fake.found                                                         # as if the search had found the take on another key
        return {'id': REMOTE, 'status': 'in_progress'}


def run_take(tmp_path, monkeypatch, result=None):
    store = Store({'provider': 'google', 'model': 'm', 'duration_seconds': 5})
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'provider_factory', Fake)
    job = {'id': 'job-1', 'run_id': 'run-1', 'request': {'request_key': 'req', 'preparation_id': 'prep'}, 'result': result}
    return VW.process_take(job), json.loads((tmp_path / 'job-1' / 'response.json').read_text(encoding='utf-8'))


def test_the_sending_keys_number_is_saved_with_the_take_and_used_for_the_next_call(tmp_path, monkeypatch):
    Fake.made, Fake.found = [], None
    out, saved = run_take(tmp_path, monkeypatch)
    assert out[0] == 'submitted' and Fake.made == [None]                                        # the send: the next key of the pool, as before
    assert saved['key_index'] == 3 and saved['result']['id'] == REMOTE
    Fake.found = 1
    out, saved = run_take(tmp_path, monkeypatch, result={'provider_id': REMOTE, 'polls': 1})
    assert out[0] == 'submitted' and Fake.made == [None, 3]                                     # the next call: the key that sent it
    assert saved['key_index'] == 1                                                              # and a key found by the search is kept from then on
    run_take(tmp_path, monkeypatch, result={'provider_id': REMOTE, 'polls': 2})
    assert Fake.made == [None, 3, 1]


def test_a_take_saved_before_this_has_no_number_and_is_made_as_before(tmp_path, monkeypatch):
    Fake.made, Fake.found = [], 1
    (tmp_path / 'job-1').mkdir()
    (tmp_path / 'job-1' / 'attempt.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'job-1' / 'response.json').write_text(json.dumps({'preparation_id': 'prep', 'provider_id': REMOTE, 'result': {'id': REMOTE, 'status': 'in_progress'}}), encoding='utf-8')
    out, saved = run_take(tmp_path, monkeypatch, result={'provider_id': REMOTE, 'polls': 4})
    assert out[0] == 'submitted' and Fake.made == [None] and saved['key_index'] == 1            # found by the search, kept
