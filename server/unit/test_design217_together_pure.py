"""design/217, the two halves together: a film at step 6 built with the server's own test pieces (as test_design217_server_pure.py), holding one
item of every kind (a question, the style sheet, a still that failed Claude's check with an earlier try, a graphic in 3 steps, a drawn graphic
with open rules and one with a finish, two pictures that could not be made (design/221 phase 4: the page opens only when everything is made), a picture "not checked"). The round the SERVER emits
(`page_flow.page`) is checked against the frozen fixture's shape, written to the page as the tool writes it, drawn by the REAL page in a headless
browser (the browser tests' harness), every line is answered there, the answer documents the page wrote go through the server's own record path
(`page_flow.page_record`), and the film's state is read back. Without a database: the session is held in memory, the store is a dict."""
import io
import json
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip('playwright.sync_api')

from app import chat_flow as CF, page_flow as PF, pictures as P, visuals_stage as V
from test_design217_browser_pure import ROUND as FIXTURE, answers, browser, go, page, saved   # noqa: F401 (`browser` is the fixture)
from test_design217_server_pure import RUN, USER, plan, ref, session

NOW = datetime.now(timezone.utc)
SHA = {k: k[0] * 64 for k in ('a', 'b', 'c', 'd', 'e', 'f')}


def _shot(sid, kind, start, title, states=0):
    return {'id': sid, 'title': title, 'visual_type': kind, 'narration': f'The words under {title}.', 'start_frame': start, 'end_frame': start + 120,
            **({'states': [{'what_appears': f'part {n}', 'hold_s': 1.0, 'words': f'words {n}'} for n in range(1, states + 1)]} if states else {}), 'subjects': []}


def look(*fails):
    rows = [{'id': f'f{n}', 'check': c, 'pass': False, 'seen': s} for n, (c, s) in enumerate(fails)]
    return lambda sha: {'who': 'assistant', 'at': NOW.isoformat(), 'sha256': sha, 'lines': rows + [{'id': 'ok', 'check': 'readable text', 'pass': True, 'seen': 'none'}]}


def film():
    shots = [_shot('D1', 'drawn', 955, 'What the cavities do'), _shot('D2', 'drawn', 1325, 'The wall builds itself'),
             _shot('S1', 'still', 2378, 'The finished three-storey building'), _shot('S2', 'still', 2515, 'The kiln worker with the clay pan'),
             _shot('G1', 'animation', 2620, 'Fewer bricks, fewer resources', states=3), _shot('S3', 'still', 3260, 'The housing site'),
             _shot('S4', 'still', 3400, 'The brick kiln at dusk'), _shot('S5', 'still', 3500, 'The kiln at night')]
    p = plan(*shots)
    p['gaps'][0]['gap_id'] = '5'
    ok = look()
    refs = [ref('sty', 'style', None, sha=SHA['a'], element_id='_STYLE', element_kind='style', look=ok(SHA['a'])),
            ref('k1', shot_id='S1', sha=SHA['b'], look=ok(SHA['b'])),
            ref('k2old', shot_id='S2', status='rejected', sha=SHA['f'], rejection={'notes': 'it already showed the worker walking away', 'at': '2026-11-18T10:00:00+00:00'}),
            ref('k2', shot_id='S2', sha=SHA['c'], look=look(('the people', 'three distant workers are visible, not two'), ('a real face', 'the face of a person in the footage'))(SHA['c'])),
            ref('g1', 'state', 'G1', sha=SHA['a'], look=ok(SHA['a'])),
            ref('g2', 'state', 'G1', sha=SHA['b'], generation={'prompt': 'step 2', 'parents': [{'id': 'g1'}]}, look=ok(SHA['b'])),
            ref('g3', 'state', 'G1', sha=SHA['d'], generation={'prompt': 'step 3', 'parents': [{'id': 'g2'}]}, look=look(('exact text', "it reads 'enviromental'"))(SHA['d'])),
            ref('k3', shot_id='S3', sha=SHA['e'], ready_at=(NOW - timedelta(days=1)).isoformat(), asked_at=(NOW - timedelta(minutes=P.PICTURE_LOOK_MINUTES + 1)).isoformat()),
            ref('k4', shot_id='S4', status='failed', sha=None),
            ref('k5', shot_id='S5', status='failed', sha=None),
            ref('fb', 'frame', None, status='approved', source={'media_id': 'C1'}), ref('fa', 'frame', None, status='approved', source={'media_id': 'C2'})]
    s = session(*refs)
    s['gap_neighbours'] = {'5': {'before': 'C1', 'after': 'C2'}}
    s['questions'] = {'k3': {'question': 'This picture already shows what happens later in the shot. Make a new picture, or use this one anyway?', 'fork': 'not_yet',
                             'choices': ['make a new picture', 'use this one anyway'], 'by': 'server'}}
    s['motion_checks'] = {'D1': [{'sha256': 'p' * 64, 'round': 3, 'rules': [{'rule': f'rule {n}', 'pass': True} for n in range(53)], 'stranger': ['0.1 s: a wall section.']}],
                          'D2': [{'sha256': 'q' * 64, 'round': 2, 'rules': [{'rule': f'rule {n}', 'pass': n > 1} for n in range(53)], 'stranger': ['0 s: a slab.']}]}
    s['assets'] = {}
    take = lambda jid, unit, fin, rk: {'id': jid, 'unit': unit, 'provider': 'drawn', 'status': 'ready', 'request': {'kind': 'motion', 'request_key': rk},
                                       'result': {'key': f'run-1/takes/{jid}.mp4', 'sha256': jid * 8, 'sheet_key': f'run-1/takes/{jid}-sheet.jpg',
                                                  'evidence': {'timing_matches_placement': True, 'exact_seconds': 4.8}, 'finish': fin}}
    jobs = [take('j1', 'D1', ['grain', 'vignette'], 'rk1'), take('j2', 'D2', [], 'rk2')]
    return s, p, jobs


