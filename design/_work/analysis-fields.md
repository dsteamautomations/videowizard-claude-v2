# Every field the video analysis writes for a clip, and where it is used

13 Nov 2026, third version. The first version had mistakes; they are listed at the end. The third version closes the open points of the second. Nothing in the application was changed.

Read in full for this: the answer shape (`server/app/clip_log/schema.py`), the prompt (`prompt.py`), the arrival check (`gate.py`), the allowed-or-not rules (`solver.py`), the package (`stage2/package.py`), the options rule check (`stage2/validator.py`), how the analysis jobs run (`analysis.py`, `analysis_jobs.py`), the reading files (`plugin/scripts/vw.py`, lines 110 to 262), the package build in `stage2/stage.py` (lines 150 to 225). Also read in full: the client's library (`brandlib.py`) and the footage character (`footage.py`). Read in part: `visuals_stage.py` (where it takes the entities), the editor's package files.

The answer shape has 159 fields. A program listed them from the shape itself; every one is named below exactly as the model writes it.

## The words in the last column

| Word | What it means |
|---|---|
| Arrival check | The server checks it when the answer comes back. |
| Allowed or not | The server decides from it whether a piece may be used, and how it is cropped. No AI. |
| Short list | The few facts about a piece that Claude reads for every scene when it chooses clips. |
| Full row | Kept in the package for every piece. Claude sees it only when it asks for one piece. |
| Coverage report | The server's count of how many pieces fit each scene. |
| Rule check | The server's check of Claude's cut. The code in brackets is the rule. A refusal stops the cut; a flag is shown. |
| Library, Visuals stage, Editor's package, Footage character, Operator status | Used there. |
| Not used | No rule, check or list reads it. It stays in the clip's full log. |

