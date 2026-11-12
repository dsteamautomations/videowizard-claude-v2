"""Motion style per film and the font set (SK, 11-12 Nov 2026; videobuilder-v4/phase2/motion/requirements-style-and-fonts.md).
S1 the film record holds a motion style; S2 the styles are files; S3 the recommendation per category; S4 the brief carries the style;
S6 a font is offered only for the scripts it holds; S7 the client's last font first; E7 a label's letters are checked against the font."""
import re
from pathlib import Path

import pytest

from app import film, library
from app import visuals_stage as VS
from app.errors import Problem
from test_design130_p1_pure import MRUN, motion_store

SERVER = Path(film.__file__).resolve().parents[1]
PLUGIN = SERVER.parent / 'plugin'
TAMIL, HINDI = 'கிட்டத்தட்ட 25% குறைவான செங்கற்கள்', 'लगभग 25% कम ईंटें'
STYLES = ['restrained', 'lively', 'bold', 'technical', 'editorial', 'playful', 'data-led', 'product']


def run_with(**choices):
    return {**MRUN, 'film': {k: {'value': v} for k, v in choices.items()}}


# ---------- S2: the styles are files ----------

def test_the_eight_styles_are_files_each_a_short_text_filed_by_category():
    st = film.styles()
    assert sorted(st) == sorted(STYLES)
    for name, s in st.items():
        words = len(re.findall(r'\w+', s['text']))
        assert 120 <= words <= 260, (name, words)
        assert s['title'] and s['for'] and set(s['first'] + s['also']) <= set(library.CATEGORIES), name
        assert '`' not in s['text'] and 'VW-' not in s['text']   # written to the builder, about motion only; no film's name
    for c in library.CATEGORIES:   # every category has the style recommended first for it
        assert [n for n, s in st.items() if c in s['first']], c


def test_no_two_styles_share_their_opening():
    opens = [s['text'].split('.')[0] for s in film.styles().values()]
    assert len(set(opens)) == len(opens)


# ---------- S1, S3: the record and the recommendation ----------

def test_the_style_is_recommended_from_the_category_and_the_others_follow():
    assert film.recommend_styles('documentary-explainer')[:1] == ['restrained']
    assert film.recommend_styles('training-education')[:1] == ['lively']
    assert film.recommend_styles('advertisement-product')[:1] == ['bold']
    for c in library.CATEGORIES:
        assert sorted(film.recommend_styles(c)) == sorted(STYLES)   # every style can be chosen
    assert film.recommend_styles('a-category-with-no-style')[0] == 'restrained'   # E1
    assert film.recommend_styles(None)[0] == 'restrained'


def test_the_film_record_takes_a_motion_style_and_refuses_another_word():
    assert film.check('motion', 'Lively') == {'value': 'lively'}
    with pytest.raises(Problem, match='restrained, lively, bold'):
        film.check('motion', 'zippy')
    assert film.motion(run_with(motion='bold')) == 'bold' and film.motion({'film': None}) is None and film.motion({'film': {}}) is None
    assert 'motion' in film.LOCKS


def test_a_film_without_a_style_is_asked_once_with_the_recommendation():
    with pytest.raises(Problem, match='no motion style yet.*Restrained') as e:
        film.need_motion(run_with(category='documentary-explainer'))
    assert 'vw motion-style' in e.value.message
    film.need_motion(run_with(category='documentary-explainer', motion='technical'))   # recorded: nothing asked
    film.need_motion({'film': None})   # a film from before these choices keeps what it was made with


# ---------- S6: the font set ----------

def test_the_set_has_fifteen_fonts_every_file_is_on_the_server_and_every_style_has_two_for_english():
    fs = film.font_set()
    assert len(fs) == 15
    for name, f in fs.items():
        assert f['styles'] and set(f['styles']) <= set(STYLES) and 'latin' in f['scripts'], name
        for sc in f['scripts'].values():
            assert sc['family'] and sc['files'] and all((SERVER / 'fonts' / x['file']).exists() for x in sc['files']), name
    for s in STYLES:
        assert len([n for n, f in fs.items() if s in f['styles']]) >= 2, s


def test_the_scripts_of_a_text_are_read_from_its_letters():
    assert film.scripts_of('Nearly 25% fewer bricks') == {'latin'}
    assert film.scripts_of(TAMIL) == {'tamil'} and film.scripts_of(HINDI) == {'devanagari'}
    assert film.scripts_of('Rat-trap bond: ' + TAMIL) == {'latin', 'tamil'}
    assert film.scripts_of('25% · ₹1,250 → 190 × 90') == set() and film.scripts_of('') == set()


def test_fonts_are_offered_for_the_style_and_only_where_they_hold_the_films_scripts():
    en = film.fonts_for('bold', {'latin'})
    assert [f['name'] for f in en if f['fits']][:1] == ['Anek'] and {'Montserrat', 'Teko'} <= {f['name'] for f in en if f['fits']}
    ta = film.fonts_for('bold', {'latin', 'tamil'})
    names = [f['name'] for f in ta]
    assert names[0] == 'Anek' and ta[0]['fits'] and 'Montserrat' not in names and 'Inter' not in names   # E4, E6: no Tamil letters, not offered
    assert 'Noto Sans' in names and not next(f for f in ta if f['name'] == 'Noto Sans')['fits']   # E5: another style's font that has the script, offered after
    assert all({'latin', 'tamil'} <= set(film.font_set()[n]['scripts']) for n in names)
    assert [f['name'] for f in film.fonts_for('data-led', {'tamil'}) if f['fits']] == ['Hind']


