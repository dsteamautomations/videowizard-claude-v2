"""Narration in pieces (design/40): split a long script at paragraph ends (sentence ends inside a paragraph that is itself too
long), identify each piece by what is sent to the provider, join the pieces' audio once, and merge their character timings over
the full text so every consumer sees one narration and one timing file. Standard library only; ffmpeg for the join."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PARAGRAPH = re.compile(r'\n\s*\n')
SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


def _trimmed(text, a, b):
    """[a, b) narrowed to its non-whitespace content."""
    seg = text[a:b]
    return a + (len(seg) - len(seg.lstrip())), b - (len(seg) - len(seg.rstrip()))


def paragraph_spans(text):
    start = 0
    for sep in PARAGRAPH.finditer(text):
        if text[start:sep.start()].strip():
            yield _trimmed(text, start, sep.start())
        start = sep.end()
    if text[start:].strip():
        yield _trimmed(text, start, len(text))


def split_for_narration(text, limit):
    """[{offset, characters}] in order: whole paragraphs packed under the limit; a paragraph over the limit is split at sentence
    ends and packed; a single sentence over the limit raises ValueError. The pieces, read from the text at their offsets,
    reproduce every spoken character; the gaps between pieces are the separators that were cut."""
    limit = int(limit)
    units = []
    for s, e in paragraph_spans(text):
        if e - s <= limit:
            units.append((s, e))
            continue
        pos = s
        for m in SENTENCE_END.finditer(text, s, e):
            if text[pos:m.start()].strip():
                units.append(_trimmed(text, pos, m.start()))
            pos = m.end()
        if text[pos:e].strip():
            units.append(_trimmed(text, pos, e))
    for a, b in units:
        if b - a > limit:
            raise ValueError(f'one sentence of {b - a:,} characters exceeds the model limit of {limit:,} per request; split it in the script stage')
    pieces, current = [], None
    for a, b in units:
        if current is None:
            current = [a, b]
        elif b - current[0] <= limit:
            current[1] = b
        else:
            pieces.append(tuple(current))
            current = [a, b]
    if current:
        pieces.append(tuple(current))
    return [{'offset': a, 'characters': b - a} for a, b in pieces]


def piece_identity(snapshot, text):
    """What the provider is asked for, hashed: the same request is journaled once and never paid for twice."""
    body = {'voice_id': snapshot.get('voice_id'), 'model_id': snapshot.get('model_id'), 'settings': snapshot.get('settings'),
            'format': snapshot.get('format'), 'text': text}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def pieces_of(snapshot):
    """The pieces of a narration snapshot with their texts and identities; a snapshot without `pieces` is one piece."""
    text = snapshot['text']
    rows = snapshot.get('pieces') or [{'offset': 0, 'characters': len(text)}]
    out = []
    for r in rows:
        piece_text = text[r['offset']:r['offset'] + r['characters']]
        out.append({'offset': r['offset'], 'characters': r['characters'], 'text': piece_text, 'identity': piece_identity(snapshot, piece_text)})
    return out


def merge_alignments(full_text, pieces):
    """pieces: [{offset, text, alignment, duration_s[, normalized_alignment]}] in order. Each piece's character times are clamped
    to its decoded duration and shifted by the durations before it; separator characters take the boundary time. Returns
    {'alignment', 'normalized_alignment' (one piece only), 'pieces': [{'overshoot_s'}]}."""
    n = len(full_text)
    chars, starts, ends = list(full_text), [0.0] * n, [0.0] * n
    t, cursor, info = 0.0, 0, []
    for p in pieces:
        a = p['alignment']
        if ''.join(a['characters']) != p['text']:
            raise ValueError('A piece alignment does not match its text; the response is retained. Do not regenerate.')
        off, dur = p['offset'], float(p['duration_s'])
        if off < cursor:
            raise ValueError('Pieces overlap.')
        for i in range(cursor, off):
            starts[i] = ends[i] = round(t, 4)
        overshoot = 0.0
        for i, (s, e) in enumerate(zip(a['character_start_times_seconds'], a['character_end_times_seconds'])):
            overshoot = max(overshoot, e - dur)
            s, e = min(float(s), dur), min(float(e), dur)
            starts[off + i], ends[off + i] = round(t + s, 4), round(t + e, 4)
        cursor = off + len(p['text'])
        t = round(t + dur, 4)
        info.append({'overshoot_s': round(max(0.0, overshoot), 3)})
    for i in range(cursor, n):
        starts[i] = ends[i] = round(t, 4)
    return {'alignment': {'characters': chars, 'character_start_times_seconds': starts, 'character_end_times_seconds': ends},
            'normalized_alignment': pieces[0].get('normalized_alignment') if len(pieces) == 1 else None, 'pieces': info}


def concat_mp3(paths, out_path, ffmpeg='ffmpeg'):
    """One piece is copied; several are joined with one re-encode (mp3 44.1 kHz 128 kb/s). Written atomically."""
    paths, out_path = [Path(p) for p in paths], Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp = out_path.with_suffix(out_path.suffix + '.tmp')
    if len(paths) == 1:
        shutil.copyfile(paths[0], temp)
    else:
        with tempfile.TemporaryDirectory() as d:
            listing = Path(d) / 'pieces.txt'
            listing.write_text(''.join(f"file '{p.resolve().as_posix()}'\n" for p in paths), encoding='utf-8')
            subprocess.run([ffmpeg, '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing), '-map', '0:a:0',
                            '-c:a', 'libmp3lame', '-b:a', '128k', '-ar', '44100', '-f', 'mp3', str(temp)], check=True, capture_output=True, timeout=600)
    os.replace(temp, out_path)
    return out_path
