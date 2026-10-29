"""design/68: the image prompt library loaded from files (L3): versions and the manifest, the step map from VW-MAP, the job form from a run, the answer lint."""
import hashlib
import json
import shutil

import pytest

from app import library as L
from app.errors import Problem

VERSION = 'vwlib-2026-10-21-4f88379be109'
RUN = {'id': 'run-1', 'code': 'VW-9', 'client_id': 'NARDEP'}
PLAN = {'foundation': {'treatment': 'documentary', 'appearance': 'overcast yard light', 'exclusions': [{'id': 'X1', 'statement': 'no logos', 'scope': 'all', 'source': 'brief'}],
                       'editing_constraints': [{'id': 'C1', 'statement': 'no gift boxes', 'scope': 'all', 'source': 'operator'}]},
        'elements': [{'id': 'E1', 'name': 'Mason hands', 'kind': 'person', 'identity': 'representative', 'requirements': 'brown hands, no rings'}]}
GAP = {'gap_id': 'G2', 'intent': 'curing shown', 'treatment_fit': 'the water'}
SCENE = {'id': 'SC2', 'location_time': 'yard, day'}
SHOT = {'id': 'VS1', 'start_frame': 900, 'end_frame': 1150, 'visual_type': 'video', 'narration': 'cured for seven days', 'purpose': 'water over the wall', 'appearance': 'wet brick',
        'information_progression': '', 'element_ids': ['E1'], 'states': []}
REFS = [{'element_id': 'E1', 'reference_id': 'R1', 'kind': 'sheet'}, {'element_id': 'E1', 'reference_id': 'R2', 'kind': 'frame'}]
BRIEF = {'audience': 'rural builders', 'production': {'format': {'frame': '16:9'}}}
CARD = {'industry': 'education', 'color_palette': 'brick red, warm grey', 'client_brand_guidelines': 'no slogans'}


def test_versions_latest_and_an_unknown_version_is_refused():
    assert VERSION in L.versions() and L.latest() == max(L.versions())
    assert L.manifest(VERSION)['version'] == VERSION
    with pytest.raises(Problem, match='library version'):
        L.manifest('vwlib-1999-01-01-000000000000')


def test_every_step_names_files_that_exist_and_the_pack_carries_their_text():
    pack = L.steps(VERSION)
    assert pack['version'] == VERSION and {f['path'] for f in pack['always']} == set(L.ALWAYS)
    assert set(pack['steps']) == {'reference', 'frame', 'still-scene', 'still-diagram', 'state', 'start', 'end', 'take'}
    for name, step in pack['steps'].items():
        assert step['files'] and all(f['text'].strip() for f in step['files']), name
    assert pack['steps']['take']['task'] == 'clip-from-frame' and pack['steps']['end']['task'] == 'first-last-frame' and pack['steps']['state']['task'] == 'graphic-states'
    assert pack['steps']['frame']['task'] is None   # no prompt is written for a frame grab
    assert 'library/video/models/gemini-omni-1-1/FACT-SHEET.md' in {f['path'] for f in pack['steps']['take']['files']}
    assert pack['map'].startswith('# VideoWizard map') and pack['field_sources'].startswith('# Where each job-form field') and pack['compliance']['path'] == L.COMPLIANCE


def test_the_manifest_check_passes_on_the_copy_and_reports_a_changed_file(tmp_path, monkeypatch):
    assert L.verify(VERSION) == []
    copy = tmp_path / VERSION
    shutil.copytree(L.ROOT / VERSION, copy)
    (copy / 'library' / 'RULEBOOK.md').write_text('edited', encoding='utf-8')
    monkeypatch.setattr(L, 'ROOT', tmp_path)
    assert L.verify(VERSION) == ['library/RULEBOOK.md: sha256 differs']


def test_steps_of_a_shot_follow_its_route():
    assert L.steps_of({'visual_type': 'video'}) == ['start', 'end', 'take']
    assert L.steps_of({'visual_type': 'image'}) == ['still-scene'] and L.steps_of({'visual_type': 'diagram'}) == ['still-diagram'] and L.steps_of({'visual_type': 'animation'}) == ['state']


