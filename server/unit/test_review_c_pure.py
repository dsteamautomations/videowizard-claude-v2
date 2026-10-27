"""Code review of 27 Oct 2026, sets 1, 2 and 4 (design/109): the page's Done/Finish flag resets on a step change (page 4); two live start candidates
both show on the Takes card (page 5); an unsized shot breaks a size run instead of being skipped, an element's sizes are checked like a spec's, and
the picture check reads the picture once (checks minors)."""
import json
from fractions import Fraction
from pathlib import Path

import pytest

from app import image_check as IC, visual_contract as VC
from test_design103_pure import doc_, kinds, sized
from test_image_check_pure import REF, RESULT, SESSION, key_set, transport
from test_visuals_pure import GAPS, shot as pshot

PAGE = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')


# ---------- page 4 and 5 ----------

def test_the_done_finish_flag_resets_when_the_step_changes():
    assert "step=s;confirmPicks=false;remember('step',s)" in PAGE


def test_two_live_start_candidates_both_show_on_the_takes_card():
    assert "const cands=of.filter(r=>r.status==='candidate');return cands.length>1?cands:of.slice(-1);" in PAGE


# ---------- checks minors ----------

def test_an_unsized_shot_breaks_a_size_run_and_is_never_read_as_the_opener():
    k = kinds(doc_(sized('VS1', 0, 200, 'WS'), sized('VS2', 200, 400, 'MS'), sized('VS3', 400, 600, 'MS'), pshot('VS4', 600, 800, 'video'), sized('VS5', 800, 1000, 'MS')))
    assert not any(w == 'size_repeat' for _, w in k)
    k = kinds(doc_(pshot('VS1', 0, 500, 'video'), sized('VS2', 500, 1000, 'MS')))
    assert not any(w == 'size_open' for _, w in k)   # the scene's opener is the unsized shot, not VS2
    k = kinds(doc_(sized('VS1', 0, 200, 'MS'), sized('VS2', 200, 400, 'MS'), sized('VS3', 400, 600, 'MS'), sized('VS4', 600, 1000, 'WS')))
    assert ('VS3', 'size_repeat') in k   # unchanged when every shot is sized


def test_an_elements_sizes_are_checked_like_a_drawing_specs():
    d = doc_(pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video'))
    d['elements'][0]['size'] = [{'part': 'block', 'measure': 'length', 'value': None, 'unit': 'cm', 'status': 'unknown'}]
    with pytest.raises(ValueError, match='element E1: block length is unknown'):
        VC.validate_plan(d, GAPS, Fraction(25))
    d['elements'][0]['size'][0]['tried'] = 'not in the client material; no ruler in the footage'
    VC.validate_plan(d, GAPS, Fraction(25))
    d['elements'][0]['size'] = [{'part': 'block', 'measure': 'length', 'value': 29, 'unit': 'cm', 'status': 'confirmed'}]
    with pytest.raises(ValueError, match='element E1: block length is confirmed: give its source'):
        VC.validate_plan(d, GAPS, Fraction(25))
    d['elements'][0]['size'][0]['source'] = 'the client brief, page 2'
    VC.validate_plan(d, GAPS, Fraction(25))


def test_the_picture_check_reads_the_picture_once(monkeypatch):
    key_set(monkeypatch)
    reads = []

    class Store:
        def get(self, key):
            reads.append(key)
            return b'png-' + key.encode()
    answer = {'lines': [{'n': n, 'pass': True, 'seen': 'ok'} for n in range(1, 6)]}
    rec = IC.run_check(Store(), SESSION, REF, RESULT, transport(answer))
    assert 'error' not in rec and reads.count(RESULT['key']) == 1