class Store(dict):
    def __init__(self, png):
        super().__init__()
        self.png = png

    def get(self, k):
        return dict.get(self, k, self.png)

    def put(self, k, data, t):
        self[k] = data

    def exists(self, k):
        return k in self


@pytest.fixture
def server(monkeypatch):
    """The film held in memory behind the server's own functions; the calls that need the database or the GPU are recorders that change the film."""
    from PIL import Image
    out = io.BytesIO()
    Image.new('RGB', (1600, 900), (150, 170, 185)).save(out, 'PNG')
    s, p, jobs = film()
    box = {'s': s, 'p': p, 'jobs': jobs, 'calls': []}
    sv = lambda store, run, s_: box.update(s=s_)
    for name, fn in {'session_of': lambda *a, **k: box['s'], 'save_session': sv, 'current_plan': lambda *a, **k: box['p'],
                     '_accepted_shots': lambda p_, s_: [(g, sh) for g in p_['gaps'] for sc in g['scenes'] for sh in sc['shots']],
                     'route_of': lambda sh: {'animation': 'graphic_sequence'}.get(sh.get('visual_type'), sh.get('visual_type')),
                     'take_jobs': lambda conn, run, shot_id=None: box['jobs'], '_set_budget': lambda *a: None, 'visuals_spend': lambda *a: 0,
                     '_round_pass': lambda s_, rd: 'complete', 'load_json': lambda store, k: {'sha256': {'rk1': 'p' * 64, 'rk2': 'q' * 64}.get(k)},
                     'locate': lambda store, s_, sid: (box['p'], box['p']['gaps'][0], box['p']['gaps'][0]['scenes'][0], next(sh for sh in box['p']['gaps'][0]['scenes'][0]['shots'] if sh['id'] == sid)),
                     '_not_yet_gate': lambda *a, **k: None, '_fingerprints': lambda *a, **k: {}, '_feedback_image': lambda *a, **k: None, '_keep_library': lambda *a: None,
                     '_place_still': lambda store, user, run, outputs, s_, sid, rid, quote, *a: s_['assets'].__setitem__(sid, {'reference_id': rid, 'quote': quote}) or {}}.items():
        monkeypatch.setattr(V, name, fn)

    def review(conn, store, user, run, outputs, job_id, decision, notes, timing, quote):
        box['s']['reviews'].setdefault(job_id, []).append({'decision': decision, 'notes': notes})
        box['calls'].append(('review', job_id, decision, notes))
        return {}

    def select(conn, store, user, run, outputs, job_id, quote, notes='', timing='', in_s=None):
        unit = next(j['unit'] for j in box['jobs'] if j['id'] == job_id)
        box['s']['selections'][unit] = {'job_id': job_id, 'notes': notes}
        box['calls'].append(('select', job_id, notes))
        return {}

    monkeypatch.setattr(V, 'review_take', review)
    monkeypatch.setattr(V, 'select_take', select)
    monkeypatch.setattr(V, 'motion_finish', lambda conn, store, user, run, outputs, shot, on: box['calls'].append(('finish', shot, on)) or {})
    monkeypatch.setattr(P, 'alike_steps', lambda store, chain: [])
    monkeypatch.setattr(CF, 'flush_sets', lambda *a, **k: None)
    monkeypatch.setattr(CF, '_plan_items', lambda c: ([], []))
    monkeypatch.setattr(PF, '_spec_lines', lambda c: [])
    monkeypatch.setattr(PF, '_drawing_lines', lambda c: [])
    monkeypatch.setattr(PF, '_log', lambda *a, **k: None)

    def copy(store, key, mark=''):   # ffmpeg's page copy: made for the first drawing, not for the second (its frames stand in, with the round's sentence)
        if 'j2' in key:
            raise RuntimeError('ffmpeg: no copy')
        return key + '.page.mp4'
    monkeypatch.setattr(PF, 'video_copy', copy)
    box['store'] = Store(out.getvalue())
    return box


