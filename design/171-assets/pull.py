"""Pull VW-18's four test shots (scene, shot, elements, foundation) and every picture of their elements into /tmp/vw18/."""
import json, os, sys
sys.path.insert(0, '/opt/vw2/app/server')
from app.storage import storage
RUN = 'c16d3ff0-84ad-47ff-980d-f39567340708'
SHOTS = {'BEAT_06-B1-s1': 'plinth', 'BEAT_06-B1-s3': 'string', 'BEAT_04-B1-S1': 'kiln', 'B10_SH1': 'pointing'}
s = storage()
plan = json.loads(s.get(f'{RUN}/visuals/plan-v5.json'))['document']
sess = json.loads(s.get(f'{RUN}/visuals/session.json'))
out = '/tmp/vw18'; os.makedirs(out + '/pics', exist_ok=True)
els = {e['id']: e for e in plan['elements']}
picked = {'foundation': plan['foundation'], 'shots': {}, 'elements': {}, 'references': {}}
need = set()
for g in plan['gaps']:
    for sc in g['scenes']:
        for sh in sc['shots']:
            if sh['id'] in SHOTS:
                picked['shots'][SHOTS[sh['id']]] = {'gap': {k: v for k, v in g.items() if k != 'scenes'}, 'scene': {k: v for k, v in sc.items() if k != 'shots'}, 'shot': sh}
                need |= set(sh.get('element_ids') or [])
for eid in sorted(need):
    picked['elements'][eid] = els[eid]
rows = [r for r in sess['references'].values() if r.get('element_id') in need and r.get('status') in ('approved', 'candidate') and r.get('key') and r.get('kind') in ('sheet', 'frame', 'isolated', 'web', 'supplied')]
for r in rows:
    fn = f"{r['element_id']}__{r['kind']}__{r.get('set_n') or ''}__{r['id'][:8]}.png"
    data = s.get(r['key'])
    if data[:4] != b'\x89PNG':
        fn = fn[:-4] + ('.jpg' if data[:2] == b'\xff\xd8' else '.bin')
    open(f'{out}/pics/{fn}', 'wb').write(data)
    picked['references'][r['id']] = {k: r.get(k) for k in ('id', 'element_id', 'kind', 'status', 'set', 'set_n', 'subject', 'name', 'width', 'height', 'golden')} | {'file': fn, 'bytes': len(data)}
picked['golden'] = sess.get('golden')
picked['fps'] = sess.get('source', {}).get('fps')
json.dump(picked, open(f'{out}/vw18-shots.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('shots', list(picked['shots']), 'elements', len(need), 'pictures', len(rows), 'fps', picked['fps'])
for eid in sorted(need):
    print(eid, els[eid]['kind'], '|', sorted(f"{r['kind']}{r.get('set_n') or ''}:{r['status'][:4]}" for r in rows if r['element_id'] == eid))
