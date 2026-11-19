"""design/221 phase 2 (SK, 19 Nov 2026): the fact check. Row 11: each rule is a must or a should; only a failed must sends a drawing back, failed
shoulds are notes ("Passed, N notes"). Row 12: "not seen" is a third answer: the frames it needs are taken and the same checker answers, the round does
not rise; the fixed set of frames; "Continues from <shot>" in the brief. Row 13: rounds 2 and 3 answer what failed and what the fix touched; a rule
left out keeps its pass; a checker's own rule is a should unless it names a must kind. Row 9: the server draws the corner note as its own layer, in the
film's font, lower right inside the inner 90 %; the render's word-for-word check skips it; the brief says so. Row 17: a label of this shot only that is
on screen too short is a must; a label shared with a neighbouring shot of the same diagram is not counted. Without a database."""
import json
import sys
from pathlib import Path

import pytest

from app import motion as M, pictures as P, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_shot, motion_store, named, project, worker_fakes, zipped
from test_design221_p1_pure import NEW, edit_plan, visuals
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]
RULES = '# Rules\n1. must: The course is solid at sill level.\n2. should: The leader lines are evenly spaced.\n3. Must: The two leaves are the same thickness.\n'
SOLID, EVEN, LEAVES = 'The course is solid at sill level.', 'The leader lines are evenly spaced.', 'The two leaves are the same thickness.'


def upload(store, files=None, rules=RULES):
    return VS.set_motion(store, USER, NEW, [], 'MO1', 'shot.zip', zipped(files or project()), rules)['sha256']


def answer(rule, said):
    return {'rule': rule, 'pass': said, **({'where': 'at 2 s, left', 'fix': 'move it'} if said is False else {}), **({'need': 'a crop of the sill'} if said == 'not seen' else {})}


def verdict(store, sha, answers, rnd=1, extra=(), conn=None):
    return VS.motion_verdict(store, USER, NEW, [], {'shot_id': 'MO1', 'sha256': sha, 'round': rnd, 'rules': [answer(r, s) for r, s in answers.items()] + list(extra)}, conn=conn)


# ---------- row 11: must and should ----------

def test_each_rule_keeps_its_class_apart_from_its_words_and_no_class_is_a_must():
    held = P.rules_of(RULES + '4. A rule with no class.\n5. **should:** Labels sit level.\n')
    assert [(r['rule'], r['class']) for r in held] == [(SOLID, 'must'), (EVEN, 'should'), (LEAVES, 'must'), ('A rule with no class.', 'must'), ('Labels sit level.', 'should')]
    assert held[0]['id'] == P.rule_id(SOLID)   # the class is not part of the id


def test_only_a_failed_must_sends_the_drawing_back_and_failed_shoulds_are_notes():
    store = motion_store()
    sha = upload(store)
    clean = verdict(store, sha, {SOLID: True, EVEN: False, LEAVES: True})
    assert clean['failed'] == [] and clean['notes'] == [EVEN] and clean['next'].startswith('Passed, 1 note:') and 'render' in clean['next']
    back = verdict(store, sha, {SOLID: False, EVEN: False, LEAVES: True}, rnd=2)
    assert back['failed'] == [SOLID] and back['notes'] == [EVEN] and 'with the 1 note' in back['next'] and 'round 3' in back['next']
    assert saved(store)['motion_checks']['MO1'][-1]['rules'][1]['class'] == 'should'
    copied = verdict(store, sha, {'must: ' + SOLID: True, 'should: ' + EVEN: True, LEAVES: True}, rnd=3)   # a class copied into the words is not part of them
    assert copied['failed'] == [] and copied['notes'] == []


def test_the_page_shows_passed_with_notes_and_select_takes_it_without_words():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: False, LEAVES: True})
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        v = P.fact_view(saved(store), store, {'unit': 'MO1', 'request': {'request_key': 'k'}}, 'MO1')
    finally:
        VS.load_json = orig
    assert v['state'] == 'pass' and v['notes'] == [EVEN] and v['head'].startswith('Fact check: passed, 1 note.')
    conn = selectable(store, sha)
    assert g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))['job_id'] == 'job-9'


