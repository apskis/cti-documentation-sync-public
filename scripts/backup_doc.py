"""Copy a document to the doc sync backup folder before it is edited.

    python scripts/backup_doc.py "<path to document>" --reason falcon-loop

Writes  _doc_sync/backups/<name>_<YYYYMMDD>-pre-<reason>.<ext>  and prints it.
A backup is never overwritten: a second run on the same day gets -2, -3 and so on.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cti_paths import assert_writable, backups_dir  # noqa: E402


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "edit"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--reason", required=True,
                    help="short reason, becomes part of the file name")
    a = ap.parse_args()

    src = Path(a.path)
    if not src.is_file():
        print(f"ERROR source not found: {src}", file=sys.stderr)
        return 1
    try:
        assert_writable(src)
    except Exception as exc:  # noqa: BLE001
        print(f"REFUSED {exc}", file=sys.stderr)
        return 2

    stamp = date.today().strftime("%Y%m%d")
    base = f"{src.stem}_{stamp}-pre-{slug(a.reason)}"
    dest = backups_dir() / f"{base}{src.suffix}"
    n = 2
    while dest.exists():
        dest = backups_dir() / f"{base}-{n}{src.suffix}"
        n += 1

    shutil.copy2(src, dest)
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
