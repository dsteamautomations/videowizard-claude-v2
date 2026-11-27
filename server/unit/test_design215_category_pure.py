"""design/215, change 4 and W8: the rules of a set's request that fit a documentary only are filed under its category. For
documentary-explainer the request reads as before (a photograph-like reference, natural colours and no stylisation, an object shown with
only the hand that holds it). Every other category reads the general rules: the reference follows the film's look, and a product may be
shown in use (worn, held, at work) while it stays the subject. Without a database."""
import pytest

from app import library, ref_sets as RS, visuals_stage as VS
import d211_fixture as F
from test_design211b_round_pure import fresh
from test_design211b_sets_pure import RUN, el, finder   # noqa: F401 (finder stands in for part A, on every test)


def request(eid, category, monkeypatch, appearance=None):
    monkeypatch.setattr(VS, 'category_of', lambda run: category)
    plan = F.plan()
    if appearance:
        plan['foundation']['appearance'] = appearance
    s = fresh()
    s['round'] = {'v': 2, 'elements': {}}
    return RS.set_request(plan, RUN, s, next(e for e in plan['elements'] if e['id'] == eid), {})


def test_a_documentary_reads_its_own_rules_as_before(monkeypatch):
    r = request('FAN', 'documentary-explainer', monkeypatch)
    assert RS.OPENING in r['prompt'] and RS.FINISH in r['prompt'] and RS.MAY_SHOW['object'] in r['prompt'] and 'photograph-like' in r['prompt']
    assert 'no stylisation' in r['prompt'] and 'the hand that holds it' in r['views'][1]['ask'] and any(l['check'] == 'no person' for l in r['lines'])
    assert r['parts']['category'] == 'documentary-explainer'


@pytest.mark.parametrize('category', [c for c in library.CATEGORIES if c != 'documentary-explainer'])
def test_every_other_category_reads_the_general_rules(category, monkeypatch):
    r = request('FAN', category, monkeypatch, appearance='Bold saturated colours. Drawn outlines on every product, flat shading.')
    p = r['prompt']
    assert 'photograph-like' not in p and 'no stylisation' not in p and 'no illustration' not in p and 'Natural colours' not in p
    assert "Colour and finish follow the film's look" in p and 'Drawn outlines on every product' in p   # the film's look reaches the request whole
    assert 'No person and no face in any picture' not in p and 'who wears, holds or uses it' in p and 'stays the subject' in p
    use = next(v for v in r['views'] if v['name'] == 'as the film uses it')
    assert 'worn, held or at work' in use['ask'] and 'no face' not in use['ask']
    checks = {l['check']: l['pass_when'] for l in r['lines']}
    assert 'no person' not in checks and 'in use' in checks['the thing is the subject']
    assert 'No text, lettering, logo or mark except what the description names' in p and RS.ONE_THING in p   # what is general stays


def test_a_material_and_a_person_keep_their_rules_in_every_category(monkeypatch):
    brick = request('BRICK', 'advertisement-product', monkeypatch)
    assert RS.MAY_SHOW['material'] in brick['prompt'] and any(l['check'] == 'no person' for l in brick['lines'])
    mason = request('MASON', 'advertisement-product', monkeypatch)
    assert mason['prompt'].startswith('Reference set of The mason, a person in this film.') and 'sheet' not in mason['prompt'].split('\n')[0]


def test_the_looker_is_told_what_may_be_shown_by_the_films_category():
    assert 'An object or a material with no person' in RS.look_how('documentary-explainer')['may_show'] and RS.look_how('documentary-explainer') == RS.LOOK_HOW
    how = RS.look_how('social-ugc')
    assert 'who wears, holds or uses it' in how['may_show'] and 'An object or a material with no person' not in how['may_show'] and how['judge'] == RS.LOOK_HOW['judge']
