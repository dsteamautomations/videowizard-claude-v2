"""Code review of 27 Oct 2026, set 3 (design/109), the plugin minors: a UNC path keeps its host in the file URL; `vw delivery open` never imports into
Studio twice; the relink section is written once; a malformed timecode tag is a refusal, not a traceback."""
import json

import pytest

import handoff as H
import vw
from test_handoff import edit
from test_handoff3 import cli, args, run   # noqa: F401 (the fixture)


def test_a_unc_path_keeps_its_host_in_the_file_url():
    text = 'x file://./Media/Camera/C1.MP4 y'
    assert H.with_base(text, '\\\\nas\\share\\VW-9\\edit') == 'x file://nas/share/VW-9/edit/Media/Camera/C1.MP4 y'
    assert H.with_base(text, '//nas/My share/edit') == 'x file://nas/My%20share/edit/Media/Camera/C1.MP4 y'
    assert H.with_base(text, 'C:\\Users\\Revathi\\edit') == 'x file:///C:/Users/Revathi/edit/Media/Camera/C1.MP4 y'
    assert H.with_base(text, '/Users/sk/edit') == 'x file:///Users/sk/edit/Media/Camera/C1.MP4 y'


def test_a_malformed_timecode_tag_is_named_not_a_traceback():
    assert H.tc_seconds('00:00:01:05', 25) == 1 + H.Fraction(5, 25) and H.tc_seconds('', 25) == 0
    for bad in ('00:00:00:00:00', 'free run', '1:2'):
        with pytest.raises(ValueError, match='hh:mm:ss:ff'):
            H.tc_seconds(bad, 25)


def test_relink_check_refuses_on_a_bad_timecode_and_writes_its_section_once(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    (d / 'Relink-list.csv').write_text('name,stem,extension,frames,fps,width,height,duration_s,start_timecode,reel,original_name,sha256,bytes,cuts\nC1.MP4,C1,.MP4,100,25,1920,1080,4.0,,,,s,1,1\n', encoding='utf-8')
    (d / 'Finishing-checklist.md').write_text('# Human finishing checklist\n\n- [edit] a line\n', encoding='utf-8')
    monkeypatch.setattr(vw.handoff, 'relink_check', lambda *a, **k: {'lines': [{'line': 'C1.MP4: lined up by hand'}], 'checklist': ['C1.MP4 → C1.MOV: by hand'], 'relinked': None})
    for _ in range(2):
        code, out, err = run(args(what='relink-check', originals=str(tmp_path)), capsys)
        assert code == 0
    text = (d / 'Finishing-checklist.md').read_text(encoding='utf-8')
    assert text.count('## Relink') == 1 and text.startswith('# Human finishing checklist\n\n- [edit] a line\n') and '- C1.MP4 → C1.MOV: by hand' in text
    monkeypatch.setattr(vw.handoff, 'relink_check', lambda *a, **k: (_ for _ in ()).throw(ValueError("timecode '00:00:00:00:00' is not hh:mm:ss:ff")))
    code, out, err = run(args(what='relink-check', originals=str(tmp_path)), capsys)
    assert code == 2 and out['action'] == 'refused' and 'hh:mm:ss:ff' in out['message']


def test_open_never_imports_into_studio_when_the_ledger_already_holds_the_step(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': True, 'version': '21.1', 'edition': 'studio'})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k-man'}}, 'resolve': {'state': 'reported', 'machine': 'pc-1'}})
    code, out, err = run(args(what='open'), capsys)
    assert code == 2 and out['action'] == 'refused' and 'reported' in out['message'] and 'pc-1' in out['message'] and sent == []
