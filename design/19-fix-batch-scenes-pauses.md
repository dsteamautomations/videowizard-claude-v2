# 19 — Fix batch: scene beats, narration pauses, word-timed rules, small fixes (approved 15 Oct 2026, implemented)

Date 15 Oct 2026. VW-2 is paused at options. Nothing in this batch makes a paid call or re-records the narration.

## Decisions taken in chat (15 Oct)
- Pauses go **between sentences only**, never inside a sentence. Used where a step of an activity should finish on screen before the next is spoken. (SK wrote "in between the sentence"; read as between sentences, consistent with "only at the end of a sentence".)
- No forced default breath at scene changes. Future voiceovers will carry their own gaps (the assistant will shape them at the voice stage); this build adapts to whatever gaps the recording already has. Extra pauses are added where the assistant asks for them.
- The PPE waiver for VK Nardep stays.

## A. Scenes and pauses (needed to resume VW-2)
| # | What | How |
|---|---|---|
| A1 | Scene beats on the existing narration | The assistant proposes scene boundaries as "scene n starts at word W…", each at a sentence start, plus which brief process stage each scene covers. The server checks the words are the accepted script's, in order, contiguous, each boundary at a sentence start, and rebuilds the beats from the timing file. Script, voice and analysis records are untouched; nothing goes stale. |
| A2 | Pauses between sentences | Each pause: `after word W…` (must end a sentence), the total silence wanted in seconds, and a reason. Ceiling 4 s per pause. The recording's own gap at that point counts toward it: only the difference is inserted, so a voiceover that already breathes gets nothing extra. |
| A3 | One approval | Scenes and pauses are proposed together and approved with one quoted yes in chat, stored on the options stage. |
| A4 | Timeline | Each beat's length = its words + its inserted pauses, on whole frames. The options package, the validator's length check and the coverage report use these lengths. |
| A5 | Beat fits from scenes | A sub-clip's fit to a scene comes from its process stage via the approved scene → stage mapping (VW-2's logs only know BEAT_01). The assistant refines it from the cards and logs as it builds options. |
| A6 | Narration in the films | Review, master and assembly cut the narration only in the silence after a sentence-ending word, on a frame boundary, and insert silence there. The words themselves are never altered or re-recorded. Loudness rule unchanged. |
| A7 | Subtitles | One cue per sentence (was one per beat), shifted by every pause before it. |
| A8 | Resolve | The narration goes to A1 as pieces placed on whole frames, one per pause-separated stretch; the readback compares the pieces too. |
| A9 | Rule change recorded | design/17 C1 "narration is never cut" becomes "never re-recorded; cut only between sentences at approved pauses". |

## B. Word-timed editing rules (flags, not refusals)
| # | Rule | Check |
|---|---|---|
| B1 | Pre-roll | A beat's first shot starts on the beat boundary; a later shot that illustrates a phrase starts 6–12 frames before that phrase's first word. |
| B2 | Cut on the word | Where an option names the word that describes a shot's action, that word should fall within ±6 frames of the sub-clip's accent. |
| B3 | Let pauses breathe | During a pause of 1.2 s or more, the current shot holds or a sub-clip with clean natural sound plays; no cut to a new idea inside the pause. |

## C. Small fixes already on the list (design/18)
| # | Fix |
|---|---|
| C1 | Slate line 1 must state the option's real length and shot count (item 1). |
| C2 | Media upload three clips at a time, each with its own retry (item 2). |
| C3 | `vw analysis policy` waits up to 10 minutes and reports a timeout as "may still be applying, check status" (item 4). |
| C4 | Close defects 3–6 with their explanations (quota, ISP block, flaky line, my syntax error). |

Not in this batch: STATIC for short clips (item 3, needs the three-clip paid comparison first); shaping pauses at the voice stage with ElevenLabs tags (a voice-stage change; the narration text would then differ from the script text, which needs its own design).

## Self-review (what I checked and changed in this plan)
1. **Ambiguity resolved, not guessed:** "in between the sentence" vs "only at the end of a sentence" → between sentences; stated above for SK to correct.
2. **Adapts to future voiceovers:** pauses are specified as total silence wanted, so existing gaps are not doubled (A2). Without this, a voiceover with built-in breaths would get them twice.
3. **No silent stale outputs:** the scene split is stored on the options stage, not by revising the script; voice and analysis stay current and nothing paid re-runs (A1).
4. **Precision:** cuts only in silence after a sentence-ending word and on whole frames; this is the VW10 failure mode (fractional placement) avoided by construction (A6, A8).
5. **Approval stays with the operator:** one quoted yes for scenes and pauses together (A3), consistent with every other stage.
6. **Rules as flags:** B1–B3 measure craft, not correctness; making them refusals would block valid edits on judgement calls.
7. **Old runs unaffected:** a run without an approved scene split keeps one beat per script paragraph exactly as today; version 1 planning untouched.
8. **Tests first:** words-unchanged check, boundary at sentence start, pause after a sentence end only, ceiling, natural gap counted, frame-aligned cut points, review/master/assembly durations including pauses, SRT shift, Resolve pieces readback, the three flags, C1–C3; then the stage 2 and 3 end-to-end tests with a scene split and two pauses.

## Effort
About one working day including tests: A ≈ 5–6 h, B ≈ 1.5 h, C ≈ 1.5 h. VW-2 resumes after A; B and C can land before or just after.
