"""design/136 (SK, 2 Nov 2026): the new guidebook version. Copies the 29 Oct version, puts in the rewritten guidebooks from design/136-guidebook-drafts,
leaves out the animatic-keyframes file (its sound parts are in the video-frame playbook's still card), and writes MANIFEST.json with the fingerprint.
Run once: python scripts/d136_library.py. The folder is named by the date and the fingerprint's first 12 characters."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'server' / 'library'
OLD = LIB / 'vwlib-2026-10-29-3d60877d3d23'
DRAFTS = ROOT / 'design' / '136-guidebook-drafts'
DROPPED = {'library/video/craft/animatic-keyframes.md'}
STATUS = 'videowizard, design/136: general part plus parts by video category (2026-11-02)'


def main():
    old = json.loads((OLD / 'MANIFEST.json').read_text(encoding='utf-8'))
    tmp = LIB / 'vwlib-new'
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(OLD, tmp)
    (tmp / 'MANIFEST.json').unlink()
    for rel in DROPPED:
        (tmp / rel).unlink()
    rewritten = set()
    for d in DRAFTS.rglob('*.md'):
        rel = d.relative_to(DRAFTS).as_posix()
        target = rel if rel in ('VW-MAP.md', 'FIELD-SOURCES.md') else f'library/{rel}'
        assert (OLD / target).is_file(), f'{target}: not a file of the old version'
        (tmp / target).write_bytes(d.read_bytes().replace(b'\r\n', b'\n'))
        rewritten.add(target)
    files = []
    for entry in old['files']:
        if entry['path'] in DROPPED:
            continue
        data = (tmp / entry['path']).read_bytes()
        files.append({**entry, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), **({'status': STATUS} if entry['path'] in rewritten else {})})
    files.sort(key=lambda f: f['path'])
    fp = hashlib.sha256(b''.join(f"{f['path']}".encode() + b'\0' + f['sha256'].encode() + b'\n' for f in files)).hexdigest()
    name = f'vwlib-2026-11-02-{fp[:12]}'
    manifest = {'version': name, 'created': '2026-11-02', 'library_master': old['library_master'], 'fingerprint_sha256': fp, 'fingerprint_rule': old['fingerprint_rule'],
                'note': ('design/136 (SK, 2 Nov 2026): every guidebook a step reads rewritten from the audit in design/136-guidebook-audit: a general part, then parts by '
                         'video category (documentary-explainer, advertisement-product, training-education, social-ugc, narrative-story), then parts not available yet; '
                         'text tuned to the copied projects, habits of older models, server-only settings and provenance removed. The animatic-keyframes file is left out. '
                         f'Copied from {OLD.name}.'), 'files': files}
    (tmp / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    final = LIB / name
    if final.exists():
        shutil.rmtree(final)
    tmp.rename(final)
    print(name, len(files), 'files;', len(rewritten), 'rewritten')
    return 0


if __name__ == '__main__':
    sys.exit(main())
