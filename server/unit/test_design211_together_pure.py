"""design/211, the three parts together (section 6.4, the merger): one v2 round walked from the digest to "complete" with the REAL `ref_find`,
`ref_sets`, `visuals_stage`, `chat_flow` and `page_flow`. Stood in for: the store (in memory), the database (a fake connection), ffmpeg (a grey
picture) and the image worker with its check (`back`: the rows the worker leaves). At every step the `then` sentence names commands the tool's
parser takes, and the next call is accepted. The same main path through the chat (`vw visuals next`). And an older round (no `v`) in each of
its states gives, on the page and in the chat, exactly what it gave at d255486 (the live film VW-24 is in the middle of such a round)."""
import copy
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from app import chat_flow as CF, page_flow as P, ref_find as RF, ref_sets as RS, visuals_stage as VS
from app.errors import Problem
from app.main import PageAnswer
import d211_fixture as F
from test_design211b_older_pure import older, whole
from test_visuals_stage_pure import FakeConn, FakeStore, USER

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugin' / 'scripts'))
import vw   # noqa: E402  (the tool: its parser is what a `then` sentence must fit)

RUN = {**F.RUN, 'image_provider': 'gemini', 'film': {'shape': {'value': 'horizontal', 'video': 'horizontal', 'fps': 25}}}
SESSION = f"{RUN['id']}/visuals/session.json"
PLAN_KEY = f"{RUN['id']}/visuals/plan-v1.json"
SHEET = 'drawing-TILE-iso-eeeeeeee'
CLIPS = [{'id': 'C001', 'name': 'C001.mp4', 'duration_s': 42.0, 'sha256': 'c' * 64}, {'id': 'C002', 'name': 'C002.mp4', 'duration_s': 20.0, 'sha256': 'c' * 64},
         {'id': 'C003', 'name': 'C003.mp4', 'duration_s': 10.0, 'sha256': 'c' * 64}]
PARSER = vw.build_parser()


@pytest.fixture(autouse=True)
def outside(monkeypatch):
    """What is outside the five modules: ffmpeg writes a grey 1920x1080 picture; the prices of the tests."""
    monkeypatch.setattr(subprocess, 'run', lambda cmd, **kw: Image.new('RGB', (1920, 1080), 'grey').save(cmd[-1]))
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})
    P._MADE.clear()


def commands(then):
    """Every `vw …` command a sentence names is one the tool's parser takes, with flags its subcommand reads. Returns the commands."""
    found = re.findall(r'`(vw [^`]+)`', then or '')
    for c in found:
        words = shlex.split(c.replace('<file>', 'f.json').replace('"<their words>"', 'words'))[1:]
        try:
            a = PARSER.parse_args(words)
        except SystemExit:
            raise AssertionError(f'the tool does not take: {c}')
        assert a.cmd != 'visuals' or not vw.visuals_flags_refused(a), c
    return found


def says(out, *names):
    """The answer carries a `then` whose commands exist; `names` are the commands it must name."""
    then = out if isinstance(out, str) else out.get('then')
    assert then, out
    got = commands(then)
    for n in names:
        assert any(c.startswith(n) for c in got), (n, then)
    return then


