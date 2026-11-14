# VW-23 before design/193: the baseline for the comparison

14 Nov 2026. Read from the live database, nothing changed.

| | |
|---|---|
| Film | VW-23, 94 clips |
| Clip study | Gemini 3.8 Flash, 13 Nov (plain way for clips of 15 seconds or less, look-again above); fit by paragraph |
| First cut | Proposed 13 Nov 11:02 UTC by the operator's assistant, after nine refusals of the check; review film rendered 11:05 |
| Operator's answers | Recorded 14 Nov, about 06:40 UTC, on the review page |
| Slides answered | 41 |
| Kept | 36 |
| Rejected | 5: slides 3.2, 5.7, 8.2, 8.4, 9.1 |
| Trimmed | 0 |

Where the old records are:
- The cut: `stage2/options-v1.json`; the review film: `stage2/review-v1-33a31026.mp4`. Both names carry their version, so a new cut does not overwrite them. The options output row (id `8462abfd-6212-46c4-a22f-f824ab4e2e0c`) is marked replaced when the analysis is redone, not deleted.
- The answers: the run's log, stage `master`, lines "slide N, decision KEEP or REJECT".
- The Flash logs and the old list (`analysis/*.json`, `stage2/package.json`, `stage2/session.json`) have fixed names and would be overwritten. They are to be copied to `kept-before-193/` on the VM before the redo. **Not done yet on 14 Nov: the Google Cloud sign-in on this computer had expired.**

The split of the 41 slides into footage shots, alternatives and blanks is not counted here; it is read from the cut when the comparison is made.
