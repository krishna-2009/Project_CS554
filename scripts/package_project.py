#!/usr/bin/env python3
"""Package project sources, results, and the check-in report."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def included(path):
    rel = path.relative_to(ROOT)
    if any(part in {".git", "_build", ".build", "__pycache__", ".deps"} for part in rel.parts):
        return False
    if path.name in {".cs554-build-flags", "MANIFEST.sha256"}:
        return False
    if path.suffix in {".o", ".d", ".so", ".a", ".pyc", ".zip"}:
        return False
    if rel.parts[:2] == ("submission", "previous"):
        return False
    if rel.parts[:3] == ("results", "cds", "bin"):
        return False
    if rel.parts[0] == "report" and path.suffix in {".log", ".out", ".aux", ".fls", ".fdb_latexmk", ".gz", ".toc", ".bbl", ".blg"}:
        return False
    return path.is_file()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=ROOT / "submission/CS554_CheckIn_Project.zip")
    args = ap.parse_args()
    subprocess.run([sys.executable, str(ROOT / "scripts/run_experiments.py"), "--tables-only"], check=True)
    if not (ROOT / "report/checkin.pdf").is_file():
        raise SystemExit("Missing report/checkin.pdf; run make checkin first")
    files = sorted(p for p in ROOT.rglob("*") if included(p))
    manifest = ROOT / "MANIFEST.sha256"
    manifest.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}\n" for p in files))
    files.append(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in files:
            archive.write(p, Path("cs554-project") / p.relative_to(ROOT))
    print(f"Created {args.output}: {len(files)} files, {args.output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
