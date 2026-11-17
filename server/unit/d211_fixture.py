"""design/211, step 0: the one fixture the three parts' tests share (section 6.0). Plain data in the contract's shapes; it imports nothing
of the application, so the plugin tests can import it too (`sys.path.insert(0, str(REPO / 'server' / 'unit'))`).

A change to this file goes through the master thread: all three parts build against it.

The film: eight things. MASON a person; TROWEL an object with two kept footage frames (one weak); FAN an object the footage does not show,
with a closest frame; BRICK a material with a material spec; STREET a place; T_LAY a way of working; TILE an object with approved drawings
and one kept frame; DOG an animal (never in the round). The first go makes MASON, STREET and T_LAY; FAN, BRICK and TILE wait in `rest`;
TROWEL is taken from its footage.

    plan()                      the plan
    digest()                    the digest of two clips, one media clip not analysed
    trials()                    the content of trials.json
    session(state)              a v2 round at one state of section 3.8: '1', 'making', 'looking', '2', 'rewrite', 'complete'
    older_session()             a round without `v`, at step 2, made the way of before design/211
    specs_approved(s, p, fn)    the material spec of BRICK approved in session `s` (`fn` is visuals_stage.spec_digest)
"""
import copy

RUN = {'id': 'run-211', 'code': 'VW-211'}
NOW = '2026-11-17T10:00:00+00:00'
SET_PRICE = 35.0   # the figures of the tests: one set, in rupees
CAP, SPENT = 3754.0, 0.0
THINGS = ('MASON', 'TROWEL', 'FAN', 'BRICK', 'STREET', 'T_LAY', 'TILE')   # the round's things, in the plan's order
FIRST = ('MASON', 'STREET', 'T_LAY')
REST = ('FAN', 'BRICK', 'TILE')


def _shot(sid, way, size, eids, **more):
    return {'id': sid, 'visual_type': way, 'size': size, 'element_ids': list(eids), 'message': sid, **more}


