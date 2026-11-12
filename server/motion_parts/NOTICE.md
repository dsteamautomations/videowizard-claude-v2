# The finish effects (design/186)

`blur.html`, `grain.html` and `vignette.html` are the components `motion-blur`, `grain-overlay` and `vignette` of the HyperFrames registry
(the HyperFrames project's public library), release 0.8.226, fetched on 12 Nov 2026 with `hyperframes add` and kept unchanged.
Licence: Apache License 2.0. The server adds them to a drawn shot at render (`app/motion.py`, `apply_finish`); it softens the grain and the
vignette there, not in these files.
