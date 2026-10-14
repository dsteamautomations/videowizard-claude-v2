"""Text stages T1–T7: intake → brief → script through the vw plugin against the live test server."""
import json
from io import BytesIO

import pytest

from conftest import rid, seed_session
from conftest import connected, vw  # noqa: F401

SOURCE = """Scene 1: The yard

Narration: Earth blocks are made from the soil beneath our feet.

Duration: 30 seconds

Visuals
- Close-up of finished blocks

Narration: Each block is pressed, not fired, so it keeps the carbon in the ground.
"""


def start_run(home, database):
    connected(home, database)
    code, out, err = vw(home, 'start', '--title', 'Earth', '--client', 'VK', '--need-gb', '0', '--inputs-ready', '--spend-caps-set', '--assembly-machine', 'this')
    assert code == 0, err
    return out['code'], home['runs'] / out['code']


def write_proposal(ws, stage, data):
    (ws / 'out' / f'{stage}.json').write_text(json.dumps(data), encoding='utf-8')


def test_t7_intake_brief_script_end_to_end(home, database):
    code, ws = start_run(home, database)
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    rc, out, err = vw(home, 'stage', 'intake', 'prepare')
    assert rc == 0, err
    assert '{numbered_script}' not in out['prompt'] and '1: Scene 1: The yard' in out['prompt']
    assert out['needs_readable_copy'] is False and out['output_file'] == 'out/intake.json'
    write_proposal(ws, 'intake', {'remove': [{'line': 1, 'kind': 'scene_heading', 'why': 'heading'}, {'line': 5, 'kind': 'timing', 'why': 'duration'},
                                             {'line': 7, 'kind': 'section_label', 'why': 'label'}, {'line': 8, 'kind': 'visual_note', 'why': 'seen not said'}],
                                  'titles': ['Earth Blocks - Documentary Explainer', 'Pressed Earth - Explainer'], 'notes': 'removed plan lines', 'client': 'VK Nardep'})
    rc, out, err = vw(home, 'stage', 'intake', 'record', '--quote', 'yes, approved')
    assert rc == 0, err
    assert out['summary']['title'] == 'Earth Blocks - Documentary Explainer' and out['summary']['client'] == 'VK Nardep'
    cleaned = (ws / 'out' / 'source.txt').read_text(encoding='utf-8')
    assert 'Scene 1' not in cleaned and 'Duration' not in cleaned and 'Close-up' not in cleaned
    assert 'Narration: Earth blocks are made' in cleaned and 'keeps the carbon' in cleaned
    assert vw(home, 'next')[1]['stage'] == 'brief'

    rc, out, err = vw(home, 'stage', 'brief', 'prepare')
    assert rc == 0 and 'keeps the carbon' in out['inputs']['script'] and out['inputs']['title'].startswith('Earth Blocks')
    write_proposal(ws, 'brief', {'purpose': 'Understand why earth blocks matter', 'audience': 'self-builders (recommendation)', 'message': 'Pressed, not fired',
                                 'tone': 'calm', 'ending': 'invite to visit the yard', 'constraints': '', 'reasons': {'audience': 'subject suggests it'}, 'questions': []})
    rc, out, err = vw(home, 'stage', 'brief', 'record', '--quote', 'yes')
    assert rc == 0, err
    assert vw(home, 'next')[1]['stage'] == 'script'

    rc, out, err = vw(home, 'stage', 'script', 'prepare')
    assert rc == 0 and out['inputs']['brief']['message'] == 'Pressed, not fired' and 'keeps the carbon' in out['inputs']['script']
    write_proposal(ws, 'script', {'spoken_text': 'Earth blocks are made from the soil beneath our feet.\n\nEach block is pressed, not fired.',
                                  'notes': '', 'assessment': 'fits', 'changes': [{'what': 'dropped the carbon clause', 'why': 'brief tone'}]})
    rc, out, err = vw(home, 'stage', 'script', 'record', '--quote', 'approved')
    assert rc == 0, err
    assert out['summary']['passages'] == 2 and len(out['summary']['content_digest']) == 64
    script = json.loads((ws / 'out' / 'script.json').read_text(encoding='utf-8'))
    assert list(script['passages']) == ['P001', 'P002']
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'voice' and nxt['paid'] == 'elevenlabs'


