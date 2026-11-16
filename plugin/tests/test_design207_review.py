"""design/207, the fixes after its review: the operator is never sent to the server's visuals page; the messages about the cost limit say who can
change it; the guard names every skill it allows; the guide checker's brief knows a shot with nobody in it, a listed overlap and a thing on a path;
the guide skill says what the server does with a thing that is not in the first frame."""
from conftest import PLUGIN, run_hook
from test_visuals_cli import args, fake_client, harness, run   # noqa: F401 (harness is a fixture)
import vw

VW_MD = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
VISUALS = next(p for p in VW_MD.split('\n') if p.startswith('**Visuals**'))
OWNER = 'from their own sign-in'


def test_prepare_gives_no_link_to_the_servers_visuals_page(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'package': {'key': 'k'}, 'gaps': ['G1'], 'next': 'treatment', 'footage': 'handheld, natural light', 'cap_inr': 1500.0, 'cap_from': 'length'})
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'version': 'vwlib-x', 'always': [], 'steps': {}, 'compliance': None, 'map': '', 'field_sources': ''})
    fake_client(monkeypatch, {'source': {'gaps': {'G1': {'start_frame': 0, 'end_frame': 100}}}, 'prompt': 'p', 'plan_schema': {}, 'world_evidence': [], 'intended_visuals': [], 'generator_catalog': []})
    code, out, err = run(args(what='prepare'), capsys)
    assert code == 0 and 'https://x.example' not in err and 'Visuals page' not in err and 'link' not in err
    assert 'Tell the operator in one line, never ask: handheld, natural light' in err and "The cost limit of this film's visuals is ₹1,500" in err


def test_the_spend_lines_say_only_the_owner_changes_the_limit_from_their_own_sign_in(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'spent_inr': 900.0, 'cap_inr': 1000.0, 'left_inr': 100.0, 'images': 6, 'planned': {'inr': 500.0}})
    code, out, err = run(args(what='budget'), capsys)
    assert 'Only the owner can set another figure for this film, from their own sign-in (`vw visuals cap`): tell the operator to ask the owner.' in err
    assert "the limit follows the film's length" not in err   # a film that keeps the older limit is not told that
    monkeypatch.setattr(vw, '_json_file', lambda m, name: {})
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'approved': [], 'queued': [], 'pass': 2, 'held': {'E2': 'the spend cap is reached'}})
    code, out, err = run(args(what='round', sets='out/round-sets.json', quote='yes'), capsys)
    assert 'Only the owner can set another limit for this film, from their own sign-in (`vw visuals cap`): tell the operator to ask the owner.' in err


def test_the_guard_names_every_skill_it_allows(tmp_path):
    (tmp_path / 'runs').mkdir()
    (tmp_path / 'runs' / '.active').write_text('VW-3')
    code, _, err = run_hook('guard.py', {'tool_name': 'Skill', 'tool_input': {'skill': 'pdf'}}, tmp_path, None)
    assert code == 2 and 'only these skills are available here: vw:vw, vw:motion, vw:guide, vw:drawing; not' in err
    for name in ('vw:vw', 'vw:guide', 'vw:drawing', 'vw:motion'):
        assert run_hook('guard.py', {'tool_name': 'Skill', 'tool_input': {'skill': name}}, tmp_path, None)[0] == 0


def test_the_command_text_keeps_the_operator_in_the_chat_and_on_the_decisions_page_only():
    for gone in ('prints the visuals page link', 'and the page link once', 'on the page or `vw visuals footage', 'or the operator approves on the page', 'Try a fix on the page',
                 'the label and the link `vw visuals status` prints', 'Done on the page', ', or on the page)', 'ticked on the page', '`, or the page)'):
        assert gone not in VISUALS, gone
    assert 'The treatment, the plan, the drawings and materials, the reference drawings and the two steps of the references are answered on the page' in VISUALS   # the operator's one page: the decisions page (the design/210 wording review names every step on it)
    assert OWNER in VISUALS and 'tell the operator to ask the owner' in VISUALS
    assert 'never to answer for the operator' in VISUALS and 'after the plan is proposed' in VISUALS


def test_the_guide_checkers_brief_knows_an_empty_shot_a_listed_overlap_and_a_thing_on_a_path():
    brief = (PLUGIN / 'agents' / 'vw-guide-check.md').read_text(encoding='utf-8')
    for needed in ('When BUILD.md names no person, every look about people (1 to 4) passes', 'when BUILD.md lists that overlap as a standing warning of the scene check',
                   'It is not a failed look 3', 'it stands where the path starts, in the last where the path ends', 'The one exception is a look about people in a shot that BUILD.md says has nobody in it'):
        assert needed in brief, needed
    scene = (PLUGIN / 'agents' / 'vw-guide-scene.md').read_text(encoding='utf-8')
    assert 'say plainly "nobody is in the shot" when no person is' in scene


def test_the_guide_skill_says_a_prop_is_always_in_the_first_frame_and_a_set_piece_is_warned():
    skill = (PLUGIN / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'a thing that comes in later is warned on' not in skill
    assert 'A piece of the set on a path that starts out of frame is warned on; a prop that is not in the first frame is refused.' in skill
    assert 'a piece of the set on a path that starts out of frame (a prop is always in the first frame: refused otherwise)' in skill