**The short list holds only these:** the piece's name, the clip's name, "seen" (line 1 of the clip's ten-line card), how it fits the scene, grade, length, in and out frames and seconds, shot size, shot size after the crop, the action peak, the outcome state, pairing constraints, risk flags, allowed or not, and the shortest hold. A piece that only relates to a scene gets fewer: name, clip, "seen", fit, grade, length.

## A. About the whole clip

| Field | What it says | Where it is used |
|---|---|---|
| clip_id | Which clip the answer is about | Arrival check: a wrong value fails the answer |
| filename | The file's name | Arrival check: a wrong value fails the answer |
| descriptive_name | A short name for the clip | Arrival check (must not be empty); the clip's card; library; slides |
| tc_confidence | How sure the times are, for the whole clip | Not used |
| clip_overview | Two or three sentences on the whole clip | Library (kept as the clip's description, and shown when the clip is offered to a later film) |
| clip_overview_uncertainty | What in the overview is unsure | Not used |
| audio_observed | Silent, natural sound, speech, mixed | Not used |
| lighting_and_weather | The light and weather, in words | Full row, as a light class found by word match (hard sun, soft overcast, mixed interior); Rule check (G8, refusal: no cut from hard sun to overcast inside a scene) |
| exposure_health | Too bright, too dark, fine | Not used |
| contrast_profile | Flat, normal, high contrast | Footage character (flat counts as a "log" look) |
| color_match_group_id | Clips that could be colour-matched together | Not used. The server replaces it with its own colour measure |
| max_safe_zoom_limit | How far the picture may be zoomed | Allowed or not (the server takes its own limit, or this one if stricter); Visuals stage (crop limit for a reused frame) |
| entities.[].name | A person, tool, material or structure seen | Library (the names are kept with the clip); Visuals stage (matched by word to the things the plan needs) |
| entities.[].kind | Person, tool, material, machine, structure, vehicle, text, other | Visuals stage (a matching kind scores higher) |
| entities.[].first_seen_s | When first seen | Visuals stage (the second at which to look for the thing) |
| entities.[].last_seen_s | When last seen | Handed to the visuals stage inside the entity; no rule reads it |
| entities.[].description | What it looks like | Visuals stage (matched by word, and shown) |
| entities.[].basis | Seen, said, inferred, unsure | Handed to the visuals stage inside the entity; no rule reads it |
| entities.[].uncertainty | Doubts about it | Handed to the visuals stage inside the entity; no rule reads it |
| clip_level_notes_for_editor | Free notes that fit no other field | Not used |
| summary_card_lines | Ten lines that sum up the clip | Arrival check (must be ten); the clip's card; its OVERVIEW line is "seen" in the short list; library |
| unavailable_or_uncertain.[].field | A thing the model could not determine | Arrival check (a warning when the list is empty but speech or crop boxes are filled); Visuals stage (passed whole) |
| unavailable_or_uncertain.[].reason | Why not | The same |

The entities are kept in the stored package but left out of the files Claude reads.

## B. Each piece (sub-clip): the basics

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].sub_clip_id | The piece's name | Everywhere |
| sub_clips.[].tc_confidence | How sure the piece's times are | Full row; lowers the piece's confidence score; Coverage report (pieces under 0.6 are listed as low confidence) |
| sub_clips.[].client_safe | Safe for the client or not | Allowed or not (unsafe is removed unless every flag is waived); Rule check (G10, refusal) |
| sub_clips.[].risk_flags | Why it may be unsafe: no helmet, a logo, a child | Allowed or not (the operator may waive a flag); Short list; Rule check (G10); Operator status (a count) |
| sub_clips.[].ocr_text_on_screen | Words readable in the picture | Not used |
| sub_clips.[].usability_grade | A, B, C or REJECT | Allowed or not (REJECT removes the piece); Short list; Coverage report; Rule check (E3, refusal: a grade C piece needs a note) |
| sub_clips.[].shot_role | Process shot, detail, establishing, talking head | Full row |
| sub_clips.[].pairing_constraints | "Do not use with piece X" | Short list; Rule check (G4, refusal, only for entries that start MUTUALLY_EXCLUSIVE_WITH) |
| sub_clips.[].max_usable_window.in_tc | Start of the usable part, as timecode | Arrival check (must agree with seconds and frames) |
| sub_clips.[].max_usable_window.out_tc | End, as timecode | Arrival check |
| sub_clips.[].max_usable_window.in_s | Start, in seconds | Arrival check |
| sub_clips.[].max_usable_window.out_s | End, in seconds | Arrival check |
| sub_clips.[].max_usable_window.in_frame | Start, as a frame number | Arrival check (outside the clip throws the piece out); Short list; Rule check (G1, refusal) |
| sub_clips.[].max_usable_window.out_frame | End, as a frame number | The same |
| sub_clips.[].max_usable_window.duration_s | Length | Short list |
| sub_clips.[].max_usable_window.video_handle_frames_before | Spare picture frames before | Full row; Rule check (G9, refusal) |
| sub_clips.[].max_usable_window.video_handle_frames_after | Spare picture frames after | Full row |
| sub_clips.[].max_usable_window.audio_handle_frames_before | Spare sound before | Not used |
| sub_clips.[].max_usable_window.audio_handle_frames_after | Spare sound after | Not used |
| sub_clips.[].must_include_action_peak | The one to three seconds that must survive a trim (may be empty) | Short list; Rule check (G2, refusal) |
| sub_clips.[].must_include_action_peak.in_s | Its start | Short list, as a frame; Rule check (G2) |
| sub_clips.[].must_include_action_peak.out_s | Its end | The same |
| sub_clips.[].must_include_action_peak.in_tc | Its start, as timecode | Not used |
| sub_clips.[].must_include_action_peak.out_tc | Its end, as timecode | Not used |
| sub_clips.[].must_include_action_peak.duration_s | Its length | Not used |
| sub_clips.[].camera_moves.[].start_s | When a pan, tilt or shake starts | Full row; Rule check (G2 move, a flag) |
| sub_clips.[].camera_moves.[].end_s | When it ends | Full row |
| sub_clips.[].camera_moves.[].kind | Pan, tilt, whip, push in, pull out, shake | Full row; Rule check (G2 move) |
| sub_clips.[].hero_frame_tc | The best single frame, as timecode | Not used |
| sub_clips.[].hero_frame_s | The same, in seconds | Not used |
| sub_clips.[].hero_frame_index | The same, as a frame number | Not used |
| sub_clips.[].action_completeness | Complete, still going, cut off, static | Full row |
| sub_clips.[].visual_action_observed | What happens in this piece, in plain words | **Not used.** Not in the short list and not in the full row |
| sub_clips.[].visual_action_uncertainty | What in that description is a guess | Lowers the confidence score |
| sub_clips.[].why_sliced_here | Why the piece starts and ends where it does | Not used |
| sub_clips.[].editorial_ideas | How an editor could use the piece | Kept in the stored row; left out of the files Claude reads; I found nothing that reads it |
| sub_clips.[].sub_clip_uncertainty | Doubts about the piece as a whole | Lowers the confidence score |

## C. People and speech

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].people_and_speaker_analysis.people_count | How many people | Not used |
| sub_clips.[].people_and_speaker_analysis.people_roles | Their roles | Not used |
| sub_clips.[].people_and_speaker_analysis.audio_nature | Silent, natural sound, speech on or off camera | Not used |
| sub_clips.[].people_and_speaker_analysis.mouth_visible | Can lips be seen | Allowed or not |
| sub_clips.[].people_and_speaker_analysis.looking_at_lens | Does someone look at the camera | Allowed or not |
| sub_clips.[].people_and_speaker_analysis.uncertainty | Doubts about the people | Lowers the confidence score |
| sub_clips.[].people_and_speaker_analysis.speech_translation_block | The speech block; empty when no speech | Allowed or not (a person counts as talking when they look at the camera, or lips show and speech is heard); Full row ("speech: yes or no"); Arrival check (a warning if speech is reported though the sound was removed) |
| …speech_translation_block.speaker_id | A label for the speaker | Not used |
| …speech_translation_block.spoken_language | The language heard | Operator status (the footage languages) |
| …speech_translation_block.speaker_role | The subject, the crew, the background | Not used |
| …speech_translation_block.verbatim_transcript | The words spoken, with times | Not used |
| …speech_translation_block.english_translation | The words in English | Not used |
| …speech_translation_block.transcription_status | Clear, partial, unintelligible | Not used |
| …speech_translation_block.extracted_domain_facts.[].fact | A fact someone says | Not used |
| …speech_translation_block.extracted_domain_facts.[].basis | Seen, said, inferred, unsure | Not used |
| …speech_translation_block.extracted_domain_facts.[].matches_visual_on_screen | Does the picture show that fact | Full row ("a spoken fact matches the picture") |
| …speech_translation_block.extracted_domain_facts.[].visual_evidence_s | When the picture shows it | Not used |
| …speech_translation_block.extracted_domain_facts.[].limits | How far the fact holds | Not used |
| …speech_translation_block.soundbite_grade | A usable quote or not | Not used |
| sub_clips.[].people_and_speaker_analysis.speaker_crop_module | The crop block; empty when nobody is seen talking | Allowed or not (a person seen talking with no boxes: the picture is refused, the sound kept) |
| …speaker_crop_module.speaker_head_mouth_box | Where the speaker's head is | Allowed or not (the crop that hides the speaker) |
| …speaker_crop_module.speaker_full_body_box | Where the speaker's body is | Allowed or not |
| …speaker_crop_module.must_preserve_action_box | What must stay in the picture | Allowed or not |
| …speaker_crop_module.sharp_in_crop_zone | Is the cropped area sharp | Allowed or not |
| …speaker_crop_module.active_speech_tc_range | When the speech runs | Not used |
| …speaker_crop_module.active_speech_tc_range.in_tc | Its start | Not used |
| …speaker_crop_module.active_speech_tc_range.out_tc | Its end | Not used |
| …speaker_crop_module.settle_buffer_applied_in_tc | The half-second safety gap applied | Not used |
| …speaker_crop_module.speaker_moves_during_subclip | Does the speaker move | Not used |
| …speaker_crop_module.suggested_split_s | Where to split the piece | Not used |
| …speaker_crop_module.limits | How rough the boxes are | Not used |

