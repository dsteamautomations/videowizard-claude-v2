# 33 — Fix list before the code freeze (for SK's approval, 17 Oct 2026)

Scope: fix the **patterns** behind VW-2's 14 tickets, not only the tickets, then review and freeze. SK runs the test rounds. Each fix still gets its own fast checks, as the working rules require; I do not run the long suites. Another thread is bringing the system online in the same code folder.

## A. Close what is open
| # | Fix | Why | Edge cases and handling | Effort |
|---|---|---|---|---|
| A1 | **Visuals instructions rewritten for v2** (ticket 11). Remove the v1 sections: local-asset packages, `scripts/local_assets.py`, editable text layers, Codex. Describe v2's real commands. Text graphics and titles are the editor's files (`vw visuals asset`). | The assistant followed v1 instructions v2 cannot carry out | Keep the creative guidance (treatment, continuity, shots and beats); only the machinery changes. A check fails if the text names a command `vw` does not have. | ~1 day |
| A2 | **The plan check refuses a text graphic on a video shot**, with the reason: text is the editor's work, put it in the shot notes | Stops ticket 11 recurring | A whole-graphic shot (diagram, animation, image) stays allowed, filled with a file | 1 h |
| A3 | **`vw visuals bind --selector ELEMENT=REF:what`** for an object inside a place image | The server supports it; `vw` could not send it | A malformed selector is refused with the expected shape | 1 h |
| A4 | **Voice and intake instructions:** remove v1's "application" voice screen and the Codex mentions; you listen to files `vw` downloads | Same cause as A1, smaller | Voice choices and auditions are unchanged | 2 h |
| A5 | **Test setup stall:** in tests, the server sometimes waits on a database connection and a `vw` command times out. It is not caused by recent code: the 15 Oct version fails the same way. | Your test rounds need a reliable suite | Find the cause; if it is this PC's Docker, give tests a connection time limit with a clear message | 2–3 h |

## B. Check limits before work starts (tickets 3, 4, 5, 6, 14)
| # | Fix | Edge cases and handling | Effort |
|---|---|---|---|
| B1 | **`vw preflight`**, also run automatically by `vw start` and before each paid or large step. It checks: storage reachable; the largest coming file against the storage limit; ElevenLabs characters left against the script; Gemini, OpenAI and video-generator keys work; FFmpeg on both machines; free disk for renders. | Supabase does not report its global upload limit to the service key, so the limit is a server setting (800 MB today), kept equal to Supabase's. An unreachable check is "unknown", not "pass". | ½ day |
| B2 | **Before narration:** refuse with numbers if ElevenLabs credit is below the script length (ticket 3) | Credit read fails → warn and proceed (the job still reports quota errors clearly) | 1 h |
| B3 | **Before uploading media or a film:** refuse a file above the storage limit with "raise the limit to at least X MB" | Film size is known only after render; the render keeps the film and says so instead of failing silently (ticket 14) | 1 h |

## C. No hidden failures (tickets 12, 14 and the silent render failure)
| # | Fix | Edge cases and handling | Effort |
|---|---|---|---|
| C1 | **Storage errors carry Supabase's own message.** "Payload too large" becomes "the file is X MB; the storage limit is lower; raise it". | Message absent → status code plus the request path | 1 h |
| C2 | **Every `vw` write waits up to 10 minutes,** and a timeout says "the server may still be working; check status before repeating". Reads keep 60 seconds. | A repeated write is safe: each request has an id and the server ignores duplicates | 1 h |
| C3 | **Failed background jobs are shown:** `vw next` and each stage's status list a failed job of the current stage with its error and what to do | Old failed jobs already superseded by a newer ready job are not shown | 2 h |

## D. Large files and scale (tickets 5, 6, 12, 14)
| # | Fix | Edge cases and handling | Effort |
|---|---|---|---|
| D1 | **Server uploads over 50 MB are resumable:** Supabase's chunked upload, 6 MB chunks, resumed after a dropped line | Smaller files keep the single upload. A chunk that keeps failing gives up with a clear error and keeps the local file. | ½ day |
| D2 | **Assembly prepare stops downloading every take:** use the duration recorded when each take was generated; download only files with no recorded duration | Mismatch between recorded and real duration is checked at render, as today | 1 h |
| D3 | Operator clip uploads keep the single upload with retries, plus the B3 size check | Clips are 20–40 MB; resumable from the operator side would need Supabase signed chunked uploads, which I would add only if a clip ever fails | — |

## E. Small, agreed
| # | Fix | Effort |
|---|---|---|
| E1 | **Generated takes are made silent when saved,** whatever the generator. The film never used their sound. | 1 h |
| E2 | Tell the operator, at `vw assembly fetch`, the film size and where it is if the upload failed | with C3 |

## F. Awaiting your yes: include in the freeze or leave for later?
| # | Item | Status |
|---|---|---|
| F1 | Contact sheets, so the assistant sees the film as stills (design/27) | You agreed in principle; the requirement list awaits your yes |
| F2 | Mason and helper look: match the real crew by clothing, build and tools; faces unclear unless the client consents (asked once per run) | My proposal, not yet approved |
| F3 | Step banner "Step 7 of 12 → next" (design/20) | Awaiting your yes |
| F4 | v1 editable text graphics (design/28) | Deferred by you; **outside** this freeze |

## Freeze procedure
1. Build A–E (and the F items you approve), each with its fast checks.
2. Review the whole change set once more, file by file, against this list.
3. Bump the server and plugin versions, tag the repository `v2.0.0-rc1`, and add a changelog entry to the walkthrough page.
4. Deploy to the live VM the way design/29 (UPDATES) says: tell SK first, push, pull the bundle on the VM, restart the services (running jobs finish first). Sync the plugin. **Never start the server or workers on the PC.**
5. From then on, only fixes for tickets you raise, each recorded against the ticket. No features.

## Coordination with the live-server thread
VideoWizard runs on the live VM since 16 Oct (design/29). Both threads work in the same code folder; I touch only the files these fixes need (storage, plugin, the visuals, voice and intake instructions, the stage modules, the tests). Updates reach the VM only as described in design/29, after SK's yes.

## Estimate
| Group | Time |
|---|---|
| A (close open work) | ~1.5 days |
| B (limits checked up front) | ~1 day |
| C (no hidden failures) | ~½ day |
| D (large files and scale) | ~1 day |
| E (small) | ~1 h |
| **Total** | **about 4 days**, plus any F items you add |
