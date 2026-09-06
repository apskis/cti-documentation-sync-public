"""Preflight check for the CTI Documentation Sync workbench.

Run it any time. It never changes anything; it reports what is ready and what
is not, and names the fix for each problem.

    python scripts/doctor.py
    python scripts/doctor.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

OK, WARN, FAIL = "OK", "WARN", "FAIL"
results: list[dict] = []


def check(name: str, status: str, detail: str = "", fix: str = "") -> None:
    results.append({"check": name, "status": status, "detail": detail, "fix": fix})


def check_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        check("Python", OK, f"{v.major}.{v.minor}.{v.micro} at {sys.executable}")
    else:
        check("Python", FAIL, f"{v.major}.{v.minor}",
              "Install Python 3.10 or newer and run the bootstrap again.")


def check_deps() -> None:
    missing = []
    for mod, pkg in (("docx", "python-docx"), ("pptx", "python-pptx"),
                     ("openpyxl", "openpyxl"), ("PIL", "Pillow")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        check("Python packages", FAIL, "missing: " + ", ".join(missing),
              "Run scripts/bootstrap.ps1 (Windows) or scripts/bootstrap.sh, or "
              "pip install -r requirements.txt")
    else:
        check("Python packages", OK, "python-docx, python-pptx, openpyxl, Pillow")


def check_config() -> dict | None:
    cfg_path = REPO / "cti.config.json"
    if not cfg_path.exists():
        check("cti.config.json", FAIL, "not found",
              "Copy cti.config.example.json to cti.config.json, then set the "
              "two folder paths.")
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        check("cti.config.json", FAIL, f"invalid JSON: {exc}",
              "Fix the JSON. Use forward slashes in Windows paths so nothing "
              "needs escaping.")
        return None
    check("cti.config.json", OK, str(cfg_path))
    return cfg


def _expand(v: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(v)))


def check_folders(cfg: dict) -> tuple[Path | None, Path | None]:
    found: dict[str, Path | None] = {}
    for key in ("deliverables", "documentation"):
        raw = cfg.get(key)
        if not raw:
            check(f"Folder: {key}", FAIL, "not set in cti.config.json",
                  "Set it to the full path of the folder on this machine.")
            found[key] = None
            continue
        p = _expand(raw)
        if p.is_dir():
            n = sum(1 for _ in p.iterdir())
            check(f"Folder: {key}", OK, f"{p}  ({n} entries)")
            found[key] = p
        else:
            check(f"Folder: {key}", FAIL, f"not found: {p}",
                  "Check the path. If OneDrive uses a different account folder "
                  "name on this machine, the path will differ from the example.")
            found[key] = None
    return found["deliverables"], found["documentation"]


def check_documents(doc_root: Path, cfg: dict) -> None:
    strategy = doc_root / "Strategy_and_Plan"
    if not strategy.is_dir():
        check("Strategy_and_Plan", FAIL, f"not found under {doc_root}",
              "Confirm the documentation folder path points at the CTI "
              "Documentation tree, not its parent.")
        return
    check("Strategy_and_Plan", OK, str(strategy))

    for key, meta in (cfg.get("documents") or {}).items():
        rel = meta.get("file")
        if not rel:
            continue
        p = doc_root / rel
        if p.is_file():
            kb = round(p.stat().st_size / 1024, 1)
            check(f"Document: {key}", OK, f"{p.name}  ({kb} KB)")
        else:
            check(f"Document: {key}", FAIL, f"not found: {p}",
                  "The sync cannot run without it. Confirm the file name in "
                  "cti.config.json matches what is on disk.")

    for rel in cfg.get("protected") or []:
        p = doc_root / rel
        if p.is_file():
            check(f"Protected: {Path(rel).name}", OK, "present, never written to")
        else:
            check(f"Protected: {Path(rel).name}", WARN, f"not found: {p}",
                  "Not fatal. The sync never writes to it either way.")


def check_doc_sync(doc_root: Path) -> None:
    ds = doc_root / "_doc_sync"
    if not ds.is_dir():
        check("_doc_sync", WARN, f"not found: {ds}",
              "The first run creates it. If the folder existed before, check "
              "the documentation path.")
        return
    check("_doc_sync", OK, str(ds))

    state = ds / "portfolio_state.md"
    if state.is_file():
        lines = state.read_text(encoding="utf-8", errors="replace").splitlines()
        check("State record", OK, f"portfolio_state.md  ({len(lines)} lines)")
    else:
        check("State record", FAIL, "portfolio_state.md not found",
              "This is the comparison baseline. Do not let the sync invent one "
              "from file timestamps: rebuild it in a run that makes no document "
              "edits, then confirm it before the next real sync.")

    backups = ds / "backups"
    if backups.is_dir():
        n = len(list(backups.glob("*")))
        check("Backups folder", OK, f"{n} existing backups")
    else:
        check("Backups folder", WARN, "not found",
              "Created automatically on the first backup.")


def check_locks(doc_root: Path) -> None:
    strategy = doc_root / "Strategy_and_Plan"
    if not strategy.is_dir():
        return
    locks = [p.name for p in strategy.glob("~$*")]
    if locks:
        check("Word lock files", WARN, ", ".join(locks),
              "A document is open in Word. Close it before a sync run, or the "
              "run will refuse to write to it.")
    else:
        check("Word lock files", OK, "none, nothing is open in Word")


def _version_of(exe: str) -> str:
    try:
        out = subprocess.run([exe, "--version"], capture_output=True,
                             text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0][:40]
    except Exception:  # noqa: BLE001
        return ""


def check_engines() -> None:
    """Either agent CLI can drive a headless run. At least one is needed."""
    claude = shutil.which("claude")
    cursor = shutil.which("cursor-agent") or shutil.which("agent")

    if claude:
        check("Claude Code CLI", OK, f"{claude} {_version_of(claude)}".strip())
    else:
        check("Claude Code CLI", WARN, "not on PATH",
              "Install: npm install -g @anthropic-ai/claude-code")

    if cursor:
        check("Cursor CLI", OK, f"{cursor} {_version_of(cursor)}".strip())
    else:
        install = ("irm 'https://cursor.com/install?win32=true' | iex"
                   if platform.system() == "Windows"
                   else "curl https://cursor.com/install -fsS | bash")
        check("Cursor CLI", WARN, "not on PATH", f"Install: {install}")

    if claude or cursor:
        picked = "claude" if claude else "cursor"
        check("Headless engine", OK,
              f"scheduled runs will use {picked} unless -Engine says otherwise")
    else:
        check("Headless engine", FAIL, "neither CLI is installed",
              "Scheduled and headless runs need one of them. Interactive use "
              "inside the Cursor or Claude Code editor works without either.")


def check_skill_mirror() -> None:
    """Cursor reads .cursor/skills, Claude Code reads .claude/skills."""
    claude_skills = REPO / ".claude" / "skills"
    if not claude_skills.is_dir():
        check("Skill mirror", FAIL, ".claude/skills is missing",
              "Run: python scripts/sync_skills.py")
        return
    try:
        out = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "sync_skills.py"), "--check"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        check("Skill mirror", WARN, f"could not check: {exc}",
              "Run: python scripts/sync_skills.py --check")
        return
    if out.returncode == 0:
        n = len([p for p in claude_skills.iterdir() if p.is_dir()])
        check("Skill mirror", OK,
              f".cursor/skills and .claude/skills match ({n} skills)")
    else:
        check("Skill mirror", WARN, "the two skills folders have drifted",
              "Run: python scripts/sync_skills.py")


def check_renderer() -> None:
    if platform.system() == "Windows":
        try:
            import win32com.client  # noqa: F401
            check("PDF renderer", OK, "pywin32, renders through Word and "
                                      "PowerPoint")
            return
        except ImportError:
            pass
        if shutil.which("soffice"):
            check("PDF renderer", WARN, "LibreOffice only",
                  "Word gives a higher fidelity render for the branding check. "
                  "pip install pywin32")
        else:
            check("PDF renderer", FAIL, "none available",
                  "pip install pywin32, or install LibreOffice.")
    else:
        if shutil.which("soffice") or shutil.which("libreoffice"):
            check("PDF renderer", OK, "LibreOffice")
        else:
            check("PDF renderer", WARN, "none available",
                  "Install LibreOffice so the branding pass can be checked "
                  "visually.")


def check_skills() -> None:
    d = REPO / ".cursor" / "skills"
    skills = sorted(p.name for p in d.iterdir() if (p / "SKILL.md").is_file())
    if len(skills) >= 18:
        check("Skills", OK, f"{len(skills)} loaded, including cti-doc-sync")
    elif skills:
        check("Skills", WARN, f"only {len(skills)} found: {', '.join(skills)}",
              "Some skills did not come across. Re extract the repository.")
    else:
        check("Skills", FAIL, "none found",
              "Check that .cursor/skills survived extraction.")


def check_rules() -> None:
    d = REPO / ".cursor" / "rules"
    rules = sorted(p.name for p in d.glob("*.mdc")) if d.is_dir() else []
    if len(rules) >= 3:
        check("Rules", OK, ", ".join(rules))
    else:
        check("Rules", WARN, f"{len(rules)} found",
              "Expected three .mdc files under .cursor/rules.")


def check_bedrock() -> None:
    """This build routes to Bedrock; bedrock_doctor.py checks it properly."""
    env_file = REPO / "config" / "bedrock.env"
    if env_file.exists():
        check("Bedrock config", OK, "config/bedrock.env present",
              "Verify it with: python scripts/bedrock_doctor.py --invoke")
    else:
        check("Bedrock config", FAIL, "config/bedrock.env not found",
              "This build sends model calls to Bedrock. Copy "
              "config/bedrock.env.example to config/bedrock.env and fill it "
              "in, or let Claude Code's wizard write ~/.claude/settings.json "
              "instead (run claude, pick 3rd-party platform, Amazon Bedrock). "
              "Then run: python scripts/bedrock_doctor.py")


def check_notify() -> None:
    if os.environ.get("CTI_NOTIFY_WEBHOOK"):
        check("Notification", OK, "CTI_NOTIFY_WEBHOOK is set")
    else:
        check("Notification", WARN, "webhook not configured",
              "Without it a run summary reaches you only as a desktop toast "
              "and a file on disk. Set CTI_NOTIFY_WEBHOOK to a Teams or Slack "
              "incoming webhook to be told when you are away from the machine.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    check_python()
    check_deps()
    check_skills()
    check_rules()
    check_skill_mirror()
    cfg = check_config()
    if cfg:
        deliv, doc = check_folders(cfg)
        if doc:
            check_documents(doc, cfg)
            check_doc_sync(doc)
            check_locks(doc)
    check_engines()
    check_renderer()
    check_bedrock()
    check_notify()

    if a.json:
        print(json.dumps(results, indent=2))
    else:
        width = max(len(r["check"]) for r in results)
        print("CTI Documentation Sync preflight")
        print("=" * (width + 60))
        for r in results:
            print(f"  [{r['status']:4}] {r['check']:<{width}}  {r['detail']}")
        problems = [r for r in results if r["status"] in (WARN, FAIL)]
        if problems:
            print("\nFixes")
            print("-" * (width + 60))
            for r in problems:
                print(f"\n  {r['status']}  {r['check']}")
                print(f"       {r['fix']}")

    fails = sum(1 for r in results if r["status"] == FAIL)
    warns = sum(1 for r in results if r["status"] == WARN)
    if not a.json:
        print(f"\n{len(results)} checks, {fails} failing, {warns} warning.")
        if fails == 0:
            print("Ready to run." if warns == 0
                  else "Ready to run, with the warnings above worth reading.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
