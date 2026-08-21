#!/usr/bin/env bash
# Single entry point for the daily carousel step.
#
#   bash run_pipeline.sh <spec.json>
#
# Does bootstrap (if needed) + build + host in ONE shell invocation, so the
# scheduled run asks for permission once instead of once per command.
# Prints the publish JSON as its last line.

set -uo pipefail

SPEC="${1:?usage: run_pipeline.sh <spec.json>}"
DEST="$HOME/carousel-tools"
RAW="https://raw.githubusercontent.com/Samyyusif/samy-linkedin-carousels/main/tools"

if [ ! -f "$DEST/generate_carousel.py" ]; then
  curl -fsSL --noproxy '*' -o /tmp/bootstrap.sh "$RAW/bootstrap.sh" || {
    echo '{"ok":false,"stage":"bootstrap_download","error":"could not reach the tools repo"}'; exit 1; }
  bash /tmp/bootstrap.sh >&2 || {
    echo '{"ok":false,"stage":"bootstrap","error":"bootstrap script failed"}'; exit 1; }
fi

python3 "$DEST/publish_carousel.py" "$SPEC"
