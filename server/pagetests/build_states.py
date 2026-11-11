"""Builds the payload of every screen state of the visuals page, as JSON under pagetests/data/<name>/.

How: a visuals session is assembled in memory with the unit tests' own fakes (FakeStore, FakeConn) and the server's own stage
functions (round_start, round_done, round_sets, treatment, approve_spec ...). What a worker or a provider would write (a set's pictures
coming back, a take job row) is set on the session or the fake jobs table the way the unit tests do it. Then the REAL
visuals_stage.page_view makes the payload. Only the small `run` block is written here (web.py's _visuals_payload reads it from the
database through core.next_for).

    python pagetests/build_states.py                         # this working tree  -> data/main
    python pagetests/build_states.py --rev ed8dcb9 --name live   # the server code of a git revision -> data/live
"""
import argparse
import copy
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
REPO = SERVER.parent

ap = argparse.ArgumentParser()
ap.add_argument('--rev', help='build with the server/ folder of this git revision (default: the working tree)')
ap.add_argument('--name', help='folder under data/ (default: main, or the revision)')
args = ap.parse_args()
root = SERVER
if args.rev:
    tar = subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar', args.rev, 'server'], capture_output=True, check=True).stdout
    tmp = tempfile.mkdtemp(prefix='vw2-states-')
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(tmp, filter='data')
    root = Path(tmp) / 'server'
sys.path[:0] = [str(root), str(root / 'unit')]
os.environ.setdefault('VW2_DATABASE_URL', '')

from app import visuals_stage as VS   # noqa: E402
import test_visuals_stage_pure as S   # noqa: E402
import test_design151_refs_pure as R   # noqa: E402

USER, NEW, OLD = S.USER, R.NEW, R.OLD
PRICES = {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0}
VS.prices = lambda: PRICES   # as the unit tests: fixed prices, no settings file
BRICK = {'id': 'BRICK', 'name': 'Red brick', 'kind': 'material', 'identity': 'exact', 'requirements': 'the client\'s fired red brick',
         'material_spec': {'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 190, 'unit': 'mm', 'source': 'the client brief p.2', 'status': 'confirmed'},
                                          {'part': 'brick', 'measure': 'height', 'value': 90, 'unit': 'mm', 'source': 'the client brief p.2', 'status': 'confirmed'},
                                          {'part': 'joint', 'measure': 'thickness', 'value': 10, 'unit': 'mm', 'source': 'measured on C0120 at 12 s', 'status': 'measured'}],
                           'laid': 'on edge, header ends to the camera', 'joint': '10 mm mortar joints', 'pattern': 'one long face alternating with one header per course',
                           'proportions': ['long face a little more than twice as wide as tall'], 'relationships': [], 'label': ''}}
DSPEC = {'dimensions': [{'part': 'cavity', 'measure': 'width', 'value': 75, 'unit': 'mm', 'source': 'the client brief p.3', 'status': 'confirmed'},
                        {'part': 'leaf', 'measure': 'thickness', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown', 'tried': 'not in the client material'}],
         'proportions': ['both leaves the same thickness'], 'relationships': ['the cavity sits between the two leaves'], 'label': 'air gap'}
TREAT = {'direction': 'technical record with scenes of work',
         'gaps': [{'gap_id': 'G1', 'intended': ['The plinth, measured.'], 'picture': 'the plinth top with its width marked', 'routes': ['still'], 'seconds': 20, 'images': 1},
                  {'gap_id': 'G2', 'intended': [], 'picture': 'water poured over a finished wall in the yard', 'routes': ['video'], 'seconds': 10, 'images': 1, 'departure': ''}]}
ROWS = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'},
        {'element_id': 'P1', 'prompt': 'kneels all day'}, {'element_id': 'BRICK', 'prompt': 'the fired red brick, one course'}]
APPROVE = lambda rows: {r['element_id']: {'verdict': 'approve'} for r in rows}


class Conn(S.FakeConn):
    """The unit tests' FakeConn, plus the one row add_asset reads from vw2_files."""
    files = {}

    def execute(self, sql, params=()):
        if 'from vw2_files' in sql:
            row = self.files.get(params[1])
            return type('R', (), {'fetchone': lambda _: row, 'fetchall': lambda _: [row] if row else []})()
        return super().execute(sql, params)


def film(els=(R.KILN, R.MASON, BRICK), run=NEW, g1=None, g2=None, frame='candidate', tweak=None, **over):
    """A film with a recorded treatment and an accepted plan: G1 one still shot, G2 one video shot; E1 has a footage frame."""
    doc = R.doc_with(*els)
    if g1:
        doc['gaps'][0]['scenes'][0]['shots'] = g1
    if g2:
        doc['gaps'][1]['scenes'][0]['shots'] = g2
    if tweak:
        tweak(doc)
    f1 = {**S.ref('F1', frame), 'kind': 'frame', 'element_id': 'E1', 'width': 1920, 'height': 1080}
    over.setdefault('accepted', S.accepted(doc))
    store = R.new_store(doc, {'F1': f1}, **over)
    VS.treatment(store, USER, run, [], TREAT, 'Yes, this treatment.')
    return doc, store, Conn([])


def sets_back(store, counts=None):
    """What the image worker writes when a set comes back: each set row becomes a candidate with its file, its siblings beside it (as with_sets in the unit tests)."""
    s = S.saved(store)
    for r in list(s['references'].values()):
        if r.get('kind') != 'sheet' or r.get('status') != 'generating':
            continue
        r.update(status='candidate', sha256='sha-' + r['id'], key=f"run-1/visuals/references/{r['id']}.png", notes='(1) one method chosen', sources=[{'url': 'https://example.org/kiln', 'title': 'kiln'}])
        for k in range(2, (counts or {}).get(r['element_id'], 3) + 1):
            s['references'][f"{r['id']}-{k}"] = {**r, 'id': f"{r['id']}-{k}", 'set_n': k, 'sha256': f"sha-{r['id']}-{k}", 'key': f"run-1/visuals/references/{r['id']}-{k}.png"}   # its own file, as the image worker stores each picture of a set (visual_workers: the set's extra pictures)
    VS.save_session(store, NEW, s)
    return s


def sheets(s, eid, status='candidate'):
    return sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid and r['status'] == status)


