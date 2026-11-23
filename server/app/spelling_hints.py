"""Spellings to start from, for a word the voice says wrongly (design/208 section J, SK, 16 Nov 2026). Since 23 Nov 2026 (SK) they are the word
written in an Indian script, Hindi first and Tamil second: the voice then says it the Indian way, and the script keeps its English spelling. The
older English respellings (syllables with hyphens) are retired. The operator asks with a button on the word page; they are guesses and the operator's
ear decides. One small text request through the server's Gemini key pool; it never blocks anything: a failure is one plain line."""
import json
import re

from . import keys
from .config import settings
from .errors import Problem

MODEL = 'gemini-3.8-flash'
MOST = 2   # per script: a word in capitals has two forms, said as one word and said letter by letter
SCRIPTS = (('hindi', 'Hindi script', re.compile('^[ऀ-ॿ‌‍ ]+$')), ('tamil', 'Tamil script', re.compile('^[஀-௿‌‍ ]+$')))
LIST = {'type': 'array', 'items': {'type': 'string'}}
SCHEMA = {'type': 'object', 'properties': {'hindi': LIST, 'tamil': LIST}, 'required': ['hindi', 'tamil']}
NONE_NOW = 'No suggestion could be made now. Type or paste your own spelling.'


def clean(word, raw):
    """At most two spellings per script, Hindi first: only that script's letters and spaces, no repeat, at most 120 characters (the word check's limit)."""
    out = []
    for key, label, letters in SCRIPTS:
        got = raw.get(key) if isinstance(raw, dict) else None
        kept = []
        for s in got if isinstance(got, list) else []:
            s = ' '.join(str(s or '').split())
            if s and len(s) <= 120 and letters.match(s) and s not in kept:
                kept.append(s)
        out += [{'label': label, 'text': s} for s in kept[:MOST]]
    return out


def build(word, sentence):
    ask = (f'A text-to-speech voice mispronounces "{word}" in this sentence of an English narration:\n{sentence}\n\n'
           f'Write "{word}" in Hindi script (Devanagari) and in Tamil script, so that a voice reading those letters says it correctly. '
           'Follow its sound, not its meaning: transliterate, never translate. Write it as it is spoken today, not in an old or bookish spelling. '
           'Normally give one spelling in each script. If it is an abbreviation written in capitals, give two in each script: first said as one word, '
           'then said letter by letter with a space between the letters. Letters and spaces only: no Latin letters, no digits, no punctuation, no explanation.')
    return {'contents': [{'role': 'user', 'parts': [{'text': ask}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 512}}


def suggest(word, sentence, transport_factory=None):
    """The word in Hindi and Tamil script, labelled, or a Problem with one plain line (no key, the provider down, nothing usable)."""
    if not keys.pool('gemini', settings()):
        raise Problem(503, 'HINTS', NONE_NOW)
    try:
        if transport_factory is None:
            from .analysis_jobs import transport_factory
        received, _ = keys.gemini(transport_factory, MODEL, lambda t: t.generate(build(word, sentence)), settings(),
                                  terminal_deadline_seconds=40, initial_soft_wait_seconds=10, on_update=lambda e: None, capture_answer_deltas=False)
        body = received.get('body')
        if not isinstance(body, dict):
            body = json.loads(received.get('raw') or '{}')
        out = clean(word, body)
    except Exception:   # a hint is never worth an error page
        out = []
    if not out:
        raise Problem(503, 'HINTS', NONE_NOW)
    return out