def emit(box):
    return PF.page(None, box['store'], USER, RUN, [])


def round_doc(pg):
    """The round as `vw visuals page` writes it to the page (plugin/scripts/vw.py `hand`): never `pictures` or `videos`."""
    return {'round': pg['round'], 'at': NOW.isoformat(), 'run': RUN['code'], 'step': pg['step'], 'open': pg['open'], 'summary': pg.get('summary') or '',
            'note': pg.get('note') or '', 'lines': pg['lines'], 'layout': pg['layout']}


SHAPE_EXTRA = {'refused'}   # optional on any line


def test_the_servers_round_has_the_fixtures_shape(server):
    pg = emit(server)
    want = {l['kind']: l for l in FIXTURE['lines']}
    got = {}
    for l in pg['lines']:
        got.setdefault(l['kind'], l)
    assert set(got) == set(want) == {'question', 'style', 'still', 'steps', 'drawn'}
    assert [l['kind'] for l in pg['lines']] == ['question', 'style', 'drawn', 'drawn', 'still', 'still', 'steps', 'still']   # questions, the style sheet, then film order
    for kind, line in got.items():
        assert set(line) - SHAPE_EXTRA == set(want[kind]), (kind, set(line) ^ set(want[kind]))
        if 'check' in want[kind]:
            assert set(line['check']) - {'short', 'notes'} == set(want[kind]['check']) - {'notes'}, kind   # release 1, B3: the short line is new (the fixture is a round of 0.118.0); `notes` only when there are any
        for b in line['buttons']:
            fbs = [x for fl in FIXTURE['lines'] if fl['kind'] == kind for x in fl['buttons'] if x['choice'].split(':')[0] == b['choice'].split(':')[0]]
            fb = next((x for x in fbs if x.get('needs_words') == b.get('needs_words')), fbs[0])
            assert set(b) - {'sure', 'need', 'hint', 'go', 'prefill', 'against'} == set(fb) - {'sure', 'need', 'hint', 'go', 'prefill'}, (kind, b['choice'], set(b) ^ set(fb))   # release 1, B1: `against` in place of `sure`
            assert ({'hint', 'go', 'prefill'} <= set(b)) == bool(b['needs_words'])
        for p in line['pics']:
            fp = next((x for fl in FIXTURE['lines'] if fl['kind'] == kind for x in fl['pics'] if x['role'] == p['role']), None) or next(x for fl in FIXTURE['lines'] for x in fl['pics'] if x['role'] == p['role'])
            assert set(p) - {'missing', 'check_head'} == set(fp) - {'check_head'}, (kind, p['role'], set(p) ^ set(fp))
        if kind == 'drawn':
            assert set(line['video']) == set(want[kind]['video'])
    assert set(pg['layout']) == set(FIXTURE['layout']) and pg['layout']['words']['pictures'] == FIXTURE['layout']['words']['pictures']
    assert pg['layout']['help'] == FIXTURE['layout']['help'] and 'made' not in pg['layout']   # not shown by the page: `end_foot` says it
    assert set(FIXTURE) - {'layout', 'lines'} <= set(pg) and set(pg) - set(FIXTURE) <= {'how', 'pictures', 'videos', 'pictures_failed', 'pic_docs', 'zoom_docs', 'loading'}   # fix set (a): what the page says while its pictures are sent
    assert [(c['name'], c['state']) for c in pg['layout']['coming']] == [('The brick kiln at dusk (S4)', 'failed'), ('The kiln at night (S5)', 'failed')]   # design/221: shown as could not be made
    # the video page copy: `videos` [{code, key}] for the one that was made; "" and `none` for the one that was not
    d1, d2 = (l for l in pg['lines'] if l['kind'] == 'drawn')
    assert pg['videos'] == [{'code': d1['video']['code'], 'key': 'run-1/takes/j1.mp4.page.mp4'}] and d1['video']['code'].startswith('v') and len(d1['video']['code']) == 13
    assert d1['video']['none'] == '' and d2['video']['code'] == '' and d2['video']['none'] == FIXTURE['lines'][6]['video']['none']
    assert not any(p.get('missing') for l in pg['lines'] for p in l['pics'])


