# Visuals steps 1 and 2: SK's review points, each answered, with the change proposed

**Status:** analysis and proposal, 16 Nov 2026. **Nothing is built. Waiting for SK's approval.**

**What was read:** the guide explained line by line (`videobuilder-v4/guides/visuals-steps-1-2-explained-line-by-line.md`, all 495 lines), the note `requirement-ai-video-any-kind-of-shot.md` (whole), the guide page on claude.ai (by a subagent), and the code and instruction text behind every rule below (three subagents; I checked their main findings in the code myself: the dead warning, the circling refusal, the one-fault-per-scene check, the reuse approval, the photo-of-a-person switch).

**Deploy state:** nothing is pending. The plan page (design/206) is live as server 0.103.0 and `main` equals the live commit. The next deploy carries only what is approved from this list.

**How to read each point:** your point; what the tool does today; my answer; the change proposed; its size; and whether it needs a decision from you.

---

## Three corrections to the guide itself

Found while checking; they change some answers below.

1. **The plan is on the page now.** The guide says the plan is answered on a card in the chat. Since this morning (0.103.0) it is answered on the artifact page.
2. **"AI video: three kinds" is not refused at the plan.** The plan check accepts a moving AI scene with no kind named. The refusal comes later, when the scene's guide is written (step 7). So a lorry accepted at the treatment also passes the plan and is thrown out only at step 7, which is later and costlier than the guide says.
3. **One warning in the guide never fires.** "The only change in this video is a look or an expression" is dead code: it sits inside a block for AI video shots and tests that the shot is not an AI video. It has not fired since 12 Nov.

---

## 1. Show the operator the world of the film

**Today.** The assistant writes the shared rules at the start of the plan: the look, the world (place, period, people, work, clothes, tools), what is not shown, the graphic style, and the list of every person, place, object and material. The operator never sees them whole. They see only a list of differences, and only when the rules change after gaps were accepted.

**Answer.** Agreed, and it is small. The plan page can show it as its first block, read only.

**Change.**
- A first block on the plan page, "The world of this film", with no buttons: the look; each world rule; what is not shown; the graphic style; then each person, place, thing and material with its description and known sizes.
- The Direction is left out of it (already accepted at step 1).
- The same rows are available to the chat card (one flow, two front ends).
- Server only. The page file already draws such a block, so no plugin release. Not yet seen in a browser.

**Size:** small. **Decision:** none now. Editing by the operator stays a later decision, as you said.

---

## 2. The plan check goes back and forth

**Today.** It is partly avoidable, and nothing in place avoids it.
- **The check does not report everything at once.** It reports the first fault of each scene, not every fault. A scene with three faults needs three rounds. Some checks (a place with no signs of use, a returning shot with nothing said to differ) come one at a time, only after everything else passes.
- **Two refusals come only at the proposal**, after a clean check: the Direction not copied word for word, and a way the treatment did not name. VW-24 hit the first.
- **The helpers have a checklist** of eleven points, but it leaves out shot sizes and everything about materials. The main assistant, who writes the shared rules and the list of things alone, has no checklist at all. "A material with no size" came from that part.
- **No check runs on the laptop.** Each round is a trip to the server.

**Answer.** A checklist helps, but the bigger gain is the check telling everything in one answer.

**Change.**
1. The check reports one fault per shot (not per scene), and collects the later checks too. One round then lists nearly everything.
2. The two proposal refusals are reported by the check as well.
3. The Direction is placed into the plan by the server (see point 14f), so that refusal cannot happen.
4. A short checklist for the part the main assistant writes alone (materials, a person's description, a place's signs of use, sizes confirmed), and the helper's checklist gains shot sizes (point 11).

**Size:** small to medium, server and one plugin text file. **Decision:** none.

**Not verified:** which four messages VW-24 actually received; I read the code, not that run's log.

---

## 3. People stay the same: time changes other than "a year later"

**Today.** The code already allows it. A change of clothes needs a field saying what time passed, and the code only tests that the field is filled. Only the wording forbids it: the instruction says "the script's words" and "identical for a person across scenes".

