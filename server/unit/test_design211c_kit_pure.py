"""design/211 part C: what the tests of part C share. A film from the shared fixture (`d211_fixture`) in a fake store, with parts A and B
stood in for: `ref_find` and `ref_sets` are stubs in part C's worktree, so their functions are replaced here by small ones that answer in
the contract's shapes from the fixture's own data (never a copy of their logic), and the calls that would spend or record are noted.
No test of its own."""
import copy
import io
import json

from PIL import Image

from app import chat_flow as CF, page_flow as P, ref_find, ref_sets, visuals_stage as VS
import d211_fixture as F
from test_visuals_stage_pure import FakeConn, FakeStore, USER

RUN = {**F.RUN, 'image_provider': 'gemini', 'film': {'shape': {'value': 'horizontal', 'video': 'horizontal', 'fps': 25}}}
SESSION = f"{RUN['id']}/visuals/session.json"
SIZES = ['ECU', 'CU', 'MCU', 'MS', 'MWS', 'WS', 'EWS']
STATES = {'1': 1, 'making': 'making', 'looking': 'looking', '2': 2, 'rewrite': 'rewrite', 'complete': 'complete'}
PAID = f'paid, about ₹{F.SET_PRICE:,.0f}'


def png(colour='white'):
    out = io.BytesIO()
    Image.new('RGB', (64, 48), colour).save(out, 'PNG')
    return out.getvalue()


def older_step1():
    """A round of before design/211 at its step 1: the fixture's first state with every field of design/211 taken away."""
    s = F.session('1')
    s.pop('found')
    for k in ('v', 'go', 'rest'):
        s['round'].pop(k)
    for eid, row in s['round']['elements'].items():
        for k in ('rec', 'reason', 'doubt', 'first', 'operator_words', 'history'):
            row.pop(k)
        row['prompt'] = row['prompt'] or f'The subject block of {eid}.'
    for ref in s['references'].values():
        for k in ('view', 'look', 'weak', 'trial'):
            ref.pop(k, None)
    return s