class Film:
    """The fixture's film, plan accepted, footage analysed, nothing searched, no round. `outputs` are the run's outputs."""

    def __init__(self, session=None, plan=None, run=RUN):
        self.run, self.plan, self.conn = run, plan or F.plan(), FakeConn([])
        for gap in self.plan['gaps']:   # a real plan's shots have their frames (the money the plan still needs is counted from them)
            for scene in gap['scenes']:
                for n, shot in enumerate(scene['shots']):
                    shot.setdefault('start_frame', n * 100), shot.setdefault('end_frame', n * 100 + 100)
        if session is None:
            session = F.specs_approved(F.session('1'), self.plan, VS.spec_digest)
            session.pop('round'), session.pop('found')
            session['references'] = {SHEET: {'id': SHEET, 'kind': 'drawing', 'element_id': 'TILE', 'status': 'approved', 'key': f"{run['id']}/visuals/drawings/TILE/iso.png", 'sha256': 'f' * 64,
                                             'width': 1600, 'height': 900, 'name': 'Roof tile: angled', 'view': 'iso'}}
            session['clip_safe_zoom'] = {'C001': 1.0, 'C002': 1.0}   # written by `prepare`: the analysed clips
        self.store = FakeStore({SESSION: whole(session), PLAN_KEY: {'document': self.plan}})
        self.store.files[f"{run['id']}/visuals/package.json"] = json.dumps({'intended_visuals': []}).encode('utf-8')
        self.outputs = [{'stage': 'media', 'unit': None, 'summary': {'clips': CLIPS}, 'files': []}, self.analysed('C001'), self.analysed('C002')]
        for c in CLIPS:
            self.store.put(f"{run['id']}/media/{c['name']}", b'video')
        for r in session['references'].values():
            if r.get('key'):
                self.store.files.setdefault(r['key'], png())
        for d in (session.get('drawings') or {}).values():
            for v in d.get('views') or []:
                self.store.files.setdefault(v['plain_key'], png())

    def analysed(self, clip):
        key = f"{self.run['id']}/analysis/{clip}.evidence.json"
        sub = {'sub_clip_id': clip + '-a', 'max_usable_window': {'in_s': 0.0, 'out_s': 18.0}, 'hero_frame_s': 6.4, 'usability_grade': 'A', 'shot_role': 'PROCESS_ACTION_B_ROLL',
               'camera_and_optics': {'native_shot_size': 'MS', 'camera_angle': 'Eye_Level'}, 'visual_action_observed': 'the mason spreads mortar', 'visual_action_uncertainty': '',
               'continuity_and_story': {'world_landmarks_and_props': ['trowel']}, 'people_and_speaker_analysis': {'people_count': 1}, 'technical_qc_and_remediation': {'defects_detected': []}}
        self.store.put(key, json.dumps({'contract_version': 'clip-log-v1', 'log': {'clip_overview': f'What {clip} shows.', 'lighting_and_weather': 'sun', 'sub_clips': [sub], 'entities': []}}).encode('utf-8'))
        return {'stage': 'analysis', 'unit': clip, 'summary': {}, 'files': [{'name': f'{clip}.evidence.json', 'key': key}]}

    # ---------- the store ----------
    def session(self):
        return json.loads(self.store.files[SESSION])

    def state(self):
        s = self.session()
        return VS._round_pass(s, s['round'])

    def row(self, eid):
        return self.session()['round']['elements'][eid]

    def do(self, fn):
        return VS.guarded(fn)

    def refused(self, fn):
        with pytest.raises((Problem, ValueError)) as e:
            VS.guarded(fn)
        return getattr(e.value, 'message', None) or str(e.value)

    # ---------- part A ----------
    def trial(self, *rows):
        frames = [{'element_id': e, 'clip': c, 'at_s': at} for e, c, at in rows]
        return self.do(lambda: RF.trial_record(self.store, USER, self.run, self.outputs, frames, RF.cut_trials(self.store, self.run, self.outputs, frames)))

    def look(self, *things, by='helper'):
        return self.do(lambda: RF.look_record(self.conn, self.store, USER, self.run, self.outputs, list(things), by))

    # ---------- part B ----------
    def post(self, file):
        return self.do(lambda: VS.round_start(self.store, USER, self.run, self.outputs, file, conn=self.conn))

    def back(self, pictures=3, fail=(), bad=()):
        """What the image worker and its check leave when the sets being made come back: `pictures` pictures each, each with its check; a thing
        in `fail` gets none; a thing in `bad` fails one line of the check on its second picture."""
        s = self.session()
        for r in list(s['references'].values()):
            if r.get('kind') == 'sheet' and r['status'] == 'generating':
                eid = r['element_id']
                if eid in fail:
                    r.update(status='failed', error=f"Google's image model {r['generation']['model']} returned no picture: SAFETY", failure={'failure': 'no_image', 'http_status': 400})
                    continue
                names = RS.view_names(next(e for e in self.plan['elements'] if e['id'] == eid))
                r.update(status='candidate', key=f"{self.run['id']}/visuals/references/{r['id']}.png", sha256='sha-' + r['id'], bytes=9, width=2752, height=1536,
                         notes='(1) One variant. (3) The request asked for wood; the photographs show bamboo.', sources=[{'url': 'https://example.org/a', 'title': 'A page'}], view=names[0], check=F._check())
                self.store.files[r['key']] = png()
                for n in range(2, pictures + 1):
                    key = f"{self.run['id']}/visuals/references/{r['id']}-{n}.png"
                    s['references'][f"{r['id']}-{n}"] = {**r, 'id': f"{r['id']}-{n}", 'set_n': n, 'key': key, 'view': names[n - 1],
                                                         'check': F._check((('the view', 'Not the view asked.'),) if eid in bad and n == 2 else ())}
                    self.store.files[key] = png()
        self.store.files[SESSION] = json.dumps(s).encode('utf-8')

    def due(self):
        return self.do(lambda: RS.looks_due(self.store, self.run, self.outputs))

    def set_looks(self, recommend=None):
        """The looks a helper sends for every set that is due; `recommend`: {eid: 'remake'|'doubt'}, the others 'use'."""
        rows = []
        for s in self.due()['sets']:
            rec = (recommend or {}).get(s['element_id'], 'use')
            rows.append({'element_id': s['element_id'], 'set': s['set'], 'recommend': rec, 'golden': s['pictures'][0]['ref'] if rec == 'use' else None, 'reason': 'Looked at against the plan.', 'chose': 'The most common variant.', 'aside': 'Nothing of the request.',
                         'pictures': [{'ref': p['ref'], 'view': p['view'], 'verdict': 'pass', 'seen': f"{p['view']}: as asked.", 'lines': [{'id': l['id'], 'pass': True, 'seen': 'As the drawing shows.' if l.get('say') else ''} for l in p['lines']]} for p in s['pictures']]})
        return self.do(lambda: RS.round_looks(self.store, USER, self.run, self.outputs, rows, 'helper'))

    def rewrite(self, rows):
        return self.do(lambda: RS.round_rewrite(self.conn, self.store, USER, self.run, self.outputs, rows))

    # ---------- part C: the page and the chat ----------
    def page(self):
        return self.do(lambda: P.page(self.conn, self.store, USER, self.run, self.outputs))

    def lines(self):
        return {l['key']: l for l in self.page()['lines']}

    def record(self, *answers):
        return self.do(lambda: P.page_record(self.conn, self.store, USER, self.run, self.outputs, list(answers)))

    def next(self):
        return self.do(lambda: CF.next_item(self.conn, self.store, USER, self.run, self.outputs))

    def decide(self, item, choice, quote='', notes=''):
        return self.do(lambda: CF.answer(self.conn, self.store, USER, self.run, self.outputs, item, choice, quote, notes))

    def ordered(self):
        """The things whose set was ordered, in order (one job each)."""
        return [(p[2].obj if hasattr(p[2], 'obj') else p[2])['reference']['element_id'] for p in self.conn.inserted]


