"""Keep .cursor/skills and .claude/skills identical.

The skills are the same Agent Skills either way; Cursor and Claude Code just
look in different folders. `.cursor/skills` is canonical. This mirrors it into
`.claude/skills` and reports drift.

    python scripts/sync_skills.py --check    report only, exit 1 on drift
    python scripts/sync_skills.py            mirror .cursor/skills to .claude/skills
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / ".cursor" / "skills"
DST = REPO / ".claude" / "skills"


def drift() -> list[str]:
    if not DST.is_dir():
        return ["<.claude/skills does not exist>"]
    out: list[str] = []
    src_names = {p.name for p in SRC.iterdir() if p.is_dir()}
    dst_names = {p.name for p in DST.iterdir() if p.is_dir()}
    for missing in sorted(src_names - dst_names):
        out.append(f"missing from .claude/skills: {missing}")
    for extra in sorted(dst_names - src_names):
        out.append(f"only in .claude/skills: {extra}")
    for name in sorted(src_names & dst_names):
        cmp = filecmp.dircmp(SRC / name, DST / name)
        stack = [cmp]
        while stack:
            c = stack.pop()
            for f in c.left_only:
                out.append(f"{name}: only in .cursor: {f}")
            for f in c.right_only:
                out.append(f"{name}: only in .claude: {f}")
            for f in c.diff_files:
                out.append(f"{name}: differs: {f}")
            stack.extend(c.subdirs.values())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report drift without changing anything")
    a = ap.parse_args()

    if not SRC.is_dir():
        print(f"ERROR canonical skills folder missing: {SRC}", file=sys.stderr)
        return 2

    problems = drift()
    if a.check:
        if problems:
            print(f"{len(problems)} difference(s) between .cursor/skills and "
                  ".claude/skills:")
            for p in problems[:20]:
                print(f"  {p}")
            if len(problems) > 20:
                print(f"  ... and {len(problems) - 20} more")
            print("\nRun: python scripts/sync_skills.py")
            return 1
        print("In sync: .cursor/skills and .claude/skills match.")
        return 0

    if not problems:
        print("Already in sync, nothing to do.")
        return 0

    if DST.exists():
        shutil.rmtree(DST)
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    n = len([p for p in DST.iterdir() if p.is_dir()])
    print(f"Mirrored {n} skills from .cursor/skills to .claude/skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