def step1(spec=True, rows=ROWS, **kw):
    doc, store, conn = film(**kw)
    if spec and any(r['element_id'] == 'BRICK' for r in rows):
        VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')
    VS.round_start(store, USER, NEW, [], rows, conn=conn)
    return doc, store, conn


def step2(spec=True, verdicts=None, rows=ROWS, **kw):
    doc, store, conn = step1(spec, rows, **kw)
    VS.round_done(store, USER, NEW, [], verdicts or APPROVE(rows), 'Yes, the frame.', conn=conn)
    return doc, store, conn, sets_back(store, {'E2': 2})


def yes_all(store, conn, s, **other):
    v = {eid: {'verdict': 'yes', **({} if eid.startswith('P') else {'golden': sheets(s, eid)[0]})} for eid, r in s['round']['elements'].items() if sheets(s, eid)}
    return VS.round_sets(store, USER, NEW, [], {**v, **other}, 'Pass one.', conn=conn)


def complete(**kw):
    doc, store, conn, s = step2(**kw)
    yes_all(store, conn, s)
    return doc, store, conn


def edit(store, fn):
    s = S.saved(store)
    fn(s)
    VS.save_session(store, NEW, s)


def keyframe(rid, shot, status='candidate', **over):
    return {**S.ref(rid, status), 'shot_id': shot, **over}


def take(jid, shot, status='ready', provider='video', **over):
    done = status == 'ready'
    return {'id': jid, 'unit': shot, 'run_id': 'run-1', 'provider': provider, 'status': status, 'request': {'duration_seconds': 10}, 'error': None, 'cost': None,
            'result': {'key': f'run-1/visuals/takes/{jid}.mp4', 'sha256': 's-' + jid, 'evidence': {'duration_seconds': 10.0, 'timing_matches_placement': True}} if done else None, **over}


def start_approved(store):
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'VS1', 'approved', role='start')))


# ---------- the states: name -> (tab, builder returning (store, conn, run) or (store, conn, run, extra)) ----------

STATES = {}


def state(name, tab, **meta):
    def deco(fn):
        STATES[name] = (tab, meta, fn)
        return fn
    return deco


# References, kept film
@state('refs-no-round-kept', 'references')
def _():
    _, store, conn = film()
    return store, conn, NEW


@state('refs-step1-to-answer', 'references')
def _():
    _, store, conn = step1(spec=False)
    return store, conn, NEW


@state('refs-step1-answered', 'references')
def _():
    _, store, conn = step1()
    VS.approve_reference(store, USER, NEW, [], 'F1', 'sha-F1', 'Yes.', conn=conn)
    return store, conn, NEW


