# design/138: questions on every assumed value, with the builder's suggested answers (2 Nov 2026)

One question per row of `design/138-silent-defaults.md`. Each has the answer the builder would choose, with one line why. Write yours after "SK:"; a blank means the suggestion stands.

## Group A: probably faults

**A1. When a film is vertical, should its AI videos be vertical too?**
Suggested: **Yes, every take follows the film's shape.** Today every take is horizontal because the tool never sends the shape.
SK (2 Nov, in chat): **The film's shape is decided from the footage, then the AI videos follow it.**
1. Once the clips are listed and analysed, count the vertical and horizontal clips and recommend the shape most clips have; the operator decides. Offer, for example, "a fully horizontal film, the vertical clips used as they are where they come up".
2. Then ask about the AI videos: recommended, the film's shape ("there is no use in making AI videos horizontal" in a vertical film). The operator may still choose otherwise: no restriction, trusting a skilled operator.
3. The two questions come one after the other: the film's shape first, then the AI videos.
4. **Parked, as a reminder:** a horizontal film from which the operator wants several short vertical videos cut. Not designed yet.

**A2. Should the cut and the footage analysis follow the film's shape and frame rate, instead of always widescreen at 25 frames a second?**
Suggested: **Yes.** The shape comes from the brief; the frame rate from the client's footage (most clips share one); if clips disagree, the operator is asked once.
SK (2 Nov): **From the footage.** The rate most clips share; if they disagree, asked once together with the film's shape (A1).

