"""design/52 (layer two, Docker): the voice page endpoints with the provider faked: compact catalog, favourite and release rules,
direction record and refusal, a directed narration whose timing equals the accepted script, the final record, and next.voice_page."""
import json

import httpx
import pytest

from app import elevenlabs, worker
from test_voice_media import FakeEleven, drain, run_until_voice, mp3_bytes
from conftest import vw


class FakePage(FakeEleven):
    @classmethod
    def request(cls, self, method, path, **kw):
        if path == '/v1/user/subscription':
            return httpx.Response(200, json={'tier': 'pro', 'voice_limit': 160, 'voice_slots_used': 54, 'voice_add_edit_counter': 3, 'max_voice_add_edits': 290, 'character_count': 10, 'character_limit': 500000})
        if method == 'DELETE' and path.startswith('/v1/voices/'):
            cls.calls.append((method, path))
            return httpx.Response(200, json={'status': 'ok'})
        return FakeEleven.request(self, method, path, **kw)


@pytest.fixture
def fake(monkeypatch):
    FakePage.mode, FakePage.history, FakePage.calls = 'ok', [], []
    monkeypatch.setattr(elevenlabs.ElevenLabs, 'request', lambda self, m, p, **kw: FakePage.request(self, m, p, **kw))
    return FakePage


def test_catalog_rows_are_compact_and_carry_the_register(home, database, fake, client, alice):
    run_until_voice(home, database)
    rc, out, err = vw(home, 'voice', 'catalog', '--scope', 'account')
    assert rc == 0 and set(out['voices'][0]) >= {'voice_id', 'name', 'accent', 'gender', 'on_account', 'favourite', 'narrations'} and 'description' in out['voices'][0]
    assert 'v1 · Asha' in err
    r = client.post('/api/voice/favourite', json={'voice_id': 'v1', 'on': True, 'note': 'warm'}, headers=alice)
    assert r.status_code == 200 and r.json()['favourite'] is True
    r = client.post('/api/voice/release', json={'voice_id': 'v1'}, headers=alice)
    assert r.status_code == 409 and 'favourite since' in r.json()['message']
    client.post('/api/voice/favourite', json={'voice_id': 'v1', 'on': False}, headers=alice)
    r = client.post('/api/voice/release', json={'voice_id': 'v1'}, headers=alice)
    assert r.status_code == 409 and 'custom voices are never deleted' in r.json()['message']   # v1 has no library identity: a custom voice


def test_direction_then_a_directed_narration_then_the_final_click(home, database, fake, client, alice):
    code, ws = run_until_voice(home, database)
    run_id = json.loads((ws / 'manifest.json').read_text())['run_id']
    rc, out, _ = vw(home, 'voice', 'direct', 'prepare')
    assert rc == 0 and [(r['passage_id'], r['sentence']) for r in out['inputs']['sentences']] == [('P001', 1), ('P002', 1)] and 'VW-DIRECTION' in out['prompt']
    doc = {'kind_of_film': 'an explainer', 'register': {'best_fit': '[measured]', 'experimental': '[warm]'},
           'options': {'best_fit': [{'passage_id': 'P002', 'sentence': 1, 'first_words': 'Not fired.', 'tag': '[softly]', 'reason': 'the turn'}],
                       'experimental': [{'passage_id': 'P001', 'sentence': 1, 'first_words': 'Earth', 'tag': '[laughs]', 'reason': 'x'}]}, 'experimental_idea': 'lighter'}
    (ws / 'out' / 'direction.json').write_text(json.dumps(doc), encoding='utf-8')
    rc, out, _ = vw(home, 'voice', 'direct', 'record', '--choice', 'experimental', '--quote', 'try it')
    assert rc == 2 and 'reaction' in out['message']
    rc, out, _ = vw(home, 'voice', 'direct', 'record', '--choice', 'best_fit', '--quote', 'the careful one')
    assert rc == 0 and out['items'] == 1
    rc, out, _ = vw(home, 'next')
    assert out['voice_page']['direction'] == 'best_fit'
    r = client.post(f'/api/runs/{run_id}/voice/narrate', json={'request_id': 'r-n1', 'voice_id': 'v1'}, headers=alice)
    assert r.status_code == 201
    snap = r.json()['request']
    assert snap['text_tagged'].startswith('[measured] Earth blocks are pressed.') and '[softly] Not fired.' in snap['text_tagged'] and snap['text'] == 'Earth blocks are pressed.\n\nNot fired.'
    drain()
    jobs_ = client.get(f'/api/runs/{run_id}/jobs?stage=voice', headers=alice).json()
    job = next(j for j in jobs_ if j['request']['kind'] == 'narration')
    assert job['status'] == 'ready', job.get('error')
    timing = json.loads(client.get(f"/api/runs/{run_id}/files/{job['result']['timing_key']}", headers=alice, follow_redirects=True).content)
    assert timing['script_characters_match'] and ''.join(timing['alignments']['alignment']['characters']) == snap['text'] and [w['text'] for w in timing['words']][:2] == ['Earth', 'blocks']
    page = client.get(f'/api/runs/{run_id}/voice/page', headers=alice).json()['page']
    assert len(page['narrations']) == 1 and page['narrations'][0]['number'] == 1 and page['final'] is None
    r = client.post(f'/api/runs/{run_id}/voice/final', json={'request_id': 'r-f1', 'job_id': job['id'], 'quote': ''}, headers=alice)
    assert r.status_code == 422
    r = client.post(f'/api/runs/{run_id}/voice/final', json={'request_id': 'r-f2', 'job_id': job['id'], 'quote': 'make this the final one'}, headers=alice)
    assert r.status_code == 201 and r.json()['summary']['direction'] == {'chosen': 'best_fit', 'digest': out['digest']} and r.json()['summary']['recorded_from'] == 'chat'
    rc, out, _ = vw(home, 'next')
    assert out['stage'] == 'media'
    hist = client.get('/api/voice/history?voice_id=v1', headers=alice).json()['voices']['v1']
    assert hist['narrations'] == 1 and hist['final_in'][0]['code'] == code