def test_the_job_form_fills_from_the_run():
    form = L.job_form('take', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=REFS, generator={'provider': 'google', 'model': 'gemini-omni-1.1-flash'}, brief=BRIEF, card=CARD, rules=['no PPE claims'], fps=25)
    assert form['job_id'] == 'VW-9-VS1-1' and form['client_code'] == 'NARDEP' and form['requested_by'] == {'kind': 'agent', 'id': 'vw-operator-assistant'} and form['round'] == 1
    assert form['playbook'] == 'video-clip' and form['task'] == 'clip-from-frame' and form['industry'] == 'education'
    assert form['video_aspect'] == '16:9' and form['placement'] == '16:9' and form['video_seconds'] == 10
    assert form['request'] == {'words': 'cured for seven days', 'purpose': 'water over the wall'} and form['purpose'] == {'intent': 'curing shown', 'treatment_fit': 'the water'}
    assert form['audience'] == 'rural builders' and form['style_direction'] == {'foundation': 'overcast yard light', 'shot': 'wet brick'}
    assert form['copy'] == 'none' and form['text_mode'] == 'rendered' and form['logo'] == 'none' and form['mandatory_text'] == 'none'
    assert form['images'] == [{'id': 'R1', 'tag': 'approved', 'element_id': 'E1', 'keep': 'brown hands, no rings'}, {'id': 'R2', 'tag': 'scene', 'element_id': 'E1', 'keep': 'brown hands, no rings'}]
    assert form['brand_kit_id'] == 'NARDEP' and 'brick red, warm grey' in form['brand_preamble'] and 'no slogans' in form['brand_preamble']
    assert form['hard_constraints'] == ['no logos', 'no PPE claims'] and form['avoid'] == ['no gift boxes']
    assert form['model'] == 'gemini-omni-1.1-flash' and form['finish'] == 'final' and form['variants'] == 1 and form['checked_by'] == 'person' and form['trial'] is False
    start = L.job_form('start', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=REFS, generator=None, brief=BRIEF, card=CARD, rules=[], fps=25)
    assert start['task'] == 'keyframe' and start['mode'] == 'multi-reference' and start['model'] == 'gpt-image-2.5-sunburst-2026-09-08' and 'video_seconds' not in start
    end = L.job_form('end', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=[], generator=None, brief=None, card=None, rules=[], fps=25)
    assert end['mode'] == 'edit-with-identity' and end['placement'] == '16:9' and end['brand_preamble'] == 'none' and end['industry'] == 'other' and end['client_code'] == 'NARDEP'
    state = L.job_form('state', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot={**SHOT, 'visual_type': 'animation', 'states': [{'what_appears': 'the cavity, label "air"', 'hold_s': 5}]}, refs=[], generator=None, brief=None, card=None, rules=[], fps=25)
    assert state['copy'] == [{'role': 'label', 'text': 'the cavity, label "air"'}] and state['mode'] == 'edit'
    with pytest.raises(ValueError, match='unknown library step'):
        L.job_form('poster', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=[], generator=None, brief=None, card=None, rules=[], fps=25)


def test_the_answer_lint_checks_what_a_machine_can_check():
    prompt = 'A brick wall in section, label "air" in the cavity. No other text.'
    good = {'status': 'ready', 'prompt': prompt, 'checklist': [{'check': 'label', 'pass_when': 'reads air', 'weight': 'must'}], 'exact_text': ['air']}
    assert L.check_answer(good, prompt) is good
    with pytest.raises(ValueError, match='status is needs_input'):
        L.check_answer({**good, 'status': 'needs_input'}, prompt)
    with pytest.raises(ValueError, match='prompt differs from the prompt sent'):
        L.check_answer({**good, 'prompt': prompt + ' Add a bird.'}, prompt)
    with pytest.raises(ValueError, match='at least one must line'):
        L.check_answer({**good, 'checklist': [{'check': 'c', 'pass_when': 'p', 'weight': 'should'}]}, prompt)
    with pytest.raises(ValueError, match="exact text 'cavity wall' is not in the prompt"):
        L.check_answer({**good, 'exact_text': ['air', 'cavity wall']}, prompt)
    with pytest.raises(ValueError, match='answer form is an object'):
        L.check_answer(['no'], prompt)


# ---------- design/71 F1, F2, P3: the VideoWizard answer form, the prompt lint, the sizes ----------

def test_the_always_open_set_names_the_videowizard_answer_form_and_the_file_exists():
    assert 'library/forms/answer-form.videowizard.md' in L.ALWAYS and 'library/forms/answer-form.md' not in L.ALWAYS
    text = L.text(VERSION, 'library/forms/answer-form.videowizard.md')
    assert text.startswith('# Answer form, VideoWizard cut') and '`keep_list`' in text and '`seen`' in text
    assert L.verify(VERSION) == []   # the variant sits outside the manifest until the master adopts it


