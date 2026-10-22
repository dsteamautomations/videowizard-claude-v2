#!/bin/bash
# Release the pushed main branch's plugin/ to the operator's Claude Code.
# The operator plugin vw@vw-local is installed from the GitHub marketplace
# (dsteamautomations/videowizard-claude-v2), so "deploying" the plugin means:
# compile-check, then ask Claude Code to refresh the marketplace clone and
# update the installed copy. Nothing changes on the VM.
set -euo pipefail

CLAUDE="/Users/vasudha/Library/Application Support/Claude/claude-code/2.1.304/6bbba6adc37f/claude.app/Contents/MacOS/claude"
if command -v claude >/dev/null 2>&1; then CLAUDE=$(command -v claude); fi   # a bare name fails the -x test (SK's PC, 22 Oct 2026)
[ -x "$CLAUDE" ] || { echo "refusing: claude binary not found at $CLAUDE (update the path in this script and CLAUDE.md)" >&2; exit 1; }
# On Windows the CLI needs git-bash named, and refuses a git found under the current directory (git is installed under the home folder):
# run this script from the repository, never from the home folder.
[ -n "${CLAUDE_CODE_GIT_BASH_PATH:-}" ] || { b=$(command -v bash 2>/dev/null); case "$b" in /c/*|/mnt/c/*) export CLAUDE_CODE_GIT_BASH_PATH="$(cygpath -w "$b" 2>/dev/null || echo "$b")";; esac; }

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

# 3. Refresh the marketplace clone, then reinstall. plugin update and plugin install are
#    no-ops while the version in plugin.json is unchanged; only uninstall + install refreshes
#    the installed copy (the plugin keeps nothing under ~/.claude/plugins/data). The install
#    re-enables the plugin at user scope, so disable it there again: the plugin is enabled
#    only by the operator folder (its .claude/settings.json, project scope).
"$CLAUDE" plugin marketplace update vw-local
"$CLAUDE" plugin uninstall vw@vw-local --scope user
"$CLAUDE" plugin install vw@vw-local --scope user
"$CLAUDE" plugin disable vw@vw-local --scope user
WANT=$(git rev-parse main)
GOT=$(python -c "import json,sys; d=json.load(open(sys.argv[1])); sys.stdout.write(d[\"plugins\"][\"vw@vw-local\"][0][\"gitCommitSha\"])" "$HOME/.claude/plugins/installed_plugins.json")
[ "$GOT" = "$WANT" ] || { echo "installed plugin is at $GOT, expected $WANT" >&2; exit 1; }
OPERATOR="${VW2_OPERATOR_DIR:-/Users/vasudha/Documents/videobuilder - Operator }"   # on SK's PC: C:/Coworkspace/VideoWizard-Operator
if [ -d "$OPERATOR" ]; then (cd "$OPERATOR" && "$CLAUDE" plugin list); fi

echo
echo "Plugin updated from main @ $(git rev-parse --short main)."
echo "The operator must restart Claude Code in \"$OPERATOR\" to pick it up."
