"""design/215, change 3: what the picture model searched. The worker reads Gemini's grounding record defensively (the field for image
search is not verified) and stores one of four states on the pictures of a set: 'yes' (with the pages, where it gave any), 'no' (asked,
record present and empty), 'not asked' (a person's set), 'not known' (asked, no record in the answer: never guessed). The set's line says
it in its own words, on the page and in the chat. Without a database."""
import pytest

from app import chat_flow as CF, page_flow as PF, ref_sets as RS, visual_workers as VW, visuals_stage as VS
import d211_fixture as F
from test_design211b_round_pure import at_two, film, put, saved   # noqa: F401
from test_design211b_sets_pure import RUN, finder   # noqa: F401 (finder stands in for part A, on every test)
from test_visuals_stage_pure import USER

W = CF.WORDS
ASK, NO_ASK = {'search': True}, {}
WEB = {'groundingMetadata': {'groundingChunks': [{'web': {'uri': 'https://a.example/trowel', 'title': 'Trowels'}}], 'webSearchQueries': ['mason trowel']}}


@pytest.fixture(autouse=True)
def new_round(monkeypatch):
    monkeypatch.setattr(VS, 'ROUND_V', 2)


@pytest.mark.parametrize('req, cands, state', [
    (NO_ASK, [WEB], 'not asked'),                                                               # a person's set: the search is never offered
    (ASK, [WEB], 'yes'),
    (ASK, [{'groundingMetadata': {'webSearchQueries': ['mason trowel']}}], 'yes'),               # "search was used", with no page
    (ASK, [{'groundingMetadata': {'searchEntryPoint': {'renderedContent': '<div/>'}}}], 'yes'),
    (ASK, [{'groundingMetadata': {'groundingChunks': [{'image': {'uri': 'https://a.example/t.jpg'}}]}}], 'yes'),   # an image chunk, whatever its name
    (ASK, [{'groundingMetadata': {}}, {'groundingMetadata': {'groundingChunks': []}}], 'no'),    # asked, the record is there and empty
    (ASK, [{'content': {}}, {}], 'not known'),                                                   # asked, no record in the answer: never guessed
    (ASK, [], 'not known'), (ASK, [None, 'x', {'groundingMetadata': 'odd'}], 'not known'),
    (ASK, [{'groundingMetadata': {}}, WEB, {}], 'yes'),                                          # counted per set: one turn that searched is enough
])
def test_the_search_record_is_read_defensively(req, cands, state):
    assert VW._searched(req, cands) == state


def test_the_pages_are_read_from_any_chunk_that_gives_an_address():
    assert VW._sources(WEB) == [{'url': 'https://a.example/trowel', 'title': 'Trowels'}]
    assert VW._sources({'groundingMetadata': {'groundingChunks': [{'image': {'uri': 'https://a.example/t.jpg'}}, {'web': {}}, 'odd', {'web': 'odd'}]}}) == [{'url': 'https://a.example/t.jpg', 'title': None}]
    assert VW._sources({}) == [] and VW._sources({'groundingMetadata': None}) == []


def test_the_state_travels_from_the_job_to_the_picture():
    for result, want in (({'notes': 'n', 'sources': [], 'searched': 'no'}, 'no'), ({'notes': 'n', 'sources': []}, None)):
        ref = {}
        VW.keep_search(ref, result)
        assert ref.get('searched') == want


def facts(store, eid, searched=None, sources=None, kind=None):
    s = saved(store)
    row = s['round']['elements'][eid]
    for r in s['references'].values():
        if r.get('set') == row['set'] or r.get('id') == row['set']:
            r.pop('searched', None)
            r.update(**({'searched': searched} if searched else {}), sources=sources or [])
    if kind:
        row['parts'] = {**(row.get('parts') or {}), 'kind': kind}
    put(store, s)
    return RS.set_facts(s, F.plan(), eid, row)['searched']


PAGES = [{'url': 'https://a.example/1', 'title': 'One'}, {'url': 'https://a.example/2', 'title': None}]


def test_a_sets_four_states_and_their_own_words():
    store, conn = at_two()
    assert facts(store, 'T_LAY', 'yes', PAGES) == {'state': 'yes', 'text': 'The picture model searched the web: 2 pages.', 'pages': PAGES}
    assert facts(store, 'T_LAY', 'yes', PAGES[:1])['text'] == 'The picture model searched the web: 1 page.'
    assert facts(store, 'T_LAY', 'yes') == {'state': 'yes', 'text': 'The picture model searched the web. It gave no list of pages.', 'pages': []}
    assert facts(store, 'T_LAY', 'no') == {'state': 'no', 'text': 'The picture model did not search the web.', 'pages': []}
    assert facts(store, 'T_LAY') == {'state': 'not known', 'text': 'Searched: not known.', 'pages': []}        # a set stored before this release
    assert facts(store, 'T_LAY', 'not asked')['state'] == 'not asked'
    assert facts(store, 'MASON') == {'state': 'not asked', 'text': "No search was asked: a person's set is made from the description and the film's own pictures.", 'pages': []}
    assert facts(store, 'T_LAY', None, PAGES)['state'] == 'yes'   # a set stored before, whose pages were kept: it searched


def test_a_set_made_from_the_films_picture_that_did_not_search_does_not_alarm():
    assert W['web_no_footage'] == "The picture model did not search the web. It was asked to search only for what the film's picture does not show."
    assert RS.searched_said('no', [], 'footage') == W['web_no_footage'] and RS.searched_said('no', [], 'web') == W['web_no']


def test_the_line_shows_it_on_the_page_and_in_the_chat_and_names_no_amount():
    store, conn = at_two()
    facts(store, 'T_LAY', 'yes', PAGES)
    item = next(i for i in CF._round_items(CF._ctx(conn, store, USER, RUN, []), every=True) if i['id'].startswith('set:T_LAY'))
    line = item['_line']
    assert line['searched'] == {'state': 'yes', 'text': 'The picture model searched the web: 2 pages.', 'pages': PAGES}
    assert 'The picture model searched the web: 2 pages.' in CF._told(line)
    rows = dict((r[0], r[1]) for r in PF._details(line))
    assert rows['What the picture model searched'] == ['The picture model searched the web: 2 pages.', 'One: https://a.example/1', 'https://a.example/2']