def test_the_round_drawn_by_the_page_answered_there_and_recorded_by_the_server(server, browser):
    pg = emit(server)
    doc = round_doc(pg)
    L = {l['name']: l for l in doc['lines']}
    view = page(browser, doc, size='fit-large')
    W = doc['layout']['words']['pictures']
    # what the page shows is what the server sent: the list, the kinds, the check line, the labels of the buttons
    assert view.locator('#srail > ul:first-of-type .srow .snm').evaluate_all('rs => rs.map(r => r.firstChild.textContent)') == [l['name'] for l in doc['lines']]
    assert view.locator('#srail .srow .pkw').all_text_contents() == [' · '.join(x for x in (l['kind_words'], l.get('film_at')) if x) for l in doc['lines']]
    for l in doc['lines']:
        go(view, l)
        assert [b.split('\n')[0] for b in view.locator('#pbar button').evaluate_all('bs => bs.map(b => b.firstChild.textContent)')] == [b['label'] for b in l['buttons']], l['name']
        assert view.locator('#sansh').text_content() == l['ask']
        if l.get('check'):
            assert view.locator('#pcheck b').text_content() == l['check']['short'] and view.locator('#pcheck').get_attribute('data-state') == l['check']['state']   # release 1, B3: the closed line
            if l['check']['faults']:
                view.locator('#pcheckb').click()
                assert view.locator('#pfaults li').all_text_contents() == l['check']['faults']
                view.locator('#pcheckb').click()
        if l['kind'] == 'drawn' and l['video']['code']:
            view.wait_for_function("(() => { const v = document.querySelector('#pvideo'); return v && v.readyState >= 2; })()")
        if l['kind'] == 'drawn' and not l['video']['code']:
            assert view.locator('#pnone').text_content() == l['video']['none'] and view.locator('#pvideo').count() == 0
    q, sty, d1, d2 = doc['lines'][0], L['The look of the graphics'], L['What the cavities do (D1)'], L['The wall builds itself (D2)']
    s1, s2, g, s3 = L['The finished three-storey building'], L['The kiln worker with the clay pan'], L['Fewer bricks, fewer resources (G1)'], [l for l in doc['lines'] if l['kind'] == 'still'][-1]
    # answer every line on the page
    plan_ = [(q, 'c2', None), (sty, 'yes', None), (d1, 'plain', None), (d2, 'select', None), (s1, 'no', None),   # release 1, B1: Select and Yes against the check are one click
             (s2, 'yes', None),(g, 'correct:2', 'The icons should turn green.'), (s3, 'correct', 'Two workers, not three.')]
    for l, choice, more in plan_:
        go(view, l)
        view.locator(f'#pbar [data-choice="{choice}"]').click()
        if more == 'sure':
            view.locator('#ssure').click()
        elif more:
            view.locator('#sfix').fill(more)
            view.locator('#sfixsend').click()
        saved(view, l['line'], choice)
    view.wait_for_selector('#send li')
    assert view.locator('#send h2').text_content() == W['end_head']
    got = answers(view)
    view.close()
    # the answer documents, as `vw visuals page --record` sends them
    sent = [{'line': k, 'key': d['key'], 'item': d['item'], 'choice': d['choice'], 'notes': d['notes']} for k, d in sorted(got.items())]
    out = PF.page_record(None, server['store'], USER, RUN, [], sent)
    assert out['refused'] == [] and out['stale'] == [] and sorted(out['recorded']) == sorted(l['key'] for l in doc['lines'])
    s, refs = server['s'], server['s']['references']
    assert 'k3' not in s['questions'] and s['answered'][-1]['answer'] == 'use this one anyway' and refs['k3']['not_yet_ok']   # the question: the choice's own words
    assert refs['sty']['status'] == 'approved'
    assert refs['k1']['status'] == 'rejected' and refs['k1']['rejection']['notes'] == ''                                        # a bare No: no reason (F4)
    assert refs['k2']['status'] == 'approved' and s['assets']['S2']['reference_id'] == 'k2'                                     # approved against its check, placed
    assert refs['g1']['status'] == 'candidate' and refs['g2']['rejection']['notes'] == 'The icons should turn green.' and refs['g3']['rejection']['notes'] == ''   # F2: the later step made again, no reason of the server's in the library
    assert refs['g3']['rejection']['cause'] == P.W['later_step'] and not any(P.W['later_step'] in str(x) for x in (s.get('not_this') or {}).values())
    assert refs['k3']['status'] == 'rejected' and refs['k3']['rejection']['notes'] == 'Two workers, not three.'
    assert ('finish', 'D1', False) in server['calls'] and s['reviews']['j1'][-1] == {'decision': 'rejected', 'notes': "made again without the effect, at the operator's word"}
    assert s['selections']['D2'] == {'job_id': 'j2', 'notes': P.W['against_note']}                                             # held: release 1, B1: selected with one click, no reason asked; the note says so
    assert out['page']['step'] == P.W['step'] and out['page']['closed'] and out['page']['lines'] == []   # design/221 phase 4: three stills and a step are made again: the page waits
    assert out['then'].endswith(P.W['page_later']) and 'Stills: 1 answered, 2 being redone, 2 could not be made.' in out['then']
