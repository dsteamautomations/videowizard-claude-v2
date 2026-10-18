#!/bin/bash
# Deploy the pushed main branch (server + workers) to the live VM.
# Implements design/29 "UPDATES ON THE VM". Run from the builder folder after
# telling SK what changes and that the workers restart.
#
# The VM holds no GitHub credential, so the code travels as a git bundle:
#   bundle main -> gcloud scp to /tmp on the VM -> git pull from the bundle
#   -> pip install -> systemctl restart vw2-server vw2-worker -> poll /api/meta
set -euo pipefail

VM=vw2
ZONE=asia-south1-a
PROJECT=sm-project-435806
URL=https://8-234-82-225.sslip.io

cd "$(dirname "$0")/.."

# gcloud needs Python 3.10+; this Mac has 3.9, so use the standalone CPython inside the SDK (also set in ~/.zprofile).
if [ -z "${CLOUDSDK_PYTHON:-}" ] && [ -x "$HOME/google-cloud-sdk/platform/python3/bin/python3" ]; then
  export CLOUDSDK_PYTHON="$HOME/google-cloud-sdk/platform/python3/bin/python3"
fi
if command -v gcloud >/dev/null 2>&1; then GCLOUD=gcloud
elif [ -x "$HOME/google-cloud-sdk/bin/gcloud" ]; then GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
else echo "refusing: gcloud not found (install ~/google-cloud-sdk, see CLAUDE.md)" >&2; exit 1; fi

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
COMMIT=$(git rev-parse --short main)
echo "deploying main @ $COMMIT to $VM ($PROJECT, $ZONE)"
echo "REMINDER: the worker restart drains first: running jobs finish before the workers come back (up to 40 minutes)."

# 2. Bundle main and copy it to the VM. The remote name is per deploy: two builders deploy with different SSH users,
#    and a leftover /tmp/vw2.bundle owned by the other one cannot be overwritten (18 Oct 2026). The VM deletes it after the pull.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
REMOTE="/tmp/vw2-$COMMIT-$$.bundle"
git bundle create -q "$TMP/vw2.bundle" main
"$GCLOUD" compute scp "$TMP/vw2.bundle" "$VM:$REMOTE" \
  --zone "$ZONE" --project "$PROJECT" --tunnel-through-iap

# 3. Pull, install, restart (restart blocks while the workers drain).
"$GCLOUD" compute ssh "$VM" --zone "$ZONE" --project "$PROJECT" --tunnel-through-iap --command \
  "set -e; chmod a+r $REMOTE; sudo -u vw2 git -C /opt/vw2/app pull $REMOTE main \
   && sudo -u vw2 /opt/vw2/venv/bin/pip install -q -r /opt/vw2/app/server/requirements.txt \
   && sudo systemctl restart vw2-server vw2-worker \
   && echo \"VM now at \$(sudo -u vw2 git -C /opt/vw2/app rev-parse --short HEAD)\" \
   && systemctl is-active vw2-server vw2-worker; rm -f $REMOTE"

# 4. Poll the public health route and print server_version.
echo "polling $URL/api/meta ..."
for i in $(seq 1 30); do
  if body=$(curl -4 -fsS --max-time 10 "$URL/api/meta" 2>/dev/null); then
    echo "$body" | python -c 'import json,sys; m=json.load(sys.stdin); print("server_version:", m["server_version"], " app_origin:", m["app_origin"])'
    echo "deployed main @ $COMMIT. Tell SK: the operator can resume with /vw:vw what is next for <run code>."
    exit 0
  fi
  sleep 5
done
echo "server did not answer at $URL/api/meta within 150 s; check: gcloud compute ssh $VM --zone $ZONE --project $PROJECT --tunnel-through-iap --command 'journalctl -u vw2-server -n 50 --no-pager'" >&2
exit 1