def test_check_prompt_refuses_a_logo_a_model_name_a_pixel_size_and_a_resolution():
    assert L.check_prompt('A brick wall in section, label "air". Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.') is None
    assert L.check_prompt('Lens flare across the top right, the yard at dusk.') is None
    with pytest.raises(ValueError, match='asks for a logo'):
        L.check_prompt('The NARDEP logo in the top right corner, the wall below.')
    with pytest.raises(ValueError, match="names a model \\('sunburst'\\)"):
        L.check_prompt('Edit with gpt image Sunburst: the bucket now empty.')
    with pytest.raises(ValueError, match="names a model \\('omni'\\)"):
        L.check_prompt('For Omni: the mason lifts the brick.')
    with pytest.raises(ValueError, match="a pixel size \\('1536x864'\\)"):
        L.check_prompt('Output at 1536x864, the wall centred.')
    with pytest.raises(ValueError, match="a resolution \\('720p'\\)"):
        L.check_prompt('Render in 720p, the yard.')


def test_an_edit_names_one_change():
    """design/86 K5; design/124 A4 (SK): one change per edit, a second is refused."""
    assert L.check_prompt('Mode: edit. Image 1 is the start.\nChange only: the helper has walked five metres on, smaller with distance.\nKeep exactly as in Image 1: the lane, the houses.') is None
    with pytest.raises(ValueError, match='names 2 changes under "Change only": one change per edit;'):
        L.check_prompt('Mode: edit. Image 1 is the start.\nChange only: the helper has walked five metres on. He is now smaller with distance.\nKeep exactly as in Image 1: the lane, the houses.')
    with pytest.raises(ValueError, match='names 2 changes'):
        L.check_prompt('Mode: edit.\nChange only: the bucket is empty; the trowel lies on the wall.\nKeep exactly as in Image 1: the lane.')
    with pytest.raises(ValueError, match='names 4 changes'):
        L.check_prompt('Mode: edit.\nChange only: the helper is redrawn at true scale. He stands two metres past the stack. He faces the house. He walks toward its entrance.\nKeep exactly as in Image 1: the lane.')
    assert L.check_prompt('Shot: a wall. Beat: built. Constraints: no people.') is None   # a fresh picture has no change section
    # a fix round's one change is the failed check line the server writes, which may run to two clauses
    assert L.check_prompt('Mode: edit.\nChange only: the picture still shows the start state; this line FAILS when the result is in it.\nKeep exactly as in Image 1: the lane.', fix=True) is None


def test_default_size_follows_the_frame_and_an_edit_takes_its_parents_size_only_when_both_sides_divide_by_16():
    assert L.default_size('16:9') == '1536x864' and L.default_size('9:16') == '1088x1936' and L.default_size(None) == '1536x864'
    assert L.edit_size(1536, 864, '16:9') == '1536x864' and L.edit_size(1088, 1936, '16:9') == '1088x1936'
    assert L.edit_size(1920, 1080, '16:9') == '1536x864'   # a footage frame: 1080 is not a multiple of 16
    assert L.edit_size(None, None, '9:16') == '1088x1936'


# ---------- design/124 A4: the corrected guide is a new snapshot; Gemini Omni only; no change-history label in a message ----------

OLD = VERSION
DROPPED = ('library/video/models/kling/FACT-SHEET.md', 'library/video/models/seedance/FACT-SHEET.md', 'library/video/models/higgsfield/NOTES.md')


def _fingerprint(files):
    h = hashlib.sha256()
    for f in sorted(files, key=lambda f: f['path']):
        h.update(f['path'].encode('utf-8') + b'\0' + f['sha256'].encode('ascii') + b'\n')
    return h.hexdigest()


def test_the_new_snapshot_is_the_latest_and_every_snapshot_matches_its_manifest_and_its_name():
    new = L.latest()
    assert new != OLD and new.startswith('vwlib-2026-10-29-') and OLD in L.versions()
    for v in L.versions():
        m = L.manifest(v)
        assert L.verify(v) == [] and m['version'] == v
        assert m['fingerprint_sha256'] == _fingerprint(m['files']) and v.endswith(m['fingerprint_sha256'][:12])
        for f in m['files']:
            assert (L.ROOT / v / f['path']).stat().st_size == f['bytes'], f['path']
    assert L.manifest(OLD)['fingerprint_sha256'].startswith('4f88379be109')   # the old snapshot stays as it was
    assert 'design/124 A4' in L.manifest(new)['note']


