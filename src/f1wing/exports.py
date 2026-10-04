"""Full analysis orchestration, data exports, figures, and provenance manifest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.io import savemat

from .aero import aero_state, wing_coefficients
from .analysis import (
    fixed_angle_sweep,
    monte_carlo,
    oat_sensitivity,
    optimize_active_angles,
    optimize_fixed_angle,
)
from .config import load_project_config, load_track, load_uncertainty_config
from .dynamics import acceleration_time, braking_distance, top_speed
from .lap import lateral_speed_limit, solve_lap
from .models import ProjectConfig, Track, UncertaintyConfig
from .strategies import ActiveAeroSchedule, FixedAngleSchedule, OpenWingSchedule


TRACK_KEYS = ("low_downforce", "balanced", "high_downforce")
COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "black": "#222222",
}


@dataclass(frozen=True)
class ResultBundle:
    config: ProjectConfig
    uncertainty: UncertaintyConfig
    tracks: dict[str, Track]
    tables: dict[str, pd.DataFrame]
    headline_metrics: dict[str, Any]
    input_paths: tuple[Path, ...]
    input_sha256: dict[str, str]
    run_id: str
    generated_at_utc: str
    angle_grid: tuple[float, ...]
    track_spacing_m: float


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_key(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _coarsen_track(track: Track, target_spacing_m: float = 50.0) -> Track:
    current = float(np.median(track.ds_m))
    stride = max(1, int(round(target_spacing_m / current)))
    if stride == 1:
        return track
    starts = np.arange(0, track.ds_m.size, stride)
    ds = np.add.reduceat(track.ds_m, starts)
    return Track(
        name=f"{track.name} optimization mesh",
        description=track.description,
        closed=track.closed,
        distance_m=np.concatenate(([0.0], np.cumsum(ds[:-1]))),
        ds_m=ds,
        curvature_1pm=track.curvature_1pm[starts],
        gradient_rad=track.gradient_rad[starts],
        aero_eligible=track.aero_eligible[starts],
        speed_limit_mps=track.speed_limit_mps[starts],
    )


def _build_aero_tables(cfg: ProjectConfig, angles: Sequence[float]) -> dict[str, pd.DataFrame]:
    polar_rows: list[dict[str, float]] = []
    for angle in angles:
        wing = wing_coefficients(
            angle,
            200.0 / 3.6,
            0.0,
            cfg.aero.nominal_ride_height_m,
            cfg.aero,
        )
        state = aero_state(angle, 200.0 / 3.6, cfg)
        polar_rows.append(
            {
                "angle_deg": angle,
                "wing_cl": wing.cl,
                "wing_cd": wing.cd,
                "wing_efficiency_cl_over_cd": wing.efficiency,
                "car_cl": state.cl_total,
                "car_cd": state.cd_total,
                "front_downforce_fraction": state.front_downforce_fraction,
                "center_of_pressure_from_front_m": state.center_of_pressure_from_front_m,
            }
        )

    force_rows: list[dict[str, float]] = []
    balance_rows: list[dict[str, float]] = []
    selected = sorted(set(float(value) for value in (0, 10, 18, 25, 30)))
    for angle in selected:
        for speed_kph in np.arange(0.0, 351.0, 25.0):
            state = aero_state(angle, speed_kph / 3.6, cfg)
            force_rows.append(
                {
                    "angle_deg": angle,
                    "speed_kph": speed_kph,
                    "downforce_n": state.downforce_n,
                    "drag_n": state.drag_n,
                    "front_downforce_n": state.front_downforce_n,
                    "rear_downforce_n": state.rear_downforce_n,
                }
            )
            balance_rows.append(
                {
                    "angle_deg": angle,
                    "speed_kph": speed_kph,
                    "front_downforce_percent": 100.0 * state.front_downforce_fraction,
                    "center_of_pressure_from_front_m": state.center_of_pressure_from_front_m,
                }
            )
    return {
        "aero_polar": pd.DataFrame(polar_rows),
        "force_speed": pd.DataFrame(force_rows),
        "aero_balance": pd.DataFrame(balance_rows),
    }


def _build_performance_tables(cfg: ProjectConfig, angles: Sequence[float]) -> dict[str, pd.DataFrame]:
    straight_rows: list[dict[str, float]] = []
    corner_rows: list[dict[str, float]] = []
    for angle in angles:
        vmax = top_speed(angle, cfg)
        zero_to_100 = acceleration_time(0.0, 100.0 / 3.6, angle, cfg)
        hundred_to_200 = acceleration_time(100.0 / 3.6, 200.0 / 3.6, angle, cfg)
        brake_300 = braking_distance(300.0 / 3.6, 0.0, angle, cfg)
        straight_rows.append(
            {
                "angle_deg": angle,
                "top_speed_kph": vmax * 3.6,
                "zero_to_100_s": zero_to_100.time_s,
                "hundred_to_200_s": hundred_to_200.time_s,
                "braking_300_to_0_m": brake_300.distance_m,
            }
        )
        for radius_m in (50.0, 100.0, 150.0, 250.0):
            limit = lateral_speed_limit(1.0 / radius_m, angle, cfg)
            if not math.isfinite(limit):
                limit = vmax
            corner_rows.append(
                {
                    "angle_deg": angle,
                    "corner_radius_m": radius_m,
                    "maximum_corner_speed_kph": min(limit, vmax) * 3.6,
                }
            )
    return {
        "straight_line": pd.DataFrame(straight_rows),
        "cornering": pd.DataFrame(corner_rows),
    }


def _strategy_rows(
    track_key: str,
    track: Track,
    cfg: ProjectConfig,
    fixed_angle: float,
    *,
    optimize_states: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    optimization_rows: list[dict[str, Any]] = []
    fixed = solve_lap(track, cfg, FixedAngleSchedule(fixed_angle))
    rows = [
        {
            "track": track_key,
            "mode": "fixed-optimum",
            "open_angle_deg": fixed_angle,
            "closed_angle_deg": fixed_angle,
            "lap_time_s": fixed.lap_time_s,
            "maximum_speed_kph": fixed.maximum_speed_mps * 3.6,
            "tractive_energy_mj": fixed.tractive_energy_j / 1e6,
            "full_throttle_fraction": fixed.full_throttle_fraction,
        }
    ]
    open_result = solve_lap(track, cfg, OpenWingSchedule.from_config(cfg))
    rows.append(
        {
            "track": track_key,
            "mode": "open-wing",
            "open_angle_deg": cfg.strategy.open_angle_deg,
            "closed_angle_deg": cfg.strategy.corner_angle_deg,
            "lap_time_s": open_result.lap_time_s,
            "maximum_speed_kph": open_result.maximum_speed_mps * 3.6,
            "tractive_energy_mj": open_result.tractive_energy_j / 1e6,
            "full_throttle_fraction": open_result.full_throttle_fraction,
        }
    )
    for actuator_limited, mode in ((False, "active-ideal"), (True, "active-limited")):
        if optimize_states:
            searched = optimize_active_angles(
                _coarsen_track(track),
                cfg,
                actuator_limited=actuator_limited,
            )
            low = float(searched.open_angle_deg)
            high = float(searched.closed_angle_deg)
            for record in searched.evaluated_points.to_dict("records"):
                optimization_rows.append({"track": track_key, "mode": mode, **record})
        else:
            low = cfg.strategy.open_angle_deg
            high = cfg.strategy.corner_angle_deg
        schedule = ActiveAeroSchedule.from_config(
            cfg,
            actuator_limited=actuator_limited,
            open_angle_deg=low,
            closed_angle_deg=high,
        )
        result = solve_lap(track, cfg, schedule)
        rows.append(
            {
                "track": track_key,
                "mode": mode,
                "open_angle_deg": low,
                "closed_angle_deg": high,
                "lap_time_s": result.lap_time_s,
                "maximum_speed_kph": result.maximum_speed_mps * 3.6,
                "tractive_energy_mj": result.tractive_energy_j / 1e6,
                "full_throttle_fraction": result.full_throttle_fraction,
            }
        )
    return rows, optimization_rows


def run_full_analysis(
    project_path: Path,
    track_dir: Path,
    output_dir: Path,
    *,
    angle_grid: Sequence[float] = tuple(range(31)),
    track_spacing_override_m: float | None = None,
) -> ResultBundle:
    """Run the complete numerical study and return an in-memory result bundle."""

    project_path = Path(project_path)
    track_dir = Path(track_dir)
    output_dir = Path(output_dir)
    del output_dir  # Export is a separate deterministic step.
    cfg = load_project_config(project_path)
    uncertainty_path = project_path.parent / "uncertainty.json"
    uncertainty = load_uncertainty_config(uncertainty_path)
    spacing = (
        cfg.solver.track_spacing_m
        if track_spacing_override_m is None
        else float(track_spacing_override_m)
    )
    angle_tuple = tuple(float(value) for value in angle_grid)
    if not angle_tuple:
        raise ValueError("angle_grid must not be empty")

    track_paths = {key: track_dir / f"{key}.json" for key in TRACK_KEYS}
    tracks = {key: load_track(path, spacing) for key, path in track_paths.items()}
    tables = _build_aero_tables(cfg, angle_tuple)
    tables.update(_build_performance_tables(cfg, angle_tuple))

    lap_tables: list[pd.DataFrame] = []
    optima_rows: list[dict[str, Any]] = []
    strategy_rows: list[dict[str, Any]] = []
    active_optimization_rows: list[dict[str, Any]] = []
    uncertainty_samples: list[pd.DataFrame] = []
    uncertainty_summary: list[pd.DataFrame] = []
    uncertainty_correlations: list[pd.DataFrame] = []
    speed_trace_rows: list[dict[str, Any]] = []
    full_resolution = len(set(angle_tuple)) >= 31 and spacing <= cfg.solver.track_spacing_m + 1e-9

    for track_key, track in tracks.items():
        sweep = fixed_angle_sweep(track, cfg, angle_tuple)
        sweep.insert(0, "track", track_key)
        lap_tables.append(sweep)
        optimum = optimize_fixed_angle(track, cfg, sweep_table=sweep)
        best_discrete = sweep.loc[sweep.lap_time_s.idxmin()]
        optima_rows.append(
            {
                "track": track_key,
                "optimum_angle_deg": optimum.angle_deg,
                "minimum_lap_time_s": optimum.lap_time_s,
                "best_discrete_angle_deg": float(best_discrete.angle_deg),
                "best_discrete_lap_time_s": float(best_discrete.lap_time_s),
                "neighbour_sensitivity_s_per_deg": optimum.neighbour_sensitivity_s_per_deg,
                "optimization_method": optimum.method,
            }
        )
        rows, search_rows = _strategy_rows(
            track_key,
            track,
            cfg,
            optimum.angle_deg,
            optimize_states=full_resolution,
        )
        strategy_rows.extend(rows)
        active_optimization_rows.extend(search_rows)

        mc = monte_carlo(cfg, uncertainty, sweep, samples=uncertainty.samples)
        sample_table = mc.samples.copy()
        sample_table.insert(0, "track", track_key)
        uncertainty_samples.append(sample_table)
        summary_table = mc.summary.copy()
        summary_table.insert(0, "track", track_key)
        summary_table["method"] = mc.method
        uncertainty_summary.append(summary_table)
        correlation_table = mc.correlations.copy()
        correlation_table.insert(0, "track", track_key)
        uncertainty_correlations.append(correlation_table)

        for label, angle in (
            ("minimum-wing", cfg.aero.minimum_angle_deg),
            ("optimum-wing", optimum.angle_deg),
            ("maximum-wing", cfg.aero.maximum_angle_deg),
        ):
            result = solve_lap(track, cfg, FixedAngleSchedule(angle))
            speed_trace_rows.extend(
                {
                    "track": track_key,
                    "setup": label,
                    "angle_deg": angle,
                    "distance_m": distance,
                    "speed_kph": speed * 3.6,
                }
                for distance, speed in zip(result.distance_m, result.speed_mps)
            )

    tables["lap_sweeps"] = pd.concat(lap_tables, ignore_index=True)
    tables["circuit_optima"] = pd.DataFrame(optima_rows)
    tables["strategy_comparison"] = pd.DataFrame(strategy_rows)
    tables["active_optimization"] = pd.DataFrame(active_optimization_rows)
    tables["monte_carlo_samples"] = pd.concat(uncertainty_samples, ignore_index=True)
    tables["monte_carlo_summary"] = pd.concat(uncertainty_summary, ignore_index=True)
    tables["monte_carlo_correlations"] = pd.concat(uncertainty_correlations, ignore_index=True)
    tables["speed_traces"] = pd.DataFrame(speed_trace_rows)

    balanced_optimum = float(
        tables["circuit_optima"].loc[
            tables["circuit_optima"].track == "balanced", "optimum_angle_deg"
        ].iloc[0]
    )
    tables["sensitivity"] = oat_sensitivity(
        _coarsen_track(tracks["balanced"]),
        cfg,
        balanced_optimum,
    )

    decision = tables["circuit_optima"].copy()
    reference = tables["lap_sweeps"].iloc[
        (tables["lap_sweeps"].angle_deg - 10.0).abs().groupby(
            tables["lap_sweeps"].track
        ).idxmin()
    ][["track", "lap_time_s"]].rename(columns={"lap_time_s": "reference_10deg_lap_time_s"})
    decision = decision.merge(reference, on="track")
    fixed_strategy = tables["strategy_comparison"].query("mode == 'fixed-optimum'")
    active_strategy = tables["strategy_comparison"].query("mode == 'active-limited'")
    decision = decision.merge(
        fixed_strategy[["track", "maximum_speed_kph", "tractive_energy_mj"]],
        on="track",
    ).merge(
        active_strategy[["track", "lap_time_s"]].rename(
            columns={"lap_time_s": "active_limited_lap_time_s"}
        ),
        on="track",
    )
    decision["fixed_gain_vs_10deg_s"] = (
        decision.reference_10deg_lap_time_s - decision.minimum_lap_time_s
    )
    decision["active_gain_vs_fixed_s"] = (
        decision.minimum_lap_time_s - decision.active_limited_lap_time_s
    )
    tables["decision_matrix"] = decision

    parity_rows: list[dict[str, Any]] = []
    for angle in (0, 10, 18, 25, 30):
        state = aero_state(angle, 200.0 / 3.6, cfg)
        parity_rows.append(
            {
                "case_type": "aero",
                "track": "",
                "angle_deg": angle,
                "speed_mps": 200.0 / 3.6,
                "cl_total": state.cl_total,
                "cd_total": state.cd_total,
                "downforce_n": state.downforce_n,
                "drag_n": state.drag_n,
                "lap_time_s": np.nan,
            }
        )
    for row in tables["circuit_optima"].itertuples(index=False):
        parity_rows.append(
            {
                "case_type": "lap",
                "track": row.track,
                "angle_deg": row.optimum_angle_deg,
                "speed_mps": np.nan,
                "cl_total": np.nan,
                "cd_total": np.nan,
                "downforce_n": np.nan,
                "drag_n": np.nan,
                "lap_time_s": row.minimum_lap_time_s,
            }
        )
    tables["parity_cases"] = pd.DataFrame(parity_rows)

    root = project_path.parent.parent
    input_paths = (project_path, uncertainty_path, *track_paths.values())
    input_sha = {_safe_key(path, root): _sha256(path) for path in input_paths}
    identity = {
        "inputs": input_sha,
        "seed": uncertainty.seed,
        "angles": angle_tuple,
        "spacing_m": spacing,
        "model_version": cfg.metadata.version,
    }
    run_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    headline = {
        "fixed_optimum_angle_deg": {
            row["track"]: float(row["optimum_angle_deg"]) for row in optima_rows
        },
        "fixed_minimum_lap_time_s": {
            row["track"]: float(row["minimum_lap_time_s"]) for row in optima_rows
        },
        "active_limited_lap_time_s": {
            row.track: float(row.lap_time_s)
            for row in tables["strategy_comparison"].query("mode == 'active-limited'").itertuples()
        },
    }
    return ResultBundle(
        config=cfg,
        uncertainty=uncertainty,
        tracks=tracks,
        tables=tables,
        headline_metrics=headline,
        input_paths=tuple(input_paths),
        input_sha256=input_sha,
        run_id=run_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        angle_grid=angle_tuple,
        track_spacing_m=spacing,
    )


def _style_axis(ax, *, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(True, alpha=0.22)
    ax.spines[["top", "right"]].set_visible(False)


def _save_figure(fig, output_dir: Path, stem: str) -> tuple[Path, Path]:
    png = output_dir / f"{stem}.png"
    svg = output_dir / f"{stem}.svg"
    fig.savefig(png, dpi=220, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png, svg


def build_all_figures(bundle: ResultBundle, output_dir: Path) -> list[dict[str, str]]:
    """Generate publication-ready PNG/SVG figures and return manifest entries."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []

    def register(
        stem: str,
        fig,
        source_table: str,
        caption: str,
        units: str,
    ) -> None:
        png, svg = _save_figure(fig, output_dir, stem)
        entries.append(
            {
                "id": stem,
                "path": png.relative_to(output_dir.parent).as_posix(),
                "svg_path": svg.relative_to(output_dir.parent).as_posix(),
                "source_data": f"data/{source_table}.csv",
                "caption": caption,
                "units": units,
            }
        )

    polar = bundle.tables["aero_polar"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(polar.angle_deg, polar.wing_cl, color=COLORS["blue"], label="$C_L$")
    ax.plot(polar.angle_deg, polar.wing_cd, color=COLORS["red"], label="$C_D$")
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Coefficient (-)", title="Rear-wing nonlinear aerodynamic polar")
    ax.legend()
    register("01_aero_polar", fig, "aero_polar", "Wing lift and drag coefficients, including the modeled stall transition.", "dimensionless")

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(polar.angle_deg, polar.wing_efficiency_cl_over_cd, color=COLORS["green"])
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="$C_L/C_D$ (-)", title="Rear-wing aerodynamic efficiency")
    register("02_aero_efficiency", fig, "aero_polar", "Aerodynamic efficiency peaks before maximum downforce and falls through stall.", "dimensionless")

    forces = bundle.tables["force_speed"]
    for column, stem, ylabel, title, units in (
        ("downforce_n", "03_downforce_speed", "Downforce (N)", "Downforce increases with the square of speed", "N"),
        ("drag_n", "04_drag_speed", "Drag (N)", "Drag penalty across wing settings", "N"),
    ):
        fig, ax = plt.subplots(figsize=(8.2, 5.0))
        for angle, group in forces.groupby("angle_deg"):
            ax.plot(group.speed_kph, group[column], label=f"{angle:g}°")
        _style_axis(ax, xlabel="Vehicle speed (km/h)", ylabel=ylabel, title=title)
        ax.legend(ncol=3)
        register(stem, fig, "force_speed", f"{title} for selected rear-wing angles.", units)

    balance = bundle.tables["aero_balance"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for angle, group in balance.groupby("angle_deg"):
        ax.plot(group.speed_kph, group.front_downforce_percent, label=f"{angle:g}°")
    _style_axis(ax, xlabel="Vehicle speed (km/h)", ylabel="Front aero balance (%)", title="Rear-wing angle shifts aerodynamic balance rearward")
    ax.legend(ncol=3)
    register("05_aero_balance", fig, "aero_balance", "Front share of total aerodynamic load for selected rear-wing angles.", "%")

    straight = bundle.tables["straight_line"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(straight.angle_deg, straight.top_speed_kph, color=COLORS["blue"])
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Top speed (km/h)", title="Top-speed cost of rear-wing angle")
    register("06_top_speed", fig, "straight_line", "Power-limited top speed decreases as wing drag rises.", "km/h")

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(straight.angle_deg, straight.zero_to_100_s, label="0–100 km/h", color=COLORS["green"])
    ax.plot(straight.angle_deg, straight.hundred_to_200_s, label="100–200 km/h", color=COLORS["orange"])
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Elapsed time (s)", title="Acceleration performance")
    ax.legend()
    register("07_acceleration", fig, "straight_line", "Acceleration time includes gearing, traction, rolling resistance, and aerodynamic drag.", "s")

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot(straight.angle_deg, straight.braking_300_to_0_m, color=COLORS["red"])
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Braking distance (m)", title="Maximum braking from 300 km/h")
    register("08_braking", fig, "straight_line", "Integrated 300–0 km/h braking distance with load-sensitive tyres and aero.", "m")

    corner = bundle.tables["cornering"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for radius, group in corner.groupby("corner_radius_m"):
        ax.plot(group.angle_deg, group.maximum_corner_speed_kph, label=f"R = {radius:g} m")
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Maximum speed (km/h)", title="Cornering-speed benefit of downforce")
    ax.legend(ncol=2)
    register("09_cornering", fig, "cornering", "Axle-constrained maximum cornering speed for representative radii.", "km/h")

    sweeps = bundle.tables["lap_sweeps"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for track, group in sweeps.groupby("track"):
        ax.plot(group.angle_deg, group.lap_time_s, marker="o", ms=3, label=track.replace("_", " ").title())
    _style_axis(ax, xlabel="Rear-wing angle (deg)", ylabel="Lap time (s)", title="Circuit-specific wing-angle optimum")
    ax.legend()
    register("10_lap_time_sweep", fig, "lap_sweeps", "Fixed-wing lap-time sweep for low-, balanced-, and high-downforce circuits.", "s")

    traces = bundle.tables["speed_traces"]
    fig, axes = plt.subplots(3, 1, figsize=(9.0, 9.0), sharex=False)
    for ax, (track, track_data) in zip(axes, traces.groupby("track")):
        for setup, group in track_data.groupby("setup"):
            ax.plot(group.distance_m / 1000.0, group.speed_kph, label=setup.replace("-", " ").title())
        _style_axis(ax, xlabel="Lap distance (km)", ylabel="Speed (km/h)", title=track.replace("_", " ").title())
        ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    register("11_speed_traces", fig, "speed_traces", "Minimum-, optimum-, and maximum-wing speed traces on each circuit archetype.", "km/h")

    strategy = bundle.tables["strategy_comparison"]
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    pivot = strategy.pivot(index="track", columns="mode", values="lap_time_s")
    pivot.plot(kind="bar", ax=ax, color=[COLORS["blue"], COLORS["orange"], COLORS["green"], COLORS["purple"]])
    _style_axis(ax, xlabel="Circuit archetype", ylabel="Lap time (s)", title="Fixed, open-wing, and active-aero comparison")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="Mode", fontsize=8)
    register("12_strategy_comparison", fig, "strategy_comparison", "Lap-time comparison of fixed, open-wing, ideal-active, and actuator-limited modes.", "s")

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    energy = strategy.pivot(index="track", columns="mode", values="tractive_energy_mj")
    energy.plot(kind="bar", ax=ax, color=[COLORS["blue"], COLORS["orange"], COLORS["green"], COLORS["purple"]])
    _style_axis(ax, xlabel="Circuit archetype", ylabel="Wheel tractive energy (MJ)", title="Energy demand by aerodynamic strategy")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="Mode", fontsize=8)
    register("13_energy_strategy", fig, "strategy_comparison", "Integrated positive wheel work for each aerodynamic strategy.", "MJ")

    samples = bundle.tables["monte_carlo_samples"]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    bins = np.arange(-0.5, 31.5, 1.0)
    for track, group in samples.groupby("track"):
        ax.hist(group.optimum_angle_deg, bins=bins, alpha=0.45, density=True, label=track.replace("_", " ").title())
    _style_axis(ax, xlabel="Monte Carlo optimum angle (deg)", ylabel="Probability density", title="Uncertainty in optimum fixed-wing angle")
    ax.legend()
    register("14_uncertainty_optimum", fig, "monte_carlo_samples", "Distribution of optimum fixed-wing angle from 1,000 bounded uncertainty samples per circuit.", "probability density")

    sensitivity = bundle.tables["sensitivity"].copy()
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    labels = sensitivity.parameter + " " + sensitivity.perturbation_percent.map(lambda value: f"{value:+.0f}%")
    order = np.argsort(np.abs(sensitivity.change_from_nominal_s.to_numpy()))
    ax.barh(labels.iloc[order], sensitivity.change_from_nominal_s.iloc[order], color=np.where(sensitivity.change_from_nominal_s.iloc[order] >= 0, COLORS["red"], COLORS["green"]))
    _style_axis(ax, xlabel="Lap-time change (s)", ylabel="Parameter perturbation", title="Balanced-circuit one-at-a-time sensitivity")
    register("15_sensitivity", fig, "sensitivity", "Lap-time sensitivity to ±10% input perturbations at the balanced-circuit optimum.", "s")

    decision = bundle.tables["decision_matrix"]
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    matrix = decision[["fixed_gain_vs_10deg_s", "active_gain_vs_fixed_s"]].to_numpy()
    image = ax.imshow(matrix, cmap="viridis", aspect="auto")
    ax.set_yticks(range(decision.shape[0]), decision.track.str.replace("_", " ").str.title())
    ax.set_xticks((0, 1), ("Fixed optimum gain", "Active-aero gain"))
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(column, row, f"{matrix[row, column]:.3f} s", ha="center", va="center", color="white" if matrix[row, column] > np.nanmean(matrix) else "black")
    ax.set_title("Wing-setting decision matrix", loc="left", fontweight="bold")
    fig.colorbar(image, ax=ax, label="Time gain (s)")
    register("16_decision_matrix", fig, "decision_matrix", "Circuit-by-circuit time gains from fixed-angle optimization and actuator-limited active aero.", "s")
    return entries


def _mat_value(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    result: dict[str, np.ndarray] = {}
    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            result[column] = series.to_numpy()
        else:
            result[column] = series.fillna("").astype(str).to_numpy(dtype=object)
    return result


def export_result_bundle(bundle: ResultBundle, output_dir: Path) -> Path:
    """Write data, figures, workbook, MAT file, and deterministic manifest."""

    output_dir = Path(output_dir)
    data_dir = output_dir / "data"
    figure_dir = output_dir / "figures"
    parity_dir = output_dir / "parity"
    workbook_dir = output_dir / "workbooks"
    for directory in (data_dir, figure_dir, parity_dir, workbook_dir):
        directory.mkdir(parents=True, exist_ok=True)

    table_manifest: dict[str, dict[str, str]] = {}
    workbook_path = workbook_dir / "F1_Wing_Angle_Results.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        for name, frame in bundle.tables.items():
            csv_path = data_dir / f"{name}.csv"
            frame.to_csv(csv_path, index=False, float_format="%.12g")
            sheet_name = name[:31]
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            table_manifest[name] = {
                "csv": csv_path.relative_to(output_dir).as_posix(),
                "xlsx_sheet": sheet_name,
            }

    parity_path = parity_dir / "reference_cases.csv"
    bundle.tables["parity_cases"].to_csv(parity_path, index=False, float_format="%.12g")
    mat_path = data_dir / "F1_Wing_Angle_Results.mat"
    savemat(
        mat_path,
        {name: _mat_value(frame) for name, frame in bundle.tables.items()},
        do_compression=True,
    )
    figures = build_all_figures(bundle, figure_dir)

    artifacts = [
        *data_dir.glob("*"),
        *figure_dir.glob("*"),
        *parity_dir.glob("*"),
        workbook_path,
    ]
    artifact_hashes = {
        path.relative_to(output_dir).as_posix(): _sha256(path)
        for path in sorted(set(artifacts))
        if path.is_file()
    }
    manifest = {
        "schema_version": "1.0",
        "run_id": bundle.run_id,
        "generated_at_utc": bundle.generated_at_utc,
        "model_name": bundle.config.metadata.name,
        "model_version": bundle.config.metadata.version,
        "interpretation_warning": (
            "This is a representative educational model; values are not proprietary F1 team data, "
            "wind-tunnel measurements, or full-car CFD results."
        ),
        "seed": bundle.uncertainty.seed,
        "monte_carlo_samples_per_circuit": bundle.uncertainty.samples,
        "angle_grid_deg": list(bundle.angle_grid),
        "track_spacing_m": bundle.track_spacing_m,
        "input_sha256": bundle.input_sha256,
        "artifact_sha256": artifact_hashes,
        "tables": table_manifest,
        "workbook": workbook_path.relative_to(output_dir).as_posix(),
        "matlab_data": mat_path.relative_to(output_dir).as_posix(),
        "parity_fixture": parity_path.relative_to(output_dir).as_posix(),
        "figures": figures,
        "headline_metrics": bundle.headline_metrics,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return manifest_path

