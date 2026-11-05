"""Review strips (design/167 D8): one frame every half second at 480 px wide, tiled with the second written on each; ffprobe facts and scene cuts.
usage: strips.py out/RUN.mp4 [step_s=0.5]"""
import json, os, subprocess, sys, math
from PIL import Image, ImageDraw


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height,avg_frame_rate,nb_frames:format=duration', '-of', 'json', path], capture_output=True, text=True)
    return json.loads(r.stdout)


def cuts(path):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-i', path, '-vf', "select='gt(scene,0.4)',showinfo", '-f', 'null', '-'], capture_output=True, text=True)
    return [float(l.split('pts_time:')[1].split()[0]) for l in r.stderr.splitlines() if 'pts_time:' in l and 'showinfo' in l]


def main(path, step=0.5):
    p = probe(path); dur = float(p['format']['duration'])
    v = next(s for s in p['streams'] if s['codec_type'] == 'video'); a = [s for s in p['streams'] if s['codec_type'] == 'audio']
    tmp = path + '.frames'; os.makedirs(tmp, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-vf', f'fps=1/{step},scale=480:-1', f'{tmp}/f%03d.png'], check=True)
    frames = sorted(f for f in os.listdir(tmp) if f.endswith('.png'))
    ims = [Image.open(f'{tmp}/{f}').convert('RGB') for f in frames]
    w, h = ims[0].size; cols = 6; rows = math.ceil(len(ims) / cols)
    sheet = Image.new('RGB', (cols * w, rows * (h + 18)), 'white'); d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * (h + 18); sheet.paste(im, (x, y + 18)); d.text((x + 4, y + 3), f'{i * step:.1f} s', fill='black')
    out = path[:-4] + '.strips.png'; sheet.save(out)
    facts = {'duration_s': round(dur, 2), 'size': f"{v['width']}x{v['height']}", 'fps': v.get('avg_frame_rate'), 'audio': bool(a), 'cuts_s': [round(c, 2) for c in cuts(path)], 'strips': out}
    print(json.dumps(facts)); return facts


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.5)
