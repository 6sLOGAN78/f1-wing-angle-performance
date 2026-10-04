"""Strict loading and validation for project and track inputs."""

from __future__ import annotations

from dataclasses import fields
import json
import math
from pathlib import Path
from typing import Any, TypeVar

import numpy as np

from .models import (
    AeroConfig,
    EnvironmentConfig,
    Metadata,
    PowertrainConfig,
    ProjectConfig,
    SolverConfig,
    StrategyConfig,
    Track,
    TyreConfig,
    UncertaintyConfig,
    UncertaintyParameter,
    VehicleConfig,
)


T = TypeVar("T")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read valid JSON from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Top-level JSON value in {path} must be an object")
    return data


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _construct(cls: type[T], data: dict[str, Any], section: str) -> T:
    names = {item.name for item in fields(cls)}
    missing = names - data.keys()
    extra = data.keys() - names
    if missing:
        raise ValueError(f"{section} is missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{section} has unknown fields: {', '.join(sorted(extra))}")
    try:
        return cls(**data)
    except TypeError as exc:
        raise ValueError(f"Invalid {section} values: {exc}") from exc


def _finite_positive(name: str, value: float, *, allow_zero: bool = False) -> None:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    if allow_zero:
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    elif value <= 0:
        raise ValueError(f"{name} must be positive")


def _fraction(name: str, value: float, *, inclusive: bool = False) -> None:
    _finite_positive(name, value)
    valid = 0 < value <= 1 if inclusive else 0 < value < 1
    if not valid:
        raise ValueError(f"{name} must lie in (0, 1{' ]' if inclusive else ')'}")