@state('refs-sets-being-made', 'references')
def _():
    _, store, conn = step1()
    VS.round_done(store, USER, NEW, [], APPROVE(ROWS), 'Yes, the frame.', conn=conn)
    return store, conn, NEW


@state('refs-step2-all-sets-back', 'references')
def _():
    _, store, conn, _s = step2()
    return store, conn, NEW


@state('refs-step2-some-sets-not-made', 'references')
def _():
    _, store, conn, _s = step2(spec=False)   # the brick's material spec is not approved: the server refuses its set and stores the reason on the row
    return store, conn, NEW


@state('refs-step2-second-pass', 'references')
def _():
    _, store, conn, s = step2()
    yes_all(store, conn, s, P1={'verdict': 'no', 'words': 'too young'})
    sets_back(store)
    return store, conn, NEW


@state('refs-round-complete', 'references')
def _():
    _, store, conn = complete()
    return store, conn, NEW


@state('refs-step2-element-ignored', 'references')
def _():
    _, store, conn, _s = step2(verdicts={**APPROVE(ROWS), 'P1': {'verdict': 'ignore'}})
    return store, conn, NEW


# References, older film (searches and picks)
def older():
    from PIL import Image
    png = io.BytesIO()
    Image.new('RGB', (64, 48), (120, 80, 40)).save(png, format='PNG')
    rows = [{'n': n, 'thumbnail': f'https://t.example/{n}.jpg', 'image_url': f'https://img.example/{n}.jpg', 'page_url': f'https://site.example/p{n}', 'site': 'site.example', 'width': 800, 'height': 600, 'title': f'kiln {n}'} for n in (1, 2, 3)]
    VS.apify.search_images = lambda keywords, n=10: rows
    VS.fetch_image = lambda url: png.getvalue()
    doc, store, conn = film(els=(R.KILN,), run=OLD)
    VS.round_start(store, USER, OLD, [], [{'element_id': 'E1', 'frames': ['F1'], 'keywords': 'village plinth Tamil Nadu'}, {'element_id': 'E2', 'frames': [], 'keywords': 'brick kiln Tamil Nadu'}])
    VS.search(store, USER, OLD, [], 'E2', 'clamp kiln Tamil Nadu', 'Yes, search for the kiln.')
    return store, conn


@state('refs-older-pass1', 'references')
def _():
    store, conn = older()
    return store, conn, OLD


@state('refs-older-pass2', 'references')
def _():
    store, conn = older()
    VS.round_done(store, USER, OLD, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'search'}}, 'Yes: the first frame.')
    return store, conn, OLD


@state('refs-older-no-round-element-view', 'references')
def _():
    store, conn = older()
    VS.round_done(store, USER, OLD, [], {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'search'}}, 'Yes: the first frame.')
    sid = S.saved(store)['round']['elements']['E2']['search_id']
    VS.round_picks(store, USER, OLD, [], {sid: [{'n': 1, 'note': 'colour only'}]}, 'This one, colour only.')
    return store, conn, OLD


# Treatment and plan
@state('treatment-draft', 'treatment')
def _():
    store = S.store_with(S.session())
    VS.treatment(store, USER, NEW, [], TREAT, '')
    return store, Conn([]), NEW


@state('treatment-accepted', 'treatment')
def _():
    store = S.store_with(S.session())
    VS.treatment(store, USER, NEW, [], TREAT, 'Yes, this treatment.')
    return store, Conn([]), NEW


@state('plan-proposed', 'plan')
def _():
    _, store, conn = film(accepted={})
    return store, conn, NEW


@state('plan-accepted', 'plan')
def _():
    _, store, conn = film()
    return store, conn, NEW


@state('plan-gap-sent-back', 'plan')
def _():
    _, store, conn = film()
    VS.revise_gap(store, USER, NEW, [], 'G1', 'Show the plinth from above, not from the side.', 'Change gap one.')
    return store, conn, NEW


# Pictures
@state('pictures-nothing-yet', 'pictures')
def _():
    _, store, conn = complete()
    return store, conn, NEW


@state('pictures-candidate', 'pictures')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1')))
    return store, conn, NEW


@state('pictures-approved', 'pictures')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1')))
    VS.approve_reference(store, USER, NEW, [], 'K1', 'sha-K1', 'Yes.', conn=conn)
    return store, conn, NEW


