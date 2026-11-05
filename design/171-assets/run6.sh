#!/bin/bash
# The first six Wan runs of design/170 §4 (W1, W2, W6), in parallel (the account allows eight in flight).
cd "$(dirname "$0")"
P=pics; E=env
py() { python -I wan_test.py "$@" --out out > "out/$1.stdout" 2>&1 & }
py W1a-plinth-8s    --prompt prompts/plinth.txt     --images $E/env-plinth.jpg,$P/worker_plinth__sheet__1__b41000a4.png,$P/worker_plinth__sheet__3__b41000a4.png,$P/technique_plinth_wetting__sheet__3__f42b4b62.png,$P/water_pot__sheet__1__a7cbc5bb.png --duration 8
py W1b-plinth-smart --prompt prompts/plinth.txt     --images $E/env-plinth.jpg,$P/worker_plinth__sheet__1__b41000a4.png,$P/worker_plinth__sheet__3__b41000a4.png,$P/technique_plinth_wetting__sheet__3__f42b4b62.png,$P/water_pot__sheet__1__a7cbc5bb.png --smart
py W2a-pointing-7s  --prompt prompts/pointing.txt   --images $P/technique_pointing__sheet__1__69c64baa.png,$P/rat_trap_wall_rep__frame____05a1dea3.png,$P/mason_pointing__sheet__2__f3cd0644.png,$P/pointing_trowel__sheet__1__94c46edf.png,$P/mortar_hawk__sheet__1__d462255a.png --duration 7
py W2b-string-5s    --prompt prompts/string.txt     --images $E/env-string.jpg,$P/worker_string__sheet__2__dc9e5f80.png,$P/technique_string_setting__sheet__3__90559b83.png --duration 5
py W6a-kiln-env-4s  --prompt prompts/kiln.txt       --images $E/env-kiln.jpg,$P/kiln_workers__sheet__1__e2594ac6.png,$P/kiln_workers__sheet__3__e2594ac6.png --duration 4
py W6b-kiln-set-4s  --prompt prompts/kiln-noenv.txt --images $P/brick_kiln__sheet__1__306c314b.png,$P/kiln_workers__sheet__1__e2594ac6.png,$P/kiln_workers__sheet__3__e2594ac6.png --duration 4
wait
cat out/*.stdout