## D. Camera

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].camera_and_optics.native_shot_size | Wide, medium, close | Allowed or not (the size after a crop); Short list; Rule check (G5: two same sizes in a row is a flag, three is a refusal); Library |
| sub_clips.[].camera_and_optics.camera_angle | Eye level, high, low, overhead | Not used |
| sub_clips.[].camera_and_optics.lens_feel | Wide, standard, long lens | Not used |
| sub_clips.[].camera_and_optics.movement_type | Static, pan, handheld, gimbal | Footage character |
| sub_clips.[].camera_and_optics.movement_direction | Which way the camera moves | Not used |
| sub_clips.[].camera_and_optics.movement_speed | How fast | Not used |
| sub_clips.[].camera_and_optics.movement_easing | How smoothly | Not used |
| sub_clips.[].camera_and_optics.has_3d_parallax | Is there depth movement | Allowed or not (may the last frame be held as a still); Rule check (G16, refusal) |
| sub_clips.[].camera_and_optics.has_internal_scene_motion | Does anything move in the picture | The same |
| sub_clips.[].camera_and_optics.subject_screen_direction | Which way the subject moves or faces | Full row; Rule check (G7, refusal: direction must not flip) |
| sub_clips.[].camera_and_optics.depth_of_field | Shallow or deep focus | Not used |
| sub_clips.[].camera_and_optics.leading_lines | Lines in the picture | Not used |
| sub_clips.[].camera_and_optics.uncertainty | Doubts about the camera fields | Lowers the confidence score |

