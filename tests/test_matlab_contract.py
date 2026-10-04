from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "scripts" / "check_matlab_static.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_matlab_static", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_required_matlab_functions_and_signatures_exist():
    report = _load_checker().check_matlab_tree(ROOT / "matlab")
    assert report.missing_files == []
    assert report.signature_errors == []
    assert report.forbidden_absolute_paths == []


def test_matlab_sources_use_shared_relative_inputs_and_si_names():
    report = _load_checker().check_matlab_tree(ROOT / "matlab")
    assert report.missing_jsondecode_calls == []
    assert report.missing_si_markers == []


def test_parity_fixture_covers_stall_and_all_tracks():
    parity = pd.read_csv(ROOT / "results" / "parity" / "reference_cases.csv")
    assert {0, 10, 18, 25, 30}.issubset(set(parity.angle_deg))
    assert set(parity.track.dropna()) == {
        "low_downforce",
        "balanced",
        "high_downforce",
    }


def test_readme_discloses_matlab_runtime_status():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "MATLAB R2022b+" in text
    assert "not runtime-tested" in text
    assert "build_simulink_demo" in text


def test_simulink_builder_is_part_of_static_contract():
    report = _load_checker().check_matlab_tree(ROOT / "matlab")
    assert report.simulink_builder_errors == []


def test_matlab_entry_points_do_not_mix_char_vectors_with_string_plus():
    run_project = (ROOT / "matlab" / "run_project.m").read_text(encoding="utf-8")
    exporter = (ROOT / "matlab" / "+f1wing" / "exportResults.m").read_text(
        encoding="utf-8"
    )
    builder = (ROOT / "matlab" / "build_simulink_demo.m").read_text(encoding="utf-8")

    assert 'key + ".json"' not in run_project
    assert 'key + "_sweep.csv"' not in exporter
    assert "modelName = 'F1WingAeroDemo'" not in builder
