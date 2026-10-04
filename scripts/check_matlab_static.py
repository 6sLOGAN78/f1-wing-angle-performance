#!/usr/bin/env python3
"""Static contract checks for MATLAB sources when MATLAB is unavailable."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


REQUIRED_SIGNATURES = {
    "run_project.m": r"function\s+results\s*=\s*run_project\s*\(\s*configPath\s*,\s*outputDir\s*\)",
    "+f1wing/loadConfig.m": r"function\s+cfg\s*=\s*loadConfig\s*\(\s*configPath\s*\)",
    "+f1wing/loadTrack.m": r"function\s+track\s*=\s*loadTrack\s*\(\s*trackPath\s*,\s*spacing_m\s*\)",
    "+f1wing/wingCoefficients.m": r"function\s+wing\s*=\s*wingCoefficients\s*\(",
    "+f1wing/aeroState.m": r"function\s+state\s*=\s*aeroState\s*\(",
    "+f1wing/tyreMu.m": r"function\s+mu\s*=\s*tyreMu\s*\(",
    "+f1wing/wheelForce.m": r"function\s+state\s*=\s*wheelForce\s*\(",
    "+f1wing/solveLap.m": r"function\s+result\s*=\s*solveLap\s*\(",
    "+f1wing/fixedAngleSweep.m": r"function\s+tableOut\s*=\s*fixedAngleSweep\s*\(",
    "+f1wing/exportResults.m": r"function\s+exportResults\s*\(",
    "build_simulink_demo.m": r"function\s+modelPath\s*=\s*build_simulink_demo\s*\(",
    "run_parity_tests.m": r"function\s+run_parity_tests\s*\(",
}


class StaticReport:
    def __init__(self) -> None:
        self.missing_files: list[str] = []
        self.signature_errors: list[str] = []
        self.forbidden_absolute_paths: list[str] = []
        self.missing_jsondecode_calls: list[str] = []
        self.missing_si_markers: list[str] = []
        self.simulink_builder_errors: list[str] = []

    @property
    def ok(self) -> bool:
        return not any(
            (
                self.missing_files,
                self.signature_errors,
                self.forbidden_absolute_paths,
                self.missing_jsondecode_calls,
                self.missing_si_markers,
                self.simulink_builder_errors,
            )
        )


def check_matlab_tree(matlab_dir: Path) -> StaticReport:
    report = StaticReport()
    matlab_dir = Path(matlab_dir)
    loaded: dict[str, str] = {}
    for relative, signature in REQUIRED_SIGNATURES.items():
        path = matlab_dir / relative
        if not path.is_file():
            report.missing_files.append(relative)
            continue
        text = path.read_text(encoding="utf-8")
        loaded[relative] = text
        if re.search(signature, text, flags=re.IGNORECASE | re.MULTILINE) is None:
            report.signature_errors.append(relative)
        if re.search(r"/home/|[A-Za-z]:\\", text):
            report.forbidden_absolute_paths.append(relative)
        if "% SI units" not in text and not re.search(r"_(mps|mps2|kg|n|m|rad)\b", text):
            report.missing_si_markers.append(relative)

    for relative in ("+f1wing/loadConfig.m", "+f1wing/loadTrack.m"):
        if relative in loaded and "jsondecode" not in loaded[relative]:
            report.missing_jsondecode_calls.append(relative)

    builder = loaded.get("build_simulink_demo.m", "")
    for required in (
        "license('test', 'Simulink')",
        "new_system",
        "add_block",
        "save_system",
        "Rate Limiter",
        "MATLAB Function",
        "To Workspace",
    ):
        if required not in builder:
            report.simulink_builder_errors.append(f"missing {required}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matlab_dir", type=Path)
    args = parser.parse_args()
    report = check_matlab_tree(args.matlab_dir)
    if report.ok:
        print(f"MATLAB static contract: PASS ({len(REQUIRED_SIGNATURES)} files)")
        return 0
    for name in (
        "missing_files",
        "signature_errors",
        "forbidden_absolute_paths",
        "missing_jsondecode_calls",
        "missing_si_markers",
        "simulink_builder_errors",
    ):
        values = getattr(report, name)
        if values:
            print(f"{name}: {', '.join(values)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

