"""design/207: `vw visuals cap`, with the server faked. The owner sets another cost limit for one film, with their words.
design/207 (D1, D2): `vw visuals likeness`, with the server faked: the operator's yes that they have a person's permission, or the person made a
stand-in again; and `vw visuals reuse`, retired by name (a reuse no longer needs approval)."""
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
def posts(monkeypatch, answer):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or answer)
    return sent


def test_likeness_records_the_operators_words_for_a_person(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'element_id': 'P1', 'likeness': True, 'next': 'The permission is recorded for P1.'})
    code, out, err = run(args(what='likeness', element='P1', quote='Yes, he signed the release.'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/likeness', {'element_id': 'P1', 'quote': 'Yes, he signed the release.', 'stand_in': False})]
    assert out['likeness'] is True and err.strip() == 'The permission is recorded for P1.'


def test_likeness_stand_in_removes_the_record(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {'element_id': 'P1', 'likeness': False, 'next': 'P1 is a stand-in again.'})
    code, out, err = run(args(what='likeness', element='P1', quote='He would rather not be shown.', stand_in=True), capsys)
    assert code == 0 and sent[0][1] == {'element_id': 'P1', 'quote': 'He would rather not be shown.', 'stand_in': True} and 'stand-in again' in err


def test_likeness_without_the_person_or_the_words_is_refused_and_nothing_is_sent(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {})
    for kw in ({'quote': 'yes'}, {'element': 'P1'}, {'element': 'P1', 'quote': '   '}):
        code, out, err = run(args(what='likeness', **kw), capsys)
        assert code == 2 and 'vw visuals likeness --element E --quote' in out['message'] and 'Nothing was sent' in out['message'] and not sent
    code, out, err = run(args(what='likeness', element='P1', quote='yes', shot='VS1'), capsys)   # a flag it does not read
    assert code == 2 and '--shot' in out['message'] and not sent


def test_the_command_line_takes_the_stand_in_flag():
    assert 'likeness' in vw.VISUALS_WHAT and vw.VISUALS_FLAGS['likeness'] == {'element', 'quote', 'stand_in'}


def test_reuse_is_retired_by_name_and_sends_nothing(harness, monkeypatch, capsys):
    sent = posts(monkeypatch, {})
    code, out, err = run(args(what='reuse', shot='VS1', quote='Yes, reuse it.'), capsys)
    assert code == 2 and not sent and "no longer needs the operator's approval" in out['message'] and '--reuse' in out['message'] and '--considered' in out['message']
