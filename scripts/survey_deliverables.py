"""Cheap inventory of the CTI Deliverables tree.

The folder is large. This gives the agent counts, classes and the newest few
items per class without opening documents.

    python scripts/survey_deliverables.py
    python scripts/survey_deliverables.py --since 2026-08-21
    python scripts/survey_deliverables.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cti_paths import deliverables_dir  # noqa: E402

SKIP_DIRS = {".git", "__pycache__", ".obsidian", "~$"}
SKIP_PREFIX = ("~$", ".~")


def walk(root: Path):
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name.startswith(SKIP_PREFIX):
            continue
        if p.is_file():
            yield p


def classify(root: Path, path: Path) -> str:
    """Deliverable class is the top folder under the deliverables root."""
    rel = path.relative_to(root)
    return rel.parts[0] if len(rel.parts) > 1 else "(root)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", help="only count files modified on or after "
                                    "this date, YYYY-MM-DD")
    ap.add_argument("--top", type=int, default=5,
                    help="newest N files to list per class")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = deliverables_dir()
    since = (datetime.strptime(a.since, "%Y-%m-%d").timestamp()
             if a.since else None)

    classes: dict[str, list[Path]] = defaultdict(list)
    exts: dict[str, int] = defaultdict(int)
    total = 0
    for p in walk(root):
        st = p.stat()
        if since and st.st_mtime < since:
            continue
        classes[classify(root, p)].append(p)
        exts[p.suffix.lower() or "(none)"] += 1
        total += 1

    report = {
        "root": str(root),
        "since": a.since,
        "total_files": total,
        "extensions": dict(sorted(exts.items(), key=lambda kv: -kv[1])),
        "classes": {},
    }
    for cls, files in sorted(classes.items(), key=lambda kv: -len(kv[1])):
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        report["classes"][cls] = {
            "count": len(files),
            "newest": [
                {
                    "path": str(f.relative_to(root)),
                    "modified": datetime.fromtimestamp(
                        f.stat().st_mtime).strftime("%Y-%m-%d"),
                    "kb": round(f.stat().st_size / 1024, 1),
                }
                for f in files[: a.top]
            ],
        }

    if a.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Deliverables root: {root}")
    if a.since:
        print(f"Filtered to files modified on or after {a.since}")
    print(f"Total files: {total}")
    print("\nBy extension: " + ", ".join(
        f"{k} {v}" for k, v in report["extensions"].items()))
    print("\nBy class:")
    for cls, d in report["classes"].items():
        print(f"\n  {cls}  ({d['count']} files)")
        for f in d["newest"]:
            print(f"    {f['modified']}  {f['kb']:>7} KB  {f['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
