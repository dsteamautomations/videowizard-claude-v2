#!/bin/bash
# Publish plugin/ of the pushed main branch to the plugin-only repository (SK, 16 Nov 2026).
# Why: an operator's laptop installs the plugin by downloading a whole repository. The main repository holds the design notes' pictures and
# videos, fonts and test data (about 210 MB); the plugin is under 1 MB. Laptops now install from dsteamautomations/vw-plugin, which holds
# only what the operator's tool needs: the marketplace file and plugin/ without its tests.
# Run from the repository after pushing main:   ./scripts/publish-plugin.sh
set -euo pipefail
TARGET="${VW2_PLUGIN_REPO:-https://github.com/dsteamautomations/vw-plugin.git}"

cd "$(dirname "$0")/.."
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "refusing: working tree has uncommitted changes" >&2; exit 1; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "refusing: not on main" >&2; exit 1; }
git fetch -q origin main
[ "$(git rev-parse main)" = "$(git rev-parse origin/main)" ] || { echo "refusing: local main differs from origin/main; push first" >&2; exit 1; }

SHA=$(git rev-parse --short main)
VERSION=$(python -c "import json,sys; sys.stdout.write(json.load(open('plugin/.claude-plugin/plugin.json', encoding='utf-8'))['version'])")
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

git clone -q "$TARGET" "$WORK/out" 2>/dev/null || { echo "refusing: cannot reach $TARGET" >&2; exit 1; }
cd "$WORK/out"
git checkout -q -B main
find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +          # the repository holds exactly this release, nothing left over
cd - >/dev/null
git archive main plugin .claude-plugin/marketplace.json | tar -x -C "$WORK/out"   # tracked files only: no caches, nothing local
rm -rf "$WORK/out/plugin/tests"                                         # the operator's tool does not need the plugin's tests
printf '%s\n' "VideoWizard operator plugin $VERSION, published from videowizard-claude-v2 main @ $SHA. Do not edit here: change plugin/ in the main repository and run scripts/publish-plugin.sh." > "$WORK/out/README.md"

cd "$WORK/out"
git add -A
if git diff --cached --quiet; then echo "nothing to publish: the plugin repository already holds $VERSION from $SHA"; exit 0; fi
git -c user.name="VideoWizard builder" -c user.email="builder@videowizard.local" commit -q -m "plugin $VERSION from main @ $SHA"
git push -q origin main
echo "published plugin $VERSION (main @ $SHA) to $TARGET: $(git ls-files | wc -l) files, $(du -sk --exclude=.git . | cut -f1) KB"
