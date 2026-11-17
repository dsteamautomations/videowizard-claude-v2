"""design/211 part B: a round without `v == 2` behaves exactly as before the references step was rebuilt, in each of its states (step 1,
making, step 2 with sets made the old way, complete). The live film VW-24 is in the middle of such a round.

Each case runs the server functions of the round on the shared fixture's older round and compares everything they answer, store and order
(the request text of every set included) with a fingerprint taken on `main` at d255486, before part B changed a line. Times are taken out.
A case that differs prints what it gives now. Without a database."""
import copy
import hashlib
import json
import re

import pytest

from app import visuals_stage as VS
from app.errors import Problem
import d211_fixture as F
from test_visuals_stage_pure import FakeConn, FakeStore, USER

RUN = {**F.RUN, 'image_provider': 'gemini'}   # no `film`: a film of before design/139, as the fixture's older round
PLAN_KEY = f"{RUN['id']}/visuals/plan-v1.json"
SESSION_KEY = f"{RUN['id']}/visuals/session.json"
WHEN = re.compile(r'\d{4}-\d\d-\d\dT[\d:.]+\+00:00')


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


def whole(s):
    """The fixture's session with what a stored session always holds, so the server's own functions can read it."""
    base = {'source': {'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': {}},
            'versions': [{'version': 1, 'file': {'key': PLAN_KEY}, 'plan_digest': 'v1', 'warnings': []}], 'bindings': {}, 'generator_choices': {}, 'preparations': {},
            'reviews': {}, 'selections': {}, 'assets': {}, 'recorded_gaps': {}}
    return {**base, **s}


def store_of(s, plan=None):
    store = FakeStore({SESSION_KEY: whole(s), PLAN_KEY: {'document': plan or F.plan()}})
    store.files[f"{RUN['id']}/visuals/package.json"] = json.dumps({'intended_visuals': []}).encode('utf-8')
    return store


def saved(store):
    return json.loads(store.files[SESSION_KEY])


def older(state):
    """The fixture's older round at 'step1', 'making', 'step2' (as the fixture gives it) or 'complete'."""
    s = F.older_session()
    rd, refs = s['round'], s['references']
    street = [r for r in refs if refs[r].get('set')]
    if state == 'step1':
        for rid in street:
            refs.pop(rid)
        for fid in ('f-trowel-side', 'f-trowel-use', 'f-tile-under'):
            refs[fid].update(status='candidate', approval=None)
        for row in rd['elements'].values():
            row['verdict'] = None
        rd['elements']['TROWEL'].pop('from_footage')
        rd['elements']['STREET'].update(set=None, round=0)
        rd['elements']['STREET'].pop('made')
        s['golden'] = {}
        rd.update({'pass': 1, 'quote': None})
    if state == 'making':
        for rid in street[1:]:
            refs.pop(rid)
        first = refs[street[0]]
        for k in ('key', 'sha256', 'bytes', 'width', 'height', 'notes', 'sources', 'check'):
            first.pop(k, None)
        first['status'] = 'generating'
    if state == 'complete':
        for rid in street:
            refs[rid].update(status='approved', approval={'by': 'u1', 'at': F.NOW, 'quote': 'Sets done', 'sha256': refs[rid]['sha256']})
        for eid, row in rd['elements'].items():
            if eid not in ('STREET', 'TROWEL'):
                row.update(verdict='ignore', ignored=True)
        rd['elements']['STREET']['verdict'] = 'yes'
        s['golden']['STREET'] = street[0]
        rd['pass'] = 'complete'
    return s


def call(fn):
    try:
        return {'answer': VS.guarded(fn)}
    except Problem as exc:
        return {'refused': exc.message}


def shape(value):
    return json.loads(WHEN.sub('T', json.dumps(value, sort_keys=True, default=lambda v: getattr(v, 'obj', str(v)))))


def case(state, act):
    """One function of the round on the older round at `state`: its answer (or refusal), the session it leaves, the jobs it orders."""
    store, conn = store_of(older(state)), FakeConn([])
    out = call(lambda: act(store, conn))
    s = saved(store)
    return shape({'out': out, 'session': {k: s.get(k) for k in ('round', 'references', 'golden', 'refs')}, 'jobs': [list(p) for p in conn.inserted],
                  'pass': VS._round_pass(s, s['round']), 'view': VS._round_view(s, F.plan())})