def png():
    import io
    out = io.BytesIO()
    Image.new('RGB', (64, 48), 'white').save(out, 'PNG')
    return out.getvalue()


def ans(line, choice, notes='', pics=None):
    """The page's answer to a line, as `vw visuals page --record` sends it: it passes the server's own model."""
    return PageAnswer(line=line['line'], key=line['key'], item=line.get('item', ''), choice=choice, notes=notes, pics=pics or {}).model_dump()


def approve(line):
    """design/213: the answer the page sends for "Approve" on a set: a thing's chosen picture (here the first made), a person's `yes`."""
    return next((p['choice'] for p in line.get('pics') or [] if p.get('choice')), next(b['choice'] for b in line['buttons'] if b.get('act') == 'approve'))


def chat(film, key):
    """The chat's item of a line of the page: it says the line's parts as one text, and has the chat's own labels."""
    return next(i for i in film.do(lambda: CF._round_items(CF._ctx(film.conn, film.store, USER, film.run, film.outputs), every=True)) if i['_key'] == key)


def a_look(trial, view, verdict='pass', seen='The whole thing, sharp.', **more):
    return {'trial': trial, 'view': view, 'verdict': verdict, 'seen': seen, **more}


def searched(film):
    """Part A, as the helpers do it: the digest, trial frames, the looks. TROWEL gets two frames (one weak), TILE one, FAN none with a closest,
    BRICK is not searched, the others are searched and not found."""
    d = film.do(lambda: RF.digest_answer(film.store, film.run, film.outputs))
    assert says(d, 'vw visuals digest', 'vw visuals trial', 'vw visuals look') == RF.FIND_START and VS.round_due(film.session(), film.plan) == RF.FIND_START
    assert [c['clip'] for c in d['digest']['clips']] == ['C001', 'C002'] and [t['id'] for t in d['things']] == list(F.THINGS) and all(t['found'] is None for t in d['things'])
    assert d['things'][1]['views'] == RS.view_names(film.plan['elements'][1]) and d['things'][1]['shots']   # part B's facts, real, in part A's answer
    t = film.trial(('TROWEL', 'C001', 30.2), ('TROWEL', 'C001', 6.4), ('TILE', 'C002', 9.0), ('FAN', 'C001', 35.0))
    assert says(t, 'vw visuals look') == RF.TRIAL_NEXT and not t['failed']
    tid = {(x['elements'][0], x['at_s']): x['id'] for x in t['trials']}
    out = film.look({'element': 'TROWEL', 'clips': ['C001'], 'note': 'Two views in one clip.',
                     'looks': [a_look(tid['TROWEL', 30.2], 'side', keep=True), a_look(tid['TROWEL', 6.4], 'in the hand, lifting mortar', 'weak', 'Half covered by mortar.', keep=True)]},
                    {'element': 'TILE', 'clips': ['C002'], 'note': 'The underside only.', 'looks': [a_look(tid['TILE', 9.0], 'underside', keep=True)]},
                    {'element': 'FAN', 'clips': ['C001', 'C002'], 'note': 'No indoor wall is filmed.', 'looks': [a_look(tid['FAN', 35.0], 'whole', 'fail', 'A switch plate, not a regulator.', closest=True)]})
    assert out['refused'] == {} and out['results'] == {'TROWEL': 'found', 'TILE': 'found', 'FAN': 'none'} and out['left'] == ['MASON', 'BRICK', 'STREET', 'T_LAY']
    assert out['then'] == RF.LOOK_MORE.format(n=3, left=4, ids='MASON, BRICK, STREET, T_LAY')
    out = film.look({'element': 'MASON', 'clips': ['C001'], 'note': 'Only his hands are seen.'}, {'element': 'STREET', 'clips': ['C001', 'C002'], 'note': 'No street is filmed.'},
                    {'element': 'T_LAY', 'clips': ['C001'], 'note': 'Never seen whole.'}, {'element': 'BRICK', 'not_searched': 'The helper was stopped.'})
    assert says(out, 'vw visuals round --file') == RF.LOOK_ALL and out['left'] == []
    return tid


def round_file(film, **change):
    """The round file Claude writes: the fixture's proposals; TROWEL names no frame (the server takes those that have a look)."""
    rows = []
    for e in F.THINGS:
        rec, reason, _, first, prompt = F.ROWS[e]
        rows.append({'element_id': e, 'rec': rec, 'reason': reason, **({'first': True} if first else {}), **({'prompt': prompt} if prompt else {}), **change.get(e, {})})
    return rows


def at_step_1(film=None):
    film = film or Film()
    tid = searched(film)
    out = film.post(round_file(film))
    assert says(out, 'vw visuals page', 'vw visuals next') == RS.ROUND_POSTED.format(n=7, d=out['doubtful']) and film.state() == 1
    return film, tid


