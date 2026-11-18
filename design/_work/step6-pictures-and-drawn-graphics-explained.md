# Step 6: Pictures and drawn graphics, explained

Read from the code and the instructions at commit d439dbd (server 0.110.0, plugin 0.94.0), 18 Nov 2026. This is the version live on the server today. Nothing was run.

## 1. Step 6 in one glance

- **What it is:** the real fills of the film's gaps are made and approved, one by one: still pictures, graphic sequences and drawn graphics. AI video is step 7.
- **What comes in:** the accepted plan (each shot, its kind, its words, its sizes), the approved references of step 5 (the "golden picture" of each thing), the approved drawings and materials, the film's motion style, colours and font.
- **What goes out:** every still and graphic shot has an approved fill placed in the film. Step 7 uses the same references; step 8 records the gaps.
- **Money:** a still, each state of a graphic sequence and the style sheet are paid pictures, made by the film's picture AI. A drawn graphic is free. The operator is told the cost, not asked. The server refuses a picture that would pass the film's cost limit.
- **Where the operator answers:** in the chat, one decision at a time. Exception: the sizes and labels of a drawn graphic (its "drawing spec") are approved earlier, on the page, after the plan; in the chat only where the page cannot be shown.

## 2. What is made in this step

- **A still**
  - A realistic picture (or an illustration without exact figures) that fills a shot, moved slowly (a push or a pan of about 5 %) when the film is put together.
  - Used where no footage fits; also the default for a shot under 4 seconds with no visible action.
  - Made by the film's picture AI from the assistant's request. Image 1 is the thing's golden picture; one reference per person and thing in the shot follows.
  - Model: chosen once per film at its start. GPT Image (`gpt-image-2.5-flare-2026-09-08` for a new picture, `gpt-image-2.5-sunburst-2026-09-08` for an edit) or Gemini (`gemini-nano-banana-2.1` on the live server, as VW-24's job records show; the code's own default is `gemini-3-pro-image`).
- **A graphic sequence**
  - Two to four pictures that are states of one graphic. Each is made from the one before, so only the new part appears. The film plays them as a build.
  - Used for a graphic of ideas with nothing exact. Arrows that travel and parts that slide are not possible here.
  - Made by the same picture AI, paid per state.
- **A drawn graphic**
  - An animated diagram, chart, map or timeline with exact labels, sizes or counts.
  - Built as a small web animation (HyperFrames) by Claude helpers on the operator's laptop; the server renders it to video. No picture model. Free.
  - On a film started the older way ("svg"), the assistant writes one drawing file; the server renders it, Gemini 3.8 Flash reads every frame and corrects it up to twice.
- **The graphics' style sheet**
  - One paid picture that fixes the palette, line and labels for the film's graphics. It goes into the first picture of every graphic sequence.
  - A drawn graphic takes its colours from the plan and its look from the film's motion style; whether a motion film still needs the style sheet picture is not confirmed (the server only warns when it is missing).
- **Also made here**
  - A component: one thing alone on a clear background, in the approved style, for a drawn graphic to place. Paid.
  - A fix: an edit of a picture for one failed check line. Paid, only on request.
  - A finish on a drawn graphic (soft blur, grain, darker corners), added by the server; the operator can take it away.

## 3. Who does what, in order

**A still or a graphic sequence**

