"""Fix set phase 1 (B4, SK 19 Nov 2026): the shape of a real step 6 session, loaded into the in-memory store the unit tests use.

step6_real_shape.json holds the shapes and ids (no picture, no film's own text): things with several views among the shared parts, pictures kept under
visuals/references/ and approved drawings under visuals/drawings/, a chain of drawings that continue one another, a still round and an animated round
of verdicts, rules a still can show and rules only motion shows. The three hotfixes of 19 Nov all came from tests built on a simpler shape."""
import copy
import json
from pathlib import Path

from app import visuals_stage as VS
from test_batch89b_pure import SPEC
from test_design130_p1_pure import FakeConn, INDEX, WALL, motion_shot, motion_store, zipped
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_design221_p2_pure import answer
from test_design221_p3c_pure import chat, still_verdict
from test_visuals_stage_pure import USER, g, shot

SHAPE = json.loads(Path(__file__).with_name('step6_real_shape.json').read_text(encoding='utf-8'))
RULES = [r['rule'] for r in SHAPE['rules']]


def rules_text(marked=True):
    """rules.md as the rule writer writes it; marked=False: as it was written before the marks (must: / should: only)."""
    return '# Rules\n' + ''.join(f"{n}. {r['class']}{' (' + r['shows'] + ')' if marked else ''}: {r['rule']}\n" for n, r in enumerate(SHAPE['rules'], 1))


def parts_svg(views=True):
    """The shared parts file; views=False: as a file drawn before a part named its view."""
    return '<svg xmlns="http://www.w3.org/2000/svg">\n' + ''.join(
        f'<symbol id="{p["id"]}" viewBox="0 0 200 100"' + (f' data-element="{p["element"]}"' if p['element'] else '') + (f' data-view="{p["view"]}"' if views and p['view'] else '')
        + f'><title>{p["title"]}</title><rect width="200" height="100"/></symbol>\n' for p in SHAPE['parts']) + '</svg>'


def drawing(*part_ids, more=''):
    """A project of a 100-frame shot that places these shared parts and no picture."""
    uses = ''.join(f'<use href="#{i}" width="200" height="100"/>' for i in part_ids)
    return zipped({'index.html': INDEX, 'compositions/wall.html': WALL.replace('<image href="assets/ref/comp-1.png" x="0" y="0" width="200" height="100"/>', uses), **({'style.css': more} if more else {})})


def load(views=True, parts=True):
    """The store of a film at the start of its drawn graphics: the plan, the approved pictures in both places, the approved shared parts."""
    store = motion_store()

    def drawn(s):
        spec = {**copy.deepcopy(SPEC), 'view': s['view'], 'view_reason': 'what the shot is about' if s['view'] else ''}
        return motion_shot(id=s['id'], start_frame=s['start_frame'], end_frame=s['end_frame'], element_ids=s['element_ids'], drawing_spec=spec, depicts='the parts',
                           scene_motion={'labels': s['labels'], 'cues': []}, **({'return_of': s['return_of']} if s.get('return_of') else {}))

    def change(d):
        d['elements'] = copy.deepcopy(SHAPE['elements'])
        d['gaps'][0]['scenes'][0]['shots'] = [drawn(s) for s in SHAPE['shots'] if s['gap'] == 'G1'] + [shot('IM1', 300, 500, 'image')]
        d['gaps'][1]['scenes'][0]['shots'] = [drawn(s) for s in SHAPE['shots'] if s['gap'] == 'G2'] + [shot('VS1', 1000, 1150, 'video', subjects=[])]
    edit_plan(store, change)
    plan = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    specs = {s['id']: s['drawing_spec'] for gap in plan['gaps'] for s in gap['scenes'][0]['shots'] if s.get('drawing_spec')}

    def fill(s):
        s['references'] = copy.deepcopy(SHAPE['references'])
        s['spec_approvals'] = {sid: {'digest': VS.spec_digest(spec)} for sid, spec in specs.items()}
        s.pop('motion_stills', None)
    edit_session(store, fill)
    for k in SHAPE['files']:
        store.files[k] = b'\x89PNG' + k.encode('utf-8')
    if parts:
        out = g(lambda: VS.set_parts(store, USER, NEW, [], 'parts.svg', parts_svg(views).encode('utf-8')))
        VS.parts_answer(store, USER, NEW, [], out['sha256'], True, 'Approve')
    return store


def build(store, shot_id):
    return g(lambda: VS.motion_brief(store, NEW, [], shot_id, build=True, conn=FakeConn([])))


def upload(store, shot_id, *part_ids, still=False, marked=True, more='', rules=None):
    """rules: the drawing's own rules.md in place of the fixture's (fix set phase 2: a rule that compares with another drawing)."""
    return g(lambda: VS.set_motion(store, USER, NEW, [], shot_id, 'shot.zip', drawing(*part_ids, more=more), rules or rules_text(marked), **({'still': True} if still else {})))


def answers(said):
    """{rule number in the fixture: its answer} as {the rule's words: its answer}; a key that is no number is a rule's own words."""
    return {RULES[int(n)] if str(n).isdigit() else n: v for n, v in said.items()}


def verdict(store, shot_id, sha, said, rnd=1):
    return g(lambda: VS.motion_verdict(store, USER, NEW, [], {'shot_id': shot_id, 'sha256': sha, 'round': rnd, 'rules': [answer(r, v) for r, v in answers(said).items()]}))


def stills(store, *shots):
    """Release 2, F1: the still end-frame of each of these shots, checked and approved, so that a drawing that continues the last one may upload its
    own still. Each is (shot id, the parts it places)."""
    for n, (shot_id, *part_ids) in enumerate(shots):
        sha = upload(store, shot_id, *part_ids, still=True, more=f'still {n} {{}}')['sha256']
        still_verdict(store, sha, answers(SHAPE['rounds']['D1']['still']), shot=shot_id, key=f'run-1/visuals/motion/tools/{shot_id}/0.png')
        next(i for i in chat(store, 'still end-frame') if shot_id in i['question'])['_run']('approve', 'Approve', '')
    return store


def play(store, shot_id, *part_ids):
    """One drawing through its two rounds as the fixture records them: the still, its verdict, the operator's approval, the motion, its verdict."""
    rounds = SHAPE['rounds']['D1']
    still = upload(store, shot_id, *part_ids, still=True)['sha256']
    first = still_verdict(store, still, answers(rounds['still']), shot=shot_id, key=f'run-1/visuals/motion/tools/{shot_id}/0.png')
    next(i for i in chat(store, 'still end-frame') if shot_id in i['question'])['_run']('approve', 'Approve', '')
    sha = upload(store, shot_id, *part_ids, more='b {}')['sha256']
    return {'still': first, 'animated': verdict(store, shot_id, sha, rounds['animated']), 'sha256': sha}