# ---------- the walk on the page ----------

def test_a_v2_round_from_the_digest_to_complete_on_the_page():
    film, tid = at_step_1()
    s = film.session()
    assert s['round']['v'] == 2 and len(s['round']['elements']['TROWEL']['frames']) == 2 and s['round']['elements']['TROWEL']['doubt'] and s['round']['elements']['FAN']['doubt']

    # step 1 on the page: the proposals, then the things in the five groups of design/212; each line with its proposal, its footage pictures and what was searched
    page = film.page()
    lines = {l['key']: l for l in page['lines']}
    G = CF.STEP1_GROUPS
    assert page['step'] == P.REFS_STEP and [l['key'] for l in page['lines']] == ['refs:proposals', 'ref:STREET', 'ref:T_LAY', 'ref:TROWEL', 'ref:FAN', 'ref:TILE', 'ref:BRICK', 'ref:MASON']
    assert [lines[k]['group'] for k in ('ref:STREET', 'ref:T_LAY', 'ref:TROWEL', 'ref:FAN', 'ref:TILE', 'ref:BRICK', 'ref:MASON')] == [G[0], G[0], G[1], G[1], G[1], G[2], G[4]]
    assert page['summary'].startswith('7 things: 6 to answer, 1 answered.') and '₹' not in json.dumps(page['lines']) + page['summary'] + page['note']   # design/212: no cost on the page; the person not in the footage needs no answer
    assert lines['refs:proposals']['buttons'][0]['label'] == 'Accept all 2' and page['layout']['kind'] == 'things'
    trowel, fan = lines['ref:TROWEL'], lines['ref:FAN']
    assert trowel['rec'] == {'do': 'footage', 'label': 'Use footage', 'choice': 'use', 'reason': F.ROWS['TROWEL'][1]} and [b['choice'] for b in trowel['buttons']] == ['use', 'set', 'fix', 'ignore']
    assert [(p['label'], p.get('weak'), p['choice'][:4]) for p in trowel['pics']] == [('side', None, 'not:'), ('in the hand, lifting mortar', True, 'not:')] and trowel['pics'][1]['note'] == 'Half covered by mortar.'
    assert trowel['case'] == 'footage' and 'search' not in trowel and trowel['used'].startswith('Used in 2 shots')
    assert 'Not searched for any thing, because they have no analysis: C003.mp4.' in page['summary'] and 'no analysis' not in json.dumps(trowel)   # design/211 review: said once, in the summary
    assert fan['search'] == {'text': 'Not in your footage. The closest picture is shown.', 'why': 'Searched: 2 clips (C001.mp4, C002.mp4).'} and fan['pics'][0]['choice'] == 'use:' + tid['FAN', 35.0]
    assert lines['ref:BRICK']['search'] == {'text': 'Not in your footage.', 'why': 'The helper was stopped.'}
    assert lines['ref:MASON']['case'] == 'auto' and [b['choice'] for b in lines['ref:MASON']['buttons']] == ['fix'] and lines['ref:MASON']['kept'] == 'A set will be made'   # not in the footage: no answer is needed
    assert 'has no picture of it' not in json.dumps(page)

    # "Not this picture" on the weak frame, "That is it" on the closest: part A changes the frames, the lines come back open
    weak = trowel['pics'][1]['choice'][4:]
    out = film.record(ans(trowel, 'pics', pics={weak: 'not'}), ans(fan, 'pics', pics={tid['FAN', 35.0]: 'use'}))
    assert out['recorded'] == ['ref:TROWEL', 'ref:FAN'] and out['refused'] == [] and film.state() == 1
    s = film.session()
    assert s['references'][weak]['status'] == 'rejected' and len(s['round']['elements']['TROWEL']['frames']) == 1 and len(s['round']['elements']['FAN']['frames']) == 1   # part A rewrote part B's rows
    lines = film.lines()
    assert len(lines['ref:TROWEL']['pics']) == 1 and lines['ref:FAN']['pics'][0]['choice'].startswith('not:') and [b['choice'] for b in lines['ref:FAN']['buttons']] == ['ignore', 'use', 'set', 'fix']
    refused = film.record(ans(lines['ref:TROWEL'], 'pics', pics={'no-such-picture': 'not'}))['refused']
    assert [r['key'] for r in refused] == ['ref:TROWEL'] and film.row('TROWEL')['frames'] == s['round']['elements']['TROWEL']['frames']

    # minor corrections (a set from the footage picture, with words), approve, make a set, leave out; then the proposals accepted: step 1 is recorded once, the first three sets are ordered;
    # MASON, a person the footage does not show, is never answered: the server has the set made (design/212)
    lines = film.lines()
    out = film.record(ans(lines['ref:TROWEL'], 'fix', 'Show the blade clean.'), ans(lines['ref:FAN'], 'use'), ans(lines['ref:BRICK'], 'set'), ans(lines['ref:TILE'], 'ignore'))
    assert out['kept'] == ['ref:TROWEL', 'ref:FAN', 'ref:BRICK', 'ref:TILE'] and film.ordered() == [] and film.state() == 1
    out = film.record(ans(film.lines()['refs:proposals'], 'accept_all'))
    assert says(out, 'vw visuals status') == RS.GO1_MAKING.format(k=3, x='106', r=2) and film.ordered() == ['MASON', 'STREET', 'T_LAY'] and film.state() == 'making'
    s = film.session()
    assert s['round']['rest'] == ['TROWEL', 'BRICK'] and s['round']['elements']['TROWEL']['clean'] and s['round']['elements']['TROWEL']['operator_words'] == ['Show the blade clean.']
    assert s['round']['elements']['FAN']['from_footage'] and s['golden']['FAN'] and s['round']['elements']['TILE']['ignored'] and 'chat_round' not in s
    waiting = {l['key']: l for l in out['page']['lines']}
    assert out['page']['step'] == P.SETS_STEP and waiting['set:TROWEL']['tag'] == CF.WORDS['tag_waiting'] and waiting['set:MASON']['state'] == 'making' and waiting['set:FAN']['state'] == 'recorded'

    # the sets come back: Claude looks first; nothing is shown or answered before
    film.back(bad=('T_LAY',))
    assert film.state() == 'looking' and says(VS.round_due(film.session(), film.plan), 'vw visuals round --looks') == RS.SETS_LOOK
    assert all(l['state'] != 'open' for l in film.page()['lines'])
    assert film.refused(lambda: VS.set_answer(film.store, USER, film.run, film.outputs, 'STREET', 'yes', None, '')) == RS.SET_NO_LOOK.format(eid='STREET')
    due = film.due()
    assert [x['element_id'] for x in due['sets']] == ['MASON', 'STREET', 'T_LAY'] and due['then'] == RS.SETS_LOOK and all(len(x['pictures']) == 3 and x['request'] and x['facts']['description'] for x in due['sets'])
    out = film.set_looks({'T_LAY': 'remake'})
    assert says(out, 'vw visuals page') == RS.SETS_PAGE and out['refused'] == {} and film.state() == 2

    # step 2 on the page: "make the rest" first, the set Claude would make again first, each set with its check, Claude's two lines on the model's notes and Claude's look
    # (design/213, 17 Nov 2026: the new layout; before: the group 'Doubtful: look at these first', the raw notes, 'Yes' / 'No' / 'Correct it')
    page = film.page()
    lines = {l['key']: l for l in page['lines']}
    assert [l['key'] for l in page['lines']] == ['sets:rest', 'set:T_LAY', 'set:MASON', 'set:STREET', 'set:TROWEL', 'set:BRICK', 'set:FAN']
    assert [b['choice'] for b in lines['sets:rest']['buttons']] == ['rest', 'rest_out'] and lines['sets:rest']['buttons'][0]['label'] == 'Make them' and lines['sets:rest']['buttons'][0]['big'] == 'Make the other 2'
    assert [b['label'] for b in chat(film, 'sets:rest')['buttons']] == ['Make the other 2 sets', 'Leave these 2 out']
    lay = lines['set:T_LAY']
    assert lay['group'] == CF.STEP2_GROUPS[0] and lay['rec']['do'] == 'remake' and lay['check'] == {'state': 'pass', 'by': "Claude's check passed: no fault found.", 'chip': "Claude's check passed", 'lines': []}   # design/214: the look passed every line; the model's stored fault ("Not the view asked.") is no longer shown
    assert 'notes' not in lay and lay['look'] == {'chose': 'The most common variant.', 'aside': 'Nothing of the request.'} and [p['label'] for p in lay['pics']] == ['A · the action at its key moment', 'B · the result just after', 'C · close on where it happens'] and lay['pics'][0]['note']
    assert lines['set:MASON']['check']['state'] == 'pass' and lines['set:MASON']['rec']['label'] == 'Use this set' and [b['choice'] for b in lines['set:MASON']['buttons']] == ['yes', 'correct', 'no']

    # one visit: "Minor corrections", "Make again", a picture chosen, and "make the other sets". Nothing is made again before Claude's rewrite; the others are ordered
    out = film.record(ans(lay, 'correct', 'Show the hand pressing the brick down.'), ans(lines['set:MASON'], 'no'), ans(lines['set:STREET'], approve(lines['set:STREET'])), ans(lines['sets:rest'], 'rest'))
    assert out['recorded'] == ['set:T_LAY', 'set:MASON', 'set:STREET', 'sets:rest'] and out['stale'] == [] and out['refused'] == []
    assert film.ordered()[3:] == ['TROWEL', 'BRICK'] and film.state() == 'making' and says(out, 'vw visuals status') == RS.ALL_MAKING.format(k=2, x='71')
    s = film.session()
    assert s['golden']['STREET'] and s['round']['go'] == 2 and s['round']['rest'] == [] and s['round']['elements']['T_LAY']['rewrite_due']['words'] == 'Show the hand pressing the brick down.'
    assert s['round']['elements']['MASON']['rewrite_due'] and s['round']['elements']['T_LAY']['corrections'] == []

    # the rewrite: the same words are refused, a new request is ordered once; the earlier one is kept
    assert film.refused(lambda: RS.round_rewrite(film.conn, film.store, USER, film.run, film.outputs, [{'element_id': 'T_LAY', 'prompt': F.ROWS['T_LAY'][4]}])) == RS.REWRITE_SAME.format(eid='T_LAY')
    out = film.rewrite([{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}, {'element_id': 'MASON', 'prompt': 'He stands straighter; the moustache is thick.'}])
    assert says(out, 'vw visuals status') == RS.REWRITE_MAKING.format(n=2, x='71') and film.ordered()[5:] == ['T_LAY', 'MASON']
    assert film.row('T_LAY')['history'][0]['added'] == F.ROWS['T_LAY'][4] and film.row('T_LAY')['round'] == 2
    film.back()
    assert film.state() == 'looking'
    due = film.due()
    clean = next(x for x in due['sets'] if x['element_id'] == 'TROWEL')
    assert sorted(x['element_id'] for x in due['sets']) == ['BRICK', 'MASON', 'TROWEL', 'T_LAY'] and [(i['role'], i['view']) for i in clean['inputs']] == [('footage', 'side')]   # the clean set is made from the frame that stands
    assert 'Show the blade clean.' in clean['request'] and 'Show the hand pressing the brick down.' in next(x for x in due['sets'] if x['element_id'] == 'T_LAY')['request']
    assert says(film.set_looks(), 'vw visuals page') == RS.SETS_PAGE and film.state() == 2

    # the sets made again say what was asked and show the set before; the clean set shows the footage picture it was made from
    lines = film.lines()
    assert lines['set:T_LAY']['asked'] == 'Made again as you asked: "Show the hand pressing the brick down."' and len(lines['set:T_LAY']['earlier']) == 3 and 'sets:rest' not in lines
    assert [(p['label'], p.get('ref_only')) for p in lines['set:TROWEL']['pics']][:2] == [('From your footage: side', True), ('A · side', None)]
    first = lambda key: approve(lines[key])
    out = film.record(ans(lines['set:MASON'], 'yes'), ans(lines['set:TROWEL'], first('set:TROWEL')), ans(lines['set:BRICK'], first('set:BRICK')), ans(lines['set:T_LAY'], 'no'))
    assert film.state() == 'rewrite' and says(out, 'vw visuals round --rewrite') == RS.rewrite_due(film.session()) == VS.round_due(film.session(), film.plan)

    # the third make is the last: "No" and "Correct it" are not offered and are held; the line offers a picture, the operator's own, or to leave it out
    assert says(film.rewrite([{'element_id': 'T_LAY', 'prompt': 'Both hands are seen; the right presses the brick.'}]), 'vw visuals status') == RS.REWRITE_MAKING.format(n=1, x='35')
    film.back()
    film.set_looks()
    lay = film.lines()['set:T_LAY']
    assert [b['choice'] for b in lay['buttons']] == ['use', 'aside'] and [p['choice'][:4] for p in lay['pics'] if p.get('choice')] == ['use:', 'use:', 'use:'] and lay['buttons'][1]['label'] == 'Leave out'
    assert lay['most'] == CF.WORDS['set_made_max_thing'].format(n=3) and lay['most'] in chat(film, 'set:T_LAY')['text']
    assert film.record(ans(lay, 'no'))['refused'][0]['key'] == 'set:T_LAY'
    held = film.do(lambda: VS.round_sets(film.store, USER, film.run, film.outputs, {'T_LAY': {'verdict': 'no'}}, 'No', conn=film.conn, partial=True))['held']
    assert held == {'T_LAY': RS.MAKES_LIMIT.format(eid='T_LAY', max=3)} and len(film.ordered()) == 8
    out = film.record(ans(lay, approve(lay)))
    assert says(out, 'vw visuals next') == P.ROUND_NEXT and film.state() == 'complete' and film.session()['round']['pass'] == 'complete'
    assert sorted(film.session()['golden']) == ['BRICK', 'FAN', 'MASON', 'STREET', 'TROWEL', 'T_LAY'] and len(film.ordered()) == 8


