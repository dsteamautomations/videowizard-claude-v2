"""design/221 phase 1, the critic's four points (SK, 19 Nov 2026). A1: the brief lines a rule list was written from are the ones `vw motion brief`
returned, saved beside the brief and sent with the upload; the server keeps what it is sent and works them out itself only when nothing is sent. A2: a
drawing that passed is read as not passed, on the page and at select, once its brief changed later, with the verdict refusal's words. A3: a heading is a
notes heading only when it starts with the word; a bullet "Questions for the operator:" with its sub-bullets and a "Colours to add" heading are caught; the
refusal names the lines and sends them back to the main assistant. A4: a size or proportion confirmed on the thing approves the diagram of a real thing;
the approval of all specs at once names every spec that fails. Without a database."""
import argparse
import json
import sys
from pathlib import Path

import pytest

from app import chat_flow as C, pictures as P, visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import FakeConn, motion_shot, motion_store, named, project, zipped
from test_design221_p1_pure import NEW, RULES, TILE, edit_plan, edit_session, run_with
from test_visuals_stage_pure import USER, g, saved

ROOT = Path(__file__).resolve().parents[2]


def upload(store, lines=None, run=NEW, rules=RULES):
    return VS.set_motion(store, USER, run, [], 'MO1', 'shot.zip', zipped(project()), rules, brief_lines=lines)


def all_pass(sha, store, run=NEW):
    return VS.motion_verdict(store, USER, run, [], {'shot_id': 'MO1', 'sha256': sha, 'round': 1, 'rules': [{'rule': r['rule'], 'pass': True} for r in P.rules_of(RULES)]})


WALLS = {'walls': {'thing': 'walls', 'colour': '#5A524C', 'words': 'dark warm grey', 'shots': ['MO1']}}


# ---------- A1: the lines the rules were written from travel with the upload ----------

def test_the_server_keeps_the_brief_lines_it_is_sent_and_a_brief_changed_before_the_upload_is_caught():
    store = motion_store()
    then = VS.motion_brief(store, NEW, [], 'MO1')['lines']   # what the rule writer read
    edit_session(store, lambda s: s.update(added_colours=WALLS))   # the brief changes before the upload
    sha = upload(store, lines=then)['sha256']
    assert saved(store)['motion_projects'][sha]['brief'] == then
    with pytest.raises((Problem, ValueError)) as e:
        g(lambda: all_pass(sha, store))
    assert 'the brief changed after these rules were written, in the line(s): "Palette"' in str(e.value)


def test_with_no_lines_sent_the_server_works_them_out_itself_and_bad_lines_are_refused():
    store = motion_store()
    sha = upload(store)['sha256']
    assert saved(store)['motion_projects'][sha]['brief'] == VS.motion_brief(store, NEW, [], 'MO1')['lines']
    with pytest.raises((Problem, ValueError), match='brief-lines.json'):
        g(lambda: upload(motion_store(), lines={'Fonts': 7}))


def test_the_route_takes_the_lines():
    main = (ROOT / 'server' / 'app' / 'main.py').read_text(encoding='utf-8')
    form = main[main.index('class MotionUpload'):main.index('class ChatAnswer')]
    assert 'brief_lines: dict[str, str]' in form and 'brief_lines=body.brief_lines' in main


def vw_module():
    sys.path.insert(0, str(ROOT / 'plugin' / 'scripts'))
    import vw
    return vw


def test_vw_motion_brief_saves_the_lines_and_upload_sends_them(monkeypatch, tmp_path, capsys):
    vw = vw_module()
    runs = tmp_path / 'runs'
    (runs / 'VW-9' / 'work').mkdir(parents=True)
    monkeypatch.setattr(vw, 'RUNS', runs)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'brief': '# Brief\n', 'refs': [], 'lines': {'Fonts': 'aa', 'Palette': 'bb'}})
    sent = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.update(body) or {'sha256': 'a' * 64, 'next': 'stored'})
    a = argparse.Namespace(what='brief', shot='MO1', dir=None, sha=None, at=None, zoom=None, job=None, file=None, subject=None, add=None, quote=None, crop=None)
    with pytest.raises(SystemExit):
        vw.cmd_motion(a)
    folder = runs / 'VW-9' / 'work' / 'motion' / 'MO1'
    assert json.loads((folder / 'brief-lines.json').read_text(encoding='utf-8')) == {'Fonts': 'aa', 'Palette': 'bb'}
    (folder / 'project' / 'index.html').write_text('<html>root</html>', encoding='utf-8')
    (folder / 'rules.md').write_text(RULES, encoding='utf-8')
    with pytest.raises(SystemExit):
        vw.cmd_motion(argparse.Namespace(**{**vars(a), 'what': 'upload'}))
    capsys.readouterr()
    assert sent['brief_lines'] == {'Fonts': 'aa', 'Palette': 'bb'} and sent['rules'] == RULES