@state('pictures-failed-check', 'pictures')
def _():
    _, store, conn = complete()
    lines = [{'check': 'the width mark', 'pass_when': 'reads 230 mm', 'weight': 'must'}, {'check': 'daylight', 'pass_when': 'warm, from the left', 'weight': 'should'}]
    failed = [{'check': 'the width mark', 'weight': 'must', 'pass': False, 'saw': 'the mark reads 320 mm'}]
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1', answer={'status': 'ready', 'prompt': 'p', 'checklist': lines, 'exact_text': []},
                                                              check={'lines': failed + [{'check': 'daylight', 'weight': 'should', 'pass': True, 'saw': 'warm light'}], 'must_failed': failed, 'model': 'gemini'})))
    return store, conn, NEW


def with_spec(vt):
    g1 = [S.shot('IM1', 0, 250, vt, element_ids=['E1'], drawing_spec=copy.deepcopy(DSPEC)), S.shot('DG2', 250, 500, vt, element_ids=['E1'], drawing_spec=copy.deepcopy(DSPEC))]
    return complete(g1=g1)


@state('pictures-drawing-specs-waiting', 'pictures')
def _():
    _, store, conn = with_spec('image')
    return store, conn, NEW


@state('pictures-drawing-specs-waiting-drawn-only-film', 'pictures')
def _():
    _, store, conn = with_spec('drawn')   # the film's accepted gaps hold only drawn and video shots: the case behind U4 (c)
    return store, conn, NEW


# Takes
@state('takes-nothing-yet', 'takes')
def _():
    _, store, conn = complete()
    return store, conn, NEW


@state('takes-being-made', 'takes')
def _():
    _, store, conn = complete()
    start_approved(store)
    conn.jobs.append(take('job-take-1', 'VS1', 'running'))
    return store, conn, NEW


@state('takes-ready-to-select', 'takes')
def _():
    _, store, conn = complete()
    start_approved(store)
    conn.jobs.append(take('job-take-1', 'VS1'))
    return store, conn, NEW


@state('takes-selected', 'takes')
def _():
    _, store, conn = complete()
    start_approved(store)
    conn.jobs.append(take('job-take-1', 'VS1'))
    edit(store, lambda s: (s['selections'].update(VS1={'job_id': 'job-take-1'}), s['reviews'].update({'job-take-1': [{'decision': 'accepted', 'notes': '', 'quote': 'Yes, this take.', 'by': 'u1'}]})))
    return store, conn, NEW


@state('takes-rejected', 'takes')
def _():
    _, store, conn = complete()
    start_approved(store)
    conn.jobs.append(take('job-take-1', 'VS1'))
    edit(store, lambda s: s['reviews'].update({'job-take-1': [{'decision': 'rejected', 'notes': 'the water pours upward', 'quote': 'No.', 'by': 'u1'}]}))
    return store, conn, NEW


@state('takes-drawn-shot-ready', 'takes')
def _():
    g1 = [S.shot('DR1', 0, 500, 'drawn', element_ids=['E1'], depicts='the plinth in section')]
    _, store, conn = complete(g1=g1)
    conn.jobs.append(take('job-draw-1', 'DR1', provider='drawn', result={'key': 'run-1/visuals/takes/job-draw-1.mp4', 'sha256': 's', 'sheet_key': 'run-1/visuals/takes/job-draw-1.sheet.png', 'evidence': {'duration_seconds': 20.0, 'timing_matches_placement': True}}))
    return store, conn, NEW


@state('takes-shot-filled-with-supplied-movie', 'takes')
def _():
    _, store, conn = complete()
    conn.files = {'run-1/uploads/wall-pour.mp4': {'key': 'run-1/uploads/wall-pour.mp4', 'sha256': 'sha-movie', 'bytes': 1000}}
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/wall-pour.mp4', 'sha-movie', 1000, 'movie', 'My own shot of the pour.')
    return store, conn, NEW


# Record
def ready_to_record():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1')))
    VS.approve_reference(store, USER, NEW, [], 'K1', 'sha-K1', 'Yes.', conn=conn)
    VS.still_from_reference(store, USER, NEW, [], 'IM1', 'K1', 'Use it.')
    start_approved_2 = lambda s: s['references'].update(K2=keyframe('K2', 'VS1', 'approved', role='start'))
    edit(store, start_approved_2)
    conn.jobs.append(take('job-take-1', 'VS1'))
    edit(store, lambda s: (s['selections'].update(VS1={'job_id': 'job-take-1'}), s['reviews'].update({'job-take-1': [{'decision': 'accepted', 'notes': '', 'quote': 'Yes, this take.', 'by': 'u1'}]})))
    return store, conn


@state('record-gaps-ready', 'record')
def _():
    store, conn = ready_to_record()
    return store, conn, NEW


