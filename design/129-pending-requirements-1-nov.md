# Pending and parked requirements, 1 Nov 2026

From the VW-12 review (design/126) and this session's defect work, 30 Oct – 1 Nov. Live today: server 0.77.9, plugin 0.64.4, main 1a417ab.
Everything deployed since 30 Oct is **not** listed: defects 35, 37, 38, 40, 41, 42, G2, the sweep W1–W13, design/128.

Mark the **SK** column (go / hold / drop) for each record you want taken up.

## A. Built, not deployed (branch `design126-build`, a727388: server 0.78.0, plugin 0.65.0)

Agreed on 30–31 Oct, built by three builders, never deployed. The branch was cut **before** every hotfix, so it must first be brought up to date with main (35–42, W1–W13, design/128) and tested again. Deploying it changes both the server and the plugin, so every laptop has to update its plugin.

| # | Change | SK |
|---|---|---|
| ST1 | A film with no picture AI is refused (no silent GPT Image) | |
| ST2 | "(as in v1: …)" removed from the start paragraph | |
| IN1 | Intake wording (design/126 1.x) | |
| BR1–BR3 | Brief prompt trimmed 1,060 → 973 words; "recommendation" stated in the reason | |
| SC1–SC5 | Script stage wording; the "defer" paragraph in plain words; the script answer shape | |
| ME1 | The footage guess at media retired (measured at visuals instead) | |
| AN1 | Analysis starts without asking again | |
| OP1–OP4 | Options: related pieces on one line; a scene lists every chapter (P7 retired); chapter warning for information; dashes and quotes on the cards | |
| MA1 | A rejected shot's gap says what was turned down and why | |
| VI1 | The chat tool's message points to the part's reading list | |
| TR1 | Treatment warns on a graphics run over 8 s | |
| TR2 | Every estimate uses the film's own picture price | |
| U1–U7 | Users' page issues: the list scrolls to the playing shot; the × always visible; a note saved with its picture; zoom; search up to 12 words; upload when search finds nothing (in the picture's panel); where a picture is used | |

**TR1's open question, decided (SK, 1 Nov: "Yes, count drawn"):** the plan's 8 s graphics run counts drawn shots too (TR1b, not built yet; VW-12 keeps today's rule). The plan never warned on VW-12's four drawn runs because the rule left drawn out.

## B. Agreed, not built

| # | Change | Work | SK |
|---|---|---|---|
| TR1b | The plan's graphics run counts drawn shots (approved 1 Nov); VW-12 keeps today's rule | `visual_contract.py`, one test; build with TR1 on the branch | go (1 Nov) |
| TR3 | The treatment gives the plan's two other length warnings: AI video back to back over 12 s, and a still over 4 s | server, one test (VW-12's treatment gives 2 + 1) | |
| PL1 | No brick figure ("3 : 1.5 : 1") as the example, in the plan instructions or the server's warning | one wording change in v3, one in `visual_contract.py`, one test | |

## C. Proposed, waiting for your decision

| # | Proposal | My recommendation | SK |
|---|---|---|---|
| F37b | `vw visuals spec --file`: put a revised spec in without editing the whole plan by hand | **Drop.** The plan download route (defect 37) already keeps accepted gaps accepted, and it also covers sizes, which F37b would not | |
| D39 | The tool's first file download retries like the other requests, and treats a network timeout as "run it again", not a defect | Take up. Small change, and it stops defects being filed for a bad connection (39 was one) | |
| G1 | The plugin's guard steps aside by itself outside the operator folder, so nobody needs the desktop "Vw off" switch (which is not working for the users) | Take up. A few lines; removes the workaround | |
| P4 | The second look (7.6) leaves a mark on the server, so you can see whether it ran and what it fixed | Hold until a film shows the need | |
| S1 | New finding: after a server wording deploy, the operator's instruction files stay old until `vw visuals prepare` is run again | Not written up yet; I would propose the smallest fix if you want it | |

## D. Old ways due for retirement (design/35)

| Row | Older way | When | SK |
|---|---|---|---|
| 9, 10 | VW-11's old slide rows and declared gaps | **due at the next release** (VW-11 closed 30 Oct) | |
| 13 | The empty `footage_character` field | next release that touches media (ME1 covers it) | |
| 15 | Docker tests that still use the retired planning stage | the next build with Docker running | |
| 17 | The take prompt without a timeline, kept for VW-12 | when VW-12 closes | |

## E. Watch items (no build)

- Drawn cutaway beside an AI graphic sequence (gap 4-B1): do they read as one style? Seen at the pictures.
- Reference pictures are not in the treatment's estimate (TR2): seen at the plan.
- Whether the plan helpers and the second-look helpers ran on VW-12: not recorded on the server.
- The first new run after design/128: are the plan's beats fine enough for the timeline to help?

## F. The review itself

Paused at visuals Phase 3, item 9.3.4 (the items). Phase 4 (pictures, takes, drawing) not reviewed yet.
