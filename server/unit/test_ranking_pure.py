"""SK, 23 Nov 2026 (VW-25 options, plan of action Phase 3). Scene 8 of VW-25 had 139 allowed pieces and used four; the order the assistant read
them in was made on the operator's computer (kind of fit, then the order of the clips), and no page could use it. The server now ranks the
pieces of each scene, by fixed rules (no model, no cost): kind of fit (exact, partly, related, same chapter, B-roll from another chapter), grade,
no warning before warned, the best piece of each clip before a second piece of any clip, a piece already in the cut last. The assistant's files,
the B-roll list of a scene, the review page's "Other clips" and the ledger read this one order. Older way retired: the ordering in the tool."""
import sys
from pathlib import Path

from app.stage2 import ledger as L, package as P

SERVER = Path(__file__).resolve().parents[1]
BEAT = {'beat_id': 'B1', 'process_stages': ['Placing the tiles'], 'steps': [{'step_id': 'B1.S1', 'text': 'The mason places Mangalore tiles between the steel bars.'}]}


def piece(name, clip, kind=None, match=None, grade='A', flags=(), what='', eligible=True, chapter='Placing the tiles'):
    fits = [{'scene': 'B1', 'step_id': 'B1.S1', 'match': match}] if match else []
    return {'sub_clip_id': name, 'clip_id': clip, 'clip_name': clip + '.mp4', 'grade': grade, 'risk_flags': list(flags), 'what': what, 'process_stage': chapter,
            'eligibility': 'ELIGIBLE_AS_IS' if eligible else 'REJECT_ALL', 'fit_kinds': {'B1': kind} if kind else {}, 'sentence_fits': fits, 'primary_fits': [], 'secondary_fits': []}


def order(rows, **more):
    return [(x['sub_clip_id'], x['kind']) for x in P.ranked(rows, BEAT, **more)]


def test_kind_of_fit_then_grade_then_no_warning_first():
    rows = [piece('chapter-A', 'c1', 'chapter'), piece('related-A', 'c2', 'related', 'RELATED'), piece('partly-A', 'c3', 'direct', 'PARTLY'), piece('exact-C', 'c4', 'direct', 'EXACT', 'C'),
            piece('exact-A-warned', 'c5', 'direct', 'EXACT', flags=['glances at the camera']), piece('exact-A', 'c6', 'direct', 'EXACT'), piece('exact-B', 'c7', 'direct', 'EXACT', 'B'),
            piece('refused', 'c8', 'direct', 'EXACT', eligible=False)]
    assert order(rows) == [('exact-A', 'exact'), ('exact-A-warned', 'exact'), ('exact-B', 'exact'), ('exact-C', 'exact'), ('partly-A', 'partly'), ('related-A', 'related'), ('chapter-A', 'chapter')]
    assert order([piece('by-paragraph', 'c1', 'direct')]) == [('by-paragraph', 'exact')]      # a film packaged by paragraph has no marks: direct is exact
    assert order([]) == [] and order([piece('odd', 'c1', 'chapter', grade=None)]) == [('odd', 'chapter')]


def test_the_best_piece_of_each_clip_comes_before_a_second_piece_of_any_clip():
    rows = [piece('c1-first', 'c1', 'chapter'), piece('c1-second', 'c1', 'chapter'), piece('c1-third', 'c1', 'chapter'), piece('c2-B', 'c2', 'chapter', grade='B'), piece('c3-exact', 'c1', 'direct', 'EXACT')]
    assert [n for n, _ in order(rows)] == ['c3-exact', 'c1-first', 'c2-B', 'c1-second', 'c1-third']   # variety inside a kind of fit; an exact fit is never pushed below a chapter fit


def test_a_piece_already_in_the_cut_goes_last():
    rows = [piece('used', 'c1', 'direct', 'EXACT'), piece('free', 'c2', 'chapter')]
    assert [n for n, _ in order(rows, used={'used'})] == ['free', 'used']


