# 28 — Reusing v1's local assets and editable graphics in v2 (assessment, 16 Oct 2026)

Asked by SK after ticket 11: can the v1 machinery for editable text graphics and local assets be brought into v2 with minimal effort? Read-only review of `videowizard-beta`. Nothing has been changed.

## What v1 had
| Piece | What it does | v1 files (lines) |
|---|---|---|
| **Editable text graphics** | At shot preparation, a graphic element gets exact text. At assembly, Pillow draws each text into a transparent PNG (word-wrapped, chosen font), and FFmpeg overlays it on the film for exactly its frames. A "graphics reviewed" check gates acceptance. | backend `assembly_graphics.py` (65), `visual_preparation.py` (197, the bind and packet part); operator `assembly_graphics.py` (106: wrap, preview, composite) |
| **Local assets** | A hand-made movie, still or **design** registered against a shot, with its approval and provenance. Stills are cropped and resized; movies and designs are used as delivered. | backend `local_assets.py` (246); operator `local_assets.py` (90), `local_asset_media.py` (84) |
| **Design layers** | A design carries a recipe of timed rectangles, images and text. v1 never drew that recipe itself: the film used the design's approved preview movie, and the recipe was rebuilt as editable Fusion nodes in Resolve on the Mac. | operator `local_asset_native.py` (81, Mac only) |
| Plumbing | 4 MiB chunked uploads, ZIP archives, encrypted operator sessions, Codex skill layout, a web UI checkbox | several files |

## What v2 can reuse
| Piece | Reuse | Effort |
|---|---|---|
| Text graphics: data model and checks (exact wording, timing inside the shot, fits the frame, visible colour) | Port almost as is | Small |
| Text graphics: drawing and timed overlay (Pillow PNG + FFmpeg overlay) | Port; it matches the way v2's renderer already draws the review-film labels | Small |
| Bind with editable text (`--text ELEMENT="exact text"`), shown in the shot packet | New in v2's bind and plugin; follows v1's rules | Small |
| Fonts | v1 used fonts the operator supplied, matched by hash. v2 would ship one open-licence font and accept a supplied brand font per run. | Small |
| Local design assets | v2 already accepts a hand-made movie or still per shot. Add `design`: the approved movie plus its layer recipe, checked with v1's model and kept in the delivery package for the editor | Small |
| Still crop and resize | Port v1's crop step into v2's still handling | Small |
| Chunked upload, archives, encrypted sessions, Codex layout, web UI | **Not needed**: v2 already has signed uploads with receipts and one `vw` tool | None |
| Rebuilding designs and text as editable Fusion nodes in Resolve | Port later with the Resolve step; needs a real Mac test | Medium, deferred |

## The other part of the fix: v2 instructions
The visuals instructions copied from v1 describe v1's commands (`scripts/local_assets.py`, `/visuals/local-assets`, Codex). They must be rewritten to describe v2's commands, including the new ones above. Needed whichever way this goes.

## Estimate
| Work | Time |
|---|---|
| Editable text graphics end to end (bind, packet, assembly overlay, review check, fonts) with tests | about 1 day |
| Design assets and still crop, with tests | about half a day |
| Visuals instructions rewritten for v2 | about half a day |
| **Total** | **about 2 days** |
| Later: Fusion rebuild in Resolve | about 1 day plus a Mac test |

## Decisions for SK
1. **Scope of on-screen text.** On 15 Oct titles and the finishing layer were declared the editor's work. Editable text graphics put text into the film itself. Which text belongs here: content graphics such as the strength table, "25% fewer bricks" and "cure for 7 days", or also titles?
2. **Timing for VW-2.** VW-2 is in the visuals stage now. Either use the ticket 11 workaround for VW-2 (the editor makes the text shots), or wait about 2 days for the port while VW-2's other shots carry on.
3. **Fusion rebuild in Resolve:** now or later.

Per the working rules, a requirement list with edge cases follows once these are decided.
