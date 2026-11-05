#!/bin/bash
cd "$(dirname "$0")"
P=pics
py() { python -I wan_test.py "$@" --out out > "out/$1.stdout" 2>&1 & }
py W3-director-30s --prompt prompts/w3-director-30s.txt --images $P/rat_trap_site__sheet__3__1f6edc69.png,$P/ref-1-mason.jpg,$P/ref-2-helper.jpg,$P/ref-6-trowel-pan.jpg --duration 30
py W4-count-10s    --prompt prompts/w4-count-10s.txt    --images $P/rat_trap_site__sheet__3__1f6edc69.png,$P/ref-2-helper.jpg,$P/ref-6-trowel-pan.jpg --duration 10
wait
cat out/W3-director-30s.stdout out/W4-count-10s.stdout