def plan():
    return {
        'foundation': {'treatment': 'The Direction.', 'appearance': 'handheld, natural colours, as the footage', 'world': [], 'exclusions': [], 'specifications': [], 'studio_background': ''},
        'elements': [
            {'id': 'MASON', 'name': 'The mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'Lays the bricks. Works with his right hand.',
             'required_views': ['right hand and forearm'], 'size': [{'part': 'body', 'measure': 'height', 'value': None, 'unit': 'cm', 'source': '', 'status': 'unknown'}],
             'description': 'A lean man in his forties, short grey hair, a moustache.', 'speaker': False},
            {'id': 'TROWEL', 'name': "Mason's trowel", 'kind': 'object', 'identity': 'exact', 'requirements': 'The trowel the mason uses on this site.',
             'required_views': ['side', 'in the hand, lifting mortar'], 'size': [{'part': 'blade', 'measure': 'length', 'value': 18, 'unit': 'cm', 'source': 'the footage', 'status': 'measured'}],
             'description': 'A pointed steel blade, a reddish-brown handle.'},
            {'id': 'FAN', 'name': 'Wall fan regulator', 'kind': 'object', 'identity': 'representative', 'requirements': 'On the wall of the family room.',
             'required_views': [], 'size': [], 'description': 'A round dial on a white plate.'},
            {'id': 'BRICK', 'name': 'Brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'The wall brick of the house.',
             'required_views': [], 'size': [], 'description': 'A burnt clay brick, uneven red.',
             'material_spec': {'parts': ['brick'], 'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'source': 'the client', 'status': 'confirmed'},
                                                                   {'part': 'brick', 'measure': 'height', 'value': 75, 'unit': 'mm', 'source': 'the client', 'status': 'confirmed'}],
                               'relationships': [], 'label': '', 'proportions': [], 'illustrative': False, 'view': '', 'view_reason': '',
                               'laid': 'flat, stretcher faces to the camera', 'joint': '10 mm mortar joints', 'pattern': 'each course offset by half a brick', 'not_this': []}},
            {'id': 'STREET', 'name': 'The street', 'kind': 'place', 'identity': 'representative', 'requirements': 'Wide enough to see several houses.',
             'required_views': [], 'size': [], 'description': 'A sandy unpaved street between low houses.',
             'signs_of_use': [{'landmark_id': 'gate', 'sign': 'tyre tracks in the sand'}, {'landmark_id': 'wall', 'sign': 'a bicycle against the wall'}], 'staged_clean': ''},
            {'id': 'T_LAY', 'name': 'Laying a brick', 'kind': 'technique', 'identity': 'representative', 'requirements': 'A brick lowered onto the mortar bed and pressed down.',
             'required_views': [], 'size': [], 'description': 'The right hand lowers the brick; the left hand rests on the wall.'},
            {'id': 'TILE', 'name': 'Roof tile', 'kind': 'object', 'identity': 'exact', 'requirements': 'The ribbed clay tile of the roof.',
             'required_views': ['underside', 'a stacked pair'], 'size': [{'part': 'tile', 'measure': 'length', 'value': 41, 'unit': 'cm', 'source': 'the client', 'status': 'confirmed'},
                                                                         {'part': 'tile', 'measure': 'width', 'value': 24, 'unit': 'cm', 'source': 'a standard', 'status': 'proposed'}],
             'description': 'A ribbed red clay tile with two lugs.'},
            {'id': 'DOG', 'name': 'A street dog', 'kind': 'animal', 'identity': 'representative', 'requirements': 'Lies in the shade.', 'required_views': [], 'size': [], 'description': 'A small tan dog.'},
        ],
        'gaps': [
            {'gap_id': 'G1', 'scenes': [{'id': 'G1-S1', 'location_time': 'the sandy street in front of the house, morning', 'outfit': {'MASON': 'a white shirt, a checked lungi'},
                                         'shots': [_shot('G1-S1-SH1', 'image', 'WS', ['STREET', 'DOG']), _shot('G1-S1-SH2', 'footage', 'MS', ['MASON'])]}]},
            {'gap_id': 'G2', 'scenes': [{'id': 'G2-S1', 'location_time': 'the wall under construction, late morning', 'outfit': {'MASON': 'a white shirt, a checked lungi'},
                                         'shots': [_shot('G2-S1-SH1', 'video', 'MS', ['MASON', 'TROWEL', 'BRICK', 'T_LAY']), _shot('G2-S1-SH2', 'image', 'CU', ['TROWEL', 'BRICK'])]}]},
            {'gap_id': 'G3', 'scenes': [{'id': 'G3-S1', 'location_time': 'the family room, evening', 'outfit': {},
                                         'shots': [_shot('G3-S1-SH1', 'image', 'WS', ['FAN']), _shot('G3-S1-SH2', 'image', 'MS', ['TILE'])]}]},
        ],
        'visual_facts': [],
    }


def digest():
    part = lambda pid, a, b, hero, size, action, props: {'id': pid, 'in_s': a, 'out_s': b, 'hero_s': hero, 'grade': 'A', 'role': 'PROCESS_ACTION_B_ROLL', 'size': size,
                                                         'angle': 'Eye_Level', 'action': action, 'uncertain': '', 'props': props, 'people': 1, 'defects': []}
    return {'contract': 'vw2-refs-digest-v1', 'stamp': 'd' * 64, 'built_at': NOW,
            'clips': [{'clip': 'C001', 'name': 'C001.mp4', 'duration_s': 42.0, 'overview': 'A mason lays bricks on a wall.', 'light': 'late morning sun',
                       'entities': [{'name': 'mason_trowel', 'kind': 'tool', 'first_seen_s': 0.0, 'last_seen_s': 40.0, 'description': 'a trowel with a reddish-brown handle', 'uncertainty': ''}],
                       'parts': [part('C001-a', 0.0, 18.0, 6.4, 'MS', 'the mason spreads mortar with a trowel', ['trowel', 'mortar pan']),
                                 part('C001-b', 18.0, 42.0, 30.2, 'CU', 'the trowel lies on the wall, side on', ['trowel', 'brick'])]},
                      {'clip': 'C002', 'name': 'C002.mp4', 'duration_s': 20.0, 'overview': 'Roof tiles stacked in a yard.', 'light': 'overcast',
                       'entities': [{'name': 'roof_tiles_stack', 'kind': 'material', 'first_seen_s': 0.0, 'last_seen_s': 20.0, 'description': 'ribbed red clay tiles', 'uncertainty': ''}],
                       'parts': [part('C002-a', 0.0, 20.0, 9.0, 'MS', 'a stack of roof tiles, one turned over', ['roof tiles'])]}],
            'not_searched': [{'clip': 'C003', 'name': 'C003.mp4', 'reason': 'no analysis'}]}