## E. Pace and flow

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].pacing_and_flow.entry_eye_grid | Where the eye is at the start | Full row; Rule check (G6, a flag) |
| sub_clips.[].pacing_and_flow.exit_eye_grid | Where the eye is at the end | The same |
| sub_clips.[].pacing_and_flow.kinetic_energy_score | How much movement, 1 to 10 | Full row; Rule check (R4, shown as information only) |
| sub_clips.[].pacing_and_flow.min_comprehension_hold_s | The shortest time needed to understand the piece | Short list; Coverage report; Rule check (G3, refusal; R5, a flag) |
| sub_clips.[].pacing_and_flow.time_manipulation_options | Slow motion, speed change, hold the last frame | The server removes slow motion under 50 frames a second. Nothing reads it after that |
| sub_clips.[].pacing_and_flow.natural_cut_points.[].tc | A good moment to cut, as timecode | Arrival check |
| sub_clips.[].pacing_and_flow.natural_cut_points.[].s | The same, in seconds | Full row |
| sub_clips.[].pacing_and_flow.natural_cut_points.[].frame | The same, as a frame | Arrival check; Full row; Rule check (R1, information only) |
| sub_clips.[].pacing_and_flow.natural_cut_points.[].description | What happens there | Not used |
| sub_clips.[].pacing_and_flow.accent_events.[].tc | An impact in picture or sound, as timecode | Arrival check |
| sub_clips.[].pacing_and_flow.accent_events.[].s | The same, in seconds | Full row |
| sub_clips.[].pacing_and_flow.accent_events.[].frame | The same, as a frame | Arrival check; Full row; Rule check (R1, information only; B2, a flag) |
| sub_clips.[].pacing_and_flow.accent_events.[].description | What the impact is | Not used |
| sub_clips.[].pacing_and_flow.text_safe_zone | Where a title can sit (may be empty) | Not used |
| sub_clips.[].pacing_and_flow.text_safe_zone.grid | Which part of the picture | Not used |
| sub_clips.[].pacing_and_flow.text_safe_zone.valid_in_tc | From when | Not used |
| sub_clips.[].pacing_and_flow.text_safe_zone.valid_out_tc | Until when | Not used |
| sub_clips.[].pacing_and_flow.text_safe_zone.contrast | White or dark text | Not used |