def test_the_new_snapshot_drops_kling_seedance_and_higgsfield_and_nothing_points_at_them():
    new = L.latest()
    paths = {f['path'] for f in L.manifest(new)['files']}
    assert not paths & set(DROPPED) and not any((L.ROOT / new / p).exists() for p in DROPPED)
    assert all((L.ROOT / OLD / p).is_file() for p in DROPPED)   # films on the old snapshot keep theirs
    assert L.MODEL_SHEETS == {'gemini-omni-1.1-flash': ('library/video/models/gemini-omni-1-1/FACT-SHEET.md',)} and not set(L.ALL_SHEETS) & set(DROPPED)
    for name, s in L.STEPS.items():
        assert not set(s['files']) & set(DROPPED), name
    pack = L.steps(new)   # every file a step names exists in the new snapshot
    for name, step in pack['steps'].items():
        assert step['files'] and all(f['text'].strip() for f in step['files']), name
    assert L.step_files('take', {'provider': 'higgsfield', 'model': 'kling-video/v3.0/std/image-to-video'}) == [p for p in L.STEPS['take']['files'] if p not in L.ALL_SHEETS]
    for p in paths:
        if p.endswith('.md') or p.endswith('.yaml'):
            t = L.text(new, p)
            assert 'models/kling' not in t and 'models/seedance' not in t and 'higgsfield/' not in t, p


def test_the_new_map_and_field_sources_say_what_the_server_does():
    new = L.latest()
    vwmap, fields = L.text(new, 'VW-MAP.md'), L.text(new, 'FIELD-SOURCES.md')
    form = L.text(new, 'library/forms/answer-form.videowizard.md')
    for t in (vwmap, fields, form):
        assert '₹' not in t and 'spend cap' not in t and '0.21.3' not in t
    assert 'Higgsfield' not in vwmap
    assert 'library/forms/answer-form.videowizard.md' in vwmap and '`library/forms/answer-form.md`' not in vwmap
    assert 'Nano Banana' in vwmap and 'Nano Banana' in fields and 'GPT Image 2.5 for every image' not in vwmap
    assert '--quality' in vwmap and 'In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts. No dialogue. No music. No captions or overlay text.' in vwmap
    assert 'end_prompt' in vwmap and 'from words' in vwmap and 'one change per edit' in vwmap.lower()
    row = fields.split('`mandatory_text`')[1].split('\n')[0]
    assert '`none`' in row and 'does not come from the client card' in row
    assert 'for {video model}' not in L.text(new, 'library/playbooks/video-frame.md')
    L.check_prompt('Asset: keyframe, shot 2 of 5, at 16:9. Target aspect ratio: 16:9. Mode: multi-reference.')


def test_messages_the_assistant_reads_carry_no_change_history_label():
    def msg(fn, *a):
        with pytest.raises(ValueError) as e:
            fn(*a)
        return str(e.value)
    texts = [msg(L.check_prompt, 'The mason stands in the centre.'), msg(L.check_prompt, 'They sit as before.'),
             msg(L.check_prompt, 'Mode: edit.\nChange only: a wall. b door.\nKeep: c.'), msg(L.check_material_prompt, 'short bricks in a row'),
             msg(L.check_quoted, 'A sign reads "Mortar bed" above.', []),
             msg(L.check_exact_places, {'exact_text': [{'text': 'air'}]}, set()),
             msg(L.check_exact_places, {'exact_text': [{'text': 'air', 'place': {'landmark_id': 'L9'}, 'size_pct': 3}]}, set()),
             msg(L.check_exact_places, {'exact_text': [{'text': 'air', 'place': {'region': 'top'}}]}, set())]
    for t in texts:
        assert 'design/' not in t, t


def test_the_job_form_names_the_films_own_picture_ai():
    """design/124 A4 item 7: a Nano Banana film's form names the Gemini image model, not GPT Image."""
    from app.config import settings
    form = L.job_form('start', run={**RUN, 'image_provider': 'gemini'}, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=REFS, generator=None, brief=BRIEF, card=CARD, rules=[], fps=25)
    assert form['model'] == settings().GEMINI_IMAGE_MODEL
    assert L.job_form('start', run=RUN, plan=PLAN, gap=GAP, scene=SCENE, shot=SHOT, refs=REFS, generator=None, brief=BRIEF, card=CARD, rules=[], fps=25)['model'].startswith('gpt-image')