def _look(view, verdict, seen, trial=None, ref=None, who='helper'):
    return {'who': who, 'at': NOW, 'view': view, 'verdict': verdict, 'seen': seen, 'trial': trial, 'ref': ref}


TRIALS = {   # trial id: (clip, second, the things it was taken for)
    't0000000000a1': ('C001', 30.2, ['TROWEL']), 't0000000000a2': ('C001', 6.4, ['TROWEL']), 't0000000000a3': ('C001', 12.0, ['TROWEL']),
    't0000000000b1': ('C002', 9.0, ['TILE']), 't0000000000c1': ('C001', 35.0, ['FAN'])}
LOOKS = {   # (trial id, thing): the look recorded on it
    ('t0000000000a1', 'TROWEL'): _look('side', 'pass', 'The whole trowel, side on, sharp; the handle is reddish-brown.', 't0000000000a1', 'f-trowel-side'),
    ('t0000000000a2', 'TROWEL'): _look('in the hand, lifting mortar', 'weak', 'In the hand, the blade half covered by mortar.', 't0000000000a2', 'f-trowel-use'),
    ('t0000000000a3', 'TROWEL'): _look('side', 'weak', 'Side on, but blurred by movement.', 't0000000000a3'),
    ('t0000000000b1', 'TILE'): _look('underside', 'pass', 'One tile turned over, the two lugs clear.', 't0000000000b1', 'f-tile-under'),
    ('t0000000000c1', 'FAN'): _look('whole', 'fail', 'A switch plate on a wall, not a fan regulator.', 't0000000000c1')}


def trials():
    """The content of `<run id>/visuals/trials.json`."""
    return {'trials': {tid: {'id': tid, 'clip': clip, 'at_s': at, 'key': f"{RUN['id']}/visuals/trials/{tid}.jpg", 'sha256': tid[-2:] * 32, 'elements': list(eids),
                             'looks': {eid: copy.deepcopy(look) for (t, eid), look in LOOKS.items() if t == tid}, 'at': NOW, 'by': 'u1'}
                       for tid, (clip, at, eids) in TRIALS.items()}}


def _frame(fid, eid, kind, name, tid, status='candidate'):
    clip, at, _ = TRIALS[tid]
    look = LOOKS[(tid, eid)]
    return {'id': fid, 'element_id': eid, 'element_kind': kind, 'name': name, 'kind': 'frame', 'subject': name, 'status': status, 'approval': None,
            'key': f"{RUN['id']}/visuals/references/{fid}.png", 'sha256': fid[-1] * 64, 'bytes': 1000, 'width': 1920, 'height': 1080, 'created_at': NOW,
            'source': {'media_id': clip, 'source_sha256': 'c' * 64, 'requested_s': at},
            'view': look['view'], 'look': copy.deepcopy(look), 'weak': look['verdict'] == 'weak', 'trial': tid}


def _found(result, clips, note, kept=(), closest=None):
    return {'result': result, 'by': 'helper', 'at': NOW, 'fingerprint': 'fp-at-search', 'clips': list(clips), 'note': note, 'kept': list(kept), 'closest': closest}


VIEWS = {'MASON': ['full length, front', 'right hand and forearm', 'the face'],
         'STREET': ['the whole place', 'from the other side', 'its fixed things'],
         'T_LAY': ['the action at its key moment', 'the result just after', 'the tool meeting the material']}
