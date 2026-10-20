"""The delivery package texts (design/47 12.3): the checklist's loudness line and OPEN-EDIT's subtitle line. No database."""
from app.stage3 import delivery as D

PK = {'sub_clips': [{'sub_clip_id': 'c1:S1', 'color_group': 'G1'}], 'sfx_cues_flat': []}


def test_checklist_carries_the_measured_loudness():
    summary = {'finishing': [], 'loudness': {'check': {'integrated_lufs': -15.8, 'true_peak_dbfs': -3.0, 'peak_ceiling_dbtp': -3, 'integrated_target_lufs': -16}}}
    items = D.checklist_of(summary, PK, {})
    bus = next(i for i in items if i['where'] == 'Fairlight bus')
    assert '-16 LUFS' in bus['item'] and '-3 dBTP' in bus['item'] and 'measured -15.8 LUFS, peak -3.0 dBTP' in bus['item'] and 'no music' in bus['item']
    assert not any('-14 LUFS' in i['item'] or '-1 dBTP' in i['item'] for i in items)


def test_checklist_without_a_check_says_not_measured():
    items = D.checklist_of({'finishing': []}, PK, {})
    bus = next(i for i in items if i['where'] == 'Fairlight bus')
    assert 'not measured' in bus['item']


def test_open_edit_names_one_cue_per_sentence():
    text = D.open_edit_text({'code': 'VW-9', 'client': 'C'})
    assert 'one cue per narrated sentence' in text and 'approved pauses' in text and 'narration beats' not in text


def test_checklist_deliver_line_carries_the_format(monkeypatch):
    items = D.checklist_of({'finishing': []}, PK, {}, brief={'production': {'format': {'frame': '9:16', 'destinations': ['Instagram', 'TikTok'], 'watched_muted': True}}})
    line = next(i for i in items if i['where'] == 'Deliver page' and 'frame' in i['item'])
    assert 'frame 9:16' in line['item'] and 'Instagram, TikTok' in line['item'] and 'burn the subtitles in' in line['item']
    items = D.checklist_of({'finishing': []}, PK, {})
    line = next(i for i in items if i['where'] == 'Deliver page' and 'frame' in i['item'])
    assert 'frame 16:9' in line['item'] and 'destinations not given' in line['item']
