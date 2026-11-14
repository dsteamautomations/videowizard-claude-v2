"""Writes design/_work/vw23-comparison.md from compare.json (the figures worked out by compare_vw23.py)."""
import json
from pathlib import Path

HERE = Path(__file__).parent
d = json.loads((HERE / 'compare.json').read_text(encoding='utf-8'))
o, n, s, m = d['old'], d['new'], d['sentences'], d['new_direct_shots_by_gemini_mark']
rows = {r['sentence']: r for r in d['rows']}
L = []
A = L.append
A('# VW-23: the cut of 13 Nov against the cut of 14 Nov')
A('')
A("14 Nov 2026. Both cuts read from the server (read only), with the operator's keep and reject answers from the run's log. Worked out by Claude's script "
  '(`model-test/vw23-compare/compare_vw23.py`); no model was called.')
A('')
A('| | The cut of 13 Nov | The cut of 14 Nov |')
A('|---|---|---|')
A('| Who watched the clips | Gemini 3.8 Flash; fit by paragraph | Gemini 4 Hydrogen, the look-again way for every clip; fit by sentence |')
A("| Who chose the clips | Claude, the operator's assistant, under the application's full rules, with the server's check and the second look | The same |")
A('| Scenes, narration, film length | 15 scenes, 42 sentences, 299.4 s | The same |')
A('')
A('## In short')
A('')
A(f"- **The new cut has less real footage, not more:** {n['footage_s']} seconds against {o['footage_s']}.")
A(f"- **What it placed was right more often:** {n['answered']['REJECT']} of {n['footage_shots']} footage shots rejected, against {o['answered']['REJECT']} of {o['footage_shots']}.")
A('- **It lost four shots the operator had kept, and gained none.** Two were lost to stricter matching, two because Gemini 4 Hydrogen flags small background things as risks and the server then refuses the piece.')
A('- **Three of the four direct shots the operator rejected on 13 Nov were right first time on 14 Nov.**')
A("- So the change made the cut more careful and less full. On the first two of Deepa's three points it is not a win.")
A('')
A('## 1. More real footage?')
A('')
A('| | 13 Nov | 14 Nov |')
A('|---|---|---|')
A(f"| Real footage | {o['footage_s']} s ({o['footage_share']} %) | {n['footage_s']} s ({n['footage_share']} %) |")
A(f"| Left blank for AI video or graphics | {o['blank_s']} s | {n['blank_s']} s |")
A(f"| Footage shots | {o['footage_shots']} | {n['footage_shots']} |")
A(f"| Footage the operator kept as placed | {o['footage_s_kept_as_placed']} s | {n['footage_s_kept_as_placed']} s |")
A(f"| Footage kept, counting a kept alternative | {o['footage_s_kept_incl_alternative']} s | {n['footage_s_kept_incl_alternative']} s |")
A('')
A('Per scene, seconds of real footage (scenes with none in both cuts are left out):')
A('')
A('| Scene | 13 Nov | 14 Nov |')
A('|---|---|---|')
for k in o['per_scene_footage_s']:
    a, b = o['per_scene_footage_s'][k], n['per_scene_footage_s'][k]
    if a or b:
        A(f'| {k} | {a} | {b} |')
A('')
A('## 2. Small pieces found?')
A('')
A('| | 13 Nov | 14 Nov |')
A('|---|---|---|')
A(f"| Pieces the clip study offered | {o['pieces_offered']} | {n['pieces_offered']} |")
A(f"| Shots under 3 seconds | {o['shots_under_3s']} | {n['shots_under_3s']} |")
A(f"| Shots cut from inside a longer piece | {o['shots_from_inside_a_longer_piece']} | {n['shots_from_inside_a_longer_piece']} |")
A(f"| Different clips used | {o['different_clips']} | {n['different_clips']} |")
A(f"| Clips used only in this cut | {len(d['clips']['only_old'])} | {len(d['clips']['only_new'])} |")
A(f"| Clips used in both cuts | {d['clips']['in_both']} | {d['clips']['in_both']} |")
A('')
A('Gemini 4 Hydrogen cut the footage into more pieces (299 against 204), but the cut did not use more of them.')
A('')
A('## 4. Kept by the operator')
A('')
A('| | 13 Nov | 14 Nov |')
A('|---|---|---|')
A(f"| Footage shots kept | {o['answered']['KEEP']} of {o['footage_shots']} | {n['answered']['KEEP']} of {n['footage_shots']} |")
A(f"| Rejected | {o['answered']['REJECT']} | {n['answered']['REJECT']} |")
A(f"| Rejected, then its alternative kept | {o['rejected_then_alternative_kept']} | {n['rejected_then_alternative_kept']} |")
A('')
A('## 5. Gained and lost, sentence by sentence')
A('')
A('| | Sentences |')
A('|---|---|')
A(f"| Footage in both cuts | {s['footage_in_both']} |")
A(f"| Blank in both | {s['blank_in_both']} |")
A(f"| Footage gained by the new cut | {len(s['gained_footage'])} |")
A(f"| Footage lost by the new cut | {len(s['lost_footage'])} |")
A(f"| The same clips in both | {s['same_clips_both']} |")
A('')
WHY = {'BEAT_02.S1': 'No piece is offered for this scene any more: the line names nothing a clip shows, and the looser B-roll the old cut used is no longer fitted to it.',
       'BEAT_03.S2': 'The assistant now treats the sentence as a strength claim that no piece shows.',
       'BEAT_12.S1': 'The piece is refused: Gemini 4 Hydrogen flagged "background banner signage" on this clip.',
       'BEAT_14.S1': 'The piece is refused: Gemini 4 Hydrogen flagged "a crew bag in the background"; the other candidate was the wrong object.'}