def test_the_other_sets_left_out_and_a_set_made_three_times_left_out_complete_the_round():
    film, _ = at_step_1()
    lines = film.lines()
    film.record(ans(lines['ref:TROWEL'], 'use'), ans(lines['ref:FAN'], 'ignore'), ans(lines['ref:BRICK'], 'set'), ans(lines['ref:TILE'], 'set'), ans(lines['refs:proposals'], 'accept_all'))
    assert film.ordered() == ['MASON', 'STREET', 'T_LAY'] and film.session()['round']['rest'] == ['BRICK', 'TILE']
    film.back()
    film.set_looks()
    lines = film.lines()
    out = film.record(ans(lines['sets:rest'], 'rest_out'), ans(lines['set:MASON'], 'yes'), ans(lines['set:STREET'], approve(lines['set:STREET'])), ans(lines['set:T_LAY'], 'no'))
    assert out['refused'] == [] and film.row('BRICK')['ignored'] and film.row('TILE')['ignored'] and film.ordered() == ['MASON', 'STREET', 'T_LAY'] and film.state() == 'rewrite'
    for n in (2, 3):   # made again twice: the limit
        film.rewrite([{'element_id': 'T_LAY', 'prompt': f'The hand presses the brick, try {n}.'}])
        film.back()
        film.set_looks()
        if n == 2:
            film.record(ans(film.lines()['set:T_LAY'], 'correct', f'Not yet, {n}.'))
    lay = film.lines()['set:T_LAY']
    out = film.record(ans(lay, 'aside', 'None of them is right.'))
    assert out['refused'] == [] and film.row('T_LAY')['ignored'] and film.row('T_LAY')['aside']['words'] == 'None of them is right.' and 'T_LAY' not in film.session()['golden']
    assert film.state() == 'complete' and says(out, 'vw visuals next') == P.ROUND_NEXT and len(film.ordered()) == 5