def load_project_config(path: Path) -> ProjectConfig:
    """Load and validate a complete representative vehicle configuration."""

    data = _read_json(path)
    required_sections = {
        "metadata",
        "environment",
        "vehicle",
        "aero",
        "tyres",
        "powertrain",
        "solver",
        "strategy",
    }
    missing = required_sections - data.keys()
    extra = data.keys() - required_sections - {"parameter_register"}
    if missing:
        raise ValueError(f"project configuration is missing sections: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"project configuration has unknown sections: {', '.join(sorted(extra))}")

    metadata = _construct(Metadata, _require_mapping(data, "metadata"), "metadata")
    environment = _construct(EnvironmentConfig, _require_mapping(data, "environment"), "environment")
    vehicle = _construct(VehicleConfig, _require_mapping(data, "vehicle"), "vehicle")
    aero = _construct(AeroConfig, _require_mapping(data, "aero"), "aero")
    tyres = _construct(TyreConfig, _require_mapping(data, "tyres"), "tyres")
    raw_powertrain = _require_mapping(data, "powertrain").copy()
    for key in ("rpm_points", "torque_nm", "gear_ratios"):
        if not isinstance(raw_powertrain.get(key), list):
            raise ValueError(f"powertrain.{key} must be an array")
        raw_powertrain[key] = tuple(float(value) for value in raw_powertrain[key])
    powertrain = _construct(PowertrainConfig, raw_powertrain, "powertrain")
    solver = _construct(SolverConfig, _require_mapping(data, "solver"), "solver")
    strategy = _construct(StrategyConfig, _require_mapping(data, "strategy"), "strategy")

    for name, value in (
        ("environment.air_density_kgpm3", environment.air_density_kgpm3),
        ("environment.gravity_mps2", environment.gravity_mps2),
        ("vehicle.mass_kg", vehicle.mass_kg),
        ("vehicle.wheelbase_m", vehicle.wheelbase_m),
        ("vehicle.tyre_radius_m", vehicle.tyre_radius_m),
        ("aero.reference_area_m2", aero.reference_area_m2),
        ("aero.wing_area_m2", aero.wing_area_m2),
        ("aero.wing_span_m", aero.wing_span_m),
        ("aero.post_stall_width_deg", aero.post_stall_width_deg),
        ("tyres.reference_load_n", tyres.reference_load_n),
        ("tyres.max_brake_force_n", tyres.max_brake_force_n),
        ("powertrain.final_drive_ratio", powertrain.final_drive_ratio),
        ("solver.track_spacing_m", solver.track_spacing_m),
        ("solver.speed_tolerance_mps", solver.speed_tolerance_mps),
        ("solver.force_tolerance_n", solver.force_tolerance_n),
        ("solver.max_iterations", solver.max_iterations),
    ):
        _finite_positive(name, value)
    for name, value in (
        ("vehicle.cg_height_m", vehicle.cg_height_m),
        ("vehicle.rolling_resistance_coefficient", vehicle.rolling_resistance_coefficient),
        ("aero.wing_cd0", aero.wing_cd0),
        ("aero.baseline_cl", aero.baseline_cl),
        ("aero.baseline_cd", aero.baseline_cd),
        ("tyres.load_sensitivity_exponent", tyres.load_sensitivity_exponent),
    ):
        _finite_positive(name, value, allow_zero=True)
    for name, value in (
        ("vehicle.front_static_fraction", vehicle.front_static_fraction),
        ("aero.span_efficiency", aero.span_efficiency),
        ("aero.baseline_front_downforce_fraction", aero.baseline_front_downforce_fraction),
        ("powertrain.driveline_efficiency", powertrain.driveline_efficiency),
        ("powertrain.driven_rear_fraction", powertrain.driven_rear_fraction),
    ):
        _fraction(name, value, inclusive=True)

    if not aero.minimum_angle_deg < aero.maximum_angle_deg:
        raise ValueError("invalid wing-angle bounds: minimum must be below maximum")
    if aero.stall_angle_deg <= aero.minimum_angle_deg:
        raise ValueError("aero.stall_angle_deg must exceed the minimum wing angle")
    if len(powertrain.rpm_points) != len(powertrain.torque_nm):
        raise ValueError("powertrain rpm_points and torque_nm must have equal lengths")
    if len(powertrain.rpm_points) < 2 or not all(
        left < right for left, right in zip(powertrain.rpm_points, powertrain.rpm_points[1:])
    ):
        raise ValueError("powertrain.rpm_points must be strictly increasing")
    if not powertrain.gear_ratios or any(value <= 0 for value in powertrain.gear_ratios):
        raise ValueError("powertrain.gear_ratios must contain positive values")
    if powertrain.idle_rpm >= powertrain.redline_rpm:
        raise ValueError("powertrain idle_rpm must be below redline_rpm")
    if solver.minimum_speed_mps >= solver.maximum_speed_mps:
        raise ValueError("solver minimum speed must be below maximum speed")
    if metadata.parameter_classification.strip().lower() != "representative educational model":
        raise ValueError("metadata must identify a representative educational model")

    register = data.get("parameter_register", {})
    if not isinstance(register, dict):
        raise ValueError("parameter_register must be an object")
    for key, note in register.items():
        if not isinstance(note, dict) or not {"unit", "classification", "description"}.issubset(note):
            raise ValueError(f"parameter_register.{key} lacks unit/classification/description")
        if note["classification"] not in {"assumed", "derived", "reference-informed"}:
            raise ValueError(f"parameter_register.{key} has invalid classification")

    return ProjectConfig(
        metadata=metadata,
        environment=environment,
        vehicle=vehicle,
        aero=aero,
        tyres=tyres,
        powertrain=powertrain,
        solver=solver,
        strategy=strategy,
        parameter_register=register,
    )


def load_uncertainty_config(path: Path) -> UncertaintyConfig:
    """Load bounded input distributions used by the uncertainty analysis."""

    data = _read_json(path)
    if set(data) != {"seed", "samples", "parameters"}:
        raise ValueError("uncertainty configuration requires seed, samples, and parameters only")
    seed = data["seed"]
    samples = data["samples"]
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("uncertainty seed must be a non-negative integer")
    if not isinstance(samples, int) or samples < 1000:
        raise ValueError("uncertainty samples must be an integer of at least 1000")
    raw_parameters = data["parameters"]
    if not isinstance(raw_parameters, dict) or not raw_parameters:
        raise ValueError("uncertainty parameters must be a non-empty object")
    parameters: dict[str, UncertaintyParameter] = {}
    for name, raw in raw_parameters.items():
        if not isinstance(raw, dict) or set(raw) != {"distribution", "minimum", "maximum"}:
            raise ValueError(f"uncertainty parameter {name} requires distribution/minimum/maximum")
        distribution = raw["distribution"]
        minimum = raw["minimum"]
        maximum = raw["maximum"]
        if distribution != "uniform":
            raise ValueError(f"uncertainty parameter {name} uses unsupported distribution")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (minimum, maximum)):
            raise ValueError(f"uncertainty parameter {name} bounds must be finite")
        if minimum >= maximum:
            raise ValueError(f"uncertainty parameter {name} minimum must be below maximum")
        parameters[name] = UncertaintyParameter(distribution, float(minimum), float(maximum))
    return UncertaintyConfig(seed=seed, samples=samples, parameters=parameters)


