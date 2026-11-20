"""Release 3, C3 and C4 (SK, 20 Nov 2026, N6 and N4: "at the plan check"). C3: a logo or brand picture the plan shows and for which no file
has been given is named when the plan is checked and proposed, as a warning that says the folder to put it in; never a refusal; the operator
reads it on the plan page; it goes when the file arrives. C4: a drawn shot that carries text and lists no labels is named with the other
plan warnings, with the way out; the gate before the first brief (step 6) stays as the safety net and reads the same rule. Without a database."""
from app import visual_contract as VC, visuals_stage as VS
from step6_shape import load
from test_design221_p1_pure import NEW, edit_plan, edit_session
from test_fixset2_pure import shots_of, warnings

LOGO = {'id': 'E-logo', 'name': 'Client logo', 'kind': 'graphic', 'identity': 'exact', 'requirements': 'the logo as the client supplies it'}


def with_logo(store, shot=0):
    edit_plan(store, lambda d: (d['elements'].append(dict(LOGO)), shots_of(d)[shot].update(element_ids=shots_of(d)[shot]['element_ids'] + ['E-logo'])))
    return shots_of(VS.current_plan(store, VS.session_of(store, NEW, [])))[shot]['id']


# ---------- C3 ----------

def test_a_logo_the_plan_shows_with_no_file_is_a_warning_with_the_folder_and_never_a_refusal():
    store = load()
    assert warnings(store, 'supplied_missing') == []                                    # a film with no supplied file: nothing is said
    sid = with_logo(store)
    hit = warnings(store, 'supplied_missing')
    assert len(hit) == 1 and hit[0]['shot_id'] == sid and hit[0]['answered'] is False
    assert hit[0]['message'] == (f'shot {sid} shows Client logo (E-logo) and no file of it has been given. Ask the operator for it now, with the plan: the file goes in the run '
                                 'folder under in/brand/ (`vw brand fetch` saves the logo files the client directory holds there), then '
                                 '`vw visuals supply --element E-logo --file in/brand/<name>`. If the film goes on without it, say so in the shot\'s warning_answers.')
    assert 'supplied_missing' in VC.WARNING_PLAIN and VC.WARNING_PLAIN['supplied_missing'] == 'This shot shows a logo or a brand picture, and its file has not been given yet.'


def test_it_is_said_once_for_each_thing_and_goes_when_the_file_arrives():
    store = load()
    with_logo(store, 0)
    edit_plan(store, lambda d: shots_of(d)[1].update(element_ids=shots_of(d)[1]['element_ids'] + ['E-logo']))
    assert len(warnings(store, 'supplied_missing')) == 1                                 # the first shot that shows it
    edit_session(store, lambda s: s['references'].update({'R-logo': {'id': 'R-logo', 'kind': 'supplied', 'element_id': 'E-logo', 'status': 'candidate'}}))
    assert warnings(store, 'supplied_missing') == []                                    # the file arrived after the warning
    edit_session(store, lambda s: s['references']['R-logo'].update(status='rejected'))
    assert len(warnings(store, 'supplied_missing')) == 1                                 # a rejected file is no file


def test_the_operator_reads_it_on_the_plan_page_until_the_file_is_given_or_the_assistant_answers_it():
    store = load()
    sid = with_logo(store)
    s = VS.session_of(store, NEW, [])
    plan = VS.current_plan(store, s)
    gap = plan['gaps'][0]
    s['versions'][-1]['warnings'] = VS.carried_warnings(s, NEW, plan, [])                # as the proposal stores them
    assert {'kind': 'supplied_missing', 'shot_id': sid, 'plain': VC.WARNING_PLAIN['supplied_missing']} in VS.plain_warnings(s, gap, plan)
    s['references']['R-logo'] = {'id': 'R-logo', 'kind': 'supplied', 'element_id': 'E-logo', 'status': 'approved'}
    assert not [w for w in VS.plain_warnings(s, gap, plan) if w['kind'] == 'supplied_missing']   # worked out now, not read from the stored proposal


def test_a_thing_not_named_as_a_logo_or_a_brand_mark_is_not_asked_for_a_file():
    store = load()
    edit_plan(store, lambda d: (d['elements'].append({**LOGO, 'id': 'E-x', 'name': 'Logistics yard'}), shots_of(d)[0].update(element_ids=shots_of(d)[0]['element_ids'] + ['E-x'])))
    assert warnings(store, 'supplied_missing') == []
    edit_plan(store, lambda d: d['elements'][-1].update(name='The brand mark of the maker'))
    assert len(warnings(store, 'supplied_missing')) == 1


# ---------- C4 ----------

def bare(store, n=0, **fields):
    edit_plan(store, lambda d: shots_of(d)[n].update(scene_motion={'labels': [], 'cues': []}, **fields))
    return shots_of(VS.current_plan(store, VS.session_of(store, NEW, [])))[n]


def test_a_drawn_shot_that_carries_text_and_lists_no_labels_is_named_at_the_plan_check_with_the_way_out():
    store = load()
    assert warnings(store, 'labels_missing') == []
    sh = bare(store, 0, carries_text=True)
    hit = warnings(store, 'labels_missing')
    assert [w['shot_id'] for w in hit] == [sh['id']] and 'labels_missing' in VC.WARNING_TECHNICAL
    assert hit[0]['message'] == (f"shot {sh['id']} is a drawn graphic that carries text and lists no labels. Add scene_motion: {{labels: [every text the viewer reads, word for word, "
                                 'never the corner note], cues: [{selector: "#id", word or at_s}]} to it now, in the plan; if its only text is the corner note or a logo '
                                 'picture, set carries_text to false on it. `vw motion brief` is refused for every drawn shot until then.')
    two = bare(store, 1, carries_text=True)
    assert [w['shot_id'] for w in warnings(store, 'labels_missing')] == [sh['id'], two['id']]   # each shot named
    edit_plan(store, lambda d: shots_of(d)[0].update(carries_text=False))
    assert [w['shot_id'] for w in warnings(store, 'labels_missing')] == [two['id']]      # the way out


def test_the_step_6_gate_stays_and_reads_the_same_rule():
    store = load()
    sh = bare(store, 0, carries_text=True)
    s = VS.session_of(store, NEW, [])
    plan = VS.current_plan(store, s)
    assert VS.text_no_labels(sh) and not VS.text_no_labels({**sh, 'carries_text': False}) and not VS.text_no_labels({**sh, 'visual_type': 'image'})
    assert VS.text_no_labels({**sh, 'carries_text': False, 'drawing_spec': {'label': 'Section A'}})   # a spec's own label is text too
    assert not VS.text_no_labels({**sh, 'carries_text': False, 'drawing_spec': {'label': 'Illustrative, not to scale', 'illustrative': True}})   # the corner note is not
    try:
        VS.motion_brief(store, NEW, [], shots_of(plan)[1]['id'], build=True)
        raise AssertionError('the gate before the first brief is gone')
    except ValueError as e:
        assert str(e).startswith(f"Before the first brief, the texts of every drawn shot go in the plan: {sh['id']} carries text and has no scene_motion.labels")


def test_a_film_drawn_the_older_way_is_not_asked_for_labels():
    store = load()
    bare(store, 0, carries_text=True)
    s = VS.session_of(store, NEW, [])
    old = {**NEW, 'drawn_route': 'svg'}
    assert not [w for w in VS.carried_warnings(s, old, VS.current_plan(store, s), []) if w['kind'] == 'labels_missing']
