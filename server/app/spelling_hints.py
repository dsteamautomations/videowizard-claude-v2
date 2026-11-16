"""design/208 section J (SK, 16 Nov 2026): spellings to start from, for a word the voice says wrongly. The operator asks for them with a button on the
word page; they are guesses in the house style (syllables with hyphens, the stressed one in capitals), and the operator's ear decides. One small text
request through the server's Gemini key pool; it never blocks anything: a failure is one plain line."""
import json
import re

from . import keys
from .config import settings
from .errors import Problem

MODEL = 'gemini-3.8-flash'
MOST = 3
SCHEMA = {'type': 'object', 'properties': {'spellings': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['spellings']}
PLAIN = re.compile(r"^[A-Za-z][A-Za-z' -]{0,58}[A-Za-z]$")   # letters, hyphens, spaces and apostrophes only: what a voice reads as text
NONE_NOW = 'No suggestion could be made now. Type your own spelling, or look the word up.'


def clean(word, raw):
    """At most three spellings a voice can read as plain text: no phonetic symbols, not the word itself, no repeat, not too long."""
    out = []
    for s in raw or []:
        s = ' '.join(str(s or '').split())
        if PLAIN.match(s) and s.lower() != str(word).lower() and s.lower() not in [x.lower() for x in out]:
            out.append(s)
        if len(out) == MOST:
            break
    return out


def build(word, sentence):
    ask = (f'A text-to-speech voice mispronounces the word "{word}" in this sentence of a narration:\n{sentence}\n\n'
           f'Give {MOST} different respellings of "{word}" that an English text-to-speech voice would read aloud with the right sounds. '
           'Write each the way a newspaper pronunciation guide does: plain English letters only, syllables separated by hyphens, the stressed syllable in capitals, '
           'for example "kun-yah-koo-MAH-ree". No phonetic symbols, no slashes, no explanation. If the word is a name or a word of another language, follow how '
           'it is said in that language, written for an English reader.')
    return {'contents': [{'role': 'user', 'parts': [{'text': ask}]}],
            'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': SCHEMA, 'thinkingConfig': {'thinkingLevel': 'LOW'}, 'maxOutputTokens': 512}}


def suggest(word, sentence, transport_factory=None):
    """Up to three spellings for the word, or a Problem with one plain line (no key, the provider down, nothing usable)."""
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
        out = clean(word, body.get('spellings'))
    except Exception:   # a hint is never worth an error page
        out = []
    if not out:
        raise Problem(503, 'HINTS', NONE_NOW)
    return out