# ---------- A2: a drawing that passed reads as not passed once its brief changed ----------

def test_the_fact_view_reads_a_changed_brief_as_not_passed_with_the_refusals_words():
    store = motion_store()
    sha = upload(store)['sha256']
    all_pass(sha, store)
    s = saved(store)
    job = {'unit': 'MO1', 'request': {'request_key': 'k'}}
    calls = []
    now = dict(s['motion_projects'][sha]['brief'])

    def brief_now(shot_id):
        calls.append(shot_id)
        return now
    orig = VS.load_json
    try:
        VS.load_json = lambda store_, k: {'sha256': sha}
        assert P.fact_view(s, store, job, 'MO1', brief_now)['state'] == 'pass'
        now['Palette'] = 'changed'
        v = P.fact_view(s, store, job, 'MO1', brief_now)
    finally:
        VS.load_json = orig
    assert v['state'] == 'fail' and v['faults'] == [VS.MOTION_BRIEF_CHANGED.format(shot='MO1', names='"Palette"')]
    assert calls == ['MO1', 'MO1']   # once per call
    src = Path(C.__file__).read_text(encoding='utf-8')
    assert 'def brief_now(sid):' in src and 'drawn_line(store, session, plan, job, check, fin, motion_take, brief_now)' in src


def selectable(store, sha):
    named(store, sha)
    VS.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'})
    s = saved(store)
    s['reviews'] = {'job-9': [{'id': 'r1', 'decision': 'accepted'}]}
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    prep = s['preparations']['MO1']
    row = {'id': 'job-9', 'run_id': 'run-1', 'unit': 'MO1', 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': prep['key'], 'preparation_id': 'p'},
           'result': {'key': 'k', 'sha256': 'x', 'bytes': 1, 'evidence': {'timing_matches_placement': True}}}

    class One(FakeConn):
        def execute(self, sql, params=()):
            if sql.startswith('select * from vw2_jobs where id'):
                return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row]})()
            return super().execute(sql, params)
    return One([])


def test_select_holds_a_passed_drawing_whose_brief_changed_with_the_same_words():
    store = motion_store()
    sha = upload(store)['sha256']
    conn = selectable(store, sha)
    all_pass(sha, store)
    edit_session(store, lambda s: s.update(added_colours=WALLS))
    with pytest.raises(Problem) as e:
        g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))
    assert VS.MOTION_BRIEF_CHANGED.format(shot='MO1', names='"Palette"') in str(e.value) and '--notes' in str(e.value)
    assert g(lambda: VS.select_take(conn, store, USER, NEW, [], 'job-9', 'yes', notes='taken as it is'))['job_id'] == 'job-9'


# ---------- A3: what counts as a notes heading ----------

def test_a_heading_is_a_notes_heading_only_when_it_starts_with_the_word():
    normal = ('# Rules\n## Corner note and labels:\n1. The note sits in the lower right.\n## From the note on the view\n2. The steel is cut across.\n'
              'Label notes:\n3. Every label is whole.\n')
    assert P.notes_in(normal) == []
    flagged = ('# Rules\n1. The course is solid.\n- Questions for the operator:\n  - Is the sill 230 mm?\n  - Is the tile red?\n2. The leaves match.\n'
               'Colours to add:\n- walls #5A524C\n**Notes:**\n- The client said tiles.\n## Rules again\n3. A rule.\n')
    assert P.notes_in(flagged) == ['- Questions for the operator:', '- Is the sill 230 mm?', '- Is the tile red?', '- walls #5A524C', '- The client said tiles.']
    assert [r['rule'] for r in P.rules_of(flagged) if r['rule'] in ('The leaves match.', 'A rule.')] == ['The leaves match.', 'A rule.']


