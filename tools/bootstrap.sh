#!/usr/bin/env bash
# Restore the carousel toolchain into a fresh sandbox.
# The repo is public, so this needs NO credentials. Safe to re-run (idempotent).
#
#   bash bootstrap.sh
#
# Afterwards the only thing still missing is ~/.secrets/ (the two tokens).

set -euo pipefail

RAW="https://raw.githubusercontent.com/Samyyusif/samy-linkedin-carousels/main/tools"
DEST="$HOME/carousel-tools"

mkdir -p "$DEST/fonts" "$DEST/assets" "$DEST/out"

fetch() {  # fetch <repo-relative-path> <local-path>
  if [ -s "$2" ]; then echo "skip  $2"; return; fi
  curl -fsSL --noproxy '*' -o "$2" "$RAW/$1" && echo "got   $2"
}

fetch generate_carousel.py       "$DEST/generate_carousel.py"
fetch publish_carousel.py        "$DEST/publish_carousel.py"
fetch icons.py                   "$DEST/icons.py"
fetch assets/samy-avatar.png     "$DEST/assets/samy-avatar.png"

for w in Regular Medium SemiBold Bold; do
  fetch "fonts/IBMPlexSans-$w.ttf" "$DEST/fonts/IBMPlexSans-$w.ttf"
done
# Mono is used by the command blocks on step-by-step slides.
for w in Regular Medium; do
  fetch "fonts/IBMPlexMono-$w.ttf" "$DEST/fonts/IBMPlexMono-$w.ttf"
done

# Runtime deps. Playwright's Chromium is preinstalled in this image.
python3 -c "import img2pdf" 2>/dev/null || pip install img2pdf --break-system-packages -q
python3 -c "import playwright" 2>/dev/null || pip install playwright --break-system-packages -q

echo
# Buffer needs no token here - posting goes through the Buffer MCP connector,
# which authenticates via the claude.ai account. The GitHub PAT is the only
# secret left, and it is only needed to host the carousel PDF publicly.
if [ -s "$HOME/.secrets/github_token" ]; then
  echo "READY - toolchain present, GitHub token present. Carousels enabled."
else
  echo "TOOLCHAIN OK, GITHUB TOKEN MISSING - text posts will work via Buffer MCP;"
  echo "carousels are disabled until ~/.secrets/github_token is restored."
fi