ROWS = [{'element_id': e, 'prompt': f'The subject block of {e}.'} for e in F.THINGS]
STEP1 = {e: {'verdict': 'ignore' if e in ('FAN', 'TILE') else 'approve'} for e in F.THINGS}   # TILE: the fixture's drawing set has no stored description to read
CASES = {
    'step1: the round file sent again makes an older round again': ('step1', lambda st, c: VS.round_start(st, USER, RUN, [], copy.deepcopy(ROWS), conn=c)),
    'step1: done orders every set at once': ('step1', lambda st, c: VS.round_done(st, USER, RUN, [], STEP1, 'Pass 1 done', conn=c)),
    'step1: an answer to a set is refused': ('step1', lambda st, c: VS.set_answer(st, USER, RUN, [], 'STREET', 'yes', 's-street-1')),
    'making: the sets are not judged yet': ('making', lambda st, c: VS.round_sets(st, USER, RUN, [], {'STREET': {'verdict': 'yes', 'golden': 's-street-1'}}, 'ok', conn=c)),
    'making: a set being made is left alone': ('making', lambda st, c: VS.set_make(c, st, USER, RUN, [], 'STREET')),
    'step2: yes on the set, the rest not made': ('step2', lambda st, c: VS.round_sets(st, USER, RUN, [], {'STREET': {'verdict': 'yes', 'golden': 's-street-1-2'}}, 'Sets done', conn=c, partial=True)),
    'step2: correct it makes the set again with the correction': ('step2', lambda st, c: VS.round_sets(st, USER, RUN, [], {'STREET': {'verdict': 'correct', 'words': 'Make the street wider.'}}, 'Sets done', conn=c, partial=True)),
    'step2: no makes the set again': ('step2', lambda st, c: VS.round_sets(st, USER, RUN, [], {'STREET': {'verdict': 'no'}}, 'Sets done', conn=c, partial=True)),
    'step2: one answer stored': ('step2', lambda st, c: VS.set_answer(st, USER, RUN, [], 'STREET', 'correct', None, 'Wider.')),
    'step2: the round file sent again orders the missing sets': ('step2', lambda st, c: VS.round_start(st, USER, RUN, [], [{'element_id': 'T_LAY', 'prompt': 'The laying of one brick, nobody in the picture.'},
                                                                                                                        {'element_id': 'FAN', 'prompt': 'The dial on its plate.'}], conn=c)),
    'step2: the round file sent again never replaces a set': ('step2', lambda st, c: VS.round_start(st, USER, RUN, [], [{'element_id': 'STREET', 'prompt': 'Another street.'}], conn=c)),
    'step2: a set not made is made now': ('step2', lambda st, c: VS.set_make(c, st, USER, RUN, [], 'T_LAY')),
    'step2: the sets queued by hand': ('step2', lambda st, c: VS._queue_sets(c, st, USER, RUN, [], ['MASON', 'T_LAY', 'FAN'])),
    'complete: nothing is judged': ('complete', lambda st, c: VS.round_sets(st, USER, RUN, [], {'STREET': {'verdict': 'no'}}, 'again', conn=c)),
    'complete: nothing is made': ('complete', lambda st, c: VS.set_make(c, st, USER, RUN, [], 'STREET')),
    'complete: the round file sent again': ('complete', lambda st, c: VS.round_start(st, USER, RUN, [], [{'element_id': 'FAN', 'prompt': 'The dial on its plate.'}], conn=c)),
}
BEFORE = {   # the fingerprint of each case on main at d255486
    'step1: the round file sent again makes an older round again': 'ff3fe20c30ccbeb9',
    'step1: done orders every set at once': '77453abfe0f0a228',
    'step1: an answer to a set is refused': 'e50ed188e547e36d',
    'making: the sets are not judged yet': '9488f049203ee40d',
    'making: a set being made is left alone': '06962716ae8841f9',
    'step2: yes on the set, the rest not made': 'eac679458d076c75',
    'step2: correct it makes the set again with the correction': 'edef9f85a2021766',
    'step2: no makes the set again': '43325798310f791a',
    'step2: one answer stored': 'f893f8e9534c9614',
    'step2: the round file sent again orders the missing sets': 'bd95a43f3812f140',
    'step2: the round file sent again never replaces a set': '58abcb79400a80d2',
    'step2: a set not made is made now': 'd3073c3857737bbc',
    'step2: the sets queued by hand': '017c11d5cdee9084',
    'complete: nothing is judged': '08a9be5e0ca5be12',
    'complete: nothing is made': 'fb8c61bbc0c4afcf',
    'complete: the round file sent again': '30eb422088d962f9',
}


def mark(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode('utf-8')).hexdigest()[:16]


@pytest.mark.parametrize('name', list(CASES))
def test_an_older_round_gives_what_it_gave_before(name):
    got = case(*CASES[name])
    assert mark(got) == BEFORE.get(name), json.dumps(got, indent=1, sort_keys=True)[:6000]


def test_the_older_round_reads_its_states_as_before():
    assert [VS._round_pass(s, s['round']) for s in (older('step1'), older('making'), older('step2'), older('complete'))] == [1, 'making', 2, 'complete']
    assert not any(VS.round_v2(older(k)) for k in ('step1', 'making', 'step2', 'complete'))


def test_the_request_of_an_older_set_is_the_text_of_before():
    """The words themselves, beside the fingerprints: the kept preamble, the set line, the three fixed views and the film's first scene."""
    store, conn = store_of(older('step2')), FakeConn([])
    VS._queue_sets(conn, store, USER, RUN, [], ['T_LAY', 'MASON'])
    lay, mason = (p[2].obj if hasattr(p[2], 'obj') else p[2] for p in conn.inserted)
    assert lay['prompt'].startswith(VS.KEPT_PREAMBLE) and VS.KEPT_SET_LINE in lay['prompt'] and 'What the picture must represent: The brick is wet from soaking.' in lay['prompt']
    assert 'The place reads as the sandy street in front of the house, morning' in lay['prompt'] and lay['views'] == VS.set_views({'kind': 'technique', 'name': 'Laying a brick'})
    assert 'view_names' not in lay and lay['search'] is True
    assert mason['prompt'].startswith('Character sheet of The mason (MASON)') and VS.PERSON_SET in mason['prompt'] and mason['views'] == VS.PERSON_VIEWS
    s = saved(store)
    assert 'parts' not in s['round']['elements']['T_LAY'] and 'fp' not in s['round']['elements']['T_LAY']['made']


if __name__ == '__main__':   # python unit/test_design211b_older_pure.py: the fingerprints of this code, to paste into BEFORE
    VS.prices = lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0}
    print(json.dumps({name: mark(case(*CASES[name])) for name in CASES}, indent=4))
