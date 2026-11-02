# design/136: the guidebook audit, and generic rules filed by video category (direction approved by SK, 2 Nov 2026; not built)

2 Nov 2026. SK asked: read every word of the guidebooks the picture and video steps read; list what is tuned to the outside projects they were copied from and convert it into generic rules; check for duplicates and for habits of older models; file the generic rules by video category so each step reads only what it needs. The principle behind it, now in CLAUDE.md ("What VideoWizard is for"): **VideoWizard serves every category of video; documentaries are only the first test.**

Method: four readers audited the 18 files section by section against VW-MAP's override table, each with the same tags (general, category, picture kind, source-specific, outdated, duplicated, overridden, server-only, provenance). Their full tables, quotes and proposed rewrites are in `design/136-guidebook-audit/`. The builder spot-checked claims from each reader against the files; every one checked held (for example: the diagram template's "for a 16:9 documentary film", the word-list's "must look like a real advertising production deliverable", the rulebook's festival and Flag Code rules, director-named palettes, "8K_UHD" flags, a start-image pointer to a size the Omni sheet does not publish).

## What the guidebooks hold today

| Group | Files | Words | Kept as sound rules | Removed, converted or left to the server |
|---|---|---|---|---|
| A. Rulebook, answer form, frame, web, diagram-state and gap-fill guides | 6 | 7,859 | 3,495 | 4,364 |
| B. Copied craft: animatic keyframes, character frames, de-slop, craft | 4 | 12,417 | 2,896 | 9,521 |
| C. Video take guide, camera and light vocabulary, motion styles, infographic examples | 4 | 5,925 | 2,519 | 3,406 |
| D. Picture and video model guides, the word-list, the compliance checklist | 4 | 10,401 | about 1,915 | about 8,490 |
| **All** | **18** | **36,602** | **about 10,800 (30 %)** | **about 25,800 (70 %)** |

Where the 70 % goes:
- **Overridden by VideoWizard (the largest share):** model choice, storyboard grids, cover frames, nine-view fashion series, batch generation, medium quality, draft-then-final, camera moves between start and end frames, quoted words in prompts, sound and transitions in takes, Seedance and Kling templates, extend and edit tasks.
- **Tuned to the source project:** the race advert's amber ban, no faces and drag-race objects (animatic keyframes); the fashion shop's bag, jewellery, studio backdrop and 3:4 frame (character frames); sign-making and roll-up banner rules, an ad prompt compiler and "must look like an advertising deliverable" (word-list); Indian festival and Flag Code rules (rulebook); director- and brand-named palettes (camera vocabulary); app-store, website and email work (web guide).
- **Outdated habits:** "8K_UHD" and "editorial finish" flags and JSON quality tags (craft §3); style strings repeated word for word in every frame; long "No …" lists, which the motion-style guide itself says backfire; "name it twice".
- **Server-only:** each model guide's Part A (API settings, sizes, price, waits, errors).
- **Provenance:** the "Evidence" and "Built from" sections.

## Contradictions found (the ones that change what the operator's AI writes)
1. **Words in the picture:** four guides put labels in quotes inside the prompt; VW-MAP and the server take them only through `exact_text`.
2. **Place words:** "centre", "in the center", "left third" in templates and examples; the server refuses them.
3. **Settings written into prompts:** "Target aspect ratio" and "Mode" lines in templates, against RULEBOOK 13 (the server sets them).
4. **Camera:** three guides put a camera move or handheld into the brief; VideoWizard keeps the camera steady and the server writes the Camera line.
5. **Sound:** two guides tell the writer to describe audio; every take is silent.
6. **Quality and drafts:** medium quality and draft rounds against the server's "always high".
7. **Negatives:** short negatives against long "Avoid"/"No …" lists in the same library.
8. **Shortest take:** 3 to 5 s per beat against "5 s or more".
9. **Sheet views:** three different sets of views for a person sheet.
10. **A pointer that leads nowhere:** VW-MAP sends the start image to "Omni A5 for its accepted size"; A5 says the size is not published (the 16:9/9:16 rule is in A3 and B7).
Each audit file lists the rest (12 in A, 12 in B, 10 in C, 8 in D, some shared).

## The proposal

1. **One clean library version** (a new snapshot folder, as every library change is made, design/89 batch 4), rewritten from the audit:
   - every file keeps only its sound rules: general, picture kind, or a video category;
   - source-specific text is converted to the generic rewrites in the audit, or removed;
   - outdated habits, server-only parts and provenance notes are removed;
   - duplicates are cut to one home, and the contradictions above are settled in favour of what VideoWizard and the server do;
   - the rules VideoWizard forbids today but another category may want (sound for advertisements and social clips, transitions for narrative films) are kept, filed under that category and marked "not available yet", so they are never read on today's films and not lost.
2. **Filed by category inside each file:** a general part, then short "For advertisement-product", "For training-education", "For documentary-explainer", "For social-ugc" and "For narrative-story" parts where a rule only fits some. The two rewrites in `B-copied-craft.md` show the shape: a general still-picture card and person table, each with a few lines by category.
3. **Each step reads its general part plus the film's own category.** This builds on design/135 (sections pulled by heading when a step's files are packed). It needs the film's category recorded once, a field in the brief (today every film is documentary-explainer, the default), and the packer then copies the general sections and that category's sections only.
4. **The rule in the operator's rulebook too:** the "every category" principle and the category filing are stated at the top of RULEBOOK (the file read on every job).
5. **design/135 joins this change:** the section pulling is the mechanism; the keep-list becomes the new library's own layout.

Before anything is built: SK approves this direction; the builder then writes the new library version file by file from the audit, shows SK the rewritten text of the files the picture steps read most (the still card, the person table, the video-frame and video-clip guides, the word-list), runs the free comparison (prompts for three VW-12 shots written with the old and the new reading, no paid picture), and only then builds the packing and the category field, tests first.

**Older way (design/35):** the 29 Oct library snapshot stays for runs already pinned to it; new runs get the new version.

## Not covered
- The guidebooks no step reads (the rest of the library shelf): not audited; the map never routes to them.
- Whether each kept rule makes better pictures: the audit judges fit and freshness, not results. The free comparison, then real films, show that.
