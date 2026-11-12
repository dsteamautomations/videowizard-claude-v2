"""The film font set (SK, 12 Nov 2026; videobuilder-v4/phase2/motion/fonts-proposed.md): fetches each family's files from Google's public
font repository (github.com/google/fonts) into server/fonts/, reads the licence and the letters FROM EACH FILE, and writes server/fonts/fonts.json.
A file whose licence is not an open one, or that lacks the letters its row claims, stops the run. Builder-side only: needs `gh` and fontTools;
the server reads fonts.json and never needs either. Run from the repository root: python scripts/fetch_fonts.py"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont

OUT = Path(__file__).resolve().parents[1] / 'server' / 'fonts'
SCRIPTS = {'latin': (0x41, 0x7A), 'devanagari': (0x0905, 0x0939), 'tamil': (0x0B85, 0x0BB9), 'telugu': (0x0C05, 0x0C39), 'kannada': (0x0C85, 0x0CB9), 'malayalam': (0x0D05, 0x0D39)}
LABEL_MARKS = '0123456789%.,:;-+()/ ₹×°→'   # what our labels use beside letters; reported per file, not required
STYLES = ('restrained', 'lively', 'bold', 'technical', 'editorial', 'playful', 'data-led', 'product')
# the font as the operator sees it: (character, the styles it is recommended for, {script: (repository folder, CSS family name)})
SET = {
    'Noto Sans': ('neutral, clear', ['restrained', 'technical'], {'latin': ('notosans', 'Noto Sans'), 'devanagari': ('notosansdevanagari', 'Noto Sans Devanagari'), 'tamil': ('notosanstamil', 'Noto Sans Tamil'),
                                                                  'telugu': ('notosanstelugu', 'Noto Sans Telugu'), 'kannada': ('notosanskannada', 'Noto Sans Kannada'), 'malayalam': ('notosansmalayalam', 'Noto Sans Malayalam')}),
    'Noto Serif': ('bookish serif', ['editorial', 'restrained'], {'latin': ('notoserif', 'Noto Serif'), 'devanagari': ('notoserifdevanagari', 'Noto Serif Devanagari'), 'tamil': ('notoseriftamil', 'Noto Serif Tamil'),
                                                                 'telugu': ('notoseriftelugu', 'Noto Serif Telugu'), 'kannada': ('notoserifkannada', 'Noto Serif Kannada'), 'malayalam': ('notoserifmalayalam', 'Noto Serif Malayalam')}),
    'Anek': ('modern, from narrow to wide, from thin to heavy', ['bold', 'lively', 'product'], {'latin': ('aneklatin', 'Anek Latin'), 'devanagari': ('anekdevanagari', 'Anek Devanagari'), 'tamil': ('anektamil', 'Anek Tamil'),
                                                                                                'telugu': ('anektelugu', 'Anek Telugu'), 'kannada': ('anekkannada', 'Anek Kannada'), 'malayalam': ('anekmalayalam', 'Anek Malayalam')}),
    'Baloo': ('round, friendly, heavy', ['playful'], {'latin': ('baloo2', 'Baloo 2'), 'devanagari': ('baloo2', 'Baloo 2'), 'tamil': ('baloothambi2', 'Baloo Thambi 2'), 'telugu': ('balootammudu2', 'Baloo Tammudu 2'),
                                                     'kannada': ('balootamma2', 'Baloo Tamma 2'), 'malayalam': ('baloochettan2', 'Baloo Chettan 2')}),
    'Hind': ('plain, built for screens', ['data-led', 'technical'], {'latin': ('hind', 'Hind'), 'devanagari': ('hind', 'Hind'), 'tamil': ('hindmadurai', 'Hind Madurai'), 'telugu': ('hindguntur', 'Hind Guntur')}),
    'Mukta': ('warm, open', ['lively'], {'latin': ('mukta', 'Mukta'), 'devanagari': ('mukta', 'Mukta'), 'tamil': ('muktamalar', 'Mukta Malar')}),
    'Tiro': ('classical serif, one weight only', ['editorial'], {'latin': ('tirodevanagarihindi', 'Tiro Devanagari Hindi'), 'devanagari': ('tirodevanagarihindi', 'Tiro Devanagari Hindi'), 'tamil': ('tirotamil', 'Tiro Tamil'),
                                                                'telugu': ('tirotelugu', 'Tiro Telugu'), 'kannada': ('tirokannada', 'Tiro Kannada')}),
    'Poppins': ('geometric, round', ['product', 'bold'], {'latin': ('poppins', 'Poppins'), 'devanagari': ('poppins', 'Poppins')}),
    'IBM Plex Sans': ('engineered, slightly mechanical', ['technical', 'data-led'], {'latin': ('ibmplexsans', 'IBM Plex Sans'), 'devanagari': ('ibmplexsansdevanagari', 'IBM Plex Sans Devanagari')}),
    'Catamaran': ('light, contemporary', ['lively'], {'latin': ('catamaran', 'Catamaran'), 'tamil': ('catamaran', 'Catamaran')}),
    'Teko': ('tall, condensed, for headlines', ['bold'], {'latin': ('teko', 'Teko'), 'devanagari': ('teko', 'Teko')}),
    'Kalam / Kavivanar': ('handwriting', ['playful'], {'latin': ('kalam', 'Kalam'), 'devanagari': ('kalam', 'Kalam'), 'tamil': ('kavivanar', 'Kavivanar')}),
    'Inter': ('neutral, for interfaces and numbers', ['data-led', 'product', 'restrained'], {'latin': ('inter', 'Inter')}),
    'Montserrat': ('wide, confident', ['bold'], {'latin': ('montserrat', 'Montserrat')}),
    'Playfair Display': ('high-contrast, elegant serif', ['editorial'], {'latin': ('playfairdisplay', 'Playfair Display')}),
}


def ranges(cmap):
    """The letters a file holds, as [first, last] code point ranges (below U+3000: the scripts and marks our labels use)."""
    out = []
    for c in sorted(c for c in cmap if c < 0x3000):
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return out


def listing(folder):
    out = subprocess.run(['gh', 'api', f'repos/google/fonts/contents/ofl/{folder}', '--jq', '.[].name'], capture_output=True, text=True, check=True).stdout.split('\n')
    return [n for n in out if n]


def pick(names):
    """The upright variable file when the family has one; else its Regular and Bold (Regular alone for a one-weight family)."""
    ttf = [n for n in names if n.endswith('.ttf') and 'Italic' not in n]
    var = [n for n in ttf if '[' in n]
    if var:
        return sorted(var, key=len)[:1]
    return [n for n in ttf if n.endswith('-Regular.ttf')] + [n for n in ttf if n.endswith('-Bold.ttf')]


def fetch(folder, name):
    dest = OUT / name.replace('[', '-').replace(']', '').replace(',', '-')
    if not dest.exists():
        url = f'https://raw.githubusercontent.com/google/fonts/main/ofl/{folder}/{urllib.parse.quote(name)}'
        dest.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    return dest


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fonts, folders = {}, {}
    for shown, (character, styles, by_script) in SET.items():
        assert all(s in STYLES for s in styles), styles
        entry = {'character': character, 'styles': styles, 'scripts': {}}
        for script, (folder, family) in by_script.items():
            if folder not in folders:
                names = listing(folder)
                assert 'OFL.txt' in names, f'{folder}: no OFL.txt in the repository folder'
                folders[folder] = [fetch(folder, n) for n in pick(names)]
                assert folders[folder], f'{folder}: no upright file found among {names}'
            files = []
            for path in folders[folder]:
                font = TTFont(str(path))
                cmap, lic = font.getBestCmap(), (font['name'].getDebugName(13) or '') + ' ' + (font['name'].getDebugName(14) or '')
                assert 'Open Font License' in lic or 'openfontlicense' in lic.lower() or 'scripts.sil.org/OFL' in lic, f'{path.name}: licence in the file is not the Open Font License: {lic[:120]!r}'
                lo, hi = SCRIPTS[script]
                have = sum(1 for c in range(lo, hi + 1) if c in cmap)
                assert have >= 20, f'{path.name}: claims {script} but holds {have} of its letters'
                files.append({'file': path.name, 'bold': 'Bold' in path.name, 'variable': 'fvar' in font, 'bytes': path.stat().st_size,
                              'missing_marks': ''.join(ch for ch in LABEL_MARKS if ord(ch) not in cmap), 'cover': ranges(cmap)})
            entry['scripts'][script] = {'family': family, 'files': files}
        fonts[shown] = entry
        print(shown.ljust(20), ', '.join(entry['scripts']), '|', sum(len(v['files']) for v in entry['scripts'].values()), 'file refs')
    doc = {'note': 'Written by scripts/fetch_fonts.py from the files themselves; every file is under the SIL Open Font License 1.1 (read in the file).', 'styles': list(STYLES), 'fonts': fonts}
    (OUT / 'fonts.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    files = {f['file'] for e in fonts.values() for s in e['scripts'].values() for f in s['files']}
    print(len(files), 'files,', round(sum((OUT / f).stat().st_size for f in files) / 1e6, 1), 'MB')
    marks = {f['file']: f['missing_marks'] for e in fonts.values() for s in e['scripts'].values() for f in s['files'] if f['missing_marks']}
    print('files missing a label mark:', json.dumps(marks, ensure_ascii=True))


if __name__ == '__main__':
    sys.exit(main())
