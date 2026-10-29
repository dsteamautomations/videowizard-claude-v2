"""design/124 C1, after c1_split_v3.py: a reference to a section that now sits in another part names that part's file."""
import json

P = 'server/procedures/v3.json'
FIXES = {  # where -> [(old, new)]
    'common': [("a longer passage is several segments (section 6)", "a longer passage is several segments (section 6, in part-later.md)")],
    'preparation': [("under work/visuals/library/ (section 6)", "under work/visuals/library/ (section 6, in part-later.md)"),
                    ("record the treatment (section 2)", "record the treatment (section 2, part-treatment.md)")],
    'picture-search': [("a picture by the picture AI (section 5)", "a picture by the picture AI (section 5, in part-later.md)"),
                       ("(sections 5 and 9)", "(sections 5 and 9, in part-later.md)")],
}
if __name__ == '__main__':   # importing it (c1_split_v3.py --check) only reads FIXES
    d = json.load(open(P, encoding='utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    for where, pairs in FIXES.items():
        for old, new in pairs:
            if where == 'common':
                assert st['prompt'].count(old) == 1, old
                st['prompt'] = st['prompt'].replace(old, new)
            else:
                part = next(p for p in st['parts'] if p['name'] == where)
                assert part['text'].count(old) == 1, old
                part['text'] = part['text'].replace(old, new)
    open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
    print('ok')