@state('record-recorded', 'record', note='recorded_gaps is set on the session directly: record_gaps writes run outputs to the database')
def _():
    store, conn = ready_to_record()
    edit(store, lambda s: s['recorded_gaps'].update({g: {'at': '2026-11-11T10:00:00+00:00', 'by': 'u1', 'quote': 'Record both.'} for g in ('G1', 'G2')}))
    return store, conn, NEW


# Cross-cutting
@state('cross-open-defect', 'references', run={'open_defects': [45]})
def _():
    _, store, conn, _s = step2()
    return store, conn, NEW


@state('cross-run-busy-read-only', 'references', repair=False, note='page_view(repair=False): the run lock was not free; the payload says busy: true')
def _():
    _, store, conn, _s = step2()
    return store, conn, NEW


@state('cross-spend-cap-reached', 'references')
def _():
    _, store, conn = step1()
    edit(store, lambda s: s.update(cap_inr=100.0))
    conn.jobs += [{**S.job('gemini-image'), 'id': f'j-img-{k}'} for k in range(6)]   # six pictures at the flat price: over the cap of 100
    VS.round_done(store, USER, NEW, [], APPROVE(ROWS), 'Yes, the frame.', conn=conn)   # every set is refused by the cap; the reason is stored on each row
    return store, conn, NEW


@state('cross-large-round-58-elements', 'references')
def _():
    clones = [{**R.KILN, 'id': f'E{k}', 'name': f'Place {k}'} for k in range(3, 59)]
    rows = ROWS[:2] + [{'element_id': e['id'], 'prompt': f"the place {e['id']}"} for e in clones]
    _, store, conn, _s = step2(els=(R.KILN, *clones), rows=rows)
    return store, conn, NEW


@state('cross-picture-file-missing', 'references', pictures='missing')
def _():
    _, store, conn, _s = step2()
    return store, conn, NEW


# ---------- states added for layer 1 (a control that appears in none of the states above) and layer 3 (edge cases) ----------
MEDIA = [{'stage': 'media', 'unit': None, 'summary': {'clips': [{'id': 'C0120', 'name': 'C0120.MP4', 'duration_s': 42.0, 'sha256': 'sha-clip', 'bytes': 1000, 'fps': 25, 'width': 1920, 'height': 1080}]}}]
PENDING = {'action': 'clip', 'clip_id': 'C0120', 'in_s': 2.0, 'crop': None, 'on_screen': 'G1 at 0:04', 'reason': 'the only shot of the pour', 'considered': 'a closer angle adds nothing', 'quote': ''}
LONG = 'The retaining wall at the north end of the yard, beside the curing tank and under the neem tree, the one the client calls the old sample wall'


@state('controls-treatment-footage', 'treatment', note='session.footage is set directly: prepare measures the clips with ffprobe')
def _():
    store = S.store_with(S.session(footage={'summary': {'camera': 'cinema', 'support': 'tripod', 'look': 'natural'}, 'per_clip': {}}))
    VS.treatment(store, USER, NEW, [], TREAT, '')
    return store, Conn([]), NEW


def two_choices(doc):
    gap = doc['gaps'][1]
    scene = lambda sid, shots: {**gap['scenes'][0], 'id': sid, 'shots': shots}
    opt = lambda cid, title, sid: {'id': cid, 'title': title, 'why': 'it shows the water', 'formats': ['ai_video'], 'description': 'd', 'tradeoff': 't', 'source_strategy': 's',
                                   'scenes': [scene('S' + cid, [S.shot(sid, 900, 1150, 'video', element_ids=['E1'])])]}
    gap.update(scenes=[], recommended_choice='A', decision_reason='the pour reads better from the side', choices=[opt('A', 'From the side', 'VS1'), opt('B', 'From above', 'VS2')])


@state('controls-plan-two-choices', 'plan')
def _():
    _, store, conn = film(tweak=two_choices, accepted={})
    return store, conn, NEW


@state('controls-pictures-many', 'pictures', note='reuse_pending is set directly: the reuse gate writes it when a placement repeats footage already on screen')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K0={**keyframe('K0', 'IM1', 'rejected'), 'rejection': {'notes': 'the mark reads 320 mm', 'quote': 'No.', 'by': 'u1'}}, K1=keyframe('K1', 'IM1'),
                                                 L1=S.ref('L1', 'approved')))
    VS.ask(store, USER, NEW, MEDIA, 'IM1', 'Make the plinth from above or from the side?', ['From above', 'From the side'], 20)
    VS.ask(store, USER, NEW, MEDIA, 'K1', 'Keep the chalk mark on this picture?', ['Keep it', 'Remove it'])
    edit(store, lambda s: s.setdefault('reuse_pending', {}).update(IM1=dict(PENDING)))
    return store, conn, NEW, MEDIA