def test_the_refusal_names_the_lines_and_sends_them_back_to_the_main_assistant():
    with pytest.raises((Problem, ValueError)) as e:
        g(lambda: upload(motion_store(), rules=RULES + '\n## Questions\n- Is the sill 230 mm?\n'))
    said = str(e.value)
    assert said.startswith('A note or a question is not a rule: move these lines to questions.md: "- Is the sill 230 mm?".')
    assert 'give these lines back to the main assistant' in said


def test_the_rule_writer_is_told_plainly_that_rules_md_holds_rules_only():
    rules = (ROOT / 'plugin' / 'agents' / 'vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'Every line of rules.md is a rule: no heading, question, note or colour to add goes in it.' in rules
    sys.path.insert(0, str(ROOT / 'scripts'))
    import d221b_wording_v3 as W
    import d221d_wording_v3 as D221D   # design/221, the critic's seven points and phase 3b: changes sentences of this script
    import fixset1_wording as FIX1   # fix set phase 1: the marks (still) and (motion) come after "Start every rule with `must:` or `should:`."
    import fixset2_wording as FIX2   # fix set phase 2: sentences added inside this script's sentences, and one replaced
    for file, old, new in W.HELPERS:
        assert (ROOT / 'plugin' / file).read_text(encoding='utf-8').count(FIX2.now(file, FIX1.now(file, D221D.now(file, new)))) == 1, file
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('d221(prompt, parts)') < split.index('d221b(prompt, parts)')


# ---------- A4: the real thing, approved with a size on the thing; every failing spec at once ----------

BARE = {'parts': ['tile'], 'dimensions': [{'part': 'tile', 'measure': 'length', 'value': None, 'unit': 'mm', 'status': 'unknown', 'tried': 'x'}],
        'illustrative': True, 'label': 'illustrative, not to scale'}
OBJ = {'id': 'E3', 'name': 'Pump', 'kind': 'object', 'identity': 'representative', 'requirements': 'a pump'}


def real_store(element, shots=('MO1',)):
    store = motion_store(sh=motion_shot(graphic_kind='diagram', element_ids=[element['id']], drawing_spec=BARE))
    def change(d):
        d['elements'].append(element)
        if 'MO2' in shots:
            d['gaps'][0]['scenes'][0]['shots'][1] = {**motion_shot(id='MO2', start_frame=100, end_frame=500, graphic_kind='diagram', element_ids=[element['id']], drawing_spec=BARE)}
    edit_plan(store, change)
    return store


def test_a_size_or_proportion_confirmed_on_the_thing_approves_the_diagram():
    assert VS.approve_spec(real_store(TILE), USER, NEW, [], 'MO1', 'yes')['shot_id'] == 'MO1'   # the tile carries a proportion and a confirmed length
    sized = {**OBJ, 'material_spec': {'parts': ['pump'], 'laid': 'standing', 'pattern': 'single',
                                      'dimensions': [{'part': 'pump', 'measure': 'height', 'value': 900, 'unit': 'mm', 'source': 'maker sheet', 'status': 'confirmed'}]}}
    assert VS.approve_spec(real_store(sized), USER, NEW, [], 'MO1', 'yes')['shot_id'] == 'MO1'
    with pytest.raises(Problem, match='has no proportion and no known size'):
        g(lambda: VS.approve_spec(real_store(OBJ), USER, NEW, [], 'MO1', 'yes'))
    assert VS.known_on_things({'elements': [TILE]}, {'element_ids': ['E2']}) and not VS.known_on_things({'elements': [OBJ]}, {'element_ids': ['E3']})


def test_approving_all_specs_names_every_spec_that_fails_in_one_refusal():
    store = real_store(OBJ, shots=('MO1', 'MO2'))
    with pytest.raises(Problem) as e:
        g(lambda: VS.approve_specs(store, USER, NEW, [], 'yes'))
    assert 'shot MO1: this diagram draws a real thing' in str(e.value) and 'shot MO2: this diagram draws a real thing' in str(e.value)
    assert 'MO2' not in (saved(store).get('spec_approvals') or {})   # nothing saved
