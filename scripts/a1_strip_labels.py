"""design/124 Phase A1: remove change-history labels from the visuals stage's instructions, into procedure version 3 (v2 untouched).
A label: design/NNN with its item tags (F14, N6, rule 0, change 3, S1, A1-A4 …), Lnn, and history notes (SK, <date> …).
Prints every changed spot, old and new, and the checks; writes v3.json only with --write."""
import json, re, sys
from datetime import datetime, timezone

ROOT = r'C:/Coworkspace/Review Videobuilder Tool/videowizard-v2/server/procedures/'
TAG = r'(?:rule \d+|change \d+|[A-Z]{1,2}\d{1,3}(?:\s?[-–]\s?[A-Z]{0,2}\d{1,3})?|[A-Z](?![A-Za-z0-9]))'
LABEL = re.compile(rf'design/\d+(?:(?:\s+and\s+|,\s*)\d+)*(?:\s+{TAG}(?:(?:,\s*|\s+and\s+){TAG})*)?(?:\'s)?|\bL\d{{2}}\b')
HISTORY = re.compile(r'the cap of four removed by SK, \d{1,2} Oct \d{4}|\bSK, \d{1,2} Oct(?: \d{4})?')
GONE = '\x00'


def clean_paren(inner):
    """Inside one (...) group: remove labels and history notes, then drop the empty pieces; the rest stays word for word, in order."""
    t = HISTORY.sub('', LABEL.sub('', inner))
    pieces = re.split(r'(;\s*|,\s*)', t)
    kept = []
    for i in range(0, len(pieces), 2):
        text = pieces[i].strip()
        if text.startswith(':'):
            text = text[1:].strip()   # "design/110: a position …" keeps "a position …"
        if text:
            kept.append([text, pieces[i + 1] if i + 1 < len(pieces) else ''])
    return ''.join(text + (sep if j < len(kept) - 1 else '') for j, (text, sep) in enumerate(kept))


def strip_labels(t):
    def paren(m):
        inner = m.group(1)
        if not (LABEL.search(inner) or HISTORY.search(inner)):
            return m.group(0)
        new = clean_paren(inner)
        return f'({new})' if new else GONE
    prev = None
    while prev != t:   # nested groups: innermost first
        prev = t
        t = re.sub(r'\(([^()]*)\)', paren, t)
    t = re.sub(r'\s*' + GONE, '', t)   # a removed group takes the space before it with it
    t = re.sub(r'\(design/\d+: ', '(', t)   # a long group opening on a label
    return t


def words(t):
    return re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?", t)


def main(write):
    v2 = json.load(open(ROOT + 'v2.json', encoding='utf-8'))
    st = next(s for s in v2['stages'] if s['name'] == 'visuals')
    old = [st['prompt']] + list(st['steps'])
    new = [strip_labels(x) for x in old]
    # checks: no label left; every number outside labels kept; every word outside labels kept, in order
    left = [m.group(0) for x in new for m in LABEL.finditer(x)]
    bad = 0
    for o, n in zip(old, new):
        ow, nw = words(HISTORY.sub('', LABEL.sub('', o))), words(n)
        if ow != nw:
            bad += 1
            k = next((i for i, (x, y) in enumerate(zip(ow, nw)) if x != y), min(len(ow), len(nw)))
            print('WORD CHANGE at', k, ow[max(0, k - 6):k + 6], '->', nw[max(0, k - 6):k + 6])
    print('labels left:', left, '| parts with a word change:', bad)
    print('words before', sum(len(words(x)) for x in old), 'after', sum(len(words(x)) for x in new))
    import difflib
    for o, n in zip(old, new):
        so, sn = re.split(r'(?<=[.;])\s+', o), re.split(r'(?<=[.;])\s+', n)
        for d in difflib.unified_diff(so, sn, lineterm='', n=0):
            if d[:1] in '+-' and d[:3] not in ('---', '+++'):
                print(' ', d[:1], d[1:][:230])
    if write:
        v3 = json.loads(json.dumps(v2))
        v3['version'] = '3'
        v3['published_at'] = datetime.now(timezone.utc).date().isoformat()
        v3['note'] = ('Version 3: version 2 with the visuals stage instructions tidied by design/124 (Phase A1: change-history labels removed, '
                      'wording otherwise unchanged). Films started on version 2 keep version 2.')
        s3 = next(s for s in v3['stages'] if s['name'] == 'visuals')
        s3['prompt'], s3['steps'] = new[0], new[1:]
        open(ROOT + 'v3.json', 'w', encoding='utf-8', newline='\n').write(json.dumps(v3, ensure_ascii=False, indent=2) + '\n')
        print('wrote v3.json')


main('--write' in sys.argv)