@state('controls-pictures-approved-not-placed', 'pictures')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1')))
    VS.approve_reference(store, USER, NEW, [], 'K1', 'sha-K1', 'Yes.', conn=conn)
    VS.still_from_reference(store, USER, NEW, [], 'IM1', 'K1', 'Use it.')
    VS.unplace(store, USER, NEW, [], 'IM1', 'Take it out for now.')
    return store, conn, NEW


@state('controls-pictures-clip-placed', 'pictures')
def _():
    _, store, conn = complete()
    VS.fill_clip(store, USER, NEW, MEDIA, 'IM1', 'C0120', 2, 'Use the clip of the plinth.')
    return store, conn, NEW, MEDIA


SEQ = [{'what_appears': 'section', 'hold_s': 7}, {'what_appears': 'cavities', 'hold_s': 7}, {'what_appears': 'label', 'hold_s': 6}]


def seq_refs(s):
    s['references'].update(R1={**S.ref('R1', 'approved'), 'shot_id': 'AN1'}, R2={**S.ref('R2', parents=['R1']), 'shot_id': 'AN1'}, R3={**S.ref('R3', parents=['R2']), 'shot_id': 'AN1'})


@state('controls-pictures-sequence-states-made', 'pictures')
def _():
    _, store, conn = complete(g1=[S.shot('AN1', 0, 500, 'animation', element_ids=['E1'], states=SEQ)])
    edit(store, seq_refs)
    return store, conn, NEW


@state('controls-pictures-sequence-one-state', 'pictures')
def _():
    _, store, conn = complete(g1=[S.shot('AN1', 0, 500, 'animation', element_ids=['E1'], states=SEQ)])
    edit(store, lambda s: s['references'].update(R1={**S.ref('R1'), 'shot_id': 'AN1'}))
    return store, conn, NEW


@state('controls-pictures-sequence-placed', 'pictures')
def _():
    _, store, conn = complete(g1=[S.shot('AN1', 0, 500, 'animation', element_ids=['E1'], states=SEQ)])
    edit(store, seq_refs)
    VS.sequence(store, USER, NEW, [], 'AN1', ['R1', 'R2', 'R3'], 'Yes, these three states.')
    return store, conn, NEW


@state('controls-takes-two-takes', 'takes', note='reuse_pending is set directly, as in controls-pictures-many')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K0={**keyframe('K0', 'VS1', 'rejected', role='start'), 'rejection': {'notes': 'too dark', 'quote': 'No.', 'by': 'u1'}},
                                                 K1=keyframe('K1', 'VS1', 'approved', role='start')))
    conn.jobs += [take('job-take-1', 'VS1'), take('job-take-2', 'VS1')]
    edit(store, lambda s: s['reviews'].update({'job-take-1': [{'decision': 'rejected', 'notes': 'the water pours upward', 'quote': 'No.', 'by': 'u1'}]}))
    VS.ask(store, USER, NEW, MEDIA, 'VS1', 'Pour from a bucket or from a hose?', ['A bucket', 'A hose'])
    edit(store, lambda s: s.setdefault('reuse_pending', {}).update(VS1=dict(PENDING)))
    return store, conn, NEW, MEDIA


@state('controls-older-search-found-nothing', 'references')
def _():
    store, conn = older()
    VS.apify.search_images = lambda keywords, n=10: []
    VS.search(store, USER, OLD, [], 'E2', 'unfindable kiln words', 'Search again.')
    return store, conn, OLD


@state('refs-no-elements', 'references')
def _():
    _, store, conn = film(els=(), tweak=lambda doc: doc.update(elements=[]))
    return store, conn, NEW


@state('refs-step1-picture-answered-spec-waits', 'references')
def _():
    _, store, conn = step1(spec=False)
    VS.approve_reference(store, USER, NEW, [], 'F1', 'sha-F1', 'Yes.', conn=conn)   # the footage picture is answered; the brick's spec still waits (U3)
    return store, conn, NEW


@state('refs-step2-spec-approved-after-refusal', 'references')
def _():
    _, store, conn, _s = step2(spec=False)   # the brick's set was refused for its unapproved spec ...
    VS.approve_spec(store, USER, NEW, [], 'element:BRICK', '')   # ... and the spec is approved afterwards (U8)
    return store, conn, NEW