1. **Assistant · Claude** reads the prompt library once, writes the picture's request in the library's form, with every word to be read listed exactly (text, place, size).
2. **Server · no AI** checks the request. It refuses, with the reason: a rejected or derived picture as a parent, a reference of a thing not in the shot, a web picture of a person, quoted words not listed as exact text, too many pictures, a cost over the limit.
3. **Server · no AI** adds its own lines to the request: the known sizes as numbers, the material's sentence, the "not this" list, the exact-text sentence.
4. **Server · GPT Image or Gemini picture model** (the film's choice) makes the picture. For a sequence: one state at a time, each from the one before.
5. **Server · no AI** measures the picture: size and shape, the parent chain, the light and fine detail against the footage, a clear background for a component.
6. **Server · Gemini 3.8 Flash** reads the picture against its check list. It marks; it never blocks.
7. **You** answer the picture in the chat (a sequence: all states together).
8. **Server · no AI** on Yes: places the still in the shot at once. On No or Correct it: the picture is rejected and never used again.
9. **Assistant · Claude** after a No: writes a new request with your note. Back to move 2.

**A drawn graphic**

1. **You** approve the drawing spec (parts, known sizes, labels) on the page. The film's font is asked once before the first drawing.
2. **Server · no AI** writes the brief of the shot from the plan: length, narration with each word's second, labels, colours, pictures.
3. **Helpers · Claude** (one rule writer per shot) write the numbered rules the picture must keep. If a fact is open, you tick, strike or add rules once.
4. **Helpers · Claude** (one builder per shot, three or four at once) build the animation and upload it. **Server · no AI** refuses a project that breaks its rules.
5. **Helpers · Claude** (a fresh checker that never saw the build) judge snapshots against the rules. Failed rules go back to a builder; at most two redo rounds, then you see the open rules.
6. **Server · no AI** renders the video. It refuses when a label is not word for word, or the spec is not approved.
7. **You** select or reject the drawing in the chat.

## 4. What will be given to the operator

In the order met. Questions the assistant raised itself come first.

- **The drawing spec** (on the page; chat only as fallback)
  - "…: are the parts and the known sizes right?" (or "are the parts right?"; a material: "are these facts right?").
  - Shown: what it is drawn as, parts, how they sit, sizes with their source, sizes not known ("so no figure is shown").
  - **Yes**: recorded. **Correct it**: you say which value is wrong. Free.
- **The style sheet**
  - "The style sheet of the graphics: is this picture right?" Shown: the picture and up to six check lines.
  - **Yes** ("It is right"), **No** ("It is wrong; another is made"), **Correct it** ("I will ask you what to correct"). No and Correct it lead to a new paid picture.
- **A still**
  - "<name>: is this picture right?" Same picture, lines and three buttons.
  - **Yes** places it in the film; you are told the film time. **No** / **Correct it**: a new paid picture with your note.
- **A graphic sequence**
  - "<shot>: are these N steps of the graphic right?" Shown: all states together.
  - **Yes** approves the whole sequence. **Correct it**: the last state is rejected; a new paid state is made from the last good one.
- **A drawn graphic**
  - "<shot>: is this drawing right for the film?" Shown: the video, a sheet of its frames, "Fact check: passed / not passed", the finish in plain words.
  - **Select** ("Use it in the film"). If a check failed, you must say why it is right all the same.
  - **Reject** ("I will ask you what is wrong with it"). **Take the effect away**: made again without the finish. All free.
- **A question of the assistant**: its own words, two to four answers as buttons, with the cost where one applies.
- Between items: "Nothing is needed from you now." or "Your answer is needed."

## 5. The checks before the operator sees a picture

- **The program (no AI):** size and shape; made from the right parent; light and fine detail close to the footage; a component's clear background.
- **Gemini 3.8 Flash:** each line of the picture's list (exact words read letter for letter, their place, sizes, the material's pattern, what the shot claims), plus three fixed lines: no other readable text, no real face from the footage, nothing extra.
- **Claude:** checks each label on the picture before asking. For a drawn graphic, the fresh checker helper is the fact check.
- **On a failure:** the picture is marked and its lines are shown. Nothing is remade by itself. A fix is made only on request, and is paid. You may still approve.
- A picture is not offered while its check is running.

## 6. Rules and instructions

**Rules the server enforces**

- One decision at a time; a reply to any other item is refused.
- A picture is made for one shot and is listed, checked and placed only there.
- A rejected picture, a fix, or a derived picture is never the parent of another.
- Words in a picture go only through the exact-text list.
- A graphic with exact sizes or numbers that is not drawn is refused.
- A graphic or a picture with words moves by push-in or not at all; never cropped or panned.
- A drawn graphic without a clean fact check is held until you give a reason.
- No paid call beyond the film's cost limit.

**Instructions the assistant follows**

- Tell the cost of a paid picture; do not ask.
- Post only the server's question and its buttons, in their order; never answer for the operator.
- Stop and ask at any fork; never guess.
- One change per edit; after a rejection start from an approved picture.
- Show all states of a sequence together.
- Never ask the operator to choose effects.

## 7. What is not proven or not built yet

- Step 6 is not on the decisions page; the page screens for stills and graphics are planned, not built.
- The chat questions for pictures, specs and stills were written without tests and "never run" at release (design note 188); a real film is the test.
- The drawn route became the default before a production film used it end to end (design note 130). Hindi and Tamil fonts on the server: not confirmed.
- "A still follows the shot-drawing steps without the guide" (design note 200) is approved but not built: a still gets no shot drawing.
- The program-decision audit (16 Nov) counts 139 program decisions on stills and 143 on graphics. Marked wrong or poor there:
  - the size check fails every checked Gemini picture;
  - a check that crashes leaves the picture "checking" for ever, never shown;
  - a picture with no list gets no check at all;
  - a Gemini failure is reported in OpenAI's name;
  - a Gemini picture is only 16:9 or 9:16;
  - the fix repairs only the first failed line;
  - a missing style sheet or unapproved spec is only warned on a picture.

## 8. Where this comes from

- Instructions: `server/procedures/v3.json` (visuals: common sections B, D, E; part "later", sections 5, 6, 8, 9, 11), `plugin/commands/vw.md`.
- Skills and helpers of step 6: `plugin/skills/motion`, `plugin/agents/vw-motion-rules.md`, `vw-motion-shot.md`, `vw-motion-check.md`. (Step 7: `skills/guide`, `vw-guide-scene`, `vw-guide-check`. Steps 3 to 5: `skills/drawing`, `vw-drawing`, `vw-reference-finder`, `vw-set-look`.)
- Server: `server/app/visuals_stage.py` (`generate_image`, `_queue_image`, `waiting`, `approve_reference`, `reject_reference`, `sequence`, `approve_spec`, `motion_brief`, `render_motion`, `motion_verdict`, `motion_finish`), `image_check.py`, `visual_workers.py`, `chat_flow.py` (`_waiting_items`, `SAYS`), `config.py`, `film.py`.
- Design notes: 86, 111, 113, 117, 120, 130, 186, 188, 200, 207, 209, 210.
- Audit: `design/_work/system-decisions/3-table-for-sk.md` (rows 1043 to 1066, 1182 to 1194).