def test_b_roll_from_another_chapter_needs_a_shared_word_and_is_a_short_list():
    rows = [piece('own', 'c1', 'chapter'), piece('tiles', 'c2', what='Stacked Mangalore tiles beside the wall.', chapter='Stacking'), piece('dog', 'c3', what='A dog sleeps in the yard.', chapter='Yard'),
            piece('bars', 'c4', what='Steel bars are tied.', grade='B', chapter='Steel')] + [piece(f'more{i}', f'm{i}', what='tiles', chapter='Stacking') for i in range(20)]
    got = order(rows)
    assert got[:3] == [('own', 'chapter'), ('tiles', 'b-roll'), ('bars', 'b-roll')]            # most shared words first; on a tie the better grade
    assert ('dog', 'b-roll') not in got                                                       # shows nothing the words are about: not offered
    assert sum(1 for _, k in got if k == 'b-roll') == P.BROLL_LIST                             # short, so a scene's file stays readable
    assert order(rows, broll=0) == [('own', 'chapter')]
    quiet = {**BEAT, 'steps': []}
    assert [x['kind'] for x in P.ranked(rows, quiet)] == ['chapter']                           # a scene with no words: no B-roll is guessed


def test_the_package_carries_the_order_and_the_ledger_says_the_rank():
    rows = [piece('a', 'c1', 'chapter'), piece('b', 'c2', 'chapter', grade='B'), piece('c', 'c3', 'chapter', grade='C')]
    pk = P.build({'code': 'VW-0'}, {'process_stages': ['Placing the tiles']}, [{**BEAT, 'timeline_start_frame': 0, 'timeline_end_frame': 100, 'target_beat_frames': 100}],
                 [], rows, set(), [], [], {'fps': 25, 'width': 1920, 'height': 1080}, {}, '', {'sentences': []})
    assert pk['ranked'] == {'B1': [{'sub_clip_id': 'a', 'kind': 'chapter'}, {'sub_clip_id': 'b', 'kind': 'chapter'}, {'sub_clip_id': 'c', 'kind': 'chapter'}]}
    doc = {'options': [{'option_number': 1, 'beat_id': 'B1', 'events': [{'sub_clip_id': 'a'}]}]}
    why = {r['sub_clip_id']: r['reason'] for r in L.rows(pk, doc)}
    assert why['c'] == 'fits B1 (chapter); ranked 3 of 3 for B1, where the proposal used 1; the proposal did not name it'


def test_the_tool_reads_the_servers_order_and_lists_the_b_roll_with_its_chapter():
    sys.path.insert(0, str(SERVER.parent / 'plugin' / 'scripts'))
    import vw
    rows = [piece('chapter-A', 'c1', 'chapter'), piece('exact-B', 'c2', 'direct', 'EXACT', 'B'), piece('tiles', 'c3', what='Stacked Mangalore tiles.', chapter='Stacking'), piece('dog', 'c4', what='A dog.', chapter='Yard')]
    data = {'beats': [BEAT], 'sub_clips': rows, 'cards': [], 'ranked': {'B1': P.ranked(rows, BEAT)}}
    scenes, other = vw.pieces_by_scene(data)
    assert [(p['sub_clip_id'], p['fit']) for p in scenes[0]['pieces']] == [('exact-B', 'direct'), ('chapter-A', 'chapter'), ('tiles', 'b-roll')]
    assert scenes[0]['pieces'][2]['chapter'] == 'Stacking'                                     # the list says which chapter a B-roll piece comes from
    assert [p['sub_clip_id'] for p in other] == ['tiles', 'dog']                               # a B-roll piece is still listed once among the pieces that fit no scene
    old, _ = vw.pieces_by_scene({k: v for k, v in data.items() if k != 'ranked'})              # a package prepared before this release: the tool's own order, as before
    assert [p['sub_clip_id'] for p in old[0]['pieces']] == ['exact-B', 'chapter-A']
