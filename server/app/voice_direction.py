"""Delivery direction on the accepted script (design/52 D, E): sentences by passage, the validator, tags applied before their
sentences for the provider, and the alignment stripped back to the accepted script. Pure; no provider, no database.

The words are never changed: a tag is inserted before a sentence's first character with one space after it, and the spans of
those insertions are kept so the provider's character timing can be returned to the accepted text. Pauses stay with the
scenes (design/19); reactions and accents are not direction for a narration."""
import hashlib
import json
import re

from .narration_pieces import SENTENCE_END, paragraph_spans

TAG = re.compile(r'^\[[^\[\]\n]{1,60}\]$')
MAX_TAG = 60
REACTIONS = ('clears throat', 'laugh', 'sigh', 'gasp', 'crying', 'cries', 'cry', 'sob', 'cough', 'giggle', 'chuckle', 'snort', 'groan', 'scream', 'yawn', 'exhale', 'inhale', 'breath')
PAUSES = ('long pause', 'pause', 'silence', 'silent', 'break', 'beat')
ACCENTS = ('accent',)


def sentences_of(text):
    """[{passage_id, sentence, start, end, text, first_words}] in order; passages are the script's paragraphs (P001…), sentences count inside each."""
    rows = []
    for p, (s, e) in enumerate(paragraph_spans(text), 1):
        pos, n = s, 0
        bounds = [m.start() for m in SENTENCE_END.finditer(text, s, e)] + [e]
        starts = [s] + [m.end() for m in SENTENCE_END.finditer(text, s, e)]
        for a, b in zip(starts, bounds):
            seg = text[a:b]
            if not seg.strip():
                continue
            a2 = a + (len(seg) - len(seg.lstrip()))
            b2 = b - (len(seg) - len(seg.rstrip()))
            n += 1
            words = text[a2:b2].split()
            rows.append({'passage_id': f'P{p:03d}', 'sentence': n, 'start': a2, 'end': b2, 'text': text[a2:b2], 'first_words': ' '.join(words[:5])})
    return rows


def _forbidden(tag):
    inner = tag.strip('[]').lower()
    for group in (REACTIONS, PAUSES, ACCENTS):
        for word in group:
            if re.search(r'(?<![a-z])' + re.escape(word) + r'(?:s|es|ing|ed)?(?![a-z])', inner):
                return word
    return None


def _tag_problem(tag, where):
    if not isinstance(tag, str) or not TAG.match(tag.strip()):
        if isinstance(tag, str) and len(tag.strip('[]')) > MAX_TAG:
            return f'{where}: a tag is at most {MAX_TAG} characters'
        return f'{where}: a tag is a short direction in square brackets, like [measured]'
    word = _forbidden(tag)
    if word:
        kind = 'a reaction' if word in REACTIONS else 'a pause' if word in PAUSES else 'an accent'
        return f'{where}: {tag} names {kind} ({word}); reactions, pauses and accents are not direction for a narration'
    return None


def validate(doc, text):
    """Problems with a direction document {register, items}; [] when it is sound. Every problem names what it refuses."""
    problems = []
    register = (doc.get('register') or '') if isinstance(doc, dict) else ''
    if not isinstance(register, str) or not register.strip():
        problems.append('register: the register of the whole film is required, as one tag like [measured]')
    else:
        p = _tag_problem(register.strip(), 'register')
        if p:
            problems.append(p)
    known = {(r['passage_id'], r['sentence']) for r in sentences_of(text)}
    seen = set()
    for i, item in enumerate(doc.get('items') or [] if isinstance(doc, dict) else [], 1):
        where = f'item {i}'
        if not isinstance(item, dict):
            problems.append(f'{where}: not an object')
            continue
        key = (item.get('passage_id'), item.get('sentence'))
        if key not in known:
            problems.append(f'{where}: {key[0]} sentence {key[1]} is not in the accepted script')
        elif key in seen:
            problems.append(f'{where}: one tag per sentence at most ({key[0]} sentence {key[1]} already has one)')
        seen.add(key)
        p = _tag_problem(item.get('tag'), where)
        if p:
            problems.append(p)
    return problems


def apply(text, items, register, tweaks=None):
    """The provider text: the register before the first sentence, each tag before its sentence; tweaks (per voice) replace or add a
    tag for a sentence without touching the base list. Returns (tagged_text, spans) with spans in the tagged text."""
    rows = {(r['passage_id'], r['sentence']): r for r in sentences_of(text)}
    tags = {(i['passage_id'], i['sentence']): i['tag'].strip() for i in (items or [])}
    for t in tweaks or []:
        tags[(t['passage_id'], t['sentence'])] = t['tag'].strip()
    inserts = {}   # position in the accepted text -> [tags]
    if rows and register and register.strip():
        first = min(rows.values(), key=lambda r: r['start'])
        inserts.setdefault(first['start'], []).append(register.strip())
    for key, tag in sorted(tags.items(), key=lambda kv: rows[kv[0]]['start'] if kv[0] in rows else -1):
        if key in rows:
            inserts.setdefault(rows[key]['start'], []).append(tag)
    out, spans, cursor, shift = [], [], 0, 0
    for pos in sorted(inserts):
        out.append(text[cursor:pos])
        for tag in inserts[pos]:
            piece = tag + ' '
            start = pos + shift
            out.append(piece)
            spans.append((start, start + len(piece)))
            shift += len(piece)
        cursor = pos
    out.append(text[cursor:])
    return ''.join(out), spans


