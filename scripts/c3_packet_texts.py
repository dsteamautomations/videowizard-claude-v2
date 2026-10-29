"""design/124 C3: the five shot-packet texts held back from A2-A4 (they are part of each shot's fingerprint), corrected now that the old runs are dropped:
a start image per video, the end only where it must be exact and made by the server after the start's approval (decision 9), the old alias gone,
continuity without 'the two frames', and an exact client pattern carried by its golden picture."""
P = 'server/app/visuals_stage.py'
FIXES = [
    ("'Write the start prompt and the end prompt together before generating either. Compose the start for the whole segment: every visible subject, '",
     "'Write the start prompt; only where the shot has end_state_exact, write the end\\'s request with it (end_prompt, end_answer, end_region: one region, a third of the frame at most). '\n"
     "                         'Compose the start for the whole segment: every visible subject, '"),
    ("'the camera only changes their screen projection. A boundary picture is shared only within one continuous shot, same place and framing: the end image '\n"
     "                         'of one segment is the start of the next there; a cut starts a new pair with its own two images. Name one human-scale anchor against a named landmark '",
     "'the camera only changes their screen projection. Where a segment has an end image, it is the start image of the next only within one continuous shot, '\n"
     "                         'same place and framing; a cut starts afresh with its own start image. Name one human-scale anchor against a named landmark '"),
    ("    end_instruction = ('Make the end image from the approved start image as its parent; the server sends the start\\'s own references with it. Show every subject in its end state '",
     "    end_instruction = ('Only for a shot with end_state_exact: the server makes the end image from the approved start (from the request written with the start); '\n"
     "                       'the start\\'s own references go with it. The request shows every subject in its end state '"),
    ("'acting subject the result of its last beat. Name the positions in words. Change nothing else: the same framing, camera, light, people and props. Keep in '",
     "'acting subject the result of its last beat. Name the positions in words. Change only what lies inside the region: the same framing, camera, light, people and props. Keep in '"),
    ("'frame whatever the motion heads for. Image 1 is the start image; images 2 onward are its identity sheets, sent by the server: take identity from them, '",
     "'frame whatever the motion heads for. Image 1 is the start image; images 2 onward are its own references, sent by the server: take identity from them, '"),
    ("              'start_image_instruction': start_instruction, 'image_instruction': start_instruction,   # the old name answers for one release (design/67 A)\n",
     "              'start_image_instruction': start_instruction,   # design/124 C3: the old alias image_instruction is gone\n"),
    ("'The take is one unbroken shot: write the motion so nothing enters the frame that the start or the end does not show. Write the continuity line (`--continuity`): what stays unchanged between the two frames, and for a person five traits from the sheet.',",
     "'The take is one unbroken shot: write the motion so nothing enters the frame that the start (or the end, where the shot has one) does not show. Write the continuity line (`--continuity`): what stays unchanged through the shot (and between the start and the end image where there is one), and for a person five traits from the sheet.',"),
    ("('' if carriers else '; no close reference is bound yet: bind a footage frame or an isolated picture of it first')",
     "('' if carriers else '; no close reference is bound yet: bind its golden picture (before one exists, a footage frame)')"),
]
s = open(P, encoding='utf-8', newline='').read()
for old, new in FIXES:
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)
open(P, 'w', encoding='utf-8', newline='').write(s)
print('applied', len(FIXES))
