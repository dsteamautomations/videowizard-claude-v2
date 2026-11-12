# design/179: motion style per film, and the font set

12 Nov 2026. Approved by SK. Requirements, edge cases and failure modes: `videobuilder-v4/phase2/motion/requirements-style-and-fonts.md`. SK's decisions and the whole motion plan (M1 to M8): `videobuilder-v4/phase2/motion/reply-to-handover.md`. Font samples by eye: `videobuilder-v4/phase2/motion/font-sample-sheet.png`.

## What changed

| # | Change | Where |
|---|---|---|
| S1 | The film record takes `motion` (the motion style), with the operator's words | `film.py` (`check`, `LOCKS`, `motion`), `main.py` `FilmChoice`; `vw motion-style` |
| S2 | Eight styles as files: `server/motion_styles/<name>.md` (title, for, the categories it is recommended first and also for, then the text). Adding a style is adding a file | `film.styles()` |
| S3 | The style is asked once at the treatment, recommended from the film's category. `GET /film` lists the styles, the first to recommend | `film.need_motion`, `recommend_styles`; `visuals_stage.treatment` |
| S4 | Every drawn shot's brief ends with a "Motion style" part. The fixed "flat, clean, technical" is gone from the brief and the fixed style line from the skill | `film.style_part`, `visuals_stage.motion_brief`; `plugin/skills/motion/SKILL.md` |
| S5 | The rule writer writes no rule that restricts motion unless the brief asks; the checker never fails what the style allows | `plugin/agents/vw-motion-rules.md`, `vw-motion-check.md` |
| S6 | The font set: 15 fonts, 50 files under `server/fonts`, described by `fonts.json` (written by `scripts/fetch_fonts.py` from the files: licence, scripts, letters). A font is refused for a film whose script it lacks, naming those that hold it | `film.font_set`, `fonts_for`, `check('font', scripts=)` |
| S7 | `GET /film` offers the fonts in the order to recommend: the client's last font, then the style's fonts, then the others that hold the film's scripts | `main.get_film`, `film.fonts_for` |
| S8 | The film's scripts are read from the letters of its script (nothing is asked) and kept with the font choice | `film.scripts_of`, `main._film_scripts`, `film.font_scripts` |
| E7 | A label with a letter the film's font lacks is refused at the brief, naming the label and the letters | `film.missing_letters`, `visuals_stage.motion_brief` |
| — | A film's font brings one file per script into a drawing, each under its own family name; the brief names them | `film.font_faces`, `visuals_stage._motion_fonts`, `film_font_files` |

A font as the operator sees it is a family across scripts ("Anek" is Anek Latin, Anek Tamil, Anek Devanagari and so on).

Versions: server 0.92.0, plugin 0.78.0, **minimum plugin 0.78.0** (an older skill carries the fixed style line and would contradict the brief).

## Old ways

- **Kept until those films close:** a film with no recorded motion style gets the older fixed style in its brief (`film.OLDER_STYLE`), word for word what the skill said before.
- **Kept for films and clients that recorded them:** Roboto and Lato (`film.FONTS`); they are no longer offered to a new film, except as a client's last font on an English film.
- **Retired:** "Noto Sans recommended" for every film; the fixed style line in the motion skill.

## Tests

`server/unit/test_motion_style_fonts_pure.py` (17). Three older tests changed to the new behaviour (the font message, Montserrat's file, the minimum plugin version).

## Not covered

- **The styles are drafts.** None is "kept" until it is rendered on the bench shots and SK has looked at it; that bench run is not done.
- E9: a drawn shot made before a change of style is not marked "made in the earlier style".
- The film choices on a web page: the style and the font offer are in the chat tool's answer only.
- A sign a font lacks (an arrow, for instance) falls to Noto Sans and is not refused; only letters are.
- The library of blocks (M6 to M8), shorter instructions, fewer rules.
- Database tests, a real Python 3.9.
