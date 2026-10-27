"""design/110 rule 0 on the plugin side: `vw visuals ask`, `vw visuals answer` and `vw visuals round --undo` exist, take their flags and nothing else, and post to the server."""
import argparse
import json

import pytest

import vw
from test_visuals_cli import harness   # noqa: F401 (the fixture)


def ns(**kw):
    base = {k: None for k in vw._VISUALS_ALL}
    base.update({'what': 'status', 'undo': False})
    return argparse.Namespace(**{**base, **kw})


def test_the_flags_table_knows_ask_answer_and_undo():
    assert 'ask' in vw.VISUALS_WHAT and 'answer' in vw.VISUALS_WHAT
    assert vw.VISUALS_FLAGS['ask'] == {'item', 'question', 'choices', 'cost'} and vw.VISUALS_FLAGS['answer'] == {'item', 'answer'} and 'undo' in vw.VISUALS_FLAGS['round']
    assert vw.visuals_flags_refused(ns(what='ask', item='K1', question='Which?', choices='a|b', cost='4')) == ''
    assert '--shot' in vw.visuals_flags_refused(ns(what='ask', item='K1', question='Which?', choices='a|b', shot='VS1'))
    assert '--question' in vw.visuals_flags_refused(ns(what='answer', item='K1', answer='a', question='x'))
    p = vw.build_parser()
    if p:
        a = p.parse_args(['visuals', 'ask', '--item', 'K1', '--question', 'Which?', '--choices', 'a|b'])
        assert a.item == 'K1' and a.choices == 'a|b'
        assert p.parse_args(['visuals', 'round', '--undo']).undo is True


def test_ask_answer_and_undo_post_to_the_server(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, **kw: sent.append((path.rsplit('/visuals', 1)[-1], body)) or {'next': 'ok', 'pass': 1})
    for a in (ns(what='ask', item='K1', question='Which brick?', choices='230 mm | 190 mm', cost='4'), ns(what='answer', item='K1', answer='190 mm'), ns(what='round', undo=True, quote='undo')):
        with pytest.raises(SystemExit) as exc:
            vw.cmd_visuals(a)
        assert exc.value.code == 0
        capsys.readouterr()
    assert sent[0] == ('/ask', {'item': 'K1', 'question': 'Which brick?', 'choices': ['230 mm', '190 mm'], 'cost_inr': 4.0})
    assert sent[1] == ('/answer', {'item': 'K1', 'answer': '190 mm'})
    assert sent[2] == ('/round/undo', {'quote': 'undo'})