def selectable(store, sha):
    named(store, sha)
    VS.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'})
    s = saved(store)
    s['reviews'] = {'job-9': [{'id': 'r1', 'decision': 'accepted'}]}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    row = {'id': 'job-9', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': s['preparations']['MO1']['key'], 'preparation_id': 'p'},
           'result': {'key': 'k', 'sha256': 'x', 'bytes': 1, 'evidence': {'timing_matches_placement': True}}}

    class One(FakeConn):
        def execute(self, sql, params=()):
            if sql.startswith('select * from vw2_jobs where id'):
                return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row]})()
            return super().execute(sql, params)
    return One([])


# ---------- row 12: not seen ----------

def test_not_seen_is_neither_a_pass_nor_a_fail_and_the_same_checker_answers_it_in_the_same_round():
    store = motion_store()
    sha = upload(store)
    first = verdict(store, sha, {SOLID: 'not seen', EVEN: True, LEAVES: True})
    assert first['failed'] == [] and first['not_seen'] == [{'rule': SOLID, 'need': 'a crop of the sill'}]
    assert 'the same round (1)' in first['next'] and 'nothing is rebuilt' in first['next'] and not first['next'].startswith('Passed')
    again = verdict(store, sha, {SOLID: True})   # the same checker, the frame it asked for, only that rule
    assert again['failed'] == [] and again['not_seen'] == [] and again['next'].startswith('Passed, 0 notes') and again['round'] == 1
    with pytest.raises(Problem, match='is not seen: say in `need`'):
        g(lambda: verdict(store, sha, {}, extra=[{'rule': SOLID, 'pass': 'not seen'}]))


def test_a_drawing_with_a_rule_not_seen_is_not_passed_on_the_page():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: 'not seen', EVEN: True, LEAVES: True})
    orig, VS.load_json = VS.load_json, (lambda store_, k: {'sha256': sha})
    try:
        v = P.fact_view(saved(store), store, {'unit': 'MO1', 'request': {'request_key': 'k'}}, 'MO1')
    finally:
        VS.load_json = orig
    assert v['state'] == 'fail' and v['faults'] == [f'Not seen yet (a crop of the sill): {SOLID}']


def two_drawn(store, **mo2):
    def change(d):
        d['gaps'][0]['scenes'][0]['shots'][1] = motion_shot(id='MO2', start_frame=100, end_frame=500, **mo2)
    edit_plan(store, change)


def test_the_brief_names_the_shot_it_continues_from():
    store = motion_store()
    two_drawn(store)
    assert 'Continues from MO1:' in VS.motion_brief(store, NEW, [], 'MO2')['brief'] and 'Continues from' not in VS.motion_brief(store, NEW, [], 'MO1')['brief']
    store2 = motion_store()
    edit_plan(store2, lambda d: d['gaps'][1]['scenes'][0]['shots'].__setitem__(0, motion_shot(id='MO3', start_frame=900, end_frame=1150, return_of='MO1')))
    assert "Continues from MO1: this drawing is built on MO1's project" in VS.motion_brief(store2, NEW, [], 'MO3')['brief']


# ---------- row 13: later rounds ----------

def test_a_later_round_answers_what_failed_and_a_rule_left_out_keeps_its_pass():
    store = motion_store()
    sha = upload(store)
    verdict(store, sha, {SOLID: True, EVEN: True, LEAVES: False})
    sha2 = upload(store, project(**{'style.css': 'body { margin: 0; }'}))
    assert sha2 != sha
    out = verdict(store, sha2, {LEAVES: True}, rnd=2)
    rec = saved(store)['motion_checks']['MO1'][-1]
    assert out['failed'] == [] and [r.get('carried') for r in rec['rules']] == [True, True, None]
    verdict(store, sha2, {SOLID: True, EVEN: False, LEAVES: False}, rnd=2)
    sha3 = upload(store, project(**{'style.css': 'body { margin: 1px; }'}))
    with pytest.raises(Problem) as e:
        g(lambda: verdict(store, sha3, {LEAVES: True}, rnd=3))
    assert 'every rule that failed before is answered' in str(e.value) and EVEN in str(e.value)


