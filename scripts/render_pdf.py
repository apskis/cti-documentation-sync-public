"""Render a .docx or .pptx to PDF so the branding pass can be checked visually.

    python scripts/render_pdf.py path/to/file.docx [--out folder]

On Windows this drives the installed Office application through COM, which is
the highest fidelity option and the one to trust for a branding check.
Elsewhere it falls back to LibreOffice if soffice is on PATH.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def render_windows(src: Path, out_dir: Path) -> Path:
    import win32com.client  # type: ignore

    dest = out_dir / (src.stem + ".pdf")
    if src.suffix.lower() == ".docx":
        app = win32com.client.Dispatch("Word.Application")
        app.Visible = False
        try:
            doc = app.Documents.Open(str(src.resolve()), ReadOnly=True)
            doc.SaveAs(str(dest.resolve()), FileFormat=17)  # wdFormatPDF
            doc.Close(False)
        finally:
            app.Quit()
    elif src.suffix.lower() == ".pptx":
        app = win32com.client.Dispatch("PowerPoint.Application")
        try:
            pres = app.Presentations.Open(str(src.resolve()),
                                          WithWindow=False, ReadOnly=True)
            pres.SaveAs(str(dest.resolve()), 32)  # ppSaveAsPDF
            pres.Close()
        finally:
            app.Quit()
    else:
        raise SystemExit(f"unsupported input: {src.suffix}")
    return dest


def render_soffice(src: Path, out_dir: Path) -> Path:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit(
            "No renderer available. On Windows install pywin32 "
            "(pip install pywin32); elsewhere install LibreOffice."
        )
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(out_dir), str(src)],
        check=True, capture_output=True,
    )
    return out_dir / (src.stem + ".pdf")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path")
    ap.add_argument("--out", help="output folder, defaults beside the source")
    a = ap.parse_args()

    src = Path(a.path)
    if not src.is_file():
        print(f"ERROR not found: {src}", file=sys.stderr)
        return 1
    out_dir = Path(a.out) if a.out else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if platform.system() == "Windows":
        try:
            dest = render_windows(src, out_dir)
        except ImportError:
            dest = render_soffice(src, out_dir)
    else:
        dest = render_soffice(src, out_dir)

    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
