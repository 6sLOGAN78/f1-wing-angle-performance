from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from f1wing.config import (
    load_project_config,
    load_track,
    load_uncertainty_config,
)


ROOT = Path(__file__).resolve().parents[1]
TRACKS = ROOT / "tracks"


def _project_payload() -> dict:
    return {
        "metadata": {
            "name": "Test configuration",
            "version": "1.0",
            "parameter_classification": "representative educational model",
        },
        "environment": {"air_density_kgpm3": 1.225, "gravity_mps2": 9.80665},
        "vehicle": {
            "mass_kg": 798.0,
            "wheelbase_m": 3.6,
            "cg_height_m": 0.31,
            "front_static_fraction": 0.45,
            "tyre_radius_m": 0.36,
            "rolling_resistance_coefficient": 0.015,
        },
        "aero": {
            "reference_area_m2": 1.50,
            "wing_area_m2": 0.72,
            "wing_span_m": 1.00,
            "span_efficiency": 0.78,
            "lift_curve_slope_2d_per_rad": 6.10,
            "zero_lift_angle_deg": -2.0,
            "stall_angle_deg": 18.0,
            "post_stall_width_deg": 7.0,
            "wing_cd0": 0.055,
            "stall_drag_gain": 0.55,
            "baseline_cl": 2.40,
            "baseline_cd": 0.78,
            "baseline_front_downforce_fraction": 0.49,
            "front_aero_application_from_front_m": 1.15,
            "rear_aero_application_from_front_m": 3.25,
            "nominal_ride_height_m": 0.045,
            "ride_height_sensitivity_per_m": 2.0,
            "yaw_sensitivity_per_deg2": 0.0007,
            "minimum_multiplier": 0.70,
            "maximum_multiplier": 1.15,
            "minimum_angle_deg": 0.0,
            "maximum_angle_deg": 30.0,
        },
        "tyres": {
            "mu_longitudinal_ref": 1.85,
            "mu_lateral_ref": 1.95,
            "reference_load_n": 3915.0,
            "load_sensitivity_exponent": 0.08,
            "friction_ellipse_exponent": 2.0,
            "max_brake_force_n": 30000.0,
        },
        "powertrain": {
            "rpm_points": [5000, 8000, 11000, 13000, 15000],
            "torque_nm": [480, 590, 610, 570, 500],
            "gear_ratios": [3.20, 2.45, 1.95, 1.60, 1.36, 1.19, 1.06, 0.96],
            "final_drive_ratio": 3.15,
            "driveline_efficiency": 0.94,
            "idle_rpm": 5000.0,
            "redline_rpm": 15000.0,
            "driven_rear_fraction": 1.0,
        },
        "solver": {
            "track_spacing_m": 5.0,
            "speed_tolerance_mps": 0.001,
            "force_tolerance_n": 5.0,
            "max_iterations": 200,
            "minimum_speed_mps": 1.0,
            "maximum_speed_mps": 110.0,
        },
        "strategy": {
            "open_angle_deg": 2.0,
            "corner_angle_deg": 20.0,
            "activation_delay_s": 0.20,
            "deactivation_delay_s": 0.10,
            "max_actuator_rate_degps": 90.0,
            "activation_speed_mps": 55.0,
            "deactivation_long_accel_mps2": -1.0,
        },
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_all_tracks_are_closed_and_resolve_to_five_metres_or_less():
    for name in ("low_downforce", "balanced", "high_downforce"):
        track = load_track(TRACKS / f"{name}.json", spacing_m=5.0)
        assert track.closed
        assert track.ds_m.max() <= 5.0 + 1e-9
        assert track.length_m > 4_000
        assert np.all(np.isfinite(track.curvature_1pm))


def test_invalid_wing_bounds_are_rejected(tmp_path: Path):
    payload = _project_payload()
    payload["aero"]["minimum_angle_deg"] = 30.0
    payload["aero"]["maximum_angle_deg"] = 0.0
    path = _write_json(tmp_path / "project.json", payload)

    with pytest.raises(ValueError, match="wing-angle bounds"):
        load_project_config(path)


def test_inconsistent_powertrain_arrays_are_rejected(tmp_path: Path):
    payload = _project_payload()
    payload["powertrain"]["torque_nm"] = [480, 590]
    path = _write_json(tmp_path / "project.json", payload)

    with pytest.raises(ValueError, match="rpm_points and torque_nm"):
        load_project_config(path)


def test_nonfinite_vehicle_value_is_rejected(tmp_path: Path):
    payload = _project_payload()
    payload["vehicle"]["mass_kg"] = float("nan")
    path = _write_json(tmp_path / "project.json", payload)

    with pytest.raises(ValueError, match="mass_kg"):
        load_project_config(path)


def test_uncertainty_ranges_are_bounded_and_ordered(tmp_path: Path):
    bad = {
        "seed": 3106,
        "samples": 1000,
        "parameters": {
            "air_density_kgpm3": {
                "distribution": "uniform",
                "minimum": 1.30,
                "maximum": 1.00,
            }
        },
    }
    path = _write_json(tmp_path / "uncertainty.json", bad)

    with pytest.raises(ValueError, match="minimum.*maximum"):
        load_uncertainty_config(path)


def test_project_metadata_identifies_representative_model(tmp_path: Path):
    path = _write_json(tmp_path / "project.json", _project_payload())

    config = load_project_config(path)

    assert config.metadata.parameter_classification == "representative educational model"
    assert config.aero.minimum_angle_deg == 0.0
    assert config.aero.maximum_angle_deg == 30.0
