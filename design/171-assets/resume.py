"""Resume a submitted Wan task: poll with `result get`, save, rename, probe, log. usage: resume.py RUN TASKID OUTDIR"""
import json, os, shutil, subprocess, sys, time
src = open('wan_test.py', encoding='utf-8').read().split('def main')[0]; exec(src)
run, task, out = sys.argv[1:4]
t0 = time.time()
while True:
    res = wan('result', 'get', task, timeout=120); label = res.get('statusLabel')
    if label in ('succeeded', 'failed', 'canceled', 'cancelled') or time.time() - t0 > 1500: break
    time.sleep(15)
log = {'run': run, 'task_id': task, 'status': label, 'resumed': True}
if label == 'succeeded':
    saved = wan('result', 'get', task, '--save', '--save-dir', os.path.abspath(out), timeout=600)
    files = saved.get('savedFiles') or []
    if files:
        dst = f'{out}/{run}.mp4'; shutil.move(files[0]['path'], dst); log['file'] = dst; log['watermark'] = files[0].get('watermark')
log['credits_after'] = credits()
json.dump(log, open(f'{out}/{run}.log.json', 'w'), indent=1); print(run, label, log.get('file'), 'credits', log['credits_after'])
