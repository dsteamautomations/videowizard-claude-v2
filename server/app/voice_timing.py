"""Generation-time timing evidence (ported from v1). No transcription, forced alignment or listening claim."""
import base64
import hashlib
import json
import math
import re
import subprocess

from .config import settings
from .errors import Problem

PARSER = 'reference-paragraphs-v1'


def spans(text):
    start = 0
    for separator in re.finditer(r'\n\s*\n', text):
        if text[start:separator.start()].strip():
            yield start, separator.start()
        start = separator.end()
    if text[start:].strip():
        yield start, len(text)


def inspect_audio(path):
    try:
        result = subprocess.run([settings().FFPROBE_EXECUTABLE, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
                                capture_output=True, check=True, timeout=60)
        data = json.loads(result.stdout)
        streams = [s for s in data['streams'] if s.get('codec_type') == 'audio']
        duration = float(data['format']['duration'])
        if len(streams) != 1 or not math.isfinite(duration) or duration <= 0:
            raise ValueError()
        subprocess.run([settings().FFMPEG_EXECUTABLE, '-v', 'error', '-xerror', '-i', str(path), '-map', '0:a:0', '-f', 'null', '-'],
                       capture_output=True, check=True, timeout=120)
        return {'duration_s': duration, 'sample_rate': int(streams[0]['sample_rate']), 'channels': streams[0]['channels'], 'codec': streams[0]['codec_name'], 'full_decode_checked': True}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        raise ValueError('Audio decode or duration validation failed.') from None


def decode_response(response):
    try:
        payload = response.json()
        data = base64.b64decode(payload['audio_base64'], validate=True)
        return data, {k: payload.get(k) for k in ('alignment', 'normalized_alignment')}
    except (ValueError, KeyError, TypeError):
        raise Problem(502, 'PROVIDER_UNKNOWN', 'Timed response could not be decoded. The response is retained; no automatic second synthesis.') from None


def validate_alignment(value):
    if not isinstance(value, dict):
        raise ValueError('Alignment is missing.')
    chars, starts, ends = value.get('characters'), value.get('character_start_times_seconds'), value.get('character_end_times_seconds')
    if not all(isinstance(x, list) for x in (chars, starts, ends)) or not chars or len(chars) != len(starts) or len(chars) != len(ends):
        raise ValueError('Character and time array lengths differ or are empty.')
    previous_start = previous_end = 0
    for char, start, end in zip(chars, starts, ends):
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError('Alignment contains invalid characters.')
        if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0 for x in (start, end)):
            raise ValueError('Alignment contains invalid seconds.')
        if start > end or start < previous_start or end < previous_end:
            raise ValueError('Alignment seconds are not ordered.')
        previous_start, previous_end = start, end
    return ''.join(chars)


def timing_evidence(snapshot, alignments):
    raw = validate_alignment(alignments.get('alignment'))
    if alignments.get('normalized_alignment') is not None:
        validate_alignment(alignments['normalized_alignment'])
    exact = raw == snapshot['text']
    words = []
    if exact:
        a = alignments['alignment']
        paragraph_spans = list(spans(raw))
        passage = 0
        for i, match in enumerate(re.finditer(r'\S+', raw)):
            while match.start() >= paragraph_spans[passage][1]:
                passage += 1
            words.append({'id': f'W{i + 1:05d}', 'text': match.group(), 'passage_id': f'P{passage + 1:03d}',
                          'start_s': a['character_start_times_seconds'][match.start()], 'end_s': a['character_end_times_seconds'][match.end() - 1],
                          'character_start': match.start(), 'character_end': match.end()})
    return {'contract': 'videowizard-generation-timing-v1', 'source_clock': 'narration_source_seconds', 'method': 'elevenlabs_tts_with_timestamps',
            'source_script': snapshot['source_script'], 'text_sha256': hashlib.sha256(snapshot['text'].encode()).hexdigest(),
            'alignments': alignments, 'script_characters_match': exact, 'words': words, 'passage_parser': PARSER,
            'last_character_end_s': alignments['alignment']['character_end_times_seconds'][-1],
            'verification_scope': 'provider character timing structure and exact input text identity; no listening verification'}