@state('refs-step2-spec-corrected-after-set', 'references')
def _():
    _, store, conn, _s = step2()
    VS.correct_spec(store, USER, NEW, [], 'element:BRICK', 'the joint is 12 mm, not 10')
    return store, conn, NEW


@state('refs-step2-set-with-a-failed-picture', 'references', note='one picture of the brick set is marked failed, as the image worker marks it')
def _():
    _, store, conn, s = step2()
    edit(store, lambda x: x['references'][sheets(s, 'BRICK')[2]].update(status='failed', key=None))
    return store, conn, NEW


@state('takes-shot-filled-with-supplied-still', 'takes')
def _():
    _, store, conn = complete()
    conn.files = {'run-1/uploads/wall.png': {'key': 'run-1/uploads/wall.png', 'sha256': 'sha-still', 'bytes': 500}}
    VS.add_asset(conn, store, USER, NEW, [], 'VS1', 'run-1/uploads/wall.png', 'sha-still', 500, 'still', 'A photograph of the wet wall instead.')
    return store, conn, NEW


@state('cross-long-names', 'references')
def _():
    wall = {**R.KILN, 'id': 'E3', 'name': LONG, 'requirements': LONG + '. ' + LONG}
    rows = ROWS + [{'element_id': 'E3', 'prompt': 'the old sample wall'}]
    _, store, conn, _s = step2(els=(R.KILN, R.MASON, BRICK, wall), rows=rows)
    return store, conn, NEW


