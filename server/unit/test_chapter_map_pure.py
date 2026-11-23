"""SK, 23 Nov 2026 (VW-25 options, plan of action Phase 1.4 and 1.5). A reused clip study carries the chapter names of the film it was made for.
VW-25's brief named its chapters a little differently ("Cement, sand, aggregates and steel" for "Cement, steel, sand and aggregates"), so 30 to 59
pieces fitted no scene. 1.4: such names are listed when the scenes are asked for; the scenes file maps each to a chapter of this film or to none
(`chapter_map`); the server applies the map. 1.5: the brief is given the chapter names the client's stored footage carries and reuses a name when
the meaning is the same. This narrows design/56 L10 (the last brief's chapters are never shown): they are still never shown as a recommended list."""
import json
import sys
from pathlib import Path

import pytest

from app import core
from app.stage2 import ledger as L, package as P

SERVER = Path(__file__).resolve().parents[1]
CHAPTERS = ['Cement, sand, aggregates and steel', 'Placing the tiles']


def piece(n, chapter):
    return {'sub_clip_id': f'c1:S{n}', 'clip_id': 'c1', 'clip_name': 'c1.mp4', 'eligibility': 'ELIGIBLE_AS_IS', 'process_stage': chapter, 'primary_fits': [], 'secondary_fits': []}


def test_names_that_are_not_chapters_of_this_film_are_listed_with_the_nearest_chapter():
    rows = [piece(1, 'Placing the tiles'), piece(2, 'Cement, steel, sand and aggregates'), piece(3, 'Cement, steel, sand and aggregates'), piece(4, 'The site office'), piece(5, None)]
    assert P.apply_chapter_map(rows, CHAPTERS, {}) == [{'name': 'Cement, steel, sand and aggregates', 'pieces': 2, 'nearest': 'Cement, sand, aggregates and steel'},
                                                      {'name': 'The site office', 'pieces': 1, 'nearest': ''}]
    assert [r['process_stage'] for r in rows] == ['Placing the tiles', 'Cement, steel, sand and aggregates', 'Cement, steel, sand and aggregates', 'The site office', None]   # nothing guessed
    assert P.apply_chapter_map([piece(1, 'Anything')], [], {}) == []                    # a film with no chapters: nothing to map to, nothing to ask


def test_the_map_gives_a_piece_this_films_chapter_and_none_means_none():
    rows = [piece(1, 'Cement, steel, sand and aggregates'), piece(2, 'The site office'), piece(3, 'Placing the tiles')]
    left = P.apply_chapter_map(rows, CHAPTERS, {'Cement, steel, sand and aggregates': CHAPTERS[0], 'The site office': ''})
    assert left == []
    assert (rows[0]['process_stage'], rows[0]['process_stage_study']) == (CHAPTERS[0], 'Cement, steel, sand and aggregates')
    assert (rows[1]['process_stage'], rows[1]['process_stage_study']) == (None, 'The site office')
    assert 'process_stage_study' not in rows[2]
    windows = [{'beat_id': 'B1', 'timeline_start_frame': 0, 'timeline_end_frame': 100, 'process_stages': [CHAPTERS[0]]}]
    assert P.scene_fits_by_sentence(rows, windows, [{'start_frame': 0}], {})[0]['fit_kinds'] == {'B1': 'chapter'}   # the mapped piece now fits its scene
    pk = {'sub_clips': rows, 'cards': [], 'ruled_out': [], 'project': {'process_stages': CHAPTERS}}
    why = {r['sub_clip_id']: r['reason'] for r in L.rows(pk, {'options': []})}
    assert why['c1:S2'] == "its chapter 'The site office' (from the film it was studied for) was mapped to no chapter of this film"   # the ledger says who decided


def test_a_map_is_checked_when_the_scenes_are_recorded():
    assert P.chapter_map_of({'chapter_map': {'Old': CHAPTERS[1], 'Gone': ''}}, CHAPTERS) == {'Old': CHAPTERS[1], 'Gone': ''}
    assert P.chapter_map_of({}, CHAPTERS) == {} and P.chapter_map_of({'chapter_map': None}, CHAPTERS) == {}
    with pytest.raises(ValueError, match="chapter_map: 'Old' is given 'Tiles', which is not a chapter of the brief"):
        P.chapter_map_of({'chapter_map': {'Old': 'Tiles'}}, CHAPTERS)
    with pytest.raises(ValueError, match='chapter_map is an object'):
        P.chapter_map_of({'chapter_map': ['Old']}, CHAPTERS)
    stage = (SERVER / 'app' / 'stage2' / 'stage.py').read_text(encoding='utf-8')
    assert "'chapter_map': P.chapter_map_of(document, stages)" in stage                 # recorded with the scenes, under the operator's approval
    assert "'chapters_unknown'" in stage and 'chapter_map' in json.dumps(P.SCENES_SHAPE)   # asked for in the refusal and the answer; the shape names it


class Conn:
    def __init__(self, rows):
        self.rows, self.sql = rows, ''

    def execute(self, sql, params=()):
        self.sql = sql
        return self

    def fetchall(self):
        return self.rows


def test_the_brief_is_given_the_chapter_names_of_the_clients_stored_footage():
    conn = Conn([{'code': 'VW-24', 'chapters': ['Placing the tiles', 'Curing']}, {'code': 'VW-23', 'chapters': ['Placing the tiles']}, {'code': 'VW-9', 'chapters': None}])
    assert core.library_chapters(conn, 'client-1') == [{'run': 'VW-24', 'chapters': ['Placing the tiles', 'Curing']}, {'run': 'VW-23', 'chapters': ['Placing the tiles']}]
    assert 'vw2_library' in conn.sql                                                    # only for a client whose library holds footage
    assert core.library_chapters(Conn([]), 'client-1') == [] and core.library_chapters(Conn([]), None) == []
    assert "'library_chapters': core.library_chapters(conn, run['client_id'])" in (SERVER / 'app' / 'main.py').read_text(encoding='utf-8')
    brief = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'brief')
    rule = ' '.join(brief['prompt'].split())
    assert '{library_chapters}' in rule and 'use that name letter for letter' in rule and 'never copy the list' in rule


def test_the_tool_fills_the_names_in_and_an_older_film_shows_none():
    sys.path.insert(0, str(SERVER.parent / 'plugin' / 'scripts'))
    import stages_text as T
    assert T.library_chapters_text(None) == 'none' and T.library_chapters_text([]) == 'none'
    assert T.library_chapters_text([{'run': 'VW-24', 'chapters': ['Placing the tiles', 'Curing']}, {'run': 'VW-23', 'chapters': ['Placing the tiles']}]) == \
        '- Placing the tiles (VW-24, VW-23)\n- Curing (VW-24)'
    vw = (SERVER.parent / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "'library_chapters': run.get('library_chapters') or []" in vw and "'library_chapters': m.get('library_chapters') or []" in vw
    assert ".replace('{library_chapters}', library_chapters_text(library_chapters))" in (SERVER.parent / 'plugin' / 'scripts' / 'stages_text.py').read_text(encoding='utf-8')