class Film:
    """The fixture's film at one state of its round, parts A and B stood in for. `calls` lists what they were asked to do."""

    def __init__(self, monkeypatch, state='1', session=None, plan=None):
        self.state, self.calls, self.planned, self.cause = STATES.get(state, state), [], 1200.0, None
        self.inputs, self.changed, self.fails, self.next_frame, self.real = {}, set(), {}, None, set()
        self.plan = plan or F.plan()
        self.conn = FakeConn([])
        self.store = FakeStore({f"{RUN['id']}/visuals/plan-v1.json": {'document': self.plan}})
        self.save(session or F.session(state))
        m = monkeypatch.setattr
        real_pass = VS._round_pass
        m(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})
        m(VS, '_round_pass', lambda s, rd: self.state if VS.round_v2(s) else real_pass(s, rd))
        m(VS, '_set_budget', lambda run, s, spend: (F.SPENT, F.CAP, F.SET_PRICE))
        m(VS, 'set_cause', lambda s, plan, eid, budget=None: self.cause if self.cause and self.cause['element_id'] == eid else None)
        m(VS, 'budget', lambda conn, store, run, outputs: {'planned': {'inr': self.planned}})
        m(VS, 'round_done', self.round_done)
        m(VS, 'round_sets', self.round_sets)
        m(VS, 'set_make', lambda conn, store, user, run, outputs, eid, quote='': self.note('set_make', eid, quote) or {'element_id': eid, 'queued': True})
        m(CF, '_plan_items', lambda ctx: ([], []))   # the plan is accepted
        m(P, '_spec_lines', lambda ctx: [])           # no drawing or material waits
        m(ref_sets, 'thing_facts', self.thing_facts)
        m(ref_sets, 'set_facts', self.set_facts)
        m(ref_sets, 'round_rest', lambda conn, store, user, run, outputs, quote: self.note('round_rest', quote) or {'pass': 'making', 'queued': list(F.REST), 'then': ref_sets.ALL_MAKING.format(k=2, x='70')})
        m(ref_sets, 'round_reopen', lambda conn, store, user, run, outputs, eid, verdict, words, quote: self.note('round_reopen', eid, verdict, words, quote) or {'element_id': eid, 'queued': verdict == 'approve'})
        m(ref_find, 'frames_of', self.frames_of)
        m(ref_find, 'found_all', self.found_all)
        m(ref_find, 'not_this', self.not_this)
        m(ref_find, 'that_is_it', self.that_is_it)
        P._MADE.clear()

    def note(self, *call):
        self.calls.append(call)

    def called(self, name):
        return [c[1:] for c in self.calls if c[0] == name]

    # ---------- the store ----------
    def save(self, s):
        s = {'source': {'from': 'first_cut', 'fps': '25', 'resolution': '1920x1080', 'plan_digest': 'pd', 'gaps': {}}, **s,
             'versions': [{'version': 1, 'file': {'key': f"{RUN['id']}/visuals/plan-v1.json"}, 'plan_digest': s['current'], 'warnings': []}]}
        self.store.files[SESSION] = json.dumps(s).encode('utf-8')
        for ref in s['references'].values():
            if ref.get('key'):
                self.store.files.setdefault(ref['key'], png())
        for t in F.trials()['trials'].values():
            self.store.files.setdefault(t['key'], png('grey'))
        for d in (s.get('drawings') or {}).values():
            for v in d.get('views') or []:
                self.store.files.setdefault(v['plain_key'], png('blue'))

    def session(self):
        return json.loads(self.store.files[SESSION])

    def change(self, fn):
        s = self.session()
        fn(s)
        self.save(s)

    # ---------- the two front ends ----------
    def ctx(self):
        return CF._ctx(self.conn, self.store, USER, RUN, [])

    def items(self, every=True):
        return CF._round_items(self.ctx(), every=every)

    def page(self):
        return P.page(self.conn, self.store, USER, RUN, [])

    def lines(self):
        return {l['key']: l for l in self.page()['lines']}

    def record(self, *answers):
        return P.page_record(self.conn, self.store, USER, RUN, [], list(answers))

    def next(self):
        return CF.next_item(self.conn, self.store, USER, RUN, [])

    def decide(self, item, choice, quote='', notes=''):
        return CF.answer(self.conn, self.store, USER, RUN, [], item, choice, quote, notes)

    # ---------- part B, stood in for ----------
    def thing_facts(self, plan, session, element):
        shots = [{'gap': g['gap_id'], 'shot': sh['id'], 'size': sh['size'], 'way': sh['visual_type']} for g in plan['gaps'] for sc in g['scenes'] for sh in sc['shots'] if element['id'] in sh['element_ids']]
        return {'id': element['id'], 'name': element['name'], 'kind': element['kind'], 'identity': element['identity'], 'real_person': element['id'] in self.real,
                'description': element['description'], 'requirements': element['requirements'], 'sizes': [{k: d.get(k) for k in ('part', 'measure', 'value', 'unit', 'status')} for d in element.get('size') or []],
                'views': F.VIEWS.get(element['id'], ['', '', '']), 'signs': [], 'shots': shots, 'shots_made': len([s for s in shots if s['way'] != 'footage']),
                'closest': min((s['size'] for s in shots), key=SIZES.index, default=''), 'scene': None}

    def set_facts(self, session, plan, eid, row):
        rows = sorted([r for r in session['references'].values() if r.get('kind') == 'sheet' and r.get('element_id') == eid and r.get('set') == row.get('set') and r.get('key')], key=lambda r: r['set_n'])
        look = row.get('set_look') if (row.get('set_look') or {}).get('set') == row.get('set') else None

        check = lambda r: ref_sets.check_summary(session, r)   # design/214: part B's own summary (Claude's check of a v2 set, from the look's line answers)
        history = [{k: h[k] for k in ('n', 'set', 'added', 'operator')} for h in row.get('history') or []]
        return {'pictures': [{'ref': r['id'], 'n': r['set_n'], 'view': r.get('view') or '', 'check': check(r), 'look': r.get('look')} for r in rows], 'inputs': self.inputs.get(eid, []), 'from': 'web',
                'notes': rows[0].get('notes') if rows else '', 'sources': rows[0].get('sources') or [] if rows else [],
                'partial': {'made': len(rows), 'asked': 3, 'missing': F.VIEWS[eid][len(rows):]} if 0 < len(rows) < 3 else None,
                'rec': {'do': look['recommend'], 'golden': look['golden'], 'reason': look['reason']} if look else None, 'makes': row.get('round') or 0, 'makes_left': 3 - (row.get('round') or 0),
                'asked': history[-1]['operator'] if history else None, 'history': history, 'changed': eid in self.changed, 'fail': self.fails.get(eid)}

    def round_done(self, store, user, run, outputs, verdicts, quote, conn=None):
        """Step 1 recorded: the fixture's own next state stands in for what part B does."""
        self.note('round_done', copy.deepcopy(verdicts), quote)
        self.state = 'making'
        self.save(F.session('making'))
        return {'pass': 'making', 'kept': True, 'queued': list(F.FIRST), 'errors': {}, 'cost_inr': 3 * F.SET_PRICE, 'then': ref_sets.GO1_MAKING.format(k=3, x='105', r=2)}

    def round_sets(self, store, user, run, outputs, verdicts, quote, conn=None, partial=False, each=False):
        if not verdicts:
            raise ValueError('a set still waits for its answer')
        self.note('round_sets', copy.deepcopy(verdicts), quote)
        return {'pass': self.state, 'queued': [], 'errors': {}, 'approved': [e for e, v in verdicts.items() if v['verdict'] == 'yes'], 'held': {}}

    # ---------- part A, stood in for ----------
    def frames_of(self, session, eid):
        order = (session.get('found') or {}).get(eid, {}).get('kept') or []
        rows = [r for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved') and r.get('look')]
        rows.sort(key=lambda r: order.index(r['id']) if r['id'] in order else len(order))
        return [{'ref': r['id'], 'view': r['view'], 'verdict': r['look']['verdict'], 'seen': r['look']['seen'], 'weak': r['weak']} for r in rows]

    def found_all(self, store, run, session, plan):
        names = {c['clip']: c['name'] for c in F.digest()['clips']}
        trials = F.trials()['trials']
        out = {}
        for eid, f in (session.get('found') or {}).items():
            t = trials.get(f.get('closest') or '')
            out[eid] = {'result': f['result'], 'by': f['by'], 'at': f['at'], 'clips': len(f['clips']), 'clip_names': [names[c] for c in f['clips']][:5], 'not_searched': [c['name'] for c in F.digest()['not_searched']],
                        'note': f['note'], 'closest': {'trial': t['id'], 'key': t['key'], 'sha256': t['sha256'], 'view': t['looks'][eid]['view'], 'seen': t['looks'][eid]['seen']} if t else None, 'stale': bool(f.get('stale'))}
        return out

    def not_this(self, conn, store, user, run, outputs, eid, ref_id, quote):
        self.note('not_this', eid, ref_id, quote)

        def do(s):
            s['references'][ref_id]['status'] = 'rejected'
            if self.next_frame:
                s['references'][self.next_frame['id']] = self.next_frame
        self.change(do)
        return {'next': self.next_frame['id'] if self.next_frame else None}

    def that_is_it(self, conn, store, user, run, outputs, eid, trial, quote):
        self.note('that_is_it', eid, trial, quote)
        t = F.trials()['trials'][trial]
        look = {**t['looks'][eid], 'verdict': 'weak'}
        self.change(lambda s: s['references'].update({f'f-{eid}-it': {'id': f'f-{eid}-it', 'element_id': eid, 'kind': 'frame', 'status': 'candidate', 'key': t['key'], 'view': look['view'], 'look': look,
                                                                    'weak': True, 'trial': trial}}))
        return {'ref': f'f-{eid}-it'}


def ans(line, choice, notes='', **more):
    return {'line': line['line'], 'key': line['key'], 'item': line.get('item', ''), 'choice': choice, 'notes': notes, **more}


def labels(line):
    return [b['label'] for b in line['buttons']]