def test_a_checkers_own_rule_is_a_should_unless_it_names_a_must_kind():
    base = {SOLID: True, EVEN: True, LEAVES: True}

    def added(rule):
        store = motion_store()
        return verdict(store, upload(store), base, extra=[{'group': 'seen', 'pass': False, 'where': 'at 2 s', **rule}])
    soft = added({'rule': 'Two leader lines cross.'})
    assert soft['failed'] == [] and soft['notes'] == ['Two leader lines cross.']
    hard = added({'rule': 'Seven bar ends show, not five.', 'class': 'must', 'kind': 'a wrong count'})
    assert hard['failed'] == ['Seven bar ends show, not five.']
    bare = added({'rule': 'A label is cut.', 'class': 'must'})
    assert bare['failed'] == [] and bare['notes'] == ['A label is cut.']   # a must with no kind named stays a should


# ---------- row 9: the corner note drawn by the server ----------

def test_the_note_layer_is_written_in_the_films_font_lower_right_inside_the_inner_90(tmp_path):
    (tmp_path / 'index.html').write_text('<html><body><div id="root"></div></body></html>', encoding='utf-8')
    note = {'text': 'Illustrative, not to scale & so on', 'fonts': ['Mukta-Regular.ttf', 'NotoSans-Variable.ttf'], 'colour': '#2B2B2B'}
    M.apply_note(tmp_path, note, 1920, 1080)
    M.apply_note(tmp_path, note, 1920, 1080)
    html = (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert html.count('id="vw-note"') == 1 and html.index('id="vw-note"') < html.index('</body>')
    assert '@font-face { font-family: "vw-note-0"; src: url("assets/fonts/Mukta-Regular.ttf"); }' in html and 'font-family:\'vw-note-0\',\'vw-note-1\',sans-serif' in html
    assert 'right:96px;bottom:54px' in html and 'font-size:24px' in html and 'color:#2B2B2B' in html and 'Illustrative, not to scale &amp; so on' in html
    M.apply_note(tmp_path / 'none', None, 1920, 1080)   # no note: nothing written, no file needed


def test_the_request_carries_the_note_from_the_spec_even_for_a_project_not_in_the_plan():
    store = motion_store()
    sha = upload(store)
    request = VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1', sha)[3]
    assert request['note'] == {'text': 'illustrative, not to scale', 'fonts': ['NotoSans-Variable.ttf'], 'colour': '#2B2B2B'}
    plain = motion_store(sh=motion_shot(drawing_spec={**motion_shot()['drawing_spec'], 'illustrative': False}))
    sha_plain = upload(plain)
    assert 'note' not in VS._motion_request(plain, VS.session_of(plain, NEW, []), NEW, 'MO1', sha_plain)[3]


def test_the_note_reads_on_the_films_ground():
    assert VS.note_colour({'foundation': {'graphic_style': {'palette': 'terracotta #B5543A, paper #F4EDE1'}}}, NEW) == '#2B2B2B'
    assert VS.note_colour({'foundation': {'graphic_style': {'palette': 'chalk #EEEEEE, background #101820'}}}, NEW) == '#F2EFE8'
    assert VS.note_colour({'foundation': {}}, {**NEW, 'film': {**NEW['film'], 'colours': {'value': 'navy ground #0B1F3A and orange'}}}) == '#F2EFE8'
    assert VS.note_colour({'foundation': {}}, NEW) == '#2B2B2B'   # no ground named: a light ground is taken


def test_the_note_is_on_every_snapshot_and_render_even_without_a_finish_but_not_in_the_check(monkeypatch, tmp_path):
    store = motion_store()
    sha = upload(store)
    worker_fakes(monkeypatch, store, tmp_path)
    seen = {}
    monkeypatch.setattr(M, 'check', lambda folder: seen.update(check=(Path(folder) / 'index.html').read_text(encoding='utf-8')) or {'ok': True, 'errors': [], 'warnings': []})
    monkeypatch.setattr(M, 'snapshot', lambda folder, at, zoom, out_dir: seen.update(snap=(Path(folder) / 'index.html').read_text(encoding='utf-8')) or [])
    for op, extra in (('check', {}), ('snapshot', {'at': [1.0]})):
        out = VS.motion_tool(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1', 'op': op, 'sha256': sha, **extra})
        assert VW.process_motion_tool({'id': f'job-{op}', 'run_id': 'run-1', 'request': {'kind': f'motion-{op}', 'request_key': out['request_key']}})[0] == 'ready'
    assert 'vw-note' not in seen['check'] and 'id="vw-note"' in seen['snap']
    request = VS._motion_request(store, VS.session_of(store, NEW, []), NEW, 'MO1', sha)[3]
    folder = VW._motion_folder(store, request, tmp_path / 'render')
    assert 'id="vw-note"' in (folder / 'index.html').read_text(encoding='utf-8')   # no finish asked: the note is there all the same


def test_the_render_skips_the_note_in_its_word_for_word_check_and_the_brief_says_the_server_draws_it():
    sm = {'sha256': 'b' * 64, 'labels': ['Solid brick-on-edge course at sill level', 'Illustrative, not to scale'], 'cues': []}
    store = motion_store(sh=motion_shot(scene_motion=sm))
    files = project(**{'compositions/wall.html': project()['compositions/wall.html'].replace('Illustrative, not to scale', '')})
    named(store, upload(store, files))
    assert VS.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'})['frames'] == 100
    b = VS.motion_brief(store, NEW, [], 'MO1')['brief']
    assert ('Corner note: "illustrative, not to scale" is drawn by the server in the lower right corner of every frame, in the box from 80 % of the width and 90 % '
            'of the height to the edges. Do not draw it, and keep that corner free.') in b   # design/221 phase 3a: the box is given
    assert 'only these: "Solid brick-on-edge course at sill level".' in b


# ---------- row 17: a label on screen too short ----------

WARN = lambda label, s: {'code': 'line_unread', 'message': f'"{label}" (1 word) is on screen {s} s (±0.01 s), under its 0.40 s floor', 'fix': 'hold it longer'}


def test_a_short_label_of_this_shot_only_is_a_must_and_one_shared_with_the_neighbour_is_not():
    report = {'warnings': [WARN('Cement', 0.36), WARN('Steel', 0.3), WARN('Aggregates', 0.2), WARN('Water', 0.31), {'code': 'file_long', 'message': 'x'}]}
    musts = VS.short_labels(report, own=['Cement', 'Steel', 'Aggregates', 'Water'], shared=['Cement', 'Steel', 'Aggregates'])
    assert musts == ['"Water" (1 word) is on screen 0.31 s (±0.01 s), under its 0.40 s floor. It is a label of this shot only, so this is a must: '
                     'keep it on screen at least its floor, then upload and check again.']
    assert VS.short_labels(report, own=['Cement'], shared=[]) == [VS.short_labels({'warnings': [WARN('Cement', 0.36)]}, ['Cement'], [])[0]]


def vw24_store():
    store = motion_store(sh=motion_shot(scene_motion={'sha256': 'b' * 64, 'labels': ['Cement', 'Steel', 'Aggregates', 'Water'], 'cues': []}))
    two_drawn(store, scene_motion={'sha256': 'c' * 64, 'labels': ['Cement', 'Steel', 'Aggregates'], 'cues': []})
    return store


class Jobs(FakeConn):
    def __init__(self, rows):
        super().__init__(rows)
        self.rows = rows

    def execute(self, sql, params=()):
        if sql.startswith('select * from vw2_jobs where id'):
            row = next(r for r in self.rows if r['id'] == params[0])
            return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row]})()
        return super().execute(sql, params)