ROWS = {   # the round file's own fields per thing: rec, reason, doubt, first, prompt
    'MASON': ('set', 'A person a picture is made of.', False, True, ''),
    'TROWEL': ('footage', 'The film shows it whole and sharp from the side.', True, False, ''),          # doubtful: one kept frame is weak
    'FAN': ('no_set', 'One wide shot; its words carry it.', True, False, ''),                           # doubtful: not found, with a closest picture
    'BRICK': ('set', 'Seen close in two shots.', False, False, ''),
    'STREET': ('set', 'The opening place, seen wide.', False, True, ''),
    'T_LAY': ('set', 'The key action of the film.', False, True, 'The brick is wet from soaking.'),
    'TILE': ('set', 'It has approved drawings; the footage shows only its underside.', False, False, '')}


def _row(eid, frames=()):
    rec, reason, doubt, first, prompt = ROWS[eid]
    return {'frames': list(frames), 'keywords': '', 'verdict': None, 'search_id': None, 'error': None, 'prompt': prompt, 'corrections': [], 'set': None, 'round': 0,
            'rec': rec, 'reason': reason, 'doubt': doubt, 'first': first, 'operator_words': [], 'history': []}


def _check(failed=()):
    lines = [{'check': 'the view', 'weight': 'must', 'pass': True, 'seen': 'It shows the view asked.'},
             {'check': 'no text', 'weight': 'must', 'pass': True, 'seen': 'No text.'}]
    bad = [{'check': c, 'weight': 'must', 'pass': False, 'seen': seen} for c, seen in failed]
    return {'code': [{'check': 'size', 'pass_when': 'the picture is 16:9', 'weight': 'must', 'pass': True, 'seen': '2752x1536'}],
            'lines': lines + bad, 'must_failed': bad, 'model': 'gemini-3.8-flash'}


def _set(eid, kind, n=1, status='candidate', checks=True, looks=True, failed=()):
    """The three reference rows of one made set (make number `n`), as the worker leaves them. Returns (set id, {reference id: row})."""
    sid = f's-{eid.lower()}-{n}'
    out = {}
    for i, view in enumerate(VIEWS[eid], 1):
        rid = sid if i == 1 else f'{sid}-{i}'
        row = {'id': rid, 'element_id': eid, 'element_kind': kind, 'name': f'set-{eid}-r{n}' + ('' if i == 1 else f'-{i}'), 'kind': 'sheet', 'subject': eid,
               'status': status, 'job_id': f'job-{sid}', 'set': sid, 'set_n': i, 'view': view,
               'generation': {'op': 'generate', 'provider': 'gemini', 'model': 'gemini-nano-banana-2.1', 'prompt': f'the request of {eid}, make {n}', 'size': {'aspect': '16:9', 'tier': '2K'},
                              'quality': 'high', 'parents': []}}
        if status == 'generating':
            if i == 1:
                out[rid] = row   # the other two exist only once the job is back
            continue
        row.update(key=f"{RUN['id']}/visuals/references/{rid}.png", sha256=str(i) * 64, bytes=5000, width=2752, height=1536,
                   notes='(1) One method, the most common. (3) The request asked for a wooden scaffold; the photographs show bamboo: I drew bamboo.',
                   sources=[{'url': 'https://example.org/a', 'title': 'A page'}])
        if checks:
            row['check'] = _check(failed if i == 2 else ())
        if looks:
            row['look'] = _look(view, 'weak' if (failed and i == 2) else 'pass', f'{view}: as asked.', ref=rid)
        out[rid] = row
    return sid, out