def test_the_round_file_sent_again_orders_nothing_and_the_thing_comes_back_as_an_open_line():
    film, _ = at_step_1()
    lines = film.lines()
    film.record(ans(lines['ref:TROWEL'], 'use'), ans(lines['ref:FAN'], 'ignore'), ans(lines['ref:BRICK'], 'ignore'), ans(lines['ref:TILE'], 'ignore'), ans(lines['refs:proposals'], 'accept_all'))
    film.back()
    film.set_looks()
    out = film.post(round_file(film, FAN={'rec': 'set', 'reason': 'It is seen closer now.'}))
    # design/211 review (M5): the plan is the same, so nothing comes back; a thing the operator left out comes back when they ask for it by name
    assert says(out, 'vw visuals round --back') == RS.MERGE_NONE and out['reopened'] == [] and film.ordered() == ['MASON', 'STREET', 'T_LAY']
    for eid in ('FAN', 'BRICK', 'TILE'):
        assert says(film.do(lambda: VS.set_aside(film.store, USER, film.run, film.outputs, eid, back=True)), 'vw visuals page') == RS.BACK_ASKED.format(eid=eid)
    lines = film.lines()
    assert [b['choice'] for b in lines['set:FAN']['buttons']] == ['approve', 'words', 'ignore'] and (lines['set:FAN']['group'], lines['set:FAN']['tag']) == (CF.STEP2_GROUPS[0], CF.WORDS['tag_back'])   # design/213: "Add words for the picture" too; in "To judge", tagged
    out = film.record(ans(lines['set:FAN'], 'approve', 'The dial is cream, not white.'), ans(lines['set:BRICK'], 'ignore'), ans(lines['set:TILE'], 'ignore'))
    assert out['refused'] == [] and film.ordered()[3:] == ['FAN'] and film.row('FAN')['operator_words'] == ['The dial is cream, not white.'] and film.row('BRICK')['ignored'] and film.state() == 'making'
    assert out['then'].startswith('3 line(s) still wait for the operator on the page') and [l['key'] for l in out['page']['lines'] if l['state'] == 'open'] == ['set:MASON', 'set:STREET', 'set:T_LAY']   # the first sets, not judged yet


