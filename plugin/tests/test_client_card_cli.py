"""design/50 in the plugin: the card in the manifest and the start line, shown at the brief with the precedence rule, recorded with the
differences, the CTA and trademark lines at the script, and `vw brand fetch`."""
import argparse
import json

import pytest

from conftest import STAGES
import vw
from stages_text import Refused, brief_prepare, brief_record, client_card_text, digest, script_prepare

CARD = {'client_name': 'VK Nardep', 'industry': 'Spiritual, educational', 'client_description': 'A service mission.', 'target_audience': 'Youth, volunteers, donors',
        'client_location': 'Kanyakumari, Tamil Nadu', 'website_url': 'https://www.vrmvk.org/', 'youtube_url': 'https://youtube.com/x', 'client_cta_instructions': '{"primary": "visit the site"}',
        'trademark_patterns': 'NARDEP in capitals', 'competitors': ['Acme Bricks'], 'client_past_learnings': '["no drone shots"]', 'client_logo_url': 'https://cdn/logo.png'}
CLEANED = 'Narration: Earth blocks are made.\n\nNarration: Not fired.\n'


def intake_of():
    return {'summary': {'title': 'T', 'client': 'VK Nardep', 'source_digest': digest(CLEANED), 'timing_lines': []}}


def test_card_text_groups_the_fields_and_says_when_empty():
    text = client_card_text(CARD)
    for line in ('audience: Youth, volunteers, donors', 'industry: Spiritual, educational', 'place: Kanyakumari', 'cta: {"primary": "visit the site"}', 'competitors: Acme Bricks',
                 'learnings: ["no drone shots"]', 'brand: logo on file; trademark patterns: NARDEP in capitals', 'destinations: website https://www.vrmvk.org/, youtube https://youtube.com/x'):
        assert line in text, line
    assert client_card_text({}) == 'the directory has nothing on this client beyond its name'
    assert client_card_text({'client_name': 'X'}) == 'the directory has nothing on this client beyond its name'


def test_brief_prepare_shows_the_card_and_the_precedence_rule(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    out = brief_prepare(ws, STAGES['brief'], lambda s: {'intake': intake_of()}[s], client_card=CARD)
    p = out['prompt']
    assert 'WHAT THE DIRECTORY SAYS ABOUT THIS CLIENT' in p and 'audience: Youth, volunteers, donors' in p and '{client_card}' not in p
    assert "operator's words" in p and 'This differs from the directory' in p and out['inputs']['client_card'] == CARD
    out = brief_prepare(ws, STAGES['brief'], lambda s: {'intake': intake_of()}[s])
    assert 'nothing on this client beyond its name' in out['prompt'] and out['inputs']['client_card'] == {}


def base(**over):
    return {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e', 'constraints': '', 'questions': [], 'answers': {},
            'production': {'field_speech_languages': ['ta'], 'narration_language': 'en'}, **over}


def test_brief_record_keeps_the_card_and_the_differences(ws):
    prior = lambda s: {'intake': intake_of()}[s]
    (ws / 'out' / 'brief.json').write_text(json.dumps(base(directory_differences=[{'field': 'target_audience', 'directory_says': 'Youth', 'chosen': 'builders', 'decided_by': 'script', 'operator_words': ''}])), encoding='utf-8')
    s = brief_record(ws, STAGES['brief'], prior, client_card=CARD)['summary']
    assert s['client_card'] == CARD and s['directory_differences'][0]['field'] == 'target_audience'
    (ws / 'out' / 'brief.json').write_text(json.dumps(base()), encoding='utf-8')
    s = brief_record(ws, STAGES['brief'], prior)['summary']
    assert s['client_card'] == {} and s['directory_differences'] == []
    (ws / 'out' / 'brief.json').write_text(json.dumps(base(directory_differences=[{'field': 'x'}])), encoding='utf-8')
    with pytest.raises(Refused):
        brief_record(ws, STAGES['brief'], prior)
    (ws / 'out' / 'brief.json').write_text(json.dumps(base(directory_differences=[{'field': 'x', 'directory_says': 'a', 'chosen': 'b', 'decided_by': 'nobody'}])), encoding='utf-8')
    with pytest.raises(Refused):
        brief_record(ws, STAGES['brief'], prior)


def test_script_prepare_prints_cta_contact_and_trademarks_only_when_present(ws):
    (ws / 'out' / 'source.txt').write_text(CLEANED, encoding='utf-8')
    brief = {'summary': {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e', 'constraints': '', 'production': {'narration_language': 'en'}, 'client_card': CARD}}
    out = script_prepare(ws, STAGES['script'], lambda s: {'intake': intake_of(), 'brief': brief}[s])
    d = out['inputs']['directory']
    assert d == {'cta': '{"primary": "visit the site"}', 'contact': {'website_url': 'https://www.vrmvk.org/'}, 'trademark_patterns': 'NARDEP in capitals'}
    brief['summary']['client_card'] = {}
    out = script_prepare(ws, STAGES['script'], lambda s: {'intake': intake_of(), 'brief': brief}[s])
    assert out['inputs']['directory'] == {}


def test_manifest_keeps_the_card_and_the_start_line_counts_it(ws, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    m = vw.make_workspace({'code': 'VW-9', 'id': 'r1', 'client': 'VK', 'client_card': CARD})
    assert m['client_card'] == CARD
    assert vw.directory_line(CARD) == 'directory: 12 fields on this client' and vw.directory_line({}) == 'directory: name only'


def test_brand_fetch_saves_the_files_into_in_brand(ws, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'r1'})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'files': [{'name': 'logo.png', 'key': 'r1/brand/logo.png', 'bytes': 3}], 'skipped': ['reverse logo: no URL']})

    class R:
        status_code = 200
        content = b'png'

    class C:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return R()
    monkeypatch.setattr(vw, 'api', lambda: C())
    with pytest.raises(SystemExit) as exc:
        vw.cmd_brand(argparse.Namespace(what='fetch'))
    out, err = capsys.readouterr()
    assert exc.value.code == 0 and (ws / 'in' / 'brand' / 'logo.png').read_bytes() == b'png' and 'in/brand/logo.png' in err and 'reverse logo: no URL' in err


def test_procedure_text_names_the_directory():
    b = STAGES['brief']
    assert '{client_card}' in b['prompt'] and 'never answers' in b['prompt'] and 'This differs from the directory' in b['prompt'] and 'directory_differences' in ' '.join(b['steps'])
    s = STAGES['script']
    assert 'directory' in s['prompt'] and 'trademark' in s['prompt'].lower()
    v = STAGES['visuals']
    assert 'vw brand fetch' in ' '.join(v['steps']) and 'competitor' in ' '.join(v['steps']).lower()
    md = (vw.Path(__file__).resolve().parents[1] / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw brand fetch' in md and 'directory' in md
