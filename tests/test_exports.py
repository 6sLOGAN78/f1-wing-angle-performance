from __future__ import annotations

import hashlib
import json
from pathlib import Path
import warnings

import pandas as pd
import pytest
from scipy.io import loadmat

from f1wing.analysis import monte_carlo
from f1wing.config import load_project_config, load_uncertainty_config
from f1wing.exports import export_result_bundle, run_full_analysis


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def result_bundle(tmp_path_factory):
    scratch = tmp_path_factory.mktemp("bundle-input")
    return run_full_analysis(
        ROOT / "config" / "project.json",
        ROOT / "tracks",
        scratch,
        angle_grid=(0, 10, 18, 25, 30),
        track_spacing_override_m=100.0,
    )


@pytest.fixture()
def exported(result_bundle, tmp_path):
    manifest_path = export_result_bundle(result_bundle, tmp_path)
    return tmp_path, manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))


def test_manifest_links_every_figure_to_data(exported):
    output_dir, _, manifest = exported
    assert len(manifest["figures"]) >= 14
    for figure in manifest["figures"]:
        assert (output_dir / figure["path"]).is_file()
        assert (output_dir / figure["source_data"]).is_file()
        assert figure["caption"]
        assert figure["units"]


def test_xlsx_and_csv_headline_values_match(exported):
    output_dir, _, manifest = exported
    csv_table = pd.read_csv(output_dir / manifest["tables"]["circuit_optima"]["csv"])
    xlsx_table = pd.read_excel(
        output_dir / manifest["workbook"],
        sheet_name="circuit_optima",
    )
    pd.testing.assert_frame_equal(csv_table, xlsx_table, check_dtype=False)


def test_matlab_file_and_parity_fixture_are_readable(exported):
    output_dir, _, manifest = exported
    mat = loadmat(output_dir / manifest["matlab_data"])
    assert "aero_polar" in mat
    assert "circuit_optima" in mat
    parity = pd.read_csv(output_dir / manifest["parity_fixture"])
    assert {0, 10, 18, 25, 30}.issubset(set(parity.angle_deg))
    assert {"low_downforce", "balanced", "high_downforce"}.issubset(
        set(parity.track.dropna())
    )


def test_manifest_hashes_match_artifacts(exported):
    output_dir, _, manifest = exported
    for relative_path, expected in manifest["artifact_sha256"].items():
        actual = hashlib.sha256((output_dir / relative_path).read_bytes()).hexdigest()
        assert actual == expected


def test_run_id_is_deterministic_for_identical_inputs(result_bundle, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = json.loads(
        export_result_bundle(result_bundle, first).read_text(encoding="utf-8")
    )
    second_manifest = json.loads(
        export_result_bundle(result_bundle, second).read_text(encoding="utf-8")
    )
    assert first_manifest["run_id"] == second_manifest["run_id"]
    assert first_manifest["input_sha256"] == second_manifest["input_sha256"]


def test_manifest_carries_headline_optima_and_interpretation_warning(exported):
    _, _, manifest = exported
    assert set(manifest["headline_metrics"]["fixed_optimum_angle_deg"]) == {
        "low_downforce",
        "balanced",
        "high_downforce",
    }
    assert "representative educational model" in manifest["interpretation_warning"].lower()
    assert "CFD" not in " ".join(item["caption"] for item in manifest["figures"])


def test_constant_monte_carlo_output_does_not_emit_rank_warning():
    config = load_project_config(ROOT / "config" / "project.json")
    uncertainty = load_uncertainty_config(ROOT / "config" / "uncertainty.json")
    sweep = pd.DataFrame(
        {
            "angle_deg": [0.0, 10.0, 20.0],
            "lap_time_s": [60.0, 50.0, 60.0],
            "full_throttle_fraction": [0.5, 0.5, 0.5],
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = monte_carlo(config, uncertainty, sweep, samples=1000)
    assert result.correlations.spearman_rho.notna().all()