def untag(tagged, spans):
    out, cursor = [], 0
    for a, b in spans:
        out.append(tagged[cursor:a])
        cursor = b
    out.append(tagged[cursor:])
    return ''.join(out)


def strip(alignment, tagged, spans, text):
    """The alignment returned to the accepted script: tag spans removed whether or not the provider timed them. Anything else raises."""
    chars = ''.join(alignment['characters'])
    if chars == text:
        return alignment
    if chars != tagged:
        raise ValueError('The provider alignment matches neither the directed text nor the accepted script; the response is retained. Do not regenerate.')
    drop = set()
    for a, b in spans:
        drop.update(range(a, b))
    keep = [i for i in range(len(chars)) if i not in drop]
    out = {k: [alignment[k][i] for i in keep] for k in ('characters', 'character_start_times_seconds', 'character_end_times_seconds')}
    if ''.join(out['characters']) != text:
        raise ValueError('Stripping the direction tags did not give back the accepted script; the response is retained. Do not regenerate.')
    return out


def digest(items, register):
    body = {'register': (register or '').strip(), 'items': sorted((i['passage_id'], int(i['sentence']), i['tag'].strip()) for i in (items or []))}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


# ---------- test passages (design/54 B) ----------

WORD = re.compile(r'\S+')
PASSAGE_MIN, PASSAGE_MAX, PASSAGES_MAX = 50, 100, 3
SENTENCE_LAST = re.compile(r'[.!?…]["\'”’)\]]*$')


def words_of(text):
    """Every word of the accepted script with its 1-based id and character range, numbered as the narration timing numbers them."""
    return [{'id': f'W{i + 1:05d}', 'n': i + 1, 'start': m.start(), 'end': m.end(), 'text': m.group()} for i, m in enumerate(WORD.finditer(text))]


def passage_text(text, first_word, last_word):
    words = words_of(text)
    return text[words[first_word - 1]['start']:words[last_word - 1]['end']]


def validate_passages(passages, text):
    """Problems with proposed test passages: at most three, each contiguous, starting at a sentence start, 50 to 100 words."""
    problems = []
    if not isinstance(passages, list):
        return ['test_passages must be a list']
    if len(passages) > PASSAGES_MAX:
        problems.append(f'at most three test passages; {len(passages)} given')
    words = words_of(text)
    for i, p in enumerate(passages[:PASSAGES_MAX], 1):
        where = f'test passage {i}'
        if not isinstance(p, dict) or not isinstance(p.get('first_word'), int) or not isinstance(p.get('last_word'), int):
            problems.append(f'{where}: first_word and last_word are word numbers')
            continue
        a, b = p['first_word'], p['last_word']
        if not (1 <= a <= b <= len(words)):
            problems.append(f'{where}: words {a} to {b} are outside the script ({len(words)} words)')
            continue
        if a > 1 and not SENTENCE_LAST.search(words[a - 2]['text']):
            problems.append(f'{where}: word {a} is not the start of a sentence')
        n = b - a + 1
        if not PASSAGE_MIN <= n <= PASSAGE_MAX:
            problems.append(f'{where}: {n} words; a test passage is 50 to 100 words')
    return problems


def directed_passage(text, items, register, first_word, last_word, tweaks=None):
    """The test passage with the register and the tags of the sentences inside it, as the provider reads it."""
    words = words_of(text)
    start, end = words[first_word - 1]['start'], words[last_word - 1]['end']
    sub = text[start:end]
    inside = [r for r in sentences_of(text) if r['start'] >= start and r['end'] <= end]
    sub_rows = sentences_of(sub)
    keymap = {(r['passage_id'], r['sentence']): (q['passage_id'], q['sentence']) for r, q in zip(inside, sub_rows)}
    rebased = [{**i, 'passage_id': keymap[(i['passage_id'], i['sentence'])][0], 'sentence': keymap[(i['passage_id'], i['sentence'])][1]}
               for i in (items or []) if (i['passage_id'], i['sentence']) in keymap]
    tw = [{**t, 'passage_id': keymap[(t['passage_id'], t['sentence'])][0], 'sentence': keymap[(t['passage_id'], t['sentence'])][1]}
          for t in (tweaks or []) if (t['passage_id'], t['sentence']) in keymap]
    tagged, _ = apply(sub, rebased, register, tw)
    return tagged
