"""design/117 P2: the SVG scene's rules (refused with the reason before any render), the actions against the document, the spec rule, the picture
embedding, and the plan contract (scene_svg on a drawn shot, the spec when the shot carries figures)."""
import copy
from fractions import Fraction

import pytest

from app import svg_scene as S, visual_contract as VC
from svg_fixture import ACTIONS, REFS, SVG, with_
from test_batch89b_pure import SPEC
from test_visuals_pure import GAPS, plan, shot as pshot


def problems(svg=SVG, **kw):
    return S.check(svg, refs=kw.pop('refs', REFS), **kw)


def test_the_fixture_scene_passes_and_its_parts_are_read():
    assert problems() == []
    root = S.parse(SVG)
    assert set(S.ids_of(root)) >= {'bg', 'title', 'wall', 'c1', 'c2', 'c3', 'flame', 'arrow', 'pitch'}
    assert S.children_of(root)['wall'] == ['c1', 'c2', 'c3']
    assert dict(S.texts_of(root)) == {'title': 'Bricks for the same wall', 'pitch': 'course pitch 75 mm'}
    assert S.image_refs(root) == ['comp-1']
    assert S.view_box(root) == (0.0, 0.0, 1600.0, 900.0)


@pytest.mark.parametrize('svg, says', [
    ('', 'not an SVG document'),
    ('<html></html>', 'not an SVG document'),
    ('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>', 'viewBox'),
    (with_(old='viewBox="0 0 1600 900"', new='viewBox="0 0 1600 1200"'), '16:9'),
    (with_(old='<path id="arrow"', new='<script>alert(1)</script><path id="arrow"'), 'script'),
    (with_(old='<path id="arrow"', new='<foreignObject/><path id="arrow"'), 'foreignObject'),
    (with_(old='<path id="arrow"', new='<animate attributeName="x"/><path id="arrow"'), 'animate'),
    (with_(old='<path id="arrow"', new='<style>rect{fill:red}</style><path id="arrow"'), 'style'),
    (with_(old='href="ref:comp-1"', new='href="https://x.example/flame.png"'), 'ref:'),
    (with_(old='href="ref:comp-1"', new='href="ref:nobody"'), 'nobody'),
    (with_(old='<rect id="bg"', new='<rect id="bg" onload="x()"'), 'onload'),
    (with_(old='fill="#F4EDE1"', new='fill="red"'), 'red'),
    (with_(old='fill="#F4EDE1"', new='style="fill:url(http://x/y)"'), 'url('),
    (with_(old='font-family="Noto Sans" font-size="64"', new='font-family="Comic Sans" font-size="64"'), 'Comic Sans'),
    (with_(old='font-size="40"', new='font-size="30"'), '4 %'),
    (with_(old='course pitch 75 mm', new='the pitch of one course of this wall is seventy five millimetres'), 'eight words'),
    (with_(old='<rect id="c2"', new='<rect id="c1"'), "'c1' twice"),
    (with_(old='viewBox="0 0 1600 900"', new='viewBox="0 0 1600 900" width="900" height="1600"'), 'differs from the viewBox'),   # review 28 Oct: each against its own
    (with_(old='<path id="arrow"', new='<use href="#nothing"/><path id="arrow"'), 'nothing'),
])
def test_each_rule_refuses_with_its_reason(svg, says):
    got = problems(svg)
    assert got and says in ' '.join(got), got


def test_a_rejected_picture_and_a_font_of_the_run_are_judged_by_the_refs_and_fonts_given():
    assert any('rejected' in p for p in problems(refs={'comp-1': {'status': 'rejected'}}))
    brand = with_(old='font-family="Noto Sans" font-size="64"', new='font-family="Brand Grotesk, sans-serif" font-size="64"')
    assert problems(brand, fonts=('Noto Sans', 'Brand Grotesk')) == [] and problems(brand)


def test_the_actions_are_checked_against_the_document():
    root = S.parse(SVG)
    assert S.action_problems(ACTIONS, root) == []
    assert any("'ghost'" in p for p in S.action_problems([{'kind': 'appear', 'ids': ['ghost'], 'at_s': 0}], root))
    assert S.members(root, ['wall']) == ['c1', 'c2', 'c3'] and S.members(root, ['c1', 'wall']) == ['c1', 'c2', 'c3'] and S.members(root, ['title']) == ['title']


