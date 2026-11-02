# design/138: questions on every assumed value, with the builder's suggested answers (2 Nov 2026)

One question per row of `design/138-silent-defaults.md`. Each has the answer the builder would choose, with one line why. Write yours after "SK:"; a blank means the suggestion stands.

## Group A: probably faults

**A1. When a film is vertical, should its AI videos be vertical too?**
Suggested: **Yes, every take follows the film's shape.** Today every take is horizontal because the tool never sends the shape.
SK:

**A2. Should the cut and the footage analysis follow the film's shape and frame rate, instead of always widescreen at 25 frames a second?**
Suggested: **Yes.** The shape comes from the brief; the frame rate from the client's footage (most clips share one); if clips disagree, the operator is asked once.
SK:

**A3. The brief offers four shapes (horizontal, vertical, square, 4:5), but only two are made. Which do we support?**
Suggested: **Offer only horizontal and vertical for now**, and refuse the other two by name. Adding square and 4:5 means new picture sizes, a new cut layout and new video settings; worth doing when a client asks.
SK:

**A4. On the voices page, should the voice model and its settings be shown, as the chat tool shows them?**
Suggested: **Yes, shown and changeable**, with today's model and settings as the starting values.
SK:

**A5. Should diagrams use the client's own colours for highlights, instead of a fixed yellow?**
Suggested: **Yes: the strongest brand colour from the client card; yellow only when the card has no colours.**
SK:

**A6. If no scene split was approved, should the cut go ahead with one scene per paragraph?**
Suggested: **No: the cut is refused until the operator approves a scene split.** The instructions already propose one; the server should not invent it.
SK:

**A7. If the brief does not say the language spoken, should the analysis assume English?**
Suggested: **No: the brief asks for the narration language and the language spoken in the footage**, and the analysis refuses to start without them.
SK:

**A8. The tool's own note still says the older drawing method is the default. Fix it?**
Suggested: **Yes, correct the note.** It is wording only; new films already use the new method.
SK:

## Group B: your earlier decisions

**B1. Drawn shots made with the new drawing method unless a film is started with the older one: keep?**
Suggested: **Keep.** It won the blind test on 1 Nov.
SK:

**B2. Is the ₹5,000 visual spending limit per film meant to be on or off?**
Suggested: **On, but shown at the start of the visuals stage with the estimate**, so the operator knows it before the first picture. Our notes say it was removed on 28 Oct, yet the code still applies it; the live setting needs checking either way.
SK:

**B3. The prices behind the spending figures (₹4 a picture, ₹8.90 a video second, ₹88 to the dollar) are the builder's estimates. Should you set the real ones?**
Suggested: **Yes: you give the real figures once; they go in the server's settings.** Until then every estimate is a guess.
SK:

**B4. One video model (Gemini Omni), takes at 720p: keep?**
Suggested: **Keep the model; review 720p** once the first finished film is watched at full size: 720p takes in a 1080p film may look soft.
SK:

**B5. Stills and graphics push in slowly (5 %) unless the plan says otherwise: keep?**
Suggested: **Keep.**
SK:

**B6. An 8-frame dissolve where a graphic meets other shots, a cut elsewhere: keep?**
Suggested: **Keep.**
SK:

**B7. A video made from its start picture alone, unless its last moment must be exact: keep?**
Suggested: **Keep.** It saves a picture, a check and an approval per shot.
SK:

**B8. Pexels as the stock-picture source: keep?**
Suggested: **Keep.**
SK:

**B9. After three review rounds, the assistant suggests turning failing scenes into AI passages, and asks: keep?**
Suggested: **Keep.**
SK:

**B10. Camera copies left out of the editor's download unless asked: keep?**
Suggested: **Keep.**
SK:

**B11. The footage analysis starts without asking and listens to the clips' sound: keep?**
Suggested: **Keep**, as long as the operator was asked about camera sound at the media step (they are).
SK:

**B12. Instruction version 3 for every new film: keep?**
Suggested: **Keep.**
SK:

## Group C: silent defaults

**C1. Should a film end with a sales call to action?**
Suggested: **Decided by the category: an advertisement or product film asks the operator; other categories have none.**
SK:

**C2. If the operator does not say the film's shape, should it be horizontal?**
Suggested: **No: the brief asks the shape** (with A3's two choices). Shape is too important to assume.
SK:

**C3. A 0.8-second pause after each paragraph of the narration: keep?**
Suggested: **Keep.**
SK:

**C4. The voice model and settings when none are given: keep today's?**
Suggested: **Keep, and show them** (see A4).
SK:

**C5. A clip over 15 seconds gets the dearer, deeper analysis: keep?**
Suggested: **Keep.**
SK:

**C6. An AI passage is at least 3 seconds; over 12 seconds, and a real shot over 4 seconds, are flagged as long: keep?**
Suggested: **Keep.**
SK:

**C7. Pictures always at high quality: keep?**
Suggested: **Keep.**
SK:

**C8. One candidate per picture, two only when asked: keep?**
Suggested: **Keep.**
SK:

**C9. Gemini pictures at 2K: keep?**
Suggested: **Keep.**
SK:

**C10. The exact picture model inside the chosen picture AI is fixed by the server: keep?**
Suggested: **Keep.**
SK:

**C11. A picture requested without a kind is treated as a start picture. Keep?**
Suggested: **No: refused until the kind is named.** A wrong kind gets the wrong checks.
SK:

**C12. A shot under 4 seconds with no visible action becomes a moving still: keep?**
Suggested: **Keep.**
SK:

**C13. No camera move named means a steady camera on a tripod: keep?**
Suggested: **Keep.**
SK:

**C14. The framing rule given to the AI is the rule of thirds. Should it depend on the category?**
Suggested: **Yes: rule of thirds in general; an advertisement or product film may centre the product.**
SK:

**C15. A graphic with no kind named is a diagram; a section drawing is a cutaway. Keep?**
Suggested: **Keep.**
SK:

**C16. Diagrams use Noto Sans when there is no brand font. Should the brand font be used when the client card has one?**
Suggested: **Yes: the brand font from the client card; Noto Sans only when there is none.**
SK:

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