## F. Story and script fit

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].continuity_and_story.primary_fit_for_beats | Paragraphs this piece shows exactly | Decides under which scenes the piece is listed for Claude, as "direct"; Coverage report |
| sub_clips.[].continuity_and_story.secondary_fit_for_beats | Paragraphs it relates to | The same, as "related" |
| sub_clips.[].continuity_and_story.beat_fit_reasoning | Why it fits | Not used |
| sub_clips.[].continuity_and_story.beat_fit_basis | Seen, said, inferred | Full row |
| sub_clips.[].continuity_and_story.beat_fit_limits | What the paragraph says that the piece does not show | Full row; lowers the confidence score |
| sub_clips.[].continuity_and_story.process_stage | Which chapter of the film it belongs to | Full row; lists the piece under scenes of that chapter; Rule check (N17 stage, information only); Editor's package (a keyword) |
| sub_clips.[].continuity_and_story.prerequisite_action | What must have happened before | Not used |
| sub_clips.[].continuity_and_story.outcome_state | What the action leaves behind | Short list |
| sub_clips.[].continuity_and_story.world_landmarks_and_props | Things seen, under one fixed name each | Full row; Rule check (R8, information only; N14, a flag); Visuals stage |
| sub_clips.[].continuity_and_story.marketing_value_tag | Scale, process, quality, people, technology, result | Not used |
| sub_clips.[].continuity_and_story.mood_tag | Calm, industrial, energetic, warm, clinical | Not used |

## G. Sound

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].in_s | Start of a stretch of clean natural sound | Full row; Rule check (Q6, refusal: kept sound must lie inside such a stretch; B3, a flag) |
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].out_s | Its end | The same |
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].description | What the sound is | Full row |
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].in_tc | Start, as timecode | Not used |
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].out_tc | End, as timecode | Not used |
| sub_clips.[].audio_and_sfx_plan.clean_nat_sound_intervals.[].duration_s | Length | Not used |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].sfx_type | A sound effect an editor could add | Editor's package (a marker "SFX to source") |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].start_tc | Where it starts | Editor's package |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].description | What it is | Editor's package |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].target_track | Which sound track | Not used |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].end_tc | Where it ends | Not used |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].duration_s | Its length | Not used |
| sub_clips.[].audio_and_sfx_plan.creative_sfx_cues.[].resolved_sfx_file | Always "a person must find it" | Not used |

The sound-effect cues are kept in the stored row but left out of the files Claude reads.

## H. Technical quality

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].technical_qc_and_remediation.defects_detected.[].defect | Focus hunting, exposure pumping, a bump, other | Not used |
| sub_clips.[].technical_qc_and_remediation.defects_detected.[].in_tc | From when | Not used |
| sub_clips.[].technical_qc_and_remediation.defects_detected.[].out_tc | Until when | Not used |
| sub_clips.[].technical_qc_and_remediation.defects_detected.[].description | What it is | Not used |
| sub_clips.[].technical_qc_and_remediation.stabilization_needed | Is the piece shaky | Allowed or not (adds to the zoom); Full row; the finishing list and the stabilise choice at assembly; Footage character |
| sub_clips.[].technical_qc_and_remediation.horizon_rotation_deg | How far the horizon is tilted | Allowed or not (adds to the zoom); Full row; the finishing list; Editor's package (the rotation value) |
| sub_clips.[].technical_qc_and_remediation.voice_isolation_recommended | Would voice cleaning help | Not used |
| sub_clips.[].technical_qc_and_remediation.dual_mono_channel_fix | Is one sound channel missing | Not used |
| sub_clips.[].technical_qc_and_remediation.uncertainty | Doubts about these fields | Not used |

## I. Ideas for graphics

| Field | What it says | Where it is used |
|---|---|---|
| sub_clips.[].vfx_and_graphics_opportunities.[].type | A label, an arrow, a zoom, a slow motion | Not used |
| sub_clips.[].vfx_and_graphics_opportunities.[].in_tc | From when | Not used |
| sub_clips.[].vfx_and_graphics_opportunities.[].out_tc | Until when | Not used |
| sub_clips.[].vfx_and_graphics_opportunities.[].what_and_why | What it would show, and why | Not used |

