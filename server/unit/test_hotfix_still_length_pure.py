"""Hotfix (SK, 21 Nov 2026, "Hotfix, B1 shorten"): VW-24's BEAT_11-B1-S3 still was refused twice by OpenAI with HTTP 400, logged without its
reason. OpenAI's body said the prompt was 52,545 and 49,623 characters, over GPT Image's 32,000. Most of it was the server's own two blocks:
the drawings' colour key and the exact layout, one line per piece of a 49-tree background belt.

A: an OpenAI refusal not handled already says OpenAI's code and message. B1: a still's prompt over the limit is shortened by the server (the
smallest background pieces of the set are summed up in one line each block; people, props and moving pieces always stay one by one), and a
prompt still over the limit is refused before anything is queued or paid. Each test failed first. Without a database."""
import json

from app import guide as GD, video_generators as VG, visual_workers as VW
from test_design151_refs_pure import NEW
from test_guide_route_pure import STILL_WORDS, refused, rendered, scene, spec10, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import USER, saved

LIMIT = 32000


# ---------- A: the reason of a refusal ----------

class Resp:
    def __init__(self, status, body=None, text=None):
        self.status_code, self._body = status, body
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise ValueError('not json')
        return self._body


TOO_LONG = {'error': {'message': "Invalid 'prompt': string too long. Expected a string with maximum length 32000, but got a string with length 52545 instead.",
                      'type': 'invalid_request_error', 'param': 'prompt', 'code': 'string_above_max_length'}}


def test_an_openai_400_says_its_code_and_message():
    result, error = VW.refusal(Resp(400, TOO_LONG), {'provider': 'openai'})
    assert error == ("OpenAI rejected the request (HTTP 400, string_above_max_length): Invalid 'prompt': string too long. Expected a string with maximum "
                     'length 32000, but got a string with length 52545 instead.')
    assert result['http_status'] == 400 and 'string_above_max_length' in result['detail']   # the body is kept as before


def test_a_body_that_is_not_json_gives_its_text_and_a_long_message_is_cut():
    _, error = VW.refusal(Resp(400, None, text='<html>Bad request</html>'), {'provider': 'openai'})
    assert error == 'OpenAI rejected the request (HTTP 400): <html>Bad request</html>'
    _, error = VW.refusal(Resp(400, {'error': {'message': 'x' * 1000}}), {'provider': 'openai'})
    assert error == 'OpenAI rejected the request (HTTP 400): ' + 'x' * 300
    _, error = VW.refusal(Resp(400, {'error': {}}, text='{"error": {}}'), {'provider': 'openai'})
    assert error == 'OpenAI rejected the request (HTTP 400).'                                    # nothing to add


def test_moderation_and_gemini_refusals_are_unchanged():
    _, error = VW.refusal(Resp(400, {'error': {'type': 'moderation_blocked', 'moderation_stage': 'input', 'categories': ['x']}}), {'provider': 'openai'})
    assert error.startswith('OpenAI refused the pictures or the prompt (moderation, stage input, x).')
    _, error = VW.refusal(Resp(400, {'error': {'message': 'bad'}}), {'provider': 'gemini', 'model': 'm'})
    assert 'rejected the request (HTTP 400): bad.' in error and not error.startswith('OpenAI')


# ---------- B1: the still's prompt within the limit ----------

def forest(n=150):
    """spec10 with a belt of n background trees far behind the house, each a piece of the set with a long name, as VW-24's roof scene had."""
    s = spec10()
    for k in range(n):
        x = -9 + (k % 50) * 0.4   # most of the belt in the frame, as the roof scene's was
        y = 25 + (k // 50) * 4
        s['set'].append({'id': f'FAR_TREE_{k:03d}', 'name': f'a dense tree in the back row of the distant belt of coconut palms and neem trees beyond the far edge, number {k}',
                         'shape': 'box', 'min': [x, y, 0], 'max': [x + 0.35, y + 0.35, 6 + (k % 7)], 'colour': [0.05 + (k % 9) * 0.04, 0.25, 0.08]})
    return s


def ordered(store, conn, spec, words=STILL_WORDS):
    scene(store, conn, spec)
    rendered(store, conn)
    return GD.request_still(conn, store, USER, NEW, [], 'VS1', words, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])


def sent(conn):
    return [q for q in conn.queued if q['provider'] == 'guide-still'][-1]['request']['prompt']


def test_the_limit_is_kept_beside_the_still_model():
    assert VG.STILL['max_prompt'] == LIMIT


def test_a_scene_with_a_large_background_belt_is_sent_under_the_limit_with_its_people_and_the_count(take_film):
    store, conn = take_film
    ordered(store, conn, forest())
    g = saved(store)['guides']['VS1']
    assert len(g['drawing']['how']) + len(GD.G.layout_block(forest())) > LIMIT                   # the two blocks whole are over the limit by themselves
    p = sent(conn)
    assert len(p) <= LIMIT
    for name in ('the father', 'the daughter', 'the mother'):
        assert f'- {name}: from ' in p                                                           # people are always listed one by one
    assert 'Exactly 3 people in view; no one else.' in p and STILL_WORDS in p
    assert 'further background pieces of the set' in p                                         # the summed-up line of the layout
    assert 'The other colours are background pieces of the set' in p                            # and of the colour key
    assert p.count('a dense tree in the back row') < 2 * 150                                     # fewer trees named than the full prompt has


def test_a_normal_scene_is_sent_exactly_as_before(take_film):
    store, conn = take_film
    ordered(store, conn, spec10())
    p = sent(conn)
    g = saved(store)['guides']['VS1']
    assert g['drawing']['how'] in p and GD.G.layout_block(spec10()) in p                          # both blocks whole, nothing summed up
    assert 'further background pieces' not in p and 'The other colours are background pieces' not in p


def test_a_prompt_that_cannot_be_brought_under_the_limit_is_refused_before_anything_is_queued(take_film):
    store, conn = take_film
    words = STILL_WORDS + ' ' + 'The light falls softly on the lime-washed wall. ' * 700        # the writer's own words alone pass the limit
    msg = refused(lambda: ordered(store, conn, spec10(), words))
    assert msg.startswith('The still\'s request would be ') and 'OpenAI takes at most 32,000' in msg and 'your words ' in msg
    assert not [q for q in conn.queued if q['provider'] == 'guide-still']
    assert saved(store)['guides']['VS1'].get('stills', []) == []
