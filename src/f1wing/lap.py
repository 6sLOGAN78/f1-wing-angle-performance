"""Quasi-steady G-G-envelope and forward/backward lap-time solver."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

import numpy as np
from scipy.optimize import brentq

from .dynamics import (
    InfeasibleVehicleState,
    best_wheel_force,
    load_sensitive_mu,
    longitudinal_capacity,
    resistance_force,
    top_speed,
    axle_loads,
)
from .models import ProjectConfig, Track


class SolverConvergenceError(RuntimeError):
    """Raised when the iterative closed-lap solver does not converge."""


@dataclass(frozen=True)
class LapState:
    index: int
    speed_mps: float
    longitudinal_accel_mps2: float
    elapsed_s: float
    curvature_1pm: float
    aero_eligible: bool


class AngleSchedule(Protocol):
    def angle_at(self, index: int, state: LapState) -> float:
        """Return commanded rear-wing angle at one track station."""


@dataclass(frozen=True)
class FixedAngleSchedule:
    angle_deg: float

    def angle_at(self, index: int, state: LapState) -> float:
        del index, state
        return float(self.angle_deg)


@dataclass(frozen=True)
class LapResult:
    track_name: str
    lap_time_s: float
    tractive_energy_j: float
    full_throttle_fraction: float
    maximum_speed_mps: float
    minimum_speed_mps: float
    maximum_braking_demand_n: float
    iterations: int
    converged: bool
    distance_m: np.ndarray
    speed_mps: np.ndarray
    time_s: np.ndarray
    local_limit_mps: np.ndarray
    angle_deg: np.ndarray
    longitudinal_accel_mps2: np.ndarray
    lateral_force_n: np.ndarray
    tractive_force_n: np.ndarray
    brake_force_n: np.ndarray
    gear: np.ndarray
    limiting_mechanism: np.ndarray
    strategy_state: np.ndarray


def lateral_speed_limit(
    curvature_1pm: float,
    angle_deg: float,
    cfg: ProjectConfig,
    *,
    grade_rad: float = 0.0,
) -> float:
    """Solve the axle-level lateral-grip limit for a constant curvature."""

    if not all(math.isfinite(value) for value in (curvature_1pm, angle_deg, grade_rad)):
        raise ValueError("curvature, angle, and grade must be finite")
    curvature = abs(curvature_1pm)
    if curvature < 1e-12:
        return math.inf

    gravity_scale = max(0.0, math.cos(grade_rad))

    def margin(speed: float) -> float:
        loads = axle_loads(speed, 0.0, angle_deg, cfg)
        # Grade correction acts on the weight component only; aero load remains normal.
        weight = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2
        lost_normal = weight * (1.0 - gravity_scale)
        front = loads.front_n - lost_normal * cfg.vehicle.front_static_fraction
        rear = loads.rear_n - lost_normal * (1.0 - cfg.vehicle.front_static_fraction)
        if front <= 0 or rear <= 0:
            raise InfeasibleVehicleState("non-positive axle normal load in lateral limit")
        total = front + rear
        front_share = front / total
        rear_share = rear / total
        mu_front = load_sensitive_mu(
            front,
            cfg.tyres.mu_lateral_ref,
            cfg.tyres.reference_load_n,
            cfg.tyres.load_sensitivity_exponent,
        )
        mu_rear = load_sensitive_mu(
            rear,
            cfg.tyres.mu_lateral_ref,
            cfg.tyres.reference_load_n,
            cfg.tyres.load_sensitivity_exponent,
        )
        axle_limited_total = min(
            mu_front * front / front_share,
            mu_rear * rear / rear_share,
        )
        required = cfg.vehicle.mass_kg * speed**2 * curvature
        return axle_limited_total - required

    upper = cfg.solver.maximum_speed_mps
    if margin(0.0) <= 0:
        raise InfeasibleVehicleState("no positive lateral grip margin at zero speed")
    if margin(upper) >= 0:
        return math.inf
    return float(brentq(margin, 0.0, upper, xtol=1e-9, rtol=1e-11))


def _time_trace(track: Track, speed_mps: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    next_speed = np.roll(speed_mps, -1)
    segment_time = 2.0 * track.ds_m / np.maximum(speed_mps + next_speed, 1e-9)
    elapsed = np.concatenate(([0.0], np.cumsum(segment_time[:-1])))
    return elapsed, segment_time


def _angle_profile(
    schedule: AngleSchedule,
    track: Track,
    speed_mps: np.ndarray,
    long_accel_mps2: np.ndarray,
    elapsed_s: np.ndarray,
    cfg: ProjectConfig,
) -> np.ndarray:
    if hasattr(schedule, "angle_profile"):
        profile = np.asarray(
            schedule.angle_profile(track, speed_mps, long_accel_mps2, elapsed_s, cfg),
            dtype=float,
        )
    else:
        profile = np.asarray(
            [
                schedule.angle_at(
                    index,
                    LapState(
                        index=index,
                        speed_mps=float(speed_mps[index]),
                        longitudinal_accel_mps2=float(long_accel_mps2[index]),
                        elapsed_s=float(elapsed_s[index]),
                        curvature_1pm=float(track.curvature_1pm[index]),
                        aero_eligible=bool(track.aero_eligible[index]),
                    ),
                )
                for index in range(track.ds_m.size)
            ],
            dtype=float,
        )
    if profile.shape != track.ds_m.shape or not np.all(np.isfinite(profile)):
        raise ValueError("angle schedule must return one finite value per track station")
    if np.any(profile < cfg.aero.minimum_angle_deg) or np.any(profile > cfg.aero.maximum_angle_deg):
        raise ValueError(
            f"wing angle schedule must remain within {cfg.aero.minimum_angle_deg:g}–"
            f"{cfg.aero.maximum_angle_deg:g} degrees"
        )
    return profile


def _local_limits(track: Track, angles: np.ndarray, cfg: ProjectConfig) -> np.ndarray:
    lateral = np.asarray(
        [
            lateral_speed_limit(curvature, angle, cfg, grade_rad=grade)
            for curvature, angle, grade in zip(track.curvature_1pm, angles, track.gradient_rad)
        ],
        dtype=float,
    )
    top_speed_cache: dict[float, float] = {}
    top_limits = np.empty_like(angles)
    for index, angle in enumerate(angles):
        key = round(float(angle), 6)
        if key not in top_speed_cache:
            top_speed_cache[key] = top_speed(float(angle), cfg)
        top_limits[index] = top_speed_cache[key]
    return np.minimum.reduce(
        (
            np.full_like(angles, cfg.solver.maximum_speed_mps),
            lateral,
            track.speed_limit_mps,
            top_limits,
        )
    )


def solve_lap(track: Track, cfg: ProjectConfig, schedule: AngleSchedule) -> LapResult:
    """Solve a closed lap with iterative acceleration and braking passes."""

    if not track.closed:
        raise ValueError("lap solver requires a closed track")
    n = track.ds_m.size
    if n < 2 or any(array.size != n for array in (
        track.distance_m,
        track.curvature_1pm,
        track.gradient_rad,
        track.aero_eligible,
        track.speed_limit_mps,
    )):
        raise ValueError("track arrays must be non-empty and equal length")

    speed = np.full(n, cfg.solver.maximum_speed_mps, dtype=float)
    longitudinal_accel = np.zeros(n, dtype=float)
    elapsed, _ = _time_trace(track, speed)
    angles = _angle_profile(schedule, track, speed, longitudinal_accel, elapsed, cfg)
    local_limits = _local_limits(track, angles, cfg)
    limit_angles = angles.copy()
    speed = np.maximum(np.minimum(speed, local_limits), cfg.solver.minimum_speed_mps)

    converged = False
    iteration = 0
    for iteration in range(1, cfg.solver.max_iterations + 1):
        previous = speed.copy()
        elapsed, _ = _time_trace(track, speed)
        next_speed = np.roll(speed, -1)
        longitudinal_accel = (next_speed**2 - speed**2) / (2.0 * track.ds_m)
        angles = _angle_profile(schedule, track, speed, longitudinal_accel, elapsed, cfg)
        if not np.array_equal(angles, limit_angles):
            local_limits = _local_limits(track, angles, cfg)
            limit_angles = angles.copy()
        speed = np.minimum(speed, local_limits)

        for index in range(n):
            target = (index + 1) % n
            current_speed = max(float(speed[index]), cfg.solver.minimum_speed_mps)
            lateral_force = cfg.vehicle.mass_kg * current_speed**2 * abs(track.curvature_1pm[index])
            wheel = best_wheel_force(current_speed, cfg)
            resistance = resistance_force(
                current_speed,
                float(angles[index]),
                cfg,
                grade_rad=float(track.gradient_rad[index]),
            )
            acceleration = 0.0
            for _ in range(12):
                capacity = longitudinal_capacity(
                    current_speed,
                    float(angles[index]),
                    cfg,
                    lateral_force_n=lateral_force,
                    long_accel_guess_mps2=acceleration,
                )
                tractive = min(wheel.force_n, capacity.available_force_n)
                updated = max(0.0, (tractive - resistance) / cfg.vehicle.mass_kg)
                if abs(updated - acceleration) < 1e-6:
                    acceleration = updated
                    break
                acceleration = 0.5 * (acceleration + updated)
            reachable_squared = current_speed**2 + 2.0 * acceleration * track.ds_m[index]
            reachable = math.sqrt(max(cfg.solver.minimum_speed_mps**2, reachable_squared))
            if reachable < speed[target]:
                speed[target] = reachable

        for offset in range(n):
            target = (n - 1 - offset) % n
            source = (target - 1) % n
            source_speed = max(float(speed[source]), cfg.solver.minimum_speed_mps)
            lateral_force = cfg.vehicle.mass_kg * source_speed**2 * abs(track.curvature_1pm[source])
            resistance = resistance_force(
                source_speed,
                float(angles[source]),
                cfg,
                grade_rad=float(track.gradient_rad[source]),
            )
            deceleration = 0.0
            for _ in range(12):
                capacity = longitudinal_capacity(
                    source_speed,
                    float(angles[source]),
                    cfg,
                    lateral_force_n=lateral_force,
                    braking=True,
                    long_accel_guess_mps2=-deceleration,
                )
                updated = max(
                    0.0,
                    (capacity.available_force_n + resistance) / cfg.vehicle.mass_kg,
                )
                if abs(updated - deceleration) < 1e-6:
                    deceleration = updated
                    break
                deceleration = 0.5 * (deceleration + updated)
            allowed = math.sqrt(
                max(
                    cfg.solver.minimum_speed_mps**2,
                    speed[target] ** 2 + 2.0 * deceleration * track.ds_m[source],
                )
            )
            if allowed < speed[source]:
                speed[source] = allowed

        speed = np.maximum(np.minimum(speed, local_limits), cfg.solver.minimum_speed_mps)
        if float(np.max(np.abs(speed - previous))) < cfg.solver.speed_tolerance_mps:
            converged = True
            break

    if not converged:
        raise SolverConvergenceError(
            f"lap solver did not converge within {cfg.solver.max_iterations} iterations"
        )

    elapsed, segment_time = _time_trace(track, speed)
    next_speed = np.roll(speed, -1)
    longitudinal_accel = (next_speed**2 - speed**2) / (2.0 * track.ds_m)
    angles = _angle_profile(schedule, track, speed, longitudinal_accel, elapsed, cfg)
    if not np.array_equal(angles, limit_angles):
        local_limits = _local_limits(track, angles, cfg)

    lateral_force = cfg.vehicle.mass_kg * speed**2 * np.abs(track.curvature_1pm)
    tractive_force = np.zeros(n)
    brake_force = np.zeros(n)
    gears = np.zeros(n, dtype=int)
    limiting: list[str] = []
    full_throttle = np.zeros(n, dtype=bool)
    for index in range(n):
        wheel = best_wheel_force(float(speed[index]), cfg)
        gears[index] = wheel.gear
        resistance = resistance_force(
            float(speed[index]),
            float(angles[index]),
            cfg,
            grade_rad=float(track.gradient_rad[index]),
        )
        if longitudinal_accel[index] >= 0:
            capacity = longitudinal_capacity(
                float(speed[index]),
                float(angles[index]),
                cfg,
                lateral_force_n=float(lateral_force[index]),
                long_accel_guess_mps2=float(longitudinal_accel[index]),
            )
            available = min(wheel.force_n, capacity.available_force_n)
            required = max(0.0, cfg.vehicle.mass_kg * longitudinal_accel[index] + resistance)
            tractive_force[index] = min(required, available)
            full_throttle[index] = available > 0 and required >= 0.98 * available
            if abs(speed[index] - local_limits[index]) <= 2 * cfg.solver.speed_tolerance_mps and abs(track.curvature_1pm[index]) > 1e-12:
                limiting.append("cornering")
            elif wheel.force_n <= capacity.available_force_n:
                limiting.append("powertrain")
            else:
                limiting.append("traction")
        else:
            required_brake = max(0.0, -cfg.vehicle.mass_kg * longitudinal_accel[index] - resistance)
            brake_force[index] = required_brake
            limiting.append("braking")

    lap_time = float(np.sum(segment_time))
    time_at_full = float(np.sum(segment_time[full_throttle]))
    if hasattr(schedule, "state_profile"):
        strategy_state = np.asarray(
            schedule.state_profile(track, angles, cfg),
            dtype=object,
        )
        if strategy_state.shape != speed.shape:
            raise ValueError("strategy state profile must match track station count")
    else:
        strategy_state = np.full(n, "fixed", dtype=object)
    return LapResult(
        track_name=track.name,
        lap_time_s=lap_time,
        tractive_energy_j=float(np.sum(tractive_force * track.ds_m)),
        full_throttle_fraction=time_at_full / lap_time if lap_time > 0 else 0.0,
        maximum_speed_mps=float(np.max(speed)),
        minimum_speed_mps=float(np.min(speed)),
        maximum_braking_demand_n=float(np.max(brake_force)),
        iterations=iteration,
        converged=converged,
        distance_m=track.distance_m.copy(),
        speed_mps=speed,
        time_s=elapsed,
        local_limit_mps=local_limits,
        angle_deg=angles,
        longitudinal_accel_mps2=longitudinal_accel,
        lateral_force_n=lateral_force,
        tractive_force_n=tractive_force,
        brake_force_n=brake_force,
        gear=gears,
        limiting_mechanism=np.asarray(limiting, dtype=object),
        strategy_state=strategy_state,
    )
