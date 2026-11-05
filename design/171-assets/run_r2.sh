#!/bin/bash
# Round 2 (SK, 5 Nov): the five single-shot takes again, steps instead of seconds, right hand, smart duration. Staggered 20 s against the rate limit.
cd "$(dirname "$0")"
P=pics; E=env
py() { python -I wan_test.py "$@" --out out --smart > "out/$1.stdout" 2>&1 & sleep 20; }
py R2-plinth   --prompt prompts/r2-plinth.txt   --images $E/env-plinth.jpg,$P/worker_plinth__sheet__1__b41000a4.png,$P/worker_plinth__sheet__3__b41000a4.png,$P/technique_plinth_wetting__sheet__3__f42b4b62.png,$P/water_pot__sheet__1__a7cbc5bb.png
py R2-string   --prompt prompts/r2-string.txt   --images $E/env-string.jpg,$P/worker_string__sheet__2__dc9e5f80.png,$P/technique_string_setting__sheet__3__90559b83.png
py R2-pointing --prompt prompts/r2-pointing.txt --images $P/technique_pointing__sheet__1__69c64baa.png,$P/rat_trap_wall_rep__frame____05a1dea3.png,$P/mason_pointing__sheet__2__f3cd0644.png,$P/pointing_trowel__sheet__1__94c46edf.png,$P/mortar_hawk__sheet__1__d462255a.png
py R2-kiln     --prompt prompts/r2-kiln.txt     --images $E/env-kiln.jpg,$P/kiln_workers__sheet__1__e2594ac6.png,$P/kiln_workers__sheet__3__e2594ac6.png
py R2-count    --prompt prompts/r2-count.txt    --images $P/rat_trap_site__sheet__3__1f6edc69.png,$P/ref-2-helper.jpg,$P/ref-6-trowel-pan.jpg
wait
cat out/R2-*.stdout
