# Fonts for the drawn-graphic route (design/113 E4)

Here, under the SIL Open Font License (`OFL.txt`): `NotoSans-Variable.ttf`, Google Fonts' one file for the Noto Sans family (`ofl/notosans/NotoSans[wdth,wght].ttf` in github.com/google/fonts, fetched 27 Oct 2026 on SK's word); the renderer takes its Regular and Bold instances by name. Static `NotoSans-Regular.ttf` and `NotoSans-Bold.ttf` are used instead when placed beside it.
Every drawn graphic and every slate uses them, so the VM needs no font of its own. A client's brand font (one TTF or OTF per film, given at the brief) is stored with the run and used in its place; nothing is downloaded at run time, and a font Pillow cannot read fails the render by name.