def test_the_verdict_is_not_clean_while_the_latest_check_has_such_a_must_and_the_check_says_so():
    store = vw24_store()
    sha = upload(store)
    report = {'ok': True, 'errors': [], 'warnings': [WARN('Cement', 0.36), WARN('Water', 0.31)]}
    rows = [{'id': 'c1', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-check', 'sha256': sha}, 'result': {'ok': True, 'warnings': []}},
            {'id': 'c2', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'motion', 'status': 'ready', 'request': {'kind': 'motion-check', 'sha256': sha}, 'result': report}]
    out = verdict(store, sha, {SOLID: True, EVEN: True, LEAVES: True}, conn=Jobs(rows))
    assert len(out['failed']) == 1 and out['failed'][0].startswith('"Water" (1 word)') and 'redo' in out['next']
    assert verdict(store, sha, {SOLID: True, EVEN: True, LEAVES: True}, conn=Jobs(rows[:1]))['failed'] == []   # the latest check had none
    job = VS.motion_job(Jobs(rows), store, NEW, 'c2')
    assert job['result']['label_musts'] == out['failed']
    vw = (ROOT / 'plugin' / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert "res.get('label_musts')" in vw
    main = (ROOT / 'server' / 'app' / 'main.py').read_text(encoding='utf-8')
    assert 'visuals_stage.motion_verdict(storage(), user, run, outputs, body_dict(body), conn=conn)' in main


def test_a_check_job_names_its_project():
    store = motion_store()
    sha = upload(store)
    conn = FakeConn([])
    VS.motion_tool(conn, store, USER, NEW, [], {'shot_id': 'MO1', 'op': 'check', 'sha256': sha})
    assert conn.inserted[-1][2].obj['sha256'] == sha


# ---------- the texts ----------

def test_the_texts_say_must_and_should_not_seen_the_frames_later_rounds_and_the_note():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221b_wording_v3 as W
    import d221d_wording_v3 as D221D   # design/221, the critic's seven points and phase 3b: changes sentences of this script
    stage = D221D.before(visuals())
    st = json.loads(json.dumps(stage))
    assert W.apply(st['prompt'], st['parts']) == stage['prompt'] and st['parts'] == stage['parts']   # applying twice changes nothing
    before = W.before(stage)
    texts = {'common': stage['prompt'], **{p['name']: p['text'] for p in stage['parts']}}
    olds = {'common': before['prompt'], **{p['name']: p['text'] for p in before['parts']}}
    for where, old, new in W.PAIRS:
        assert texts[where].count(new) == 1 and olds[where].count(old) == 1, old[:50]
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(D221D.now(file, new)) == 1, file
    later = texts['later']
    frames = 'the first frame, each cue, the middle of each move, the last frame, and a close-up of each labelled part'
    assert frames in later and 'Only a failed must sends the drawing back' in later and '"not seen"' in later and 'keeps its pass' in later
    assert 'never the spec\'s not-to-scale note' in later and 'too short' in later
    check = (ROOT / 'plugin' / 'agents' / 'vw-motion-check.md').read_text(encoding='utf-8')
    assert 'A rule you cannot judge from these frames fails' not in check and '"pass": "not seen"' in check and frames in check
    assert 'do not re-measure a look rule that passed' in check and 'a wrong count, a wrong fact, a part that reads as something else, a label that cannot be read' in check
    assert 'Continues from' in check
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'Start every rule with `must:` or `should:`' in rules and 'Write no rule about the corner note' in rules
    assert 'a small break in an arrow that still reaches its end' in rules and 'a label on screen too short to read' in rules
    skill = (ROOT / 'plugin' / 'skills' / 'motion' / 'SKILL.md').read_text(encoding='utf-8')
    assert frames in skill and 'Continues from' in skill and 'drawn by the server' in skill
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert all(s in retired for s in W.RETIRED) and W.RETIRED
