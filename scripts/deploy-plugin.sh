#!/bin/bash
# Release the pushed main branch's plugin/ to the operator's Claude Code.
# The operator plugin vw@vw-local is installed from the GitHub marketplace
# (dsteamautomations/videowizard-claude-v2), so "deploying" the plugin means:
# compile-check, then ask Claude Code to refresh the marketplace clone and
# update the installed copy. Nothing changes on the VM.
set -euo pipefail

CLAUDE="/Users/vasudha/Library/Application Support/Claude/claude-code/2.1.295/9d6405864fdc/claude.app/Contents/MacOS/claude"
if command -v claude >/dev/null 2>&1; then CLAUDE=claude; fi
[ -x "$CLAUDE" ] || { echo "refusing: claude binary not found at $CLAUDE (update the path in this script and CLAUDE.md)" >&2; exit 1; }

cd "$(dirname "$0")/.."

# 1. Refuse unless the working tree is clean and main is exactly what is pushed.
if [ -n "$(git status --porcelain)" ]; then
  echo "refusing: working tree is dirty (commit or stash first)" >&2; exit 1
fi
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
  echo "refusing: not on main" >&2; exit 1
fi
git fetch -q origin main
if [ "$(git rev-parse main)" != "$(git rev-parse origin/main)" ]; then
  echo "refusing: local main ($(git rev-parse --short main)) differs from origin/main ($(git rev-parse --short origin/main)); push first" >&2; exit 1
fi

# 2. Compile-check every plugin Python file.
while IFS= read -r f; do
  python -m py_compile "$f"
  echo "compiled $f"
done < <(find plugin -name '*.py' | sort)

# 3. Refresh the marketplace clone and update the installed plugin.
"$CLAUDE" plugin marketplace update vw-local
"$CLAUDE" plugin update vw@vw-local --scope user
"$CLAUDE" plugin list

echo
echo "Plugin updated from main @ $(git rev-parse --short main)."
echo "The operator must restart Claude Code in \"/Users/vasudha/Documents/videobuilder - Operator \" to pick it up."
