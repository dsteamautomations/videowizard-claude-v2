"""design/136 (SK, 2 Nov 2026): the guidebooks filed by video category. A step reads each file's general part plus the film's own category part;
"Not available yet" parts are never read. VideoWizard serves every category; documentary-explainer is the default until a film records its own."""
import pytest

from app import library, visuals_stage as VS
from app.errors import Problem

TEXT = """# A guide

One purpose line.

## General: every category

Rule for everyone.

## For advertisement-product

Product rule.

## For training-education and documentary-explainer

Working-hand rule.

## Not available yet (filed for later categories)

Sound rule.
"""


def test_a_documentary_reads_the_general_part_and_its_own_part_only():
    out = library.for_category(TEXT, 'documentary-explainer')
    assert 'Rule for everyone.' in out and 'Working-hand rule.' in out and 'One purpose line.' in out
    assert 'Product rule.' not in out and 'Sound rule.' not in out and 'Not available yet' not in out


def test_an_advertisement_reads_its_own_part():
    out = library.for_category(TEXT, 'advertisement-product')
    assert 'Product rule.' in out and 'Working-hand rule.' not in out and 'Sound rule.' not in out


def test_a_file_without_category_parts_is_read_whole():
    plain = '# Old guide\n\n## 1. A section\n\nText.\n\n### A sub-section\n\nMore.\n'
    assert library.for_category(plain, 'social-ugc') == plain


def test_the_categories_and_the_default():
    assert library.CATEGORIES == ('documentary-explainer', 'advertisement-product', 'training-education', 'social-ugc', 'narrative-story')
    assert library.DEFAULT_CATEGORY == 'documentary-explainer'
    assert VS.category_of({'film': None}) == 'documentary-explainer'   # design/137: a film from before keeps the documentary guidebooks
    assert VS.category_of({'film': {'category': {'value': 'social-ugc'}}}) == 'social-ugc'
    with pytest.raises(Problem):
        VS.category_of({'film': {}})   # a new film is never assumed


def test_the_pack_reads_by_category(monkeypatch):
    seen = {}
    monkeypatch.setattr(library, 'text', lambda version, path: TEXT)
    monkeypatch.setattr(library, 'manifest', lambda version: {})
    pack = library.steps('v', 'advertisement-product')
    assert pack['category'] == 'advertisement-product'
    first = pack['steps']['start']['files'][0]['text']
    assert 'Product rule.' in first and 'Working-hand rule.' not in first and 'Sound rule.' not in first
    assert 'Product rule.' in pack['always'][0]['text']


# ---------- the new guidebook version ----------

NEW = library.latest()
LEFTOVERS = ('amber ban', 'amber-ban', 'handbag', 'Apple style', 'proof-of-speed', 'Seedance', '8K_UHD', 'Target aspect ratio', 'drag race', 'Retro Analog Flash',
             'roll-up banner', 'advertising production deliverable', 'Not available yet')


def test_new_runs_get_the_new_version_and_it_is_whole():
    assert NEW.startswith('vwlib-2026-11-02-') and library.verify(NEW) == []


def test_every_step_reads_files_that_exist_and_the_animatic_file_is_gone():
    paths = set(library.ALWAYS) | {library.COMPLIANCE} | {p for s in library.STEPS.values() for p in s['files']} | set(library.ALL_SHEETS)
    assert all((library.ROOT / NEW / p).is_file() for p in paths)
    assert not any('animatic' in p for p in paths)


def test_the_start_image_reads_no_video_model_sheet_and_the_take_does():
    assert not any('gemini-omni' in p for p in library.step_files('start')) and any('gemini-omni' in p for p in library.step_files('take'))


def test_no_category_reads_a_leftover_of_the_copied_projects():
    for cat in library.CATEGORIES:
        pack = library.steps(NEW, cat)
        text = ''.join(f['text'] for f in pack['always']) + ''.join(f['text'] for s in pack['steps'].values() for f in s['files']) + pack['compliance']['text']
        assert [w for w in LEFTOVERS if w in text] == [], cat


def test_the_rulebook_opens_with_the_every_category_rule():
    head = library.text(NEW, 'library/RULEBOOK.md')[:800].lower()
    assert 'every' in head and 'category' in head