def test_t1_docx_tables_included_images_not(home, database):
    from docx import Document
    code, ws = start_run(home, database)
    doc = Document()
    doc.add_paragraph('Narration: hello from a paragraph')
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = 'cell one', 'cell two'
    doc.save(ws / 'in' / 'script.docx')
    rc, out, err = vw(home, 'stage', 'intake', 'prepare')
    assert rc == 0, err
    assert 'hello from a paragraph' in out['prompt'] and 'cell one\tcell two' in out['prompt']
    assert any('images' in w for w in out['warnings'])


def test_t2_pdf_unreadable_page(home, database):
    from pypdf import PdfWriter
    code, ws = start_run(home, database)
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(ws / 'in' / 'script.pdf', 'wb') as f:
        w.write(f)
    rc, out, err = vw(home, 'stage', 'intake', 'prepare')
    assert rc == 0, err
    assert out['needs_readable_copy'] is True and any('pages 1' in w for w in out['warnings'])


def test_t3_source_too_large(home, database):
    code, ws = start_run(home, database)
    (ws / 'in' / 'big.txt').write_bytes(b'x' * (20 * 1024 * 1024 + 1))
    rc, out, err = vw(home, 'stage', 'intake', 'prepare')
    assert rc == 2 and out['action'] == 'refused' and '20 MB' in out['message']


def test_t4_malformed_proposals_refused(home, database):
    code, ws = start_run(home, database)
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    vw(home, 'stage', 'intake', 'prepare')
    write_proposal(ws, 'intake', {'remove': [{'line': 2, 'kind': 'timing', 'why': 'blank'}], 'titles': ['T'], 'notes': '', 'client': 'VK'})
    rc, out, _ = vw(home, 'stage', 'intake', 'record', '--quote', 'yes')
    assert rc == 2 and out['action'] == 'refused' and 'Blank' in out['message']
    write_proposal(ws, 'intake', {'remove': [{'line': 99, 'kind': 'timing', 'why': 'x'}], 'titles': ['T'], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 2
    write_proposal(ws, 'intake', {'remove': [], 'titles': [], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 2  # a title is required
    write_proposal(ws, 'intake', {'remove': [], 'titles': ['Earth'], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'brief', {'purpose': 'p', 'audience': '', 'message': 'm', 'tone': 't', 'ending': 'e'})
    rc, out, _ = vw(home, 'stage', 'brief', 'record', '--quote', 'yes')
    assert rc == 2 and 'audience' in out['message']
    write_proposal(ws, 'brief', {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e'})
    assert vw(home, 'stage', 'brief', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'script', {'spoken_text': '   ', 'notes': '', 'assessment': '', 'changes': []})
    rc, out, _ = vw(home, 'stage', 'script', 'record', '--quote', 'yes')
    assert rc == 2 and 'spoken_text' in out['message']


def test_t5_revise_brief_after_script_is_free(home, database):
    code, ws = start_run(home, database)
    (ws / 'in' / 'source.txt').write_text('Just narration.\n', encoding='utf-8')
    vw(home, 'stage', 'intake', 'prepare')
    write_proposal(ws, 'intake', {'remove': [], 'titles': ['Only'], 'notes': '', 'client': 'VK'})
    assert vw(home, 'stage', 'intake', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'brief', {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 't', 'ending': 'e'})
    assert vw(home, 'stage', 'brief', 'record', '--quote', 'yes')[0] == 0
    write_proposal(ws, 'script', {'spoken_text': 'Just narration.', 'notes': '', 'assessment': '', 'changes': []})
    assert vw(home, 'stage', 'script', 'record', '--quote', 'yes')[0] == 0
    rc, out, _ = vw(home, 'revise', '--stage', 'brief')
    assert rc == 0 and out['reopened'] == ['brief', 'script', 'voice', 'media', 'analysis', 'planning', 'edit', 'first_cut', 'visuals', 'assembly', 'delivery']
    assert vw(home, 'next')[1]['stage'] == 'brief'
    assert vw(home, 'view', '--stage', 'script')[1]['outputs'][0]['stale'] is True


def test_t6_procedures_executor_only(client, database):
    assert client.get('/api/procedures/1/intake', headers=seed_session(database, 'x', kind='browser')).status_code == 403
    r = client.get('/api/procedures/1/intake', headers=seed_session(database, 'x', kind='executor'))
    assert r.status_code == 200 and 'YOU NEVER REWRITE A LINE' in r.json()['prompt'] and r.json()['output_file'] == 'intake.json'
    assert client.get('/api/procedures/1/nope', headers=seed_session(database, 'y', kind='executor')).status_code == 422
    assert client.get('/api/procedures/9/intake', headers=seed_session(database, 'z', kind='executor')).status_code == 404
