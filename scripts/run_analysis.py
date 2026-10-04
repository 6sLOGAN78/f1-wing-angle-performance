#!/usr/bin/env python3
"""Command-line entry point for the complete numerical analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from f1wing.exports import export_result_bundle, run_full_analysis


def _safe_clean(path: Path) -> None:
    resolved = path.resolve()
    if resolved == Path.cwd().resolve() or resolved == Path(resolved.anchor):
        raise ValueError("refusing to clean the project or filesystem root")
    if resolved.exists():
        for child in resolved.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tracks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    if args.clean:
        _safe_clean(args.output)
    bundle = run_full_analysis(args.config, args.tracks, args.output)
    manifest = export_result_bundle(bundle, args.output)
    print(f"Analysis complete: {manifest}")
    print(f"Run ID: {bundle.run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
