"""design/216, the tool's side, with the server faked: before many pictures are fetched for the page, the server's sentence `preparing` is said
first and nothing is fetched or written until `--fetch` (B2); the message the server gives for the link (`say`) is passed on unchanged (B1);
`vw visuals round --answer --every-picture` sends the page's tick (B6)."""
import json

from test_design210_pictures import fake, with_pics
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw

SAID = 'Preparing 12 pictures for the page, about 1 minute.'
SAY = '1 thing needs your answer: the mason. Then say done here.'


def test_many_pictures_are_announced_first_and_fetched_on_fetch(harness, monkeypatch, capsys):
    ws, _ = harness
    got = fake(monkeypatch, lambda: with_pics('r1', *range(1, 13), preparing=SAID, say=SAY))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 0 and got == [] and out['preparing'] == SAID and out['pictures_to_fetch'] == 12 and f'"{SAID}"' in err and '`vw visuals page --fetch`' in err
    assert not (ws / 'work' / 'page' / 'r1.json').exists()                                    # nothing written yet
    rc, out, err = run(args(what='page', record=False, fetch=True), capsys)
    assert rc == 0 and len(got) == 24 and out['say'] == SAY and (ws / 'work' / 'page' / 'r1.json').exists()


def test_a_few_pictures_or_an_older_server_are_fetched_at_once(harness, monkeypatch, capsys):
    got = fake(monkeypatch, lambda: with_pics('r1', *range(1, 10), preparing=SAID))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 0 and len(got) == 18 and 'say' not in out                                    # under ten: no stop; no `say` from the server: none passed on
    got = fake(monkeypatch, lambda: with_pics('r2', *range(20, 40)))
    rc, out, err = run(args(what='page', record=False), capsys)
    assert rc == 0 and len(got) == 40


def test_every_picture_sends_the_tick(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'stored': True, 'answer': {'verdict': 'correct', 'words': 'x'}})
    run(args(what='round', answer='MASON', verdict='correct', words='Longer sleeves.', every_picture=True), capsys)
    assert sent[-1][1] == {'element_id': 'MASON', 'verdict': 'correct', 'golden': None, 'words': 'Longer sleeves.', 'all': True}
    run(args(what='round', answer='MASON', verdict='correct', words='Longer sleeves.'), capsys)
    assert 'all' not in sent[-1][1]
    rc, out, err = run(args(what='round', answer='MASON', verdict='yes', every_picture=True), capsys)
    assert rc == 2 and '--every-picture goes with --verdict correct' in json.dumps(out) + err