def test_the_clients_last_font_is_offered_first_and_an_older_font_is_kept_for_them():
    first = film.fonts_for('lively', {'latin'}, last='Noto Serif')[0]
    assert first['name'] == 'Noto Serif' and first['last'] is True
    kept = film.fonts_for('lively', {'latin'}, last='Roboto')[0]   # E8: no longer in the set, still theirs
    assert kept['name'] == 'Roboto' and kept['kept'] is True
    assert film.fonts_for('lively', {'latin', 'tamil'}, last='Roboto')[0]['name'] != 'Roboto'   # but never for a script it lacks


def test_a_font_is_refused_for_a_film_whose_script_it_lacks_naming_those_that_have_it():
    assert film.check('font', 'Anek', scripts={'latin', 'tamil'}) == {'value': 'Anek'}
    with pytest.raises(Problem, match='Inter has no Tamil letters.*Anek') as e:
        film.check('font', 'Inter', scripts={'latin', 'tamil'})
    assert 'Montserrat' not in e.value.message
    assert film.check('font', 'Roboto') == {'value': 'Roboto'}   # an older film's font stays recordable
    with pytest.raises(Problem, match='not a font the server holds'):
        film.check('font', 'Comic Sans')


def test_the_films_font_gives_one_file_per_script_under_its_own_family_name():
    faces = film.font_faces('Anek', {'tamil'})   # English is always carried: labels hold figures and Latin words
    assert [f['family'] for f in faces] == ['Anek Latin', 'Anek Tamil'] and all((SERVER / 'fonts' / f['file']).exists() for f in faces)
    assert [f['family'] for f in film.font_faces('Hind', {'latin'})] == ['Hind', 'Hind'] and {f['bold'] for f in film.font_faces('Hind', {'latin'})} == {True, False}
    assert film.font_faces('Roboto', {'latin'}) == [{'family': 'Roboto', 'file': 'Roboto-Variable.ttf', 'bold': False}]
    assert film.font_faces('Noto Sans', set())[0]['family'] == 'Noto Sans'


def test_a_label_with_a_letter_the_font_lacks_is_named_before_the_render():
    assert film.missing_letters('Anek', ['Nearly 25% fewer bricks', TAMIL]) == []
    miss = film.missing_letters('Inter', ['Nearly 25% fewer bricks', TAMIL])
    assert miss and miss[0]['label'] == TAMIL and miss[0]['letters'][0] == 'க'
    assert film.missing_letters('Roboto', ['Plain words']) == []   # an older font: not judged


# ---------- S4: the brief ----------

def test_the_brief_carries_the_films_motion_style_and_no_fixed_style_words():
    b = VS.motion_brief(motion_store(), run_with(motion='lively', font='Noto Sans'), [], 'MO1')['brief']
    assert 'Motion style (Lively)' in b and film.styles()['lively']['text'].split('.')[0] in b
    assert 'flat, clean, technical' not in b and 'every label sentence case' in b


def test_a_film_from_before_keeps_the_older_style_in_its_brief():
    b = VS.motion_brief(motion_store(), MRUN, [], 'MO1')['brief']
    assert 'Motion style (the older fixed style' in b and 'Calm, eased, technical' in b


def test_the_brief_names_each_family_of_the_films_font_with_its_file():
    b = VS.motion_brief(motion_store(), run_with(motion='bold', font='Anek'), [], 'MO1')['brief']
    assert '"Anek Latin"' in b and 'assets/fonts/AnekLatin-wdth-wght.ttf' in b


# ---------- the routes and the plugin's texts ----------

def test_the_film_route_takes_the_new_choice_and_offers_styles_and_fonts():
    src = (SERVER / 'app' / 'main.py').read_text(encoding='utf-8')
    assert "'motion'" in src[src.index('class FilmChoice'):src.index('class FilmChoice') + 400]
    assert 'motion_styles' in src and 'fonts_for' in src


def test_the_skill_no_longer_fixes_one_style_and_the_helpers_read_the_briefs():
    skill = (PLUGIN / 'skills/motion/SKILL.md').read_text(encoding='utf-8')
    assert 'Calm, eased, technical' not in skill and 'Motion style' in skill
    rules = (PLUGIN / 'agents/vw-motion-rules.md').read_text(encoding='utf-8')
    assert 'no rule that restricts motion unless the brief asks' in rules and 'Motion style' in rules
    check = (PLUGIN / 'agents/vw-motion-check.md').read_text(encoding='utf-8')
    assert 'Motion style' in check and 'never fail' in check
    vw = (PLUGIN / 'scripts/vw.py').read_text(encoding='utf-8')
    assert "'motion-style'" in vw
