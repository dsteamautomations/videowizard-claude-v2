"""Defect 38 (VW-12, 31 Oct 2026): a reference sheet sent with its answer form was always refused ("The answer's prompt differs from the
prompt sent"): the server added its sheet lines to the prompt before keeping the writer's words for the check."""
from test_design119_d_pure import sheet_store
from test_design111_f11_pure import image
from test_visuals_stage_pure import saved

PROMPT = 'Image 1 is the web picture of the broom: take its form. Image 2 is the supplied picture: take its binding.'
ANSWER = {'status': 'ready', 'prompt': PROMPT, 'checklist': [{'check': 'the broom', 'weight': 'must', 'pass_when': 'one coconut-midrib broom'}]}


def test_a_sheet_with_its_answer_form_is_accepted_and_still_gets_the_servers_lines():
    store = sheet_store()
    out = image(store, element_id='E3', kind='sheet', name='sheet-E3', subject='the broom', parents=['W3', 'U3'], prompt=PROMPT, answer=ANSWER)
    sent = saved(store)['references'][out['reference_id']]['generation']['prompt']
    assert sent.startswith(PROMPT) and len(sent) > len(PROMPT)   # the server's sheet lines still follow the writer's words