# ---------- the same main path in the chat ----------

def test_the_main_path_in_the_chat_one_question_at_a_time():
    film, _ = at_step_1()
    out = film.next()
    assert out['item']['id'] == 'round1:all' and [b['choice'] for b in out['item']['buttons']] == ['accept_all', 'each']
    page = film.lines()
    assert out['item']['text'] == page['refs:proposals']['text'] and out['item']['buttons'][0]['label'] == page['refs:proposals']['buttons'][0]['label']   # the same words on both
    out = film.decide('round1:all', 'accept_all', 'yes, accept them')
    asked = []
    while out.get('item'):   # the doubtful things, one by one, each answered as Claude proposes
        item = out['item']
        line = page['ref:' + item['id'].split(':')[1]]
        assert item['text'].startswith(line['desc'] + '\n' + line['used']) and 'Claude suggests: ' in item['text'] and line['rec']['reason'] in item['text'] and [b['label'] for b in item['buttons']] == [b['label'] for b in line['buttons']][:len(item['buttons'])]
        asked.append(item['id'])
        out = film.decide(item['id'], item['buttons'][0]['choice'], item['buttons'][0]['label'])
    assert asked == ['round1:TROWEL', 'round1:FAN', 'round1:TILE', 'round1:BRICK'] and film.ordered() == ['MASON', 'STREET', 'T_LAY'] and film.state() == 'making'
    assert RS.GO1_MAKING.format(k=3, x='106', r=2) in says(out, 'vw visuals status')
    assert 'then' not in film.next()                                                           # while the sets are made: nothing to do
    film.back()
    assert says(film.next(), 'vw visuals round --looks') == RS.SETS_LOOK and film.next()['item'] is None      # Claude's turn: the chat says so too
    film.set_looks()
    answered = []
    out = film.next()
    while out.get('item'):
        item = out['item']
        answered.append('rest' if item['id'].startswith('rest:') else ':'.join(item['id'].split(':')[:2]))
        choice = 'rest' if item['id'].startswith('rest:') else 'correct' if item['id'].startswith('set:T_LAY') else item['buttons'][0]['choice']
        out = film.decide(item['id'], choice, 'my word for it', 'Show the hand pressing the brick down.' if choice == 'correct' else '')
    assert answered == ['set:MASON', 'set:STREET', 'set:T_LAY', 'rest'] and film.ordered()[3:] == ['BRICK', 'TILE'] and film.state() == 'making'
    assert RS.ALL_MAKING.format(k=2, x='71') in says(out, 'vw visuals status')                 # the second go ordered in the chat says the server's sentence
    film.rewrite([{'element_id': 'T_LAY', 'prompt': 'The right hand presses the wet brick into the mortar bed.'}])
    film.back()
    film.set_looks()
    out = film.next()
    while out.get('item'):
        out = film.decide(out['item']['id'], out['item']['buttons'][0]['choice'], 'this one')
    assert film.state() == 'complete' and sorted(film.session()['golden']) == ['BRICK', 'MASON', 'STREET', 'TILE', 'TROWEL', 'T_LAY']
    assert P.ROUND_NEXT in says(out, 'vw visuals next') and 'then' not in film.next()          # the answer that completes the round says so, once