## What the server adds itself, with no AI

These are not written by the model. The server works them out from the fields above and puts them in each piece's row.

| Added value | Worked out from |
|---|---|
| Allowed or not (five answers: as it is, with a crop, as a speaker, sound only, rejected) | Grade, safety, the speaker test, the crop boxes, the film's speaker policy |
| The crop, zoom and position | The three boxes, the zoom limit, the tilt, the shake |
| Shot size after the crop | The shot size and the zoom |
| May the last frame be held as a still | The two movement fields |
| The confidence score | The time confidence and five doubt fields |
| The colour group | The server's own measure of the clip's colours |
| The light class | Words in `lighting_and_weather` |
| How the piece fits each scene: direct, chapter, related | The paragraph fit, the chapter, and the approved scenes |

## What this shows

- A small set of fields decides a film today: the usable window, the grade, the safety flags, the speaker test and boxes, the shot size, the action peak, the shortest hold, the cut points, and the paragraph fit.
- Claude reads a short list for each piece. The piece's own description (`visual_action_observed`) is not in it and not in the full row. Claude reads the whole clip's one-line overview, once per clip.
- Much is written for every clip and read by nothing: the spoken words and their translation, the editor's notes, the reason for each cut, the best frame, where a title can sit, the ideas for graphics, the defects found.
- The script fit is by paragraph.

## Mistakes in the first version, now corrected

1. **Colour group.** I wrote that the model's `color_match_group_id` is used by the rule check and the editor's package. It is not. The server replaces it with its own measure.
2. **"Placer's table" was one thing; it is two.** Many fields I said Claude sees are only in the full row, which Claude reads on request. The short list is much smaller. The tables now say which.
3. **`editorial_ideas`.** I repeated a note in the code that it is used at assembly. I found nothing that reads it.
4. **`time_manipulation_options`.** I wrote "allowed or not". The server only removes slow motion from it; nothing reads it afterwards.
5. **Entities.** I wrote that two parts are not used. The entities are passed whole to the visuals stage.
6. **Twenty fields were described in words** (for example "the three boxes") and not by name. All 159 are now named, and a program confirmed each has its own row.

## What a library clip brings to a later film

Read from `brandlib.py` in full.

- After the analysis, every analysed clip of a film is stored for the client, with a short description: its name, its ten-line card, its overview and the names of the things seen. The operator marks which clips would be true in any film of this client.
- When a later film uploads the same clip, the server notices before any paid request and asks once: analyse again, or skip. Skipped is free.
- A skipped or marked clip is offered later, in the library round of the options stage. Its old log is checked again by the server for this film: allowed or not, and the crop. No paid request.
- **Its script fit is wiped.** The code says "its beat fits named another film". So a library clip comes with no word on which lines of this film it fits. Claude matches it from the description alone.
- What Claude is given for a library piece: its name, length, in and out, shot size, allowed or not, the things seen, the overview, the card.

## Closed after the second version

| Open point | What I found |
|---|---|
| Which parts of an entity the visuals stage reads | Name, description, kind and first-seen time are read. Last-seen time, basis and doubts are handed over inside the entity and read by no rule. |
| How often Claude opens a clip's full log | Never, in the three latest runs. The server's request lines show no download of any clip's full log in VW-21 (45 clips analysed, 7 footage choices, 21 still-frame requests, 1 paid inspect), VW-22 (1 clip analysed, 45 skipped as library repeats) or VW-23 (94 clips analysed, 6 footage choices, 35 still-frame requests). So in those runs the unused fields were read by nobody. |
| The library file in full | Read. See the section above. |
| The footage character file in full | Read. It takes three fields only: `movement_type`, `stabilization_needed`, `contrast_profile`. |

## Not checked

- The editor's package files in full (`delivery.py`, `timeline.py`, `assembly.py`). I read the lines that touch these fields. They come after the stages this review is about.
- Whether Claude, in VW-23, asked for the full row of single pieces. That request is answered from the package on the operator's computer, so the server does not see it.