**Answer.** Agreed. Morning and evening, another day, another season are all real reasons. One caution: the viewer must still know it is the same person, so the face, build and hair never change; only the clothes do.

**Proposed rule.**
> A person keeps the same clothes within one continuous time. When the time changes (later the same day, another day, another season, years later), the clothes may change. The plan says what changed in time, from the script or from the scene's own time. The person's face, build and hair stay the same throughout. Two different people in the same scene are not dressed in the same colours, unless a uniform is the point.

**Size:** words only (one message, two instruction sentences). **Decision:** none.

**Known limit:** a person's fixed description today includes the *types* of garment; only colours are per scene. A change of garment type (a shirt to a sari) contradicts that description. I will move garment types to the per-scene clothes in the wording. No new field.

---

## 4. A real speaker is real: remove it

**Today.** When the assistant marks a person as a real speaker, every shot of them must be real footage, and any AI picture of them is refused (two places in the code, one sentence).

**Answer.** The refusal can go. But removing it alone does not give you what you want, for two reasons:

- **Their face cannot reach the picture AI today.** Three other rules stop it: a person's reference is made from words only; an uploaded photo of a person is switched off (your own open point of 11 Nov, "not ruled yet"); and the page has the same switch. So after the removal the AI picture would show a *different-looking* person beside their real footage.
- **AI takes are silent.** A take has no sound, and lips will not match the voice. "Make them talk" is not possible on today's route. They can be shown, in a new angle or doing something, not speaking in sync.

**Change proposed.**
- Remove the two refusals and the sentence.
- Allow a real person's own photo or footage frame as the reference for their AI pictures **when the operator records the person's consent in their own words**, once per person.
- Keep: no AI scene may pretend to be the client's own site, people or measured result without that consent.

**Size:** medium (the switch, a consent record, the page). It adds one answer per real person. **Decision needed:** yes. This is your open point of 11 Nov.

---

## 5. Materials have sizes: the water question