def test_the_chat_says_the_rewrite_is_due():
    film, _ = at_step_1()
    lines = film.lines()
    film.record(ans(lines['ref:TROWEL'], 'use'), ans(lines['ref:FAN'], 'ignore'), ans(lines['ref:BRICK'], 'ignore'), ans(lines['ref:TILE'], 'ignore'), ans(lines['refs:proposals'], 'accept_all'))
    film.back()
    film.set_looks()
    out = film.next()
    while out.get('item'):
        out = film.decide(out['item']['id'], 'no', 'No')
    due = RS.rewrite_due(film.session())
    assert film.state() == 'rewrite' and due in says(out, 'vw visuals round --rewrite') and film.next()['then'] == due and due.startswith('3 set(s) wait for your rewrite: MASON (no words')


# ---------- every "what next" sentence of the three parts names commands the tool takes ----------

def test_every_what_next_sentence_names_commands_the_tool_takes():
    for module, names in ((RF, ('FIND_START', 'FIND_WORDS', 'TRIAL_NEXT', 'LOOK_MORE', 'LOOK_ALL', 'OLDER_ROUND')),
                          (RS, ('ROUND_POSTED', 'GO1_MAKING', 'ALL_MAKING', 'SETS_LOOK', 'SETS_PAGE', 'REWRITE_DUE', 'REWRITE_MAKING', 'MERGE_ASK', 'SET_NO_LOOK', 'LOOK_SET_UNKNOWN', 'MAKE_NO_QUOTE',
                                'SETS_MAKING', 'ROUND_STEP1', 'ROUND_STEP2', 'ROUND_DONE', 'MERGE_NONE', 'BACK_ASKED', 'NOT_ORDERED', 'WORD_NEEDED')),   # the second line: the sentences of the review
                          (P, ('REST_LEFT', 'REFS_HERE', 'REFS_GO', 'SETS_WAIT', 'SETS_STAND', 'SETS_NONE', 'ROUND_NEXT', 'ROUND_REFUSED', 'REFS_START'))):
        for name in names:
            commands(getattr(module, name))
    assert commands(RF.FIND_START) == ['vw visuals digest', 'vw visuals trial', 'vw visuals look'] and P.REFS_START == RF.FIND_START
    with pytest.raises(AssertionError):
        commands('Run `vw visuals round --lookz`.')
    with pytest.raises(AssertionError):
        commands('Run `vw visuals digest --file f.json`.')


# ---------- an older round (no `v`): the page and the chat as at d255486 ----------

WHEN = re.compile(r'\d{4}-\d\d-\d\dT[\d:.]+\+00:00|r\d{8}-\d{6}-\d+')


def older_view(state):
    """What both front ends give for the fixture's older round at `state`: the page, the chat's questions, the chat's next item. Times taken out."""
    film = Film(session=F.specs_approved(older(state), F.plan(), VS.spec_digest))   # the material is approved, so the page is at the references

    def call(fn):
        try:
            return VS.guarded(fn)
        except (Problem, ValueError) as exc:
            return {'refused': getattr(exc, 'message', None) or str(exc)}
    public = lambda item: {k: v for k, v in item.items() if not k.startswith('_')}
    view = {'page': call(film.page), 'items': call(lambda: [public(i) for i in CF._round_items(CF._ctx(film.conn, film.store, USER, film.run, film.outputs), every=True)]), 'next': call(film.next)}
    return json.loads(WHEN.sub('T', json.dumps(view, sort_keys=True, default=str)))


OLDER = {'step1': 'ad40300f115390166ae596bd425c9e242642c2ab3475522018ffcd10a4270577', 'making': 'f3ae90372d4fff132776ac21c001e5c3a2d74bb4e4a89ac126052cb7a634cdd3',
         'step2': '379099b3917b77ee604baebde94d75f3dba11edfb8302a465b938719bfecae69', 'complete': 'b00170c2ca9659316c629b0d1806415489fc1449448ac6484a622abe121eb0be'}   # taken on main at d255486, before the three parts


@pytest.mark.parametrize('state', sorted(OLDER))
def test_an_older_round_gives_the_page_and_the_chat_it_gave_before_design_211(state, monkeypatch):
    real = P.pic
    monkeypatch.setattr(P, 'pic', lambda key, label, mark='': real(key, label))   # defect 55: but for the content's mark in a picture's code and in the names of its two sizes, the page is that of before
    view = older_view(state)
    assert 'refused' not in view['page'] and (state == 'complete' or view['page']['step'] in (P.REFS_STEP, P.SETS_STEP))
    assert hashlib.sha256(json.dumps(view, sort_keys=True).encode()).hexdigest() == OLDER[state], json.dumps(view, sort_keys=True, ensure_ascii=False)[:3000]
    assert '"then"' not in json.dumps(view['next']) and not any('rec' in l or 'group' in l for l in view['page']['lines'])