def test_the_spec_rule_wants_every_known_size_as_text_and_no_figure_for_an_unknown_one():
    spec = {'dimensions': [{'part': 'course', 'measure': 'pitch', 'value': 75, 'unit': 'mm', 'status': 'sourced'},
                           {'part': 'leaf', 'measure': 'thickness', 'value': None, 'unit': 'mm', 'status': 'unknown'}]}
    root = S.parse(SVG)
    assert S.spec_problems(root, spec) == []
    missing = S.spec_problems(S.parse(with_(old='course pitch 75 mm', new='course pitch')), spec)
    assert missing and '75 mm' in missing[0]
    figure = S.spec_problems(S.parse(with_(old='course pitch 75 mm', new='leaf thickness 110 mm')), spec)
    assert any('leaf thickness' in f and 'unknown' in f for f in figure) and any('75 mm' in f for f in figure)   # the unknown size's figure, and the known size now missing


def test_pictures_are_embedded_as_data_uris_and_nothing_else_changes():
    out = S.embed(SVG, {'comp-1': ('image/png', b'\x89PNG')})
    assert 'href="data:image/png;base64,iVBORw==' in out and 'ref:' not in out and out.count('<rect') == SVG.count('<rect')
    single = S.embed(with_(old='href="ref:comp-1"', new="href='ref:comp-1'"), {'comp-1': ('image/png', b'\x89PNG')})   # review 28 Oct: the parser takes single quotes, so does the embed
    assert "href='data:image/png;base64,iVBORw=='" in single and 'ref:' not in single
    with pytest.raises(ValueError, match='comp-1'):
        S.embed(SVG, {})


def drawn(**over):
    sh = {**pshot('DR1', 0, 100, 'diagram'), 'visual_type': 'drawn', 'depicts': 'the wall section', 'narration': 'The cavity between the two leaves holds still air.',
          'drawing_spec': copy.deepcopy(SPEC), 'scene_svg': {'sha256': 'a' * 64, 'actions': copy.deepcopy(ACTIONS)}, **over}
    return plan([sh, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def test_the_plan_takes_scene_svg_on_a_drawn_shot_and_scene_drawn_is_gone():
    out, warnings = check(drawn())
    assert out['gaps'][0]['scenes'][0]['shots'][0]['scene_svg']['sha256'] == 'a' * 64 and VC.routes(out)['drawn'] == 1
    assert 'scene_drawn' not in VC.Shot.model_fields and not hasattr(VC, 'DrawnShape') and not hasattr(VC, 'drawn_labels')
    with pytest.raises(ValueError, match='DR1 is drawn: give scene_svg'):
        check(drawn(scene_svg=None))
    with pytest.raises(ValueError, match='sha256'):
        check(drawn(scene_svg={'sha256': 'short', 'actions': []}))
    with pytest.raises(ValueError, match='scene_drawn'):   # extra forbid: the old field is named back
        check(drawn(scene_drawn={'unit': 'mm'}))


def test_the_spec_is_required_only_when_the_shot_carries_figures():
    with pytest.raises(ValueError, match='it carries figures, so it needs a drawing_spec'):
        check(drawn(drawing_spec=None, claims=['one course is 75 mm high']))
    out, warnings = check(drawn(drawing_spec=None, claims=['the wall keeps the house cool'], production_method='a chart'))
    assert out['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] is None


def test_the_actions_of_the_plan_are_keyed_inside_the_shot():
    with pytest.raises(ValueError, match='at_s or word'):
        check(drawn(scene_svg={'sha256': 'a' * 64, 'actions': [{'kind': 'appear', 'ids': ['title']}]}))
    with pytest.raises(ValueError, match='past the end'):
        check(drawn(scene_svg={'sha256': 'a' * 64, 'actions': [{'kind': 'appear', 'ids': ['title'], 'at_s': 99}]}))
    with pytest.raises(ValueError, match='two points'):
        check(drawn(scene_svg={'sha256': 'a' * 64, 'actions': [{'kind': 'move', 'ids': ['title'], 'at_s': 1, 'path': [[0, 0]]}]}))
    with pytest.raises(ValueError, match="'nothing' is not in the narration"):
        check(drawn(scene_svg={'sha256': 'a' * 64, 'actions': [{'kind': 'appear', 'ids': ['title'], 'word': 'nothing'}]}))
