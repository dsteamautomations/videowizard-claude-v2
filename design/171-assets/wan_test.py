"""Reusable Wan 3.0 Omni test runner (design/170 §4). One job per call; the worker's provider will follow these steps line for line.

usage: wan_test.py RUN --prompt p.txt --images a.png,b.png [--videos v.mp4 --video-ranges 0:5] [--audios x.mp3] [--duration 8 | --smart]
                   [--ratio 16:9] [--resolution 720P] [--audio-output false] --out DIR
steps: check inputs and tags locally (never --dry-run: it submits) -> credits before -> submit -> poll with `result get` -> save -> credits after -> log line.
The key is the CLI's saved login on this machine (never read, never printed)."""
import argparse, json, os, re, shutil, subprocess, sys, time

WAN_JS = os.path.join(subprocess.run(['npm.cmd' if os.name == 'nt' else 'npm', 'root', '-g'], capture_output=True, text=True).stdout.strip(), '@wan-ai', 'cli', 'dist', 'index.js')
WAN = [shutil.which('node') or 'node', WAN_JS]   # the JS entry through node: the Windows .cmd shim cuts a multi-line prompt at its first line break


def wan(*args, timeout=120):
    r = subprocess.run([*WAN, *args, '--output', 'json'], capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    out = r.stdout.strip()
    try:
        return json.loads(out[out.index('{'):]) if '{' in out else {'ok': False, 'raw': out, 'stderr': r.stderr[-500:]}
    except json.JSONDecodeError:
        return {'ok': False, 'raw': out[-800:], 'stderr': r.stderr[-500:]}


def credits():
    d = wan('credits')
    return d.get('availableCount') if d.get('ok', True) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run'); ap.add_argument('--prompt', required=True); ap.add_argument('--images', default=''); ap.add_argument('--videos', default='')
    ap.add_argument('--video-ranges', default=''); ap.add_argument('--audios', default=''); ap.add_argument('--audio-ranges', default='')
    ap.add_argument('--duration', type=int); ap.add_argument('--smart', action='store_true'); ap.add_argument('--ratio', default='16:9')
    ap.add_argument('--resolution', default='720P'); ap.add_argument('--audio-output', default='false'); ap.add_argument('--out', required=True)
    ap.add_argument('--poll', type=int, default=15); ap.add_argument('--max-wait', type=int, default=1500)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    prompt = open(a.prompt, encoding='utf-8').read().strip()
    imgs = [p for p in a.images.split(',') if p]; vids = [p for p in a.videos.split(',') if p]; auds = [p for p in a.audios.split(',') if p]
    for p in imgs + vids + auds:
        assert os.path.isfile(p), f'missing input {p}'
    tags = {f'@Image{i+1}' for i in range(len(imgs))} | {f'@Video{i+1}' for i in range(len(vids))} | {f'@Audio{i+1}' for i in range(len(auds))}
    used = set(re.findall(r'@(?:Image|Video|Audio)\d+', prompt))
    assert used <= tags, f'prompt names references that were not passed: {sorted(used - tags)}'
    assert tags <= used, f'inputs passed but never named in the prompt: {sorted(tags - used)}'
    args = ['omni2video', '--prompt', prompt, '--ratio', a.ratio, '--resolution', a.resolution, f'--audio-output={a.audio_output}']
    if imgs: args += ['--images', ','.join(os.path.abspath(p) for p in imgs)]
    if vids: args += ['--videos', ','.join(os.path.abspath(p) for p in vids)]
    if a.video_ranges: args += ['--video-ranges', a.video_ranges]
    if auds: args += ['--audios', ','.join(os.path.abspath(p) for p in auds)]
    if a.audio_ranges: args += ['--audio-ranges', a.audio_ranges]
    args += ['--smart-duration=true'] if a.smart else ['--smart-duration=false', '--duration', str(a.duration or 5)]
    log = {'run': a.run, 'prompt_file': a.prompt, 'images': imgs, 'videos': vids, 'audios': auds, 'duration': 'smart' if a.smart else (a.duration or 5), 'ratio': a.ratio, 'resolution': a.resolution, 'audio_output': a.audio_output}
    # No --dry-run: on CLI 0.0.3 a dry run of omni2video created and ran a real task (two paid 5 s tasks on 5 Nov 2026); the tags are checked locally above.
    log['credits_before'] = credits()
    t0 = time.time()
    sub = wan(*args, timeout=600)
    json.dump(sub, open(f'{a.out}/{a.run}.submit.json', 'w', encoding='utf-8'), indent=1)
    task = sub.get('taskId') or (sub.get('data') or {}).get('taskId')
    if not task:
        print(a.run, 'SUBMIT FAILED', json.dumps(sub)[:800]); sys.exit(3)
    log['task_id'] = task; print(a.run, 'submitted', task, flush=True)
    while True:
        res = wan('result', 'get', task, timeout=120)
        label = res.get('statusLabel') or (res.get('data') or {}).get('statusLabel')
        if label in ('succeeded', 'failed', 'canceled', 'cancelled') or time.time() - t0 > a.max_wait:
            break
        time.sleep(a.poll)
    json.dump(res, open(f'{a.out}/{a.run}.result.json', 'w', encoding='utf-8'), indent=1)
    log['status'] = label; log['seconds'] = round(time.time() - t0)
    if label == 'succeeded':
        saved = wan('result', 'get', task, '--save', '--save-dir', os.path.abspath(a.out), timeout=600)
        files = saved.get('savedFiles') or (saved.get('data') or {}).get('savedFiles') or []
        if files:
            src = files[0]['path']; dst = f'{a.out}/{a.run}.mp4'
            shutil.move(src, dst); log['file'] = dst; log['watermark'] = files[0].get('watermark')
            pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,avg_frame_rate:format=duration', '-of', 'json', dst], capture_output=True, text=True)
            try:
                log['probe'] = json.loads(pr.stdout)
            except Exception:
                log['probe'] = pr.stdout[:300]
    log['credits_after'] = credits()
    if log.get('credits_before') is not None and log.get('credits_after') is not None:
        log['cost_credits'] = log['credits_before'] - log['credits_after']
    json.dump(log, open(f'{a.out}/{a.run}.log.json', 'w', encoding='utf-8'), indent=1)
    print(a.run, label, f"{log['seconds']}s", 'cost', log.get('cost_credits'), log.get('file', ''), 'watermark', log.get('watermark'))


if __name__ == '__main__':
    main()
