"""Defect 52 (SK, 15 Nov 2026): a clip skipped at the analysis because the client's library holds the same file brings its stored study into the
new film, free: the description, the pieces, the grades and the crops do not depend on the script. The line fits do, so a fit is carried only for
a sentence whose words are exactly the same in both films (only spaces may differ); it follows the sentence to its new number, and every other fit
is dropped. A study of another form or model, or one whose files or record are missing, is not reused: the clip stays skipped, as before."""
import json
import re

from .stage2.package import _beat_lines

FIT_LISTS = ('primary_fit_for_beats', 'secondary_fit_for_beats')
FIT_TEXTS = ('beat_fit_reasoning', 'beat_fit_limits')


def _number(beat_id):
    return int(re.search(r'(\d+)$', str(beat_id)).group(1))


def sentence_map(old_beats, new_beats):
    """{old sentence number: new sentence number} for the sentences that are word for word the same; one said twice is matched in order."""
    words = lambda b: ' '.join(str(b.get('text') or '').split())
    slots = {}
    for b in new_beats:
        slots.setdefault(words(b), []).append(_number(b['beat_id']))
    out = {}
    for b in old_beats:
        free = slots.get(words(b))
        if free:
            out[_number(b['beat_id'])] = free.pop(0)
    return out


def carry(raw, mapping, n_old, n_new):
    """The stored answer with its fits moved to this film's sentence numbers, and what was kept and dropped. The same script: the answer itself,
    untouched. (None, None) when the answer is not a study."""
    if n_old == n_new and mapping == {i: i for i in range(1, n_old + 1)}:
        return raw, {'kept': 'all', 'dropped': 0}
    try:
        body = json.loads(raw)
    except (ValueError, TypeError):
        return None, None
    if not isinstance(body, dict):
        return None, None
    width = max(2, len(str(n_new)))
    tag = lambda n: f'BEAT_{n:0{width}d}'
    kept = dropped = 0
    for sub in body.get('sub_clips') or []:
        story = sub.get('continuity_and_story') if isinstance(sub, dict) else None
        if not isinstance(story, dict):
            continue
        for k in FIT_LISTS:
            moved = []
            for b in story.get(k) or []:
                m = re.match(r'BEAT_(\d+)$', str(b))
                if m and int(m.group(1)) in mapping:
                    moved.append(tag(mapping[int(m.group(1))]))
                    kept += 1
                else:
                    dropped += 1
            story[k] = moved
        for k in FIT_TEXTS:   # a line belongs to the sentence it starts with: kept under the new number, or left out
            lines = [(int(re.match(r'BEAT_(\d+)', line).group(1)), line) for line in _beat_lines(story.get(k))]
            story[k] = '\n'.join(re.sub(r'^BEAT_\d+', tag(mapping[n]), line) for n, line in lines if n in mapping)
    return json.dumps(body, ensure_ascii=False), {'kept': kept, 'dropped': dropped}


def plan(conn, store, row, request):
    """What reusing this library row for `request` (this film's own request for the same file) gives: {'raw', 'from', 'fits'}, or None when the
    stored study may not be reused."""
    ev_key = (row or {}).get('evidence_key')
    if not ev_key or not ev_key.endswith('.evidence.json'):
        return None
    resp_key = ev_key[:-len('.evidence.json')] + '.response.json'
    if not store.exists(ev_key) or not store.exists(resp_key):
        return None
    try:
        old_identity = json.loads(store.get(ev_key).decode('utf-8')).get('identity') or {}
    except (ValueError, AttributeError):
        return None
    new_identity = request['identity']
    if any(old_identity.get(k) != new_identity.get(k) for k in ('contract_version', 'model', 'schema_digest')):
        return None   # a study made in another form or by another model is not this film's study
    job = conn.execute("select request, result from vw2_jobs where stage='analysis' and result->>'evidence_key'=%s order by created_at desc limit 1", (ev_key,)).fetchone()
    old_key = ((job or {}).get('request') or {}).get('request_key')
    if not old_key or not store.exists(old_key):
        return None
    try:
        old_beats = (json.loads(store.get(old_key).decode('utf-8')).get('project_config') or {}).get('script_beats') or []
    except (ValueError, AttributeError):
        return None
    new_beats = request['project_config']['script_beats']
    by_sentence = old_identity.get('fit_unit') == 'sentence' and new_identity.get('fit_unit') == 'sentence'
    raw, fits = carry(store.get(resp_key).decode('utf-8'), sentence_map(old_beats, new_beats) if by_sentence else {}, len(old_beats), len(new_beats))
    if raw is None:
        return None
    look = (((job or {}).get('result') or {}).get('summary') or {}).get('look')   # the clip's colour measure does not depend on the film
    return {'raw': raw, 'from': str((row.get('films') or ['?'])[0]), 'fits': fits, **({'look': look} if look else {})}
