"""End-to-end acceptance and cross-artifact verification tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_project import verify_project, VerificationReport


@pytest.fixture(scope="module")
def project_verification_report() -> VerificationReport:
    return verify_project(ROOT)


def test_all_artifacts_share_run_id(project_verification_report):
    assert project_verification_report.run_id_consistent
    assert project_verification_report.run_id != ""


def test_headline_values_consistent(project_verification_report):
    assert project_verification_report.headline_values_consistent


def test_no_missing_artifacts_or_hash_mismatches(project_verification_report):
    assert project_verification_report.missing_artifacts == []
    assert project_verification_report.hash_mismatches == []


def test_report_and_presentation_valid(project_verification_report):
    assert project_verification_report.report_valid
    assert project_verification_report.presentation_valid


def test_matlab_code_is_statically_valid(project_verification_report):
    assert project_verification_report.matlab_valid


def test_full_project_verification_passes(project_verification_report):
    assert project_verification_report.all_passed


def test_verification_report_json_persisted():
    report_json_path = ROOT / "results" / "verification" / "verification_report.json"
    assert report_json_path.is_file()
    data = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert data["all_passed"] is True
    assert data["run_id"] != ""
