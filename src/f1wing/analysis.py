"""Wing-angle sweeps, optimization, sensitivity, and uncertainty analysis."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize_scalar
from scipy.stats import spearmanr

from .lap import solve_lap
from .models import ProjectConfig, Track, UncertaintyConfig
from .strategies import ActiveAeroSchedule, FixedAngleSchedule


@dataclass(frozen=True)
class OptimizationResult:
    angle_deg: float
    lap_time_s: float
    success: bool
    method: str
    evaluated_points: pd.DataFrame
    neighbour_sensitivity_s_per_deg: float
    open_angle_deg: float | None = None
    closed_angle_deg: float | None = None


@dataclass(frozen=True)
class MonteCarloResult:
    samples: pd.DataFrame
    summary: pd.DataFrame
    correlations: pd.DataFrame
    method: str


def _lap_row(angle: float, result) -> dict[str, float | bool | int]:
    return {
        "angle_deg": float(angle),
        "lap_time_s": result.lap_time_s,
        "maximum_speed_kph": result.maximum_speed_mps * 3.6,
        "minimum_speed_kph": result.minimum_speed_mps * 3.6,
        "tractive_energy_mj": result.tractive_energy_j / 1e6,
        "full_throttle_fraction": result.full_throttle_fraction,
        "maximum_braking_demand_kn": result.maximum_braking_demand_n / 1000.0,
        "iterations": result.iterations,
        "converged": result.converged,
    }


def fixed_angle_sweep(
    track: Track,
    cfg: ProjectConfig,
    angles_deg: Sequence[float],
) -> pd.DataFrame:
    """Evaluate fixed rear-wing angles while caching duplicate requests."""

    cache: dict[float, dict[str, float | bool | int]] = {}
    rows: list[dict[str, float | bool | int]] = []
    for raw_angle in angles_deg:
        angle = float(raw_angle)
        if not math.isfinite(angle):
            raise ValueError("sweep angles must be finite")
        if not cfg.aero.minimum_angle_deg <= angle <= cfg.aero.maximum_angle_deg:
            raise ValueError("sweep angle lies outside configured wing-angle bounds")
        key = round(angle, 9)
        if key not in cache:
            cache[key] = _lap_row(angle, solve_lap(track, cfg, FixedAngleSchedule(angle)))
        rows.append(cache[key].copy())
    return pd.DataFrame(rows)


def optimize_fixed_angle(
    track: Track,
    cfg: ProjectConfig,
    *,
    sweep_table: pd.DataFrame | None = None,
) -> OptimizationResult:
    """Refine the discrete sweep using shape-preserving interpolation."""

    table = (
        fixed_angle_sweep(track, cfg, range(31))
        if sweep_table is None
        else sweep_table.copy()
    )
    ordered = table.sort_values("angle_deg").drop_duplicates("angle_deg")
    if ordered.shape[0] < 3:
        raise ValueError("optimization requires at least three unique sweep angles")
    interpolator = PchipInterpolator(ordered.angle_deg, ordered.lap_time_s)
    bounded = minimize_scalar(
        lambda value: float(interpolator(value)),
        bounds=(cfg.aero.minimum_angle_deg, cfg.aero.maximum_angle_deg),
        method="bounded",
        options={"xatol": 0.02},
    )
    candidate_angle = float(np.clip(bounded.x, cfg.aero.minimum_angle_deg, cfg.aero.maximum_angle_deg))
    candidate_result = solve_lap(track, cfg, FixedAngleSchedule(candidate_angle))
    candidate_row = _lap_row(candidate_angle, candidate_result)
    evaluated = pd.concat([table, pd.DataFrame([candidate_row])], ignore_index=True)
    discrete_best = ordered.loc[ordered.lap_time_s.idxmin()]
    if candidate_result.lap_time_s <= float(discrete_best.lap_time_s):
        best_angle = candidate_angle
        best_time = candidate_result.lap_time_s
    else:
        best_angle = float(discrete_best.angle_deg)
        best_time = float(discrete_best.lap_time_s)
    lower = max(cfg.aero.minimum_angle_deg, best_angle - 1.0)
    upper = min(cfg.aero.maximum_angle_deg, best_angle + 1.0)
    sensitivity = (
        float(interpolator(upper)) - float(interpolator(lower))
    ) / max(upper - lower, 1e-12)
    return OptimizationResult(
        angle_deg=best_angle,
        lap_time_s=best_time,
        success=bool(bounded.success and candidate_result.converged),
        method="integer sweep + PCHIP bounded refinement",
        evaluated_points=evaluated,
        neighbour_sensitivity_s_per_deg=sensitivity,
    )


def optimize_active_angles(
    track: Track,
    cfg: ProjectConfig,
    *,
    actuator_limited: bool,
) -> OptimizationResult:
    """Search a compact low/high-angle grid for a two-state strategy."""

    low_candidates = sorted({cfg.aero.minimum_angle_deg, cfg.strategy.open_angle_deg, 5.0})
    high_candidates = (12.0, 15.0, 18.0, 21.0, 24.0)
    rows: list[dict[str, float | bool]] = []
    for low in low_candidates:
        for high in high_candidates:
            if low >= high or high > cfg.aero.maximum_angle_deg:
                continue
            schedule = ActiveAeroSchedule.from_config(
                cfg,
                actuator_limited=actuator_limited,
                open_angle_deg=low,
                closed_angle_deg=high,
            )
            result = solve_lap(track, cfg, schedule)
            rows.append(
                {
                    "open_angle_deg": low,
                    "closed_angle_deg": high,
                    "lap_time_s": result.lap_time_s,
                    "converged": result.converged,
                    "actuator_limited": actuator_limited,
                }
            )
    table = pd.DataFrame(rows)
    best = table.loc[table.lap_time_s.idxmin()]
    return OptimizationResult(
        angle_deg=float(best.closed_angle_deg),
        lap_time_s=float(best.lap_time_s),
        success=bool(best.converged),
        method=("actuator-limited grid" if actuator_limited else "ideal two-state grid"),
        evaluated_points=table,
        neighbour_sensitivity_s_per_deg=float("nan"),
        open_angle_deg=float(best.open_angle_deg),
        closed_angle_deg=float(best.closed_angle_deg),
    )


def _replace_config_value(cfg: ProjectConfig, path: str, value: float) -> ProjectConfig:
    section_name, field_name = path.split(".", 1)
    section = getattr(cfg, section_name)
    return replace(cfg, **{section_name: replace(section, **{field_name: value})})


def oat_sensitivity(
    track: Track,
    cfg: ProjectConfig,
    optimum_angle_deg: float,
    *,
    fraction: float = 0.10,
    parameters: Sequence[str] = (
        "environment.air_density_kgpm3",
        "tyres.mu_lateral_ref",
        "tyres.mu_longitudinal_ref",
        "aero.wing_cd0",
        "aero.baseline_cl",
    ),
) -> pd.DataFrame:
    """Evaluate one-at-a-time lap-time sensitivity at the nominal optimum."""

    nominal = solve_lap(track, cfg, FixedAngleSchedule(optimum_angle_deg)).lap_time_s
    rows: list[dict[str, float | str]] = []
    for path in parameters:
        section_name, field_name = path.split(".", 1)
        base = float(getattr(getattr(cfg, section_name), field_name))
        for direction in (-1.0, 1.0):
            perturbed = base * (1.0 + direction * fraction)
            changed = _replace_config_value(cfg, path, perturbed)
            lap_time = solve_lap(track, changed, FixedAngleSchedule(optimum_angle_deg)).lap_time_s
            rows.append(
                {
                    "parameter": path,
                    "perturbation_percent": direction * fraction * 100.0,
                    "baseline_lap_time_s": nominal,
                    "lap_time_s": lap_time,
                    "change_from_nominal_s": lap_time - nominal,
                }
            )
    return pd.DataFrame(rows)


def _nominal_parameter_value(name: str, cfg: ProjectConfig) -> float:
    if name == "environment.headwind_mps":
        return 0.0
    if name in {"powertrain.power_scale", "aero.lift_curve_slope_scale"}:
        return 1.0
    section_name, field_name = name.split(".", 1)
    return float(getattr(getattr(cfg, section_name), field_name))


def monte_carlo(
    cfg: ProjectConfig,
    uncertainty: UncertaintyConfig,
    nominal_sweep: pd.DataFrame,
    *,
    samples: int | None = None,
) -> MonteCarloResult:
    """Propagate bounded uncertainty through a documented response surface.

    The response surface uses the fully solved nominal angle sweep and applies
    first-order physics scalings to its straight- and corner-dominated time
    fractions. This makes 1,000+ reproducible samples practical while retaining
    the nonlinear nominal angle/lap-time relationship.
    """

    count = uncertainty.samples if samples is None else samples
    if count < 1000:
        raise ValueError("Monte Carlo analysis requires at least 1000 samples")
    ordered = nominal_sweep.sort_values("angle_deg").drop_duplicates("angle_deg")
    required = {"angle_deg", "lap_time_s", "full_throttle_fraction"}
    if not required.issubset(ordered.columns):
        raise ValueError("nominal sweep lacks response-surface columns")
    rng = np.random.default_rng(uncertainty.seed)
    sampled: dict[str, np.ndarray] = {}
    for name, definition in uncertainty.parameters.items():
        sampled[name] = rng.uniform(definition.minimum, definition.maximum, count)

    angles = ordered.angle_deg.to_numpy(dtype=float)
    nominal_lap = ordered.lap_time_s.to_numpy(dtype=float)
    full_fraction = ordered.full_throttle_fraction.to_numpy(dtype=float)
    corner_fraction = 1.0 - full_fraction
    angle_norm = np.clip(angles / max(cfg.aero.maximum_angle_deg, 1.0), 0.0, 1.0)
    curves = np.tile(nominal_lap, (count, 1))

    density_ratio = sampled["environment.air_density_kgpm3"] / cfg.environment.air_density_kgpm3
    curves += nominal_lap * (density_ratio[:, None] - 1.0) * (
        0.035 * full_fraction - 0.025 * corner_fraction * angle_norm
    )
    wind = sampled["environment.headwind_mps"]
    curves += nominal_lap * (wind[:, None] / 100.0) * (
        0.22 * full_fraction - 0.08 * corner_fraction
    )
    mu_lat_ratio = sampled["tyres.mu_lateral_ref"] / cfg.tyres.mu_lateral_ref
    curves += nominal_lap * corner_fraction * (mu_lat_ratio[:, None] ** -0.5 - 1.0)
    mu_long_ratio = sampled["tyres.mu_longitudinal_ref"] / cfg.tyres.mu_longitudinal_ref
    curves += nominal_lap * 0.35 * full_fraction * (mu_long_ratio[:, None] ** -0.5 - 1.0)
    power_scale = sampled["powertrain.power_scale"]
    curves += nominal_lap * full_fraction * (power_scale[:, None] ** -0.5 - 1.0)
    lift_scale = sampled["aero.lift_curve_slope_scale"]
    curves -= nominal_lap * 0.025 * corner_fraction * angle_norm * (lift_scale[:, None] - 1.0)
    cd_ratio = sampled["aero.wing_cd0"] / cfg.aero.wing_cd0
    curves += nominal_lap * 0.018 * full_fraction * (0.2 + angle_norm) * (cd_ratio[:, None] - 1.0)
    sampled_stall = sampled["aero.stall_angle_deg"]
    stall_excess = np.maximum(angles[None, :] - sampled_stall[:, None], 0.0)
    curves += nominal_lap * 0.025 * stall_excess / cfg.aero.post_stall_width_deg
    floor_ratio = sampled["aero.baseline_cl"] / cfg.aero.baseline_cl
    curves += nominal_lap * 0.45 * corner_fraction * (floor_ratio[:, None] ** -0.5 - 1.0)

    best_index = np.argmin(curves, axis=1)
    row_index = np.arange(count)
    reference_index = int(np.argmin(np.abs(angles - 10.0)))
    output = pd.DataFrame(sampled)
    output["optimum_angle_deg"] = angles[best_index]
    output["minimum_lap_time_s"] = curves[row_index, best_index]
    output["gain_vs_10deg_s"] = curves[:, reference_index] - curves[row_index, best_index]

    metrics = ("optimum_angle_deg", "minimum_lap_time_s", "gain_vs_10deg_s")
    summary_rows: list[dict[str, float | str]] = []
    for percentile in (2.5, 50.0, 97.5):
        for metric in metrics:
            summary_rows.append(
                {
                    "percentile": percentile,
                    "metric": metric,
                    "value": float(np.percentile(output[metric], percentile)),
                }
            )
    correlation_rows: list[dict[str, float | str]] = []
    for parameter in uncertainty.parameters:
        for metric in metrics:
            parameter_values = output[parameter].to_numpy(dtype=float)
            metric_values = output[metric].to_numpy(dtype=float)
            if np.ptp(parameter_values) == 0.0 or np.ptp(metric_values) == 0.0:
                correlation = 0.0
            else:
                correlation = spearmanr(parameter_values, metric_values).statistic
            correlation_rows.append(
                {
                    "parameter": parameter,
                    "metric": metric,
                    "spearman_rho": 0.0 if not math.isfinite(correlation) else float(correlation),
                }
            )
    return MonteCarloResult(
        samples=output,
        summary=pd.DataFrame(summary_rows),
        correlations=pd.DataFrame(correlation_rows),
        method="nominal full-solver sweep + first-order physics response surface",
    )