def session(state='2'):
    """A session whose v2 round is at `state`: '1', 'making', 'looking', '2', 'rewrite' or 'complete' (design/211 section 3.8)."""
    assert state in ('1', 'making', 'looking', '2', 'rewrite', 'complete'), state
    refs = {'f-trowel-side': _frame('f-trowel-side', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a1'),
            'f-trowel-use': _frame('f-trowel-use', 'TROWEL', 'object', 'frame-TROWEL', 't0000000000a2'),
            'f-tile-under': _frame('f-tile-under', 'TILE', 'object', 'frame-TILE', 't0000000000b1')}
    rows = {'MASON': _row('MASON'), 'TROWEL': _row('TROWEL', ['f-trowel-side', 'f-trowel-use']), 'FAN': _row('FAN'), 'BRICK': _row('BRICK'), 'STREET': _row('STREET'),
            'T_LAY': _row('T_LAY'), 'TILE': _row('TILE', ['f-tile-under'])}
    rd = {'pass': 1, 'at': NOW, 'by': 'u1', 'elements': rows, 'quote': None, 'kept': True, 'v': 2, 'go': 1, 'rest': []}
    s = {'contract': 'vw2-visuals-session-v1', 'current': 'v1', 'refs': 'kept', 'cap_inr': CAP, 'cap_from': 'length', 'accepted': {'G1': {}, 'G2': {}, 'G3': {}},
         'choice_selections': {}, 'references': refs, 'golden': {}, 'round': rd,
         'drawings': {'TILE': {'status': 'approved', 'sha256': 'e' * 64, 'views': [{'id': 'iso', 'kind': 'iso', 'plain_key': f"{RUN['id']}/visuals/drawings/TILE/iso.png", 'plain_sha256': 'f' * 64}]}},
         'found': {'MASON': _found('none', ['C001'], 'Only his hands are seen.'),
                   'TROWEL': _found('found', ['C001'], 'Two views in one clip.', ['f-trowel-side', 'f-trowel-use']),
                   'FAN': _found('none', ['C001', 'C002'], 'No indoor wall is filmed.', closest='t0000000000c1'),
                   'BRICK': _found('not_searched', [], 'The helper was stopped.'),
                   'STREET': _found('none', ['C001', 'C002'], 'No street is filmed.'),
                   'T_LAY': _found('none', ['C001'], 'The laying is never seen whole.'),
                   'TILE': _found('found', ['C002'], 'The underside only.', ['f-tile-under'])}}
    if state == '1':
        return s
    # step 1 recorded: TROWEL from its footage, FAN left out, the first go ordered, the rest waiting
    for fid in ('f-trowel-side', 'f-trowel-use', 'f-tile-under'):
        refs[fid].update(status='approved', approval={'by': 'u1', 'at': NOW, 'quote': 'Done, on the page', 'sha256': refs[fid]['sha256']})
    rows['TROWEL'].update(verdict='approve', from_footage=True)
    s['golden']['TROWEL'] = 'f-trowel-side'
    rows['FAN'].update(verdict='ignore', ignored=True)
    rows['STREET']['operator_words'] = ['The street is wider than it looks.']
    for eid in ('MASON', 'STREET', 'T_LAY', 'BRICK', 'TILE'):
        rows[eid]['verdict'] = 'approve'
    rd.update({'pass': 'making', 'quote': 'Done, on the page', 'rest': ['BRICK', 'TILE']})
    kinds = {'MASON': 'person', 'STREET': 'place', 'T_LAY': 'technique'}
    made = lambda eid, n=1, **kw: _set(eid, kinds[eid], n, **kw)
    stamp = {'at': NOW, 'specs': {}, 'photo': None, 'fp': 'fp-at-make'}
    if state == 'making':
        for eid in FIRST:
            sid, new = made(eid, status='generating')
            refs.update(new)
            rows[eid].update(set=sid, round=1, made=dict(stamp))
        return s
    looked = state != 'looking'
    for eid in FIRST:
        sid, new = made(eid, looks=looked, failed=(('the action is shown', 'A tool lying still; no hand.'),) if eid == 'T_LAY' else ())
        refs.update(new)
        rows[eid].update(set=sid, round=1, made=dict(stamp), parts={'kind': kinds[eid], 'subject': eid, 'source': 'web'})
        if looked:
            rows[eid]['set_look'] = {'who': 'helper', 'at': NOW, 'set': sid, 'recommend': 'remake' if eid == 'T_LAY' else 'use', 'golden': None if eid in ('T_LAY', 'MASON') else sid,
                                     'reason': 'Picture B shows no hand at work.' if eid == 'T_LAY' else 'All three agree with the plan.'}
    if state in ('looking', '2'):
        return s
    # the operator judged the first sets: MASON and STREET yes, T_LAY "Correct it"
    for eid in ('MASON', 'STREET'):
        for rid in [r for r, x in refs.items() if x.get('set') == rows[eid]['set']]:
            refs[rid].update(status='approved', approval={'by': 'u1', 'at': NOW, 'quote': 'Sets done', 'sha256': refs[rid]['sha256']})
        rows[eid]['verdict'] = 'yes'
        s['golden'][eid] = rows[eid]['set']
    old = rows['T_LAY']['set']
    for rid in [r for r, x in refs.items() if x.get('set') == old]:
        refs[rid].update(status='rejected', rejection={'by': 'u1', 'at': NOW, 'quote': 'Sets done', 'notes': 'Show the hand pressing the brick down.'})
    rows['T_LAY'].update(verdict='correct', operator_words=['Show the hand pressing the brick down.'])
    rd['pass'] = 2
    if state == 'rewrite':
        rows['T_LAY']['rewrite_due'] = {'words': 'Show the hand pressing the brick down.', 'set': old, 'at': NOW}
        return s
    # complete: the rewrite was sent, the second make approved; the operator left the rest out
    rows['T_LAY'].update(prompt='The right hand presses the wet brick into the mortar bed.',
                         history=[{'n': 1, 'set': old, 'added': 'The brick is wet from soaking.', 'operator': 'Show the hand pressing the brick down.', 'at': NOW}])
    sid, new = made('T_LAY', 2, status='approved')
    refs.update(new)
    rows['T_LAY'].update(set=sid, round=2, verdict='yes', set_look={'who': 'helper', 'at': NOW, 'set': sid, 'recommend': 'use', 'golden': sid, 'reason': 'The hand is at work in all three.'})
    s['golden']['T_LAY'] = sid
    for eid in ('BRICK', 'TILE'):
        rows[eid].update(verdict='ignore', ignored=True)
    rd.update({'pass': 'complete', 'rest': [], 'go': 1})
    return s


def older_session():
    """A round of before design/211 (no `v`), at step 2: STREET's set made the older way, the check on its first picture only, with the false
    size failure; TROWEL taken from its first frame. Nothing of design/211 may change what the server does with it."""
    s = session('1')
    s.pop('found')
    rd = s['round']
    for k in ('v', 'go', 'rest'):
        rd.pop(k)
    for eid, row in rd['elements'].items():
        for k in ('rec', 'reason', 'doubt', 'first', 'operator_words', 'history'):
            row.pop(k)
        row['prompt'] = row['prompt'] or f'The subject block of {eid}.'
    for fid in ('f-trowel-side', 'f-trowel-use', 'f-tile-under'):
        for k in ('view', 'look', 'weak', 'trial'):
            s['references'][fid].pop(k)
        s['references'][fid].update(status='approved', approval={'by': 'u1', 'at': NOW, 'quote': 'Pass 1 done', 'sha256': s['references'][fid]['sha256']})
    for eid in THINGS:
        rd['elements'][eid]['verdict'] = 'approve'
    rd['elements']['TROWEL']['from_footage'] = True
    s['golden']['TROWEL'] = 'f-trowel-side'
    sid, new = _set('STREET', 'place', looks=False)
    for i, (rid, row) in enumerate(new.items(), 1):
        row.pop('view')
        row.pop('check')
        if i == 1:
            row['check'] = {'code': [{'check': 'size', 'pass_when': "the picture is {'aspect': '16:9', 'tier': '2K'}", 'weight': 'must', 'pass': False, 'seen': '2752x1536'}],
                            'lines': [], 'must_failed': [{'check': 'size', 'weight': 'must', 'pass': False, 'seen': '2752x1536'}], 'model': 'gemini-3.8-flash'}
    s['references'].update(new)
    rd['elements']['STREET'].update(set=sid, round=1, made={'at': NOW, 'specs': {}, 'photo': None})
    rd.update({'pass': 'making', 'quote': 'Pass 1 done'})   # 'making' with nothing being made reads as step 2 (visuals_stage._round_pass)
    return s


def specs_approved(s, p, spec_digest):
    """The session `s` with BRICK's material spec approved; `spec_digest` is `visuals_stage.spec_digest`."""
    brick = next(e for e in p['elements'] if e['id'] == 'BRICK')
    s.setdefault('spec_approvals', {})['element:BRICK'] = {'digest': spec_digest(brick['material_spec']), 'by': 'u1', 'at': NOW}
    return s