A('The four sentences that lost footage. In every one the operator had kept the old shot.')
A('')
A('| Sentence | Old shot (kept) | Why the new cut has a blank |')
A('|---|---|---|')
for sid in s['lost_footage']:
    r = rows[sid]
    x = r['old_shots'][0]
    kind = 'B-roll' if x['match'] == 'b_roll' else 'a direct match'
    A(f"| {r['text'][:95]} | {x['clip'][:5]}, {x['in_s']} to {x['out_s']} s, placed as {kind} | {WHY.get(sid, '')} |")
A('')
A('## 6. Honest labels')
A('')
A('| | 13 Nov | 14 Nov |')
A('|---|---|---|')
A(f"| Placed as a direct match | {o['direct']} | {n['direct']} |")
A(f"| Placed as B-roll | {o['b_roll']} | {n['b_roll']} |")
A(f"| From the client's library | {o['library']} | {n['library']} |")
A('')
A(f"Of the new cut's {n['direct']} direct shots, Gemini marked {m.get('EXACT', 0)} as showing the sentence exactly and {m.get('PARTLY', 0)} as showing part of it. "
  'None was only "related": the new rule held.')
A('')
A('## 7. Repeats')
A('')
A(f"- 13 Nov: no clip used twice. 14 Nov: one clip used twice ({', '.join(c[:5] for c in n['clips_used_more_than_once']) or 'none'}), under two neighbouring sentences of one scene.")
A("- Two neighbouring shots of the same subject: for the team's eye, in the list at the end.")
A('')
A('## 8. Effort')
A('')
A('| | 13 Nov | 14 Nov |')
A('|---|---|---|')
A("| Refusals of the cut by the server's check | 9 | 3 |")
A('| Analysis time | 51 minutes | 60 minutes, of which about 40 were waiting on two clips that stopped without an answer |')
A('| Analysis cost | not worked out | 28.62 US dollars |')
A('')
A('## What caused the loss of footage')
A('')
A('| Cause | Evidence |')
A('|---|---|')
A('| **Small background things flagged as risks** | Gemini 4 Hydrogen put a risk flag on 52 pieces; Flash on 17. Its flags are things like "background motorcycle licence plate, unreadable", '
  '"minor background clutter", "commercial paint bucket label", "background banner signage", "personal item on prop". The server refuses any piece that carries a flag, even when the model '
  'itself marks the piece safe for the client. Clips with at least one usable piece fell from 95 to 89 of 106. Four clips the old cut used (C0081, C0084, C0101, C0104) are refused in the '
  'new list for this reason alone. |')
A('| **Stricter matching** | The fit is now by sentence, and a piece only related to a sentence cannot be a direct match. Looser B-roll under an opening line, and a shot under a strength '
  'claim, are no longer offered. |')
A('')
A("## 3. Order and choice within a sentence: for the team's eye")
A('')
A('Every sentence where the two cuts chose differently, shots in play order. "Operator" is the answer on the review page; "Gemini" is its mark for that piece under that sentence.')
A('')
for r in d['rows']:
    if r['old'] == r['new'] == 'footage' and not r['same_clips']:
        A(f"**{r['text']}**")
        A('')
        A('| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |')
        A('|---|---|---|---|---|---|---|')
        for tag, xs in (('13 Nov', r['old_shots']), ('14 Nov', r['new_shots'])):
            for x in xs:
                ans = (x['answer'] or '').capitalize() + (' (its alternative kept)' if x['answer'] == 'REJECT' and x.get('alt_answer') == 'KEEP' else '')
                A(f"| {tag} | {x['slide']} | {x['clip'][:5]}, {x['in_s']} to {x['out_s']} s | {x['size']} | {x['match']} | {ans} | {x.get('gemini') or ''} |")
        A('')
A('## Not known')
A('')
A('- Whether the four lost shots were good film. The operator kept them on 13 Nov; nobody has judged whether the blank is the better choice.')
A('- Order within a sentence (area 3): listed above, not judged.')
A('- One film, one operator, one pass.')
out = HERE.parents[1] / 'videowizard-v2-handover' / 'design' / '_work' / 'vw23-comparison.md'
out.write_text('\n'.join(L) + '\n', encoding='utf-8', newline='\n')
print(out, len(L), 'lines')
