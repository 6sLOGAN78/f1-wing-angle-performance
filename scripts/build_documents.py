#!/usr/bin/env python3
"""Build the report now and, when available, the project presentation."""

from __future__ import annotations

import argparse
from pathlib import Path

from f1wing.documents import build_report, convert_office_to_pdf


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("results/manifest.json"))
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    root = args.manifest.resolve().parent.parent
    report_dir = root / "results" / "report"
    report = build_report(
        args.manifest,
        report_dir / "F1_Wing_Angle_Performance_Report.docx",
    )
    report_pdf = convert_office_to_pdf(report, report_dir)
    print(f"Report: {report}")
    print(f"Report PDF: {report_pdf}")
    if not args.report_only:
        try:
            from f1wing.presentation import build_presentation
        except ImportError:
            print("Presentation engine not installed yet; report build complete.")
        else:
            content = root / "presentation" / "slide_content.json"
            if content.is_file():
                deck_dir = root / "results" / "presentation"
                deck = build_presentation(args.manifest, content, deck_dir / "F1_Wing_Angle_Performance_Presentation.pptx")
                deck_pdf = convert_office_to_pdf(deck, deck_dir)
                print(f"Presentation: {deck}")
                print(f"Presentation PDF: {deck_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