**Today.** The instruction tells the assistant to file every material the film relies on as a "material". A later rule made "material" mean "built from identical units", so every material must give unit sizes, how it is laid and its pattern. Water was filed as a material and was asked for its unit size. (This is my reading of the code; VW-24's own log was not read.)

**Answer.** You are right that the question was wrong, not the idea. A thing laid in units needs unit sizes. A liquid or a loose material needs how much, or how much of the surface it covers.

**Proposed rule.**
> A material laid as repeating units (bricks, tiles, planks, pavers) carries its unit sizes with their source, how it is laid and its pattern. A liquid or a loose material (water, sand, mortar, paint) carries none of that: the plan says how much is used, or how much of the surface it covers, and that is shown in the shot.

**Change.** One condition in the check, one sentence in the instructions and the helper's brief. No new field: the amount goes where facts about how a thing looks already go.

**Size:** small. **Decision:** none.

**Guard:** a brick filed with no sizes would then pass silently, and brick patterns were why the rule exists. So the assistant gets a note (not the operator) when a material has neither unit sizes nor an amount.

---

## 6. A size claim needs a size: a human for scale

**Today.**
- The plan check asks for a real measurement and a "thing in frame to compare against". Any thing is accepted; a person is not preferred.
- **The comparison then barely reaches the picture.** The sentence that tells the picture AI "size is the point, read it against X" is written on one older path only. A still's picture never gets it, and neither does the starting picture of an AI video.
- The trigger is a word match, so "big savings" also trips it.

**Answer.** Yes, and it belongs in both places: the plan names the comparison, and the prompt for every picture carries it. Your order is right: a person first; with no person, a thing whose size everyone knows.

**Proposed rule.**
> When size is the message, the picture shows the thing beside a person. With no person in the scene, it is shown beside a thing whose size is generally fixed (a door, a chair, a hand tool, a brick). The same sentence goes into the prompt of the still and of the AI video's starting picture.

**Change.** The message and the instruction name the order; the size sentence is added to still pictures and to the starting picture of AI video; a note to the assistant when a person is in the shot and the comparison is not the person.

**Size:** small. **Decision:** none.

**Limits:** never applied to reference pictures of a product alone (those must show no person). Adding a person to an AI video shot adds one to its people count.

---

## 7. People in a shot, and the word "crowd"

**Today.**
- At most **three** named background people per scene; more must be a "crowd" group described loosely (refused otherwise).
- At most **four** people in one AI video shot (refused: "a crowd is not yet available").
- The word "crowd" appears in a check line and can reach a prompt through the group's name. The consultant's register already says to keep crowd words out of prompts.
- A named person needs only a written description. A character sheet (three pictures, about ₹35) is made in the reference round and judged by the operator.

**Answer.** Your practice fits the tool with **no new step**. People are already described one by one, and sheets are already made in the reference round. What changes is the limit and the wording.

**Change proposed.**
1. Up to **ten** people may be named in a scene, each with their own description.
2. People beyond those are still described **one by one** (one trait each), never as a loose group. The loose "varied crowd" way is retired by name.
3. The word "crowd" is removed from the check line and from what the assistant is told to write.
4. The same applies to still pictures.
5. Sheets only for people who come back or are seen at medium distance or closer. The rest are carried by their written description.

**Cost and effort:** each sheeted person is about ₹35 and one more judgement in the reference round. Ten sheets is about ₹350 and ten judgements. So it is not a new step, but it is more answers when many people are sheeted. Point 5 keeps that down.

**Limits you should know:**
- One picture request takes a limited number of reference pictures: about six sheeted people (five on Gemini). Beyond that a person rides on their words.
- In an AI video shot, each named person needs a place in the guide, and two moving people who overlap on screen are still refused there.

**Size:** medium. **Decision needed:** yes, on the sheet rule in point 5 (who gets a sheet).

---

## 8. No circling camera: remove

**Today.** A camera move that reads as circling a person is refused at the plan.

**Change.** Remove the refusal, its word list and its test. It also had false hits ("a circle of bricks").

**Honest limit:** removing the refusal lets the shot be planned. It does not yet make a true circling shot: the guide that the take is made from has one fixed camera position. Until that changes, a circling shot will be planned but shot from a fixed camera.

**Size:** small. **Decision:** none (you asked for it).

---

## 9. No picture twice

**Today.** Four different things sit under this one line:

| # | What | Today |
|---|---|---|
| A | The same person appears again | **Allowed.** No code refuses it. Only the instruction's wording reads stricter |
| B | The identical picture file in two shots | Refused. The assistant fixes it; the operator is not asked |
| C | The same footage clip shown again | Needs the assistant's reason, what else it considered, a different stretch or crop, at least 60 s apart, **and then the operator's approval in their own words** |
| D | Two placed pictures that are nearly the same file | A warning told to the operator ("looks like another one in the film") |

**Answer.** Agreed on all three of your points:
- the same character appearing again is normal;
- the same person in the same place in the same picture must not repeat, unless the script keeps the place (a workshop where the part is made);
- the operator should not be asked.

**Proposed rule.**
> The same person may appear as often as the film needs. The same person in the same place, in the same clothes and the same framing, is not shown twice: the second showing differs in angle, distance or moment. When the script itself stays in one place (a workplace), the place may stay the same and the framing changes. The identical picture is never used in two shots.

**Change.**
- A: reword the instruction (no code).
- B: stays as it is.
- C: the operator's approval is dropped. The assistant's reason is kept on record ("the script stays in this workshop"). The other checks stay.
- D: handled by the assistant, not told to the operator.
- New, for the assistant only: a note when a later shot has the same person, clothes, place and framing as an earlier one with nothing said to differ. It compares the plan's words, so it is a rough test.

**Size:** small to medium. **Decision needed:** yes. Dropping the approval in C reverses your decision of 23 Oct (made after VW-6 repeated pictures). I recommend it, since the checks stay and the reason is recorded.

**Open detail:** the "60 s apart" test refuses any reuse in a film shorter than about a minute. I propose it becomes "60 s, or a quarter of the film if that is shorter".

---

## 10. A drawing of a real object

**Today.**
- The view (cutaway, plan, side, elevation) and its reason are required; refused without.
- A size the voice states cannot be left unknown in the drawing.
- The words "illustrative, not to scale" are required when any size is unknown, and the assistant must first show it tried four sources before a drawing may be called illustrative.
- Nothing in the instructions mentions drawing to the conventions of a field. The server cannot tell whether a drawing follows a standard.

**Answer.** Your rule is simpler and fits how drawings are made now. The one thing a program can check is "is every size known"; "drawn to an industry standard" is Claude's own judgement, so it has to be an instruction plus a label.

**Proposed rule.**
> A drawing of a real object is drawn to the convention of its field (a plan, a section or an elevation; dimension lines with units) and to scale. If it is not drawn to scale, or any size in it is unknown, it carries the words "not to scale" and shows no figure for the unknown size. A size the voice states is always shown as stated.

**Change.**
- Keep: the label refused when a size is unknown; a stated size never unknown.
- Drop: the four-sources test before a drawing may be illustrative.
- The view and its reason: a note to the assistant instead of a refusal.
- One sentence added to the drawing instructions.

**Size:** small. **Decision:** none.

---

## 11. "Opens close in" and "three shots at the same size"

**Today.** All three framing warnings are worked out **inside one scene only**. None looks at the gap before. So you are right: the writer can prevent every one of them.

**Why they still happen.**
1. The helper's checklist never mentions shot sizes.
2. The instruction states it as a consequence ("warned unless…") deep in a long text, not as something to do.
3. Every gap starts a new scene. A gap of one or two shots cannot spend a shot on a wide opener, and the check does not remember that the gap before, or the footage beside it, already showed the place. Those are false alarms.

**Change.**
1. The helper's checklist and the instruction say it as a rule: a scene's first camera shot is wide or medium-wide; never a third shot in a row at one size; a close-up only after its subject was seen wider; when the place was already shown just before, say so.
2. The three warnings go to the assistant only. It fixes them at the check; the operator no longer reads them.
3. The check remembers a place already shown in the gap before, when both name the same place. This removes the false alarms.

**Size:** small. **Decision:** none, unless you want to keep seeing these three.

---

## 12. "The only change is a look or an expression"

**Today.** It never fires (dead code, see the corrections). Its instruction says the opposite of what you want: "prefer a profile or a back view".

**Change.**
- Delete the warning.
- Replace the instruction with your rule: **when a shot is about a look or an expression, frame it close, with the face in frame.**
- A note to the assistant when such a shot is framed wide.

**Limit:** a close face is where a person's likeness drifts most, so the person's face picture must be among the references for that shot. The rule will say so.

**Size:** small. **Decision:** none.

---

## 13. A rule for the world: everyday things, not overdone, right for the period

**Today.**
- The world is a list of short rules in the plan (place, period, people, work, clothes, tools). There is no separate field for period; it is one of the world's topics.
- "Props fit the work and the region" is an instruction only.
- "A place shows its use" is checked (two signs of use, or the place is refused).
- The picture prompt library pulls the other way in three lines: every object must earn its place; anything the brief lacks is named as absent.
- The consultant's register has this exact idea as an untested learning, marked "waits for SK's ruling" (wires, birds, a passer-by).

**Answer.** This is that ruling. It needs no new machinery: two lines in the world, one rule for each picture, and one note to the assistant.

**Proposed rule.**
> **Ask of the world.** Before any place is pictured, ask: for this place and this time, what would a viewer expect to see that the script does not name? Write it once in the film's world, as exact kinds: "concrete electric poles with overhead wires along the road", "an Indian street dog", "house sparrows". Write once what the period forbids: "set in 1850: nothing electric, no plastic, no motor vehicle".
>
> **Use it lightly.** A picture takes at most one or two of these. A living extra (a dog, a cat, a bird) is named by its exact kind with its size, so it stays the same size each time. Not in every shot. Not the same extra in two shots in a row, unless it carries on from the shot before. Never several kinds of animal in one shot.
>
> **Fixed things belong to the place.** Poles, wires, signs and street furniture are part of the place and stay where they are in every picture of it.

**Change.**
- Two sentences in the plan instructions (the world; the per-picture use).
- The library's three lines get the exception stated, so the two do not fight.
- A note to the assistant when the same living extra is in two shots in a row with nothing saying it carries on.

**Limits.**
- **Stills and starting pictures first.** An AI video shot says "exactly N people, no one else", and its guide has no place for an animal. A moving animal in an AI video is not in this change.
- **No sheet for a living extra.** Otherwise each dog or bird enters the reference round (about ₹35 and one judgement). I propose they are carried by words: exact kind and size.

**Size:** small. **Decision needed:** yes, on "no sheet for a living extra".

---

## 14. Part Three: what the first step hands to the second

You asked whether the "not carried" and "partly" lines have a reason. Each was checked:

| Line | True? | Why it is so | Fix proposed |
|---|---|---|---|
| The way and seconds of each shot | True | Built as first specified (which ways, not how much of each). Seconds per shot came later and the check was never extended. No decision against it | A warning when a gap has more still seconds than the operator accepted |
| Stills at most a tenth | True | Built for the treatment only (15 Nov); never built for the plan | The same warning worked out again at the plan, in the same plain sentence |
| The two reasons of each shot | True | Left for later on purpose (design/202: "could be carried into each plan shot later") | The plan page shows, under each gap, the shots and reasons accepted at the treatment. Per shot would need a new link between the two; per gap needs none |
| Footage first, else AI video, else a still | True | Never written into the plan's instructions | One sentence, where two ways are offered |
| Words on the picture, by category | True | The two rules were built at different times and never joined | A warning when a card of words is planned in a documentary or an explaining film |
| The Direction copied by hand | True | A deliberate check; placing it by the server was never considered | The server places the Direction at the head of the plan. The refusal cannot happen |
| One instruction contradicts the page | True, in two places | The older sentence was never retired: "decides everything here in the chat, never on a page: do not give a page link" | Reword both; it now contradicts the plan page too |
| Building-site wording | True | Examples were written from the first films | Reword each example for every kind of film (nine instruction sentences and six server messages listed in the working notes) |

None of these was a decision to keep things apart. All were built at different times and never joined.

---

## 15. Part Four: the suggested fixes, brought into the change

Every fix in Part Four is in the table above or in points 2 and 16. Sizes:

- **Small, no new step, no new operator answer:** the split of ways flagged; the still warning at the plan; a card of words flagged; the Direction placed by the server; the contradicting sentence; the building-site wording.
- **Small in the form proposed:** the accepted reasons shown per gap.
- **Not small:** the kinds of AI video (point 16).

---

## 16. Part Five

### 16a. "AI video is narrow": any kind of shot

The note `requirement-ai-video-any-kind-of-shot.md` is right in its four places, and nothing in it is built yet. Checking it against the code found more that it must change, and one real limit:

| Found | Meaning |
|---|---|
| More than three background people in a scene is refused | Changed by point 7 |
| A person moving faster than 2.5 m/s is refused ("a run is not yet available") | Must become a warning too; the note lists a run as allowed |
| Two people who overlap on screen while one moves are refused | Must become a warning too; the note lists crossing as allowed |
| Circling: the note makes it a warning | You now want it removed (point 8) |
| **A thing cannot travel in the guide** | The guide that a take is made from can place people, and things that turn in place. It cannot describe a vehicle driving, or items moving along a conveyor |

**The last row matters most.** Opening the door at the plan is not enough. For a machine, a vehicle or a landscape, the take is still made from a guide of boxes that cannot draw the movement. So either that shot is refused again at step 7, or it needs a second way of making a take: from a starting picture and words, with no guide.

**Proposal.**
1. Build the note as written, with the three additions above (run, crossing, three background people). Untried kinds warn; nothing is refused for "no evidence".
2. **Try before building the second way.** One trial on this PC: a machine-only shot and a vehicle shot, each made from a starting picture and words with no guide. If they hold, the second way is written up as its own requirement.

Generic by design: nothing here names a kind of film.

**Size:** step 1 medium; step 2 is a trial, then its own change. **Decision needed:** yes, on the trial.

### 16b. The cost limit by length

**Today.** One figure, ₹5,000 for every film, in the server's settings and also typed into the instructions. No command can change it for one film (the old one was removed). The plan page shows no cost; the treatment page does.

**What a film costs** (from the server's default prices: ₹8.9 a second of AI video, ₹11.79 a picture on Gemini, ₹35 a reference set). Each cell: the server's estimate / a plausible total with 30 % retakes and reference sets.

| Film | Light: 10 % AI video, 10 % stills | Medium: 30 %, 15 % | Heavy: 60 %, 15 % |
|---|---|---|---|
| 1 min | ₹85 / ₹600 | ₹229 / ₹770 | ₹432 / ₹1,020 |
| 2 min | ₹170 / ₹840 | ₹458 / ₹1,190 | ₹864 / ₹1,690 |
| 3 min | ₹256 / ₹1,080 | ₹688 / ₹1,610 | ₹1,296 / ₹2,360 |
| 5 min | ₹426 / ₹1,570 | ₹1,146 / ₹2,450 | ₹2,159 / ₹3,700 |
| 10 min | ₹852 / ₹2,780 | ₹2,292 / ₹4,540 | ₹4,318 / ₹7,050 |

Assumptions: AI video shots of 5 s, one take each in the estimate; stills of 4 s; reference sets guessed at 10 plus 4 per minute; graphics and footage cost nothing. The reference-set guess is the weakest and weighs most on short films. The live prices on the VM may differ from these defaults; they were not read. Real figures on record: VW-12's treatment estimate ₹936 for 186 s; VW-11 about ₹1,750 for 196 s of AI video before pictures.

**Reading it:** ₹5,000 is far more than a short film needs and not enough for a heavy 10-minute one.

**Change proposed.**
- The limit is worked out per film: **a rupee amount per minute, with a lowest figure.** Both are settings.
- You can set a different limit for one film, with your words (a small owner-only command).
- The figure is taken out of the instruction text; the server already tells it.
- The plan page shows the plan's estimate beside the limit, as the treatment page does.

**Size:** small. **Decision needed:** yes: the rupees per minute and the lowest figure. From the table, ₹750 a minute with a lowest figure of ₹1,500 covers the heavy mix at every length shown (10 min: ₹7,500).

---

## Decisions needed from SK

| # | Decision | My recommendation |
|---|---|---|
| D1 | A real person's own photo may be the reference for their AI pictures, when the operator records their consent (point 4) | Yes |
| D2 | A footage reuse no longer waits for the operator's approval; the assistant's reason is recorded (point 9) | Yes |
| D3 | Up to ten named people; a sheet only for those who return or are seen medium or closer (point 7) | Yes |
| D4 | A living extra (dog, bird) is carried by words, with no sheet (point 13) | Yes |
| D5 | A trial of AI video made from a starting picture and words, with no guide, before building that way (point 16a) | Yes |
| D6 | The cost limit: rupees per minute and the lowest figure (point 16b) | ₹750 a minute, lowest ₹1,500 |
| D7 | The three framing warnings go to the assistant only (point 11) | Yes |

## How it would be built

- **One set, one deploy, no new operator step:** points 1, 2, 3, 5, 6, 8, 10, 11, 12, 13, 14, 15, 16b, and step 1 of 16a.
- **After your decisions:** points 4, 7, 9.
- **Its own later change:** the second way of making a take (16a step 2), after the trial.
- Tests first for each. The instruction wording goes through a wording script, with the word count updated. Each retired way gets its row in the decision log (design/35).
- Server and plugin both change (the helper's checklist is in the plugin), so every laptop updates after the deploy.

## Not covered

- Editing the world of the film by the operator (decided later).
- A moving animal in an AI video shot; a true circling camera; sound and lip sync on takes.
- The other findings of the eight-stage odd-rules review (taken up separately, as you said).
- The reference steps on the artifact page (your first question there is still open).
- Nothing here was run against a real plan. The VW-24 explanations (the water, the four rounds) are read from the code, not from that run's log.