**A3. The brief offers four shapes (horizontal, vertical, square, 4:5), but only two are made. Which do we support?**
Suggested: **Offer only horizontal and vertical for now**, and refuse the other two by name. Adding square and 4:5 means new picture sizes, a new cut layout and new video settings; worth doing when a client asks.
SK (2 Nov): **Only horizontal and vertical now. Square and 4:5 are kept for a future update** (parked, like A1's vertical shorts from a horizontal film).

**A4. On the voices page, should the voice model and its settings be shown, as the chat tool shows them?**
Suggested: **Yes, shown and changeable**, with today's model and settings as the starting values.
SK (2 Nov, after the details in design/138-a4-voice-settings.md): **Eleven v4 only. Show and allow editing every setting v4 takes**; v2 and v3 and their settings are not offered. v4 takes two: stability and similarity (both shown with their plain effect, today's 0.5 and 0.75 as the start; a change is heard by re-reading the test passage). The narration uses the settings of the audition the operator chose (the fault found).

**A5. Should diagrams use the client's own colours for highlights, instead of a fixed yellow?**
Suggested: **Yes: the strongest brand colour from the client card; yellow only when the card has no colours.**
SK (2 Nov): **The assistant chooses the highlight colour for each drawing so it stands out and does not clash with the background or anything else in the frame.** Brand colours are used where given or found; if none, the operator is asked once: "What colours would you prefer to use?" Used wisely: a preferred colour is never forced where it would not stand out.

**A6. If no scene split was approved, should the cut go ahead with one scene per paragraph?**
Suggested: **No: the cut is refused until the operator approves a scene split.** The instructions already propose one; the server should not invent it.
SK (2 Nov): **Refuse until approved.**

**A7. If the brief does not say the language spoken, should the analysis assume English?**
Suggested: **No: the brief asks for the narration language and the language spoken in the footage**, and the analysis refuses to start without them.
SK (2 Nov): **Never assume English; detect the language from the material.**
- **Footage:** the Gemini analysis already transcribes each clip's sound; it reports the languages spoken (the main one first, and one or two others when the speech is mixed), instead of being told "English".
- **Narration:** read from the narration text itself (the script sent to ElevenLabs), which may be Hindi, Tamil or another language.
- Today no one speaks on camera in the films, so the footage language matters less for now; it is still detected, not assumed.

**A8. The tool's own note still says the older drawing method is the default. Fix it?**
Suggested: **Yes, correct the note.** It is wording only; new films already use the new method.
SK (2 Nov): **Correct the note.**

## Group B: your earlier decisions

**B1. Drawn shots made with the new drawing method unless a film is started with the older one: keep?**
Suggested: **Keep.** It won the blind test on 1 Nov.
SK: (2 Nov) **Keep.**

**B2. Is the ₹5,000 visual spending limit per film meant to be on or off?**
Suggested: **On, but shown at the start of the visuals stage with the estimate**, so the operator knows it before the first picture. Our notes say it was removed on 28 Oct, yet the code still applies it; the live setting needs checking either way.
SK: (2 Nov) **On, shown at the start of the visuals stage with the estimate.**

**B3. The prices behind the spending figures (₹4 a picture, ₹8.90 a video second, ₹88 to the dollar) are the builder's estimates. Should you set the real ones?**
Suggested: **Yes: you give the real figures once; they go in the server's settings.** Until then every estimate is a guess.
SK: (2 Nov) **Keep the builder's estimates** for now.

**B4. One video model (Gemini Omni), takes at 720p: keep?**
Suggested: **Keep the model; review 720p** once the first finished film is watched at full size: 720p takes in a 1080p film may look soft.
SK: (2 Nov) **Keep; review 720p later**, once a finished film is watched at full size.

**B5. Stills and graphics push in slowly (5 %) unless the plan says otherwise: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep as is.** (The push-in applies to still pictures and AI-painted graphics, never to drawn motion graphics.)

**B6. An 8-frame dissolve where a graphic meets other shots, a cut elsewhere: keep?**
Suggested: **Keep.**
SK: (2 Nov) **The plan must always decide** the joins; no fixed dissolve rule.

**B7. A video made from its start picture alone, unless its last moment must be exact: keep?**
Suggested: **Keep.** It saves a picture, a check and an approval per shot.
SK: (2 Nov) **Keep.**

**B8. Pexels as the stock-picture source: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**B9. After three review rounds, the assistant suggests turning failing scenes into AI passages, and asks: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**B10. Camera copies left out of the editor's download unless asked: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**B11. The footage analysis starts without asking and listens to the clips' sound: keep?**
Suggested: **Keep**, as long as the operator was asked about camera sound at the media step (they are).
SK: (2 Nov) **Keep.**

**B12. Instruction version 3 for every new film: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

## Group C: silent defaults

**C1. Should a film end with a sales call to action?**
Suggested: **Decided by the category: an advertisement or product film asks the operator; other categories have none.**
SK: (2 Nov) **Keep none**: no call to action unless the operator brings it up (every category).

**C2. If the operator does not say the film's shape, should it be horizontal?**
Suggested: **No: the brief asks the shape** (with A3's two choices). Shape is too important to assume.
SK: (2 Nov) **Settled by A1**: the shape is recommended from the footage and the operator decides; never assumed.

**C3. A 0.8-second pause after each paragraph of the narration: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C4. The voice model and settings when none are given: keep today's?**
Suggested: **Keep, and show them** (see A4).
SK: (2 Nov) **Settled by A4**: Eleven v4, settings shown and editable.

**C5. A clip over 15 seconds gets the dearer, deeper analysis: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C6. An AI passage is at least 3 seconds; over 12 seconds, and a real shot over 4 seconds, are flagged as long: keep?**
Suggested: **Keep.**
SK: (2 Nov) SK's limits: an AI video (Google, Seedance) needs at least 3 s to generate; at worst 3 s is made and cut to 2 s; 1 s is a single picture. Explainer and drawn graphics can be 1 to 2 s. Longest take: 10 s (Gemini Omni; 30 s is the ceiling for any model today, unused). Approved changes:
1. No minimum on a blank (the 3 s refusal at `stage2/validator.py:10` goes).
2. An AI video shot is at least 2 s on screen (made at 3 s and trimmed, as today); under 2 s is refused with "use a single picture".
3. Drawn and explainer graphics: no minimum.
4. Longest take 10 s: kept (Omni is the only video model).
5. Both 12 s warnings removed (`stage2/validator.py:11` long blank, `visual_contract.py:502` AI run).
6. The 4 s long-real-shot warning removed (`stage2/validator.py:19`).

**C7. Pictures always at high quality: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C8. One candidate per picture, two only when asked: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C9. Gemini pictures at 2K: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C10. The exact picture model inside the chosen picture AI is fixed by the server: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C11. A picture requested without a kind is treated as a start picture. Keep?**
Suggested: **No: refused until the kind is named.** A wrong kind gets the wrong checks.
SK: (2 Nov) **Refused until the kind is named.**

**C12. A shot under 4 seconds with no visible action becomes a moving still: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C13. No camera move named means a steady camera on a tripod: keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C14. The framing rule given to the AI is the rule of thirds. Should it depend on the category?**
Suggested: **Yes: rule of thirds in general; an advertisement or product film may centre the product.**
SK: (2 Nov) **By category**: rule of thirds in general; an advertisement or product film may centre the product (the category from design/137).

**C15. A graphic with no kind named is a diagram; a section drawing is a cutaway. Keep?**
Suggested: **Keep.**
SK: (2 Nov) **Keep.**

**C16. Diagrams use Noto Sans when there is no brand font. Should the brand font be used when the client card has one?**
Suggested: **Yes: the brand font from the client card; Noto Sans only when there is none.**
SK: (2 Nov) **The operator is asked for the font once per film, with Noto Sans as the recommended reference** ("Noto Sans, or a font of the same quality"), so a poor-quality font is not chosen. Noto Sans also stays where the chosen font cannot draw the script.

**C17. One reference-picture round per film: keep?**
Suggested: **Keep.**
SK:

**C18. A reused clip is not cropped when the analysis gave no limit: keep?**
Suggested: **Keep.**
SK:

**C19. When the client card is empty, the picture requests say industry "other" and audience "general". Keep?**
Suggested: **No: read them from the client card and the brief; if still empty, the brief asks once.**
SK:

**C20. Frames a second fall back to 25 when a film has none recorded. Keep?**
Suggested: **No: taken from the footage** (see A2).
SK:

**C21. Each video starts at its beginning; a long one is trimmed, a short one holds its last frame (listed to the operator at assembly): keep?**
Suggested: **Keep.**
SK:

**C22. A shaky clip is left as it is. Keep?**
Suggested: **No: when the analysis flags a clip as shaky, the operator is asked: steady it, or leave it.**
SK:

**C23. A picture fills the frame by enlarging up to 1.35 times, then keeps bars: keep?**
Suggested: **Keep.**
SK:

**C24. Narration loudness, peak level, camera-sound level and fades are fixed. Should they follow where the film is shown?**
Suggested: **Keep today's levels for now**; a platform's own loudness becomes a choice when a film is made for one (the brief already names destinations).
SK:

**C25. The film title is empty until chosen: keep?**
Suggested: **Keep.**
SK:

## Group D: found while answering

**D1. When a clip has no camera maker saved and an unfamiliar file name, should the system guess "phone"?**
Today `footage.py` guesses "phone" for any ordinary-quality recording (8-bit, under 50 Mbit/s), so many regular cameras are called phones. The Gemini analysis has no camera field; the camera is read from the file's own details.
SK (2 Nov, after seeing "mobile videos matched" on a film): **Say "not known".** No guess; the footage line says the camera is not known and nothing downstream assumes a phone. The operator can still correct it.
