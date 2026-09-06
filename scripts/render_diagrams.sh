#!/usr/bin/env bash
# Re-render the diagrams after editing a .mmd source.
#
#   ./scripts/render_diagrams.sh
#
# Needs the Mermaid CLI:  npm install -g @mermaid-js/mermaid-cli
# The .mmd sources are the originals; the .png and .svg are generated.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO/docs/diagrams"

command -v mmdc >/dev/null 2>&1 || {
  echo "mmdc not found. Install: npm install -g @mermaid-js/mermaid-cli" >&2
  exit 127
}

for src in *.mmd; do
  name="${src%.mmd}"
  # Width by shape: the infrastructure diagram is wide, the routing one narrow.
  case "$name" in
    *infrastructure)   width=1800 ;;
    *bedrock-routing)  width=1600 ;;
    *)                 width=1700 ;;
  esac
  echo "rendering $name"
  mmdc -i "$src" -o "$name.png" -c mermaid-theme.json -b white -w "$width"
  mmdc -i "$src" -o "$name.svg" -c mermaid-theme.json -b white
done

echo "done. PNG for pasting, SVG for scaling into a deck."
