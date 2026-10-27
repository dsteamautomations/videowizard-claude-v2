# Fonts for the drawn-graphic route (design/113 E4)

Expected here, under the SIL Open Font License: `NotoSans-Regular.ttf` and `NotoSans-Bold.ttf` (Google Fonts, the Noto Sans family), with `OFL.txt` beside them.
Every drawn graphic and every slate uses them, so the VM needs no font of its own. A client's brand font (one TTF or OTF per film, given at the brief) is stored with the run and used in its place; nothing is downloaded at run time, and a font Pillow cannot read fails the render by name.
