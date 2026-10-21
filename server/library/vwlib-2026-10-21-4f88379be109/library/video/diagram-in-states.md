# Diagram in states: a graphic that builds

Version 0.1, written 2026-10-21 for VideoWizard (design/65, decision S1). Status: **draft, untested.** No job has run on it. Read it with `RULEBOOK.md`, `playbooks/video-frame.md`, `models/gpt-image/FACT-SHEET.md` sections B1, B4 and B5, and `00-method/craft.md` section 5.

## 1. What this covers

Task `graphic-states`: one diagram, chart or illustrated explainer that changes on screen in two to four steps. Each step is a still image (a "state"). Together they play as a build: each state holds, then dissolves into the next, sometimes with a slow push. Nothing moves inside a state. Arrows that travel and parts that slide are out of scope; plan a build (parts appear) or a reveal (parts get highlighted) instead.

A graphic that never changes is not this task. It is one still (`process-explainer` or `spot-illustration`).

## 2. Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Model | GPT Image 2.5. Flare (generate) for state 1; Sunburst (edit) for every later state, with the previous approved state attached as Image 1. | Edits keep the drawing; Sunburst is the edit-precision model. Fact sheet A1. |
| Count | Two to four states. One state is a still; five or more is a slideshow. | design/65. |
| Hold | At least three seconds per state, long enough to read every new label twice. | design/64 A.4. |
| Plan the last state first | Write the full final diagram in words before generating state 1: every part, label, colour and position. Earlier states are that picture with parts missing or not yet highlighted. | Forward generation leaves no room for parts added later. Room must be reserved from the start. |
| One change per state | Each state adds or highlights one idea. | RULEBOOK rule 8; fact sheet B5. |
| The keep-list is repeated in full every time | Every edit prompt names everything that must not change. | Fact sheet B5: "Repeated edits drift. Restate the preserve list every turn." |
| Retry from the last approved state | Never edit a state that drifted; go back to the last approved one. | Fact sheet B5 and the failure table. |
| Text | Exact strings in quotes, short, large. Text is not a reason to avoid this route. | RULEBOOK rule 4; design/64 D2. |

## 3. Before writing

1. The narration under the shot, and what the viewer must understand by the last state.
2. The final state in words (the "end picture"): canvas and aspect, background, every part, each label exactly, colour meanings, and where each part sits (left third, centre, lower band…).
3. The state list: what each state adds or highlights, and its hold in seconds. The holds add up to the shot's length.
4. The film's graphic style, if one is set: palette with hex values, line weight, label font feel, background. Repeat it word for word in every graphic of the film.

## 4. Writing the prompts

State 1 (generate):

```text
Asset: diagram, state 1 of {n}, for a 16:9 documentary film. Target aspect ratio: 16:9. Mode: generate.
Canvas: {background}, {margins}. Reserve empty space at {positions} for parts that appear later; keep that space plain.
Style, verbatim: {palette hex list}; {line weight}; {label style}; {flat | cutaway | isometric}.
Diagram: {chart family or cutaway}. Shown now: {parts in state 1, each with its position}.
Exact text: "{label 1}" at {position}; "{label 2}" at {position}. No other text.
Constraints: no parts from later states; no arrows unless listed; no logos, watermarks or captions.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

State 2 and later (edit, Image 1 = the previous approved state):

```text
Asset: diagram, state {k} of {n}. Mode: edit. Image 1 is the approved state {k-1}.
Change only: add {the new part} at {position} {with label "{text}"} | highlight {part} with {a coloured outline | a brighter fill}.
Keep exactly as in Image 1: canvas, background, every existing part and its position and size, every existing label letter for letter, palette, line weight, label style, margins.
Constraints: no other new elements or text; do not redraw, restyle or move anything; no logos, watermarks or captions.
```

An alternative, to be tested: generate the **final** state first, then make the earlier states by removal edits ("remove only X; keep everything else"). If removals hold the drawing better than additions, adopt this and record it in the feedback log.

## 5. Checklist lines (the answer form's checklist)

- Every label reads letter for letter as quoted; no extra text. must.
- State k shows everything in state k-1 at the same place, size and colour. must.
- Only the planned change differs between consecutive states. must.
- The reserved space is still plain until its state. must.
- The final state matches the end picture written in section 3. must.
- Aspect 16:9 (or the film's format) at the size the renderer expects. must.
- Each new label can be read in its hold time at phone size. should.

## 6. What goes wrong, and the fix

| Habit | Fix |
| --- | --- |
| A later edit restyles the whole drawing | Shorter "change only" line; the full keep-list; retry from the last approved state, not the drifted one |
| No room for the next part | Plan the end picture first; reserve named empty space in state 1 |
| Labels re-spelt or reflowed on edit | List every existing label in the keep-list, in quotes |
| Colours shift between states | Hex values in the style line of every prompt |
| Too many words for the hold | One idea per state; three to five words a label |

## 7. Evidence

None yet. The first VideoWizard sequence (VW-6) is the first test. Record each state in the feedback log with `app: videowizard`.

## 8. Built from

`models/gpt-image/FACT-SHEET.md` A1, B1, B4, B5 and the failure table; `00-method/craft.md` section 5 (diagram grammar); `prompts/05-information.md` P025 and P030; `playbooks/web-app.md` process-explainer; RULEBOOK rules 3, 4 and 8; VideoWizard design/64 and design/65.
