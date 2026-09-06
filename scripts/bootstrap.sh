#!/usr/bin/env bash
# One time setup for the CTI Documentation Sync workbench on macOS, Linux or WSL.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PYTHON="${PYTHON:-python3}"

echo "CTI Documentation Sync setup"
echo "============================"
$PYTHON --version
echo

[[ -d .venv ]] || { echo "Creating virtual environment .venv"; $PYTHON -m venv .venv; }
PY="$REPO/.venv/bin/python"

echo "Installing dependencies"
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet
echo "  done"
echo

[[ -f cti.config.json ]] || { cp cti.config.example.json cti.config.json; echo "Created cti.config.json from the example."; }

echo "Checking configured folders"
"$PY" - <<'PYEOF' || echo "
Edit cti.config.json so both folders point at the real locations, then run this again."
import sys
sys.path.insert(0, 'scripts')
from cti_paths import load_config, _expand
cfg = load_config()
ok = True
for key in ('deliverables', 'documentation'):
    p = _expand(cfg[key])
    print(f"  {'OK  ' if p.is_dir() else 'MISS'} {key}: {p}")
    ok = ok and p.is_dir()
sys.exit(0 if ok else 1)
PYEOF

echo
if command -v cursor-agent >/dev/null 2>&1; then
  echo "Cursor CLI found at $(command -v cursor-agent)"
else
  echo "Cursor CLI not on PATH. For scheduled runs install it with:"
  echo "  curl https://cursor.com/install -fsS | bash"
  echo "Interactive use inside the Cursor editor does not need it."
fi

echo
echo "Running preflight"
echo
"$PY" scripts/doctor.py || true

echo
echo "Next:"
echo "  Open this folder in Cursor and paste into the Agent chat:"
echo
echo "    Set up this repository on my machine. Run the cti-setup skill and"
echo "    walk me through it. I am at the keyboard, so ask me rather than"
echo "    guessing, especially about where my CTI folders actually live."
echo
echo "  Or continue by hand:"
echo "    ./scripts/run_doc_sync.sh --force --dry-run    read only trial run"
echo "    ./scripts/register_schedule.sh --at 07:30      monthly schedule"