def load_track(path: Path, spacing_m: float) -> Track:
    """Discretize a synthetic segment-based circuit definition."""

    _finite_positive("spacing_m", spacing_m)
    data = _read_json(path)
    required = {"name", "description", "closed", "segments"}
    if set(data) != required:
        raise ValueError(f"track requires exactly: {', '.join(sorted(required))}")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("track name must be non-empty")
    if not isinstance(data["closed"], bool):
        raise ValueError("track closed must be boolean")
    segments = data["segments"]
    if not isinstance(segments, list) or not segments:
        raise ValueError("track segments must be a non-empty array")

    ds_values: list[float] = []
    curvature_values: list[float] = []
    gradient_values: list[float] = []
    eligible_values: list[bool] = []
    speed_limit_values: list[float] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"track segment {index} must be an object")
        expected = {
            "length_m",
            "curvature_start_1pm",
            "curvature_end_1pm",
            "gradient_percent",
            "aero_eligible",
            "speed_limit_kph",
        }
        if set(segment) != expected:
            raise ValueError(f"track segment {index} has incorrect fields")
        length = segment["length_m"]
        _finite_positive(f"track segment {index} length_m", length)
        for key in ("curvature_start_1pm", "curvature_end_1pm", "gradient_percent"):
            value = segment[key]
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"track segment {index} {key} must be finite")
        if not isinstance(segment["aero_eligible"], bool):
            raise ValueError(f"track segment {index} aero_eligible must be boolean")
        limit_kph = segment["speed_limit_kph"]
        if limit_kph is not None:
            _finite_positive(f"track segment {index} speed_limit_kph", limit_kph)

        count = int(math.ceil(length / spacing_m))
        ds = float(length) / count
        fractions = (np.arange(count, dtype=float) + 0.5) / count
        curvatures = float(segment["curvature_start_1pm"]) + fractions * (
            float(segment["curvature_end_1pm"]) - float(segment["curvature_start_1pm"])
        )
        ds_values.extend([ds] * count)
        curvature_values.extend(curvatures.tolist())
        gradient_values.extend([math.atan(float(segment["gradient_percent"]) / 100.0)] * count)
        eligible_values.extend([segment["aero_eligible"]] * count)
        speed_limit_values.extend([math.inf if limit_kph is None else float(limit_kph) / 3.6] * count)

    ds_array = np.asarray(ds_values, dtype=float)
    distance = np.concatenate(([0.0], np.cumsum(ds_array[:-1])))
    return Track(
        name=data["name"],
        description=data["description"],
        closed=data["closed"],
        distance_m=distance,
        ds_m=ds_array,
        curvature_1pm=np.asarray(curvature_values, dtype=float),
        gradient_rad=np.asarray(gradient_values, dtype=float),
        aero_eligible=np.asarray(eligible_values, dtype=bool),
        speed_limit_mps=np.asarray(speed_limit_values, dtype=float),
    )

