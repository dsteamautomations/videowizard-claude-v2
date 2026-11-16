"""design/207: `vw visuals cap`, with the server faked. The owner sets another cost limit for one film, with their words."""
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw


def test_cap_sends_the_figure_and_the_owners_words(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'cap_inr': 3000.0, 'was_inr': 1500.0, 'cap_from': 'owner'})
    code, out, err = run(args(what='cap', inr='3000', quote='This one may cost up to three thousand.'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/cap', {'inr': 3000.0, 'quote': 'This one may cost up to three thousand.'})]
    assert err.strip() == "The cost limit of this film's visuals is now ₹3,000 (it was ₹1,500), set by the owner."


def test_cap_without_a_figure_or_the_owners_words_sends_nothing(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append(path) or {})
    for kw in ({'quote': 'raise it'}, {'inr': '3000'}, {'inr': 'lots', 'quote': 'raise it'}, {'inr': '0', 'quote': 'raise it'}):
        code, out, err = run(args(what='cap', **kw), capsys)
        assert code == 2 and 'vw visuals cap --inr N --quote' in out['message'], kw
    assert sent == []


def test_cap_takes_only_its_own_flags_and_the_budget_line_says_how_the_limit_is_set(harness, monkeypatch, capsys):
    code, out, err = run(args(what='cap', inr='3000', quote='raise it', gap='G1'), capsys)
    assert code == 2 and 'does not take --gap' in out['message']
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'spent_inr': 900.0, 'cap_inr': 1000.0, 'left_inr': 100.0, 'images': 6, 'planned': {'inr': 500.0}})
    code, out, err = run(args(what='budget'), capsys)
    assert "the limit follows the film's length; the owner can set another figure for this film with `vw visuals cap`" in err and 'builder' not in err