# Follow-up, ten fixes (11 Nov 2026)
WALL = {**R.KILN, 'id': 'E3', 'name': 'Yard wall', 'kind': 'object', 'requirements': 'the wall at the end of the yard',
        'size': [{'part': 'wall', 'measure': 'height', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown', 'tried': 'not in the client material'}]}


def wall_not_made():
    """Step 2 where the wall's set cannot be made: a footage picture of it was approved after its first set, the set was answered No, and the server
    will not make it again before its height is measured (nothing on the page settles that)."""
    _, store, conn, _s = step2(els=(R.KILN, R.MASON, BRICK, WALL), rows=ROWS + [{'element_id': 'E3', 'prompt': 'the yard wall'}])
    edit(store, lambda x: x['references'].update(F9={**S.ref('F9', 'approved'), 'kind': 'frame', 'element_id': 'E3', 'width': 1920, 'height': 1080}))
    VS.round_sets(store, USER, NEW, [], {'E3': {'verdict': 'no', 'words': 'the wall is too low'}}, 'Again.', conn=conn, partial=True)
    return store, conn


@state('refs-step2-size-not-measured', 'references')
def _():
    store, conn = wall_not_made()
    return store, conn, NEW


@state('refs-step2-set-aside', 'references')
def _():
    store, conn = wall_not_made()
    VS.set_aside(store, USER, NEW, [], 'E3', 'we film the wall ourselves')
    return store, conn, NEW


@state('refs-step2-set-aside-rest-approved', 'references')
def _():
    store, conn = wall_not_made()
    s = S.saved(store)
    VS.round_sets(store, USER, NEW, [], {eid: {'verdict': 'yes', **({} if eid == 'P1' else {'golden': sheets(s, eid)[0]})} for eid in ('E2', 'P1', 'BRICK')}, 'These.', conn=conn, partial=True)
    VS.set_aside(store, USER, NEW, [], 'E3', '')   # every other set approved, the wall set aside: nothing is left to judge; Done closes the round
    return store, conn, NEW


@state('cross-spend-cap-reached-sets-back', 'references')
def _():
    _, store, conn, _s = step2()
    edit(store, lambda s: s.update(cap_inr=100.0))
    conn.jobs += [{**S.job('gemini-image'), 'id': f'j-img-{k}'} for k in range(6)]   # every set is back; the spend has passed the cap of 100 since
    return store, conn, NEW


# Round 3 (11 Nov 2026): a verdict changed both ways (U17), the operator's own picture (U19)
def own_png(colour=(120, 80, 40)):
    from PIL import Image
    png = io.BytesIO()
    Image.new('RGB', (64, 48), colour).save(png, format='PNG')
    return png.getvalue()


@state('refs-step1-footage-picture-ignored', 'references')
def _():
    _, store, conn = step1()
    VS.reject_reference(store, USER, NEW, [], 'F1', '', '')   # Ignore on the footage picture: it stays on its card and offers Use this picture
    return store, conn, NEW


@state('refs-step1-own-picture', 'references')
def _():
    _, store, conn = step1()
    VS.supply_own(conn, store, USER, NEW, [], 'E2', content=own_png(), name='my-kiln.png')
    return store, conn, NEW


@state('refs-step2-own-picture', 'references')
def _():
    _, store, conn, _s = step2()
    VS.supply_own(conn, store, USER, NEW, [], 'E2', content=own_png(), name='my-kiln.png')   # beside the set's pictures; it can be chosen as the starting picture
    return store, conn, NEW


# Faults 1 to 4 of the VW-20 test run (11 Nov 2026): a set that failed in the call, one set made again while the others wait, an own picture as the reference
def brick_failed(error='OpenAI rejected the request (HTTP 400).'):
    """Step 2 where the brick's set failed in the call: the kiln's and the mason's sets are back."""
    _, store, conn = step1()
    VS.round_done(store, USER, NEW, [], APPROVE(ROWS), 'Yes, the frame.', conn=conn)
    edit(store, lambda x: [r.update(status='failed', error=error) for r in x['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'BRICK'])
    return store, conn, sets_back(store, {'E2': 2})


@state('refs-step2-set-failed-in-call', 'references')
def _():
    store, conn, _s = brick_failed()
    return store, conn, NEW


@state('refs-step2-one-set-being-made', 'references')
def _():
    store, conn, s = brick_failed('The model returned no picture: no image in the answer')
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', sheets(s, 'E2')[0], '')   # answered before; the mason is not answered yet
    VS.set_make(conn, store, USER, NEW, [], 'BRICK')   # Make it now: only the brick is being made
    return store, conn, NEW


@state('refs-step2-own-picture-on-failed-set', 'references')
def _():
    store, conn, _s = brick_failed()
    VS.supply_own(conn, store, USER, NEW, [], 'BRICK', content=own_png(), name='my-brick.png')
    return store, conn, NEW


@state('refs-second-pass-being-made', 'references')
def _():
    _, store, conn, s = step2()
    VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sheets(s, 'E2')[0]}, 'P1': {'verdict': 'yes'}, 'BRICK': {'verdict': 'no', 'words': 'too dark'}}, 'These.', conn=conn, partial=True)
    return store, conn, NEW


@state('refs-round-complete-own-picture-and-set-aside', 'references')
def _():
    _, store, conn = step1()
    VS.supply_own(conn, store, USER, NEW, [], 'E2', content=own_png(), name='my-kiln.png')   # at step 1: no set is made for the kiln
    VS.round_done(store, USER, NEW, [], APPROVE(ROWS), 'Yes, the frame.', conn=conn)
    edit(store, lambda x: [r.update(status='failed', error='OpenAI rejected the request (HTTP 400).') for r in x['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'BRICK'])
    sets_back(store)
    VS.set_aside(store, USER, NEW, [], 'BRICK', '')
    VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'Yes.', conn=conn, partial=True)
    return store, conn, NEW


@state('pictures-picture-rejected', 'pictures')
def _():
    _, store, conn = complete()
    edit(store, lambda s: s['references'].update(K1=keyframe('K1', 'IM1')))
    VS.reject_reference(store, USER, NEW, [], 'K1', 'the mark reads 320 mm', '')   # nothing else stands in its place: it can be approved after all
    return store, conn, NEW


def main():
    out = HERE / 'data' / (args.name or args.rev or 'main')
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob('*.json'):
        f.unlink()
    failed = []
    for name, (tab, meta, fn) in STATES.items():
        try:
            store, conn, run, *rest = fn()   # a fourth item, when given: the run's outputs (the media stage's clips)
            view = VS.page_view(conn, store, run, rest[0] if rest else [], run['code'], meta.get('repair', True))
        except Exception as exc:   # a state this version of the server cannot make: listed, never written
            failed.append((name, f'{type(exc).__name__}: {getattr(exc, "message", None) or exc}'))
            continue
        payload = {'run': {'code': run['code'], 'title': 'Rat-trap bond', 'status': 'open', 'stage': 'visuals', 'open_defects': [], **meta.get('run', {})}, **view}
        doc = {'state': name, 'tab': tab, 'source': 'generated by visuals_stage.page_view' + (f' at {args.rev}' if args.rev else ''), 'pictures': meta.get('pictures', 'ok'),
               'note': meta.get('note', ''), 'payload': payload}
        (out / f'{name}.json').write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    print(f'{len(STATES) - len(failed)} states written to {out}')
    for name, why in failed:
        print(f'NOT MADE  {name}: {why}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
