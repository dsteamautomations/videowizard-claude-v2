# design/138: every value the process assumes when nobody chose it (2 Nov 2026, for SK's decisions)

SK, 2 Nov 2026: "Is there anything that we are assuming as default as of now in the whole process? Bring that out. I'll tell you what to do with them."

A read of the server, the tool and the instructions found 52 places where a film gets a value nobody chose: 34 silent (nothing tells the operator), 12 told (the operator is shown it but not asked), 6 asked. The full table, with every file and line, is in `design/138-silent-defaults/table.md`. Four of the claims were re-checked in the code and hold. Pure technical fallbacks (timeouts, retries, sizes of uploads) are left out.

For each row, SK's call is one of: **ask** (the operator chooses, like the category), **read** (take it from the film's own material: the brief, the client card, the script), **keep** (a sound default, said to the operator), **fix** (a fault: it should already follow the film).

## A. Probably faults: the film's own choice is ignored

| # | What happens today | Why it matters | Suggested | SK |
|---|---|---|---|---|
| A1 | **Every AI video take is horizontal (16:9)**, even when the brief says vertical (9:16): the tool never sends the frame, and the server's own default wins | a vertical film gets horizontal videos | fix: the take follows the brief's frame | |
| A2 | **The cut and the analysis are always 1920 × 1080 at 25 frames a second**; the brief's frame is never read there | a vertical, square or 4:5 film is cut horizontal | fix: the timeline follows the brief's frame | |
| A3 | **A square or 4:5 film gets horizontal pictures**: only horizontal and vertical sizes exist | the brief offers four shapes; two are not made | fix: add the two sizes, or offer only the two shapes we make | |
| A4 | **Voices page:** every audition and narration uses one voice model and fixed settings, and the page never shows them (the chat tool tells them) | the voice is chosen without the operator seeing how | keep, but show the model and settings on the page | |
| A5 | **The highlight colour in drawn scenes is a fixed yellow**, never the client's colours | graphics clash with the brand | read: from the brand palette, yellow only when there is none | |
| A6 | **When no scene split is approved, the cut uses one scene per paragraph** without telling the operator | scene boundaries decide the whole cut | ask (the instructions already propose it; the server should refuse without it) | |
| A7 | **The analysis assumes English** for the field speech and the narration when the brief leaves them empty | a Tamil field recording is read as English | ask at the brief, or read from the script | |
| A8 | **Older films with no drawing method recorded are drawn the old way**, and the tool's own note still says the old way is the default | confusion only; the server's new default wins for new films | fix the note | |

## B. Already your decisions (listed so they are not taken for accidents)

| # | Default | Your decision |
|---|---|---|
| B1 | Drawn shots made with HyperFrames unless the film is started with the older way | design/130 (1 Nov) |
| B2 | ₹5,000 visual spending limit per film, raised only on your word | design/66 (21 Oct). **Check:** our notes say the limit was removed on 28 Oct, but the code still applies it; the live setting may differ. Is it on or off? |
| B3 | The prices the limit counts (₹4 a picture, ₹8.90 a video second, ₹88 to the dollar) are the builder's estimates | design/120; never set by you |
| B4 | One video model (Gemini Omni), takes at 720p | design/124 |
| B5 | Stills and graphics push in slowly (5 %) unless the plan says otherwise | design/89 (23 Oct) |
| B6 | An 8-frame dissolve where a graphic meets other shots, a cut elsewhere | design/91 (23 Oct) |
| B7 | A take from the start image alone, unless the shot's end must be exact | design/112 |
| B8 | Pexels as the stock-picture source | design/121 (29 Oct) |
| B9 | After three review rounds, the assistant suggests turning failing scenes into AI passages, and asks | agreed 16 Oct |
| B10 | Camera copies left out of the editor's download | design/115 |
| B11 | The footage analysis starts without asking and listens to the clips' sound | design/42, design/125 |
| B12 | Instruction version 3 for new films | design/35 |

## C. Silent defaults with no decision on record

| # | Stage | What is assumed | Value | Suggested | SK |
|---|---|---|---|---|---|
| C1 | brief | The film ends with no sales call to action | none | read: from the category (an advertisement may want one) | |
| C2 | brief | The frame shape, when the operator does not say | horizontal 16:9 | ask with the brief (it is shown today, not asked) | |
| C3 | voice | The pause after each paragraph | 0.8 s | keep | |
| C4 | voice | The voice model and settings when none are given | Eleven v4; 0.5 / 0.75 | keep (see A4) | |
| C5 | analysis | A clip over 15 s gets the dearer, deeper analysis | 15 s | keep | |
| C6 | options | A blank AI passage is at least 3 s; 12 s and 4 s flagged as long | 3 / 12 / 4 s | keep | |
| C7 | visuals | Picture quality | always high | keep (it is the system's rule) | |
| C8 | visuals | One candidate per picture | 1 | keep | |
| C9 | visuals | Gemini picture size | 2K | keep | |
| C10 | visuals | The exact picture model inside the chosen picture AI | fixed per picture AI | keep | |
| C11 | visuals | A picture with no kind named is a start image | keyframe | fix: refuse without a kind | |
| C12 | visuals | A shot under 4 s with no visible action becomes a moving still | moving still | keep | |
| C13 | visuals | No camera move named means a steady camera on a tripod | locked off | keep | |
| C14 | visuals | Framing rule given to the AI | rule of thirds | read: by category (an advertisement often centres the product) | |
| C15 | visuals | A graphic with no kind is a diagram; a section drawing is a cutaway | diagram; cutaway | keep | |
| C16 | visuals | The font of drawn shots without a brand font | Noto Sans | read: the brand font when the client card has one; else keep | |
| C17 | visuals | One reference-picture round per film | one | keep | |
| C18 | visuals | A reused clip is not cropped when the analysis gave no limit | no crop | keep | |
| C19 | visuals | Picture-request fields when the client card is empty | industry "other", audience "general", logo none, no required text | read: from the client card and brief; ask when empty | |
| C20 | visuals / assembly | Frames a second, when the film has none recorded | 25 | fix: from the footage (A2) | |
| C21 | assembly | Each take starts at its beginning; a long one is trimmed, a short one holds its last frame | offset 0, trim / hold | keep (it is listed to the operator) | |
| C22 | assembly | A shaky clip is left as it is | leave | ask when a clip is flagged shaky | |
| C23 | assembly | A picture fills the frame by enlarging up to 1.35 ×, then keeps bars | 1.35 × | keep | |
| C24 | assembly | Narration loudness, peak ceiling, camera-sound level, fades | −16 LUFS, −3 dBTP, −27 dBFS, 4 frames | read: by where the film plays (a platform's own loudness) | |
| C25 | start | The film title is empty until chosen | empty | keep | |

Not defaults (for contrast): the picture AI is required at the start; camera sound is asked at media; the category will be read from the script and confirmed (design/137).
