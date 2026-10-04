"""Tyre, powertrain, acceleration, braking, and top-speed calculations."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import brentq

from .aero import aero_state
from .models import ProjectConfig


class InfeasibleVehicleState(RuntimeError):
    """Raised when the requested state violates a physical/model bound."""


@dataclass(frozen=True)
class AxleLoads:
    front_n: float
    rear_n: float
    total_n: float
    aero_downforce_n: float
    load_transfer_n: float


@dataclass(frozen=True)
class PowertrainState:
    gear: int
    engine_rpm: float
    torque_nm: float
    raw_force_n: float
    force_n: float
    limiting_mechanism: str


@dataclass(frozen=True)
class ForceCapacity:
    available_force_n: float
    front_available_n: float
    rear_available_n: float
    front_lateral_n: float
    rear_lateral_n: float
    limiting_mechanism: str


@dataclass(frozen=True)
class AccelerationResult:
    time_s: float
    distance_m: float
    speed_mps: np.ndarray
    time_trace_s: np.ndarray
    distance_trace_m: np.ndarray
    acceleration_mps2: np.ndarray
    tractive_force_n: np.ndarray


@dataclass(frozen=True)
class BrakingResult:
    time_s: float
    distance_m: float
    speed_mps: np.ndarray
    time_trace_s: np.ndarray
    distance_trace_m: np.ndarray
    deceleration_mps2: np.ndarray
    brake_force_n: np.ndarray


def load_sensitive_mu(
    normal_load_n: float,
    mu_ref: float,
    ref_load_n: float,
    exponent: float,
) -> float:
    """Return a friction coefficient that decreases with increasing load."""

    values = (normal_load_n, mu_ref, ref_load_n, exponent)
    if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values):
        raise ValueError("tyre inputs must be finite")
    if normal_load_n <= 0:
        raise InfeasibleVehicleState("tyre normal load must be positive")
    if mu_ref <= 0 or ref_load_n <= 0 or exponent < 0:
        raise ValueError("tyre reference values must be positive and exponent non-negative")
    return float(mu_ref * (normal_load_n / ref_load_n) ** (-exponent))


def axle_loads(
    speed_mps: float,
    long_accel_mps2: float,
    angle_deg: float,
    cfg: ProjectConfig,
) -> AxleLoads:
    """Calculate front/rear normal loads including aero and load transfer."""

    aero = aero_state(angle_deg, speed_mps, cfg)
    weight = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2
    transfer = (
        cfg.vehicle.mass_kg
        * long_accel_mps2
        * cfg.vehicle.cg_height_m
        / cfg.vehicle.wheelbase_m
    )
    front = (
        weight * cfg.vehicle.front_static_fraction
        + aero.front_downforce_n
        - transfer
    )
    rear = (
        weight * (1.0 - cfg.vehicle.front_static_fraction)
        + aero.rear_downforce_n
        + transfer
    )
    if front <= 0 or rear <= 0:
        raise InfeasibleVehicleState(
            f"non-positive axle normal load (front={front:.1f} N, rear={rear:.1f} N)"
        )
    return AxleLoads(
        front_n=front,
        rear_n=rear,
        total_n=front + rear,
        aero_downforce_n=aero.downforce_n,
        load_transfer_n=transfer,
    )


def _engine_torque(rpm: float, cfg: ProjectConfig) -> float:
    return float(
        np.interp(
            rpm,
            np.asarray(cfg.powertrain.rpm_points, dtype=float),
            np.asarray(cfg.powertrain.torque_nm, dtype=float),
        )
    )


def best_wheel_force(speed_mps: float, cfg: ProjectConfig) -> PowertrainState:
    """Select the gear producing the highest admissible driven-wheel force."""

    if not math.isfinite(speed_mps) or speed_mps < 0:
        raise ValueError("speed_mps must be finite and non-negative")
    candidates: list[PowertrainState] = []
    for index, gear_ratio in enumerate(cfg.powertrain.gear_ratios, start=1):
        actual_rpm = (
            speed_mps
            / cfg.vehicle.tyre_radius_m
            * gear_ratio
            * cfg.powertrain.final_drive_ratio
            * 60.0
            / (2.0 * math.pi)
        )
        if actual_rpm > cfg.powertrain.redline_rpm:
            continue
        engine_rpm = max(cfg.powertrain.idle_rpm, actual_rpm)
        torque = _engine_torque(engine_rpm, cfg)
        force = (
            torque
            * gear_ratio
            * cfg.powertrain.final_drive_ratio
            * cfg.powertrain.driveline_efficiency
            / cfg.vehicle.tyre_radius_m
        )
        candidates.append(
            PowertrainState(
                gear=index,
                engine_rpm=engine_rpm,
                torque_nm=torque,
                raw_force_n=force,
                force_n=force,
                limiting_mechanism="powertrain",
            )
        )
    if not candidates:
        return PowertrainState(
            gear=len(cfg.powertrain.gear_ratios),
            engine_rpm=cfg.powertrain.redline_rpm,
            torque_nm=0.0,
            raw_force_n=0.0,
            force_n=0.0,
            limiting_mechanism="engine-speed limit",
        )
    return max(candidates, key=lambda item: item.force_n)


def _ellipse_remaining(total_capacity: float, lateral_force: float, exponent: float) -> float:
    if total_capacity <= 0:
        return 0.0
    usage = abs(lateral_force) / total_capacity
    if usage >= 1.0:
        return 0.0
    return float(total_capacity * (1.0 - usage**exponent) ** (1.0 / exponent))


def longitudinal_capacity(
    speed_mps: float,
    angle_deg: float,
    cfg: ProjectConfig,
    *,
    lateral_force_n: float = 0.0,
    braking: bool = False,
    long_accel_guess_mps2: float = 0.0,
) -> ForceCapacity:
    """Return available longitudinal tyre force after lateral-force use."""

    if not math.isfinite(lateral_force_n) or lateral_force_n < 0:
        raise ValueError("lateral_force_n must be finite and non-negative")
    loads = axle_loads(speed_mps, long_accel_guess_mps2, angle_deg, cfg)
    front_share = loads.front_n / loads.total_n
    front_lateral = lateral_force_n * front_share
    rear_lateral = lateral_force_n - front_lateral

    front_mu_long = load_sensitive_mu(
        loads.front_n,
        cfg.tyres.mu_longitudinal_ref,
        cfg.tyres.reference_load_n,
        cfg.tyres.load_sensitivity_exponent,
    )
    rear_mu_long = load_sensitive_mu(
        loads.rear_n,
        cfg.tyres.mu_longitudinal_ref,
        cfg.tyres.reference_load_n,
        cfg.tyres.load_sensitivity_exponent,
    )
    front_mu_lat = load_sensitive_mu(
        loads.front_n,
        cfg.tyres.mu_lateral_ref,
        cfg.tyres.reference_load_n,
        cfg.tyres.load_sensitivity_exponent,
    )
    rear_mu_lat = load_sensitive_mu(
        loads.rear_n,
        cfg.tyres.mu_lateral_ref,
        cfg.tyres.reference_load_n,
        cfg.tyres.load_sensitivity_exponent,
    )
    p = cfg.tyres.friction_ellipse_exponent
    front_long = _ellipse_remaining(front_mu_long * loads.front_n, front_lateral, p)
    rear_long = _ellipse_remaining(rear_mu_long * loads.rear_n, rear_lateral, p)

    if braking:
        total = min(front_long + rear_long, cfg.tyres.max_brake_force_n)
        mechanism = "brake-system limit" if total == cfg.tyres.max_brake_force_n else "tyre friction"
    else:
        front_long = 0.0
        rear_long *= cfg.powertrain.driven_rear_fraction
        total = rear_long
        mechanism = "driven-tyre friction"
    return ForceCapacity(
        available_force_n=total,
        front_available_n=front_long,
        rear_available_n=rear_long,
        front_lateral_n=front_lateral,
        rear_lateral_n=rear_lateral,
        limiting_mechanism=mechanism,
    )


def resistance_force(
    speed_mps: float,
    angle_deg: float,
    cfg: ProjectConfig,
    *,
    grade_rad: float = 0.0,
    headwind_mps: float = 0.0,
) -> float:
    """Return drag, rolling, and grade resistance; positive opposes travel."""

    aero = aero_state(angle_deg, speed_mps, cfg, headwind_mps=headwind_mps)
    weight = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2
    rolling = cfg.vehicle.rolling_resistance_coefficient * (weight * math.cos(grade_rad) + aero.downforce_n)
    grade = weight * math.sin(grade_rad)
    return float(aero.drag_n + rolling + grade)


def top_speed(angle_deg: float, cfg: ProjectConfig) -> float:
    """Solve the flat-road wheel-force/resistance equilibrium."""

    def residual(speed: float) -> float:
        return best_wheel_force(speed, cfg).force_n - resistance_force(speed, angle_deg, cfg)

    lower = cfg.solver.minimum_speed_mps
    upper = cfg.solver.maximum_speed_mps
    if residual(lower) <= 0:
        raise InfeasibleVehicleState("vehicle cannot overcome resistance at minimum solver speed")
    if residual(upper) >= 0:
        raise InfeasibleVehicleState("top speed lies above the configured solver maximum")
    return float(brentq(residual, lower, upper, xtol=1e-10, rtol=1e-12))


def _tractive_force_with_transfer(speed: float, angle_deg: float, cfg: ProjectConfig) -> tuple[float, float]:
    powertrain = best_wheel_force(speed, cfg)
    accel_guess = 0.0
    force = 0.0
    for _ in range(12):
        capacity = longitudinal_capacity(
            speed,
            angle_deg,
            cfg,
            long_accel_guess_mps2=accel_guess,
        )
        force = min(powertrain.force_n, capacity.available_force_n)
        new_accel = (force - resistance_force(speed, angle_deg, cfg)) / cfg.vehicle.mass_kg
        if abs(new_accel - accel_guess) < 1e-6:
            break
        accel_guess = 0.5 * (accel_guess + new_accel)
    return force, max(new_accel, 0.0)


def acceleration_time(
    v0_mps: float,
    v1_mps: float,
    angle_deg: float,
    cfg: ProjectConfig,
) -> AccelerationResult:
    """Integrate a full-throttle acceleration run between two speeds."""

    if not all(math.isfinite(value) for value in (v0_mps, v1_mps)):
        raise ValueError("acceleration speeds must be finite")
    if v0_mps < 0 or v1_mps <= v0_mps:
        raise ValueError("acceleration requires 0 <= v0 < v1")
    vmax = top_speed(angle_deg, cfg)
    if v1_mps > vmax + cfg.solver.speed_tolerance_mps:
        raise InfeasibleVehicleState(
            f"requested target exceeds top speed ({vmax * 3.6:.1f} km/h)"
        )

    steps = max(2, int(math.ceil((v1_mps - v0_mps) / 0.25)) + 1)
    speeds = np.linspace(v0_mps, v1_mps, steps)
    times = [0.0]
    distances = [0.0]
    accelerations: list[float] = []
    forces: list[float] = []
    for lower, upper in zip(speeds[:-1], speeds[1:]):
        midpoint = 0.5 * (lower + upper)
        force, accel = _tractive_force_with_transfer(midpoint, angle_deg, cfg)
        if accel <= 1e-8:
            raise InfeasibleVehicleState("vehicle cannot continue accelerating toward target")
        dt = (upper - lower) / accel
        ds = 0.5 * (lower + upper) * dt
        times.append(times[-1] + dt)
        distances.append(distances[-1] + ds)
        accelerations.append(accel)
        forces.append(force)
    return AccelerationResult(
        time_s=times[-1],
        distance_m=distances[-1],
        speed_mps=speeds,
        time_trace_s=np.asarray(times),
        distance_trace_m=np.asarray(distances),
        acceleration_mps2=np.asarray(accelerations),
        tractive_force_n=np.asarray(forces),
    )


def braking_distance(
    v0_mps: float,
    v1_mps: float,
    angle_deg: float,
    cfg: ProjectConfig,
) -> BrakingResult:
    """Integrate maximum braking distance with speed-dependent aero and grip."""

    if not all(math.isfinite(value) for value in (v0_mps, v1_mps)):
        raise ValueError("braking speeds must be finite")
    if v1_mps < 0 or v0_mps <= v1_mps:
        raise ValueError("braking requires v0 > v1 >= 0")
    steps = max(2, int(math.ceil((v0_mps - v1_mps) / 0.25)) + 1)
    speeds = np.linspace(v0_mps, v1_mps, steps)
    times = [0.0]
    distances = [0.0]
    decelerations: list[float] = []
    forces: list[float] = []
    decel_guess = 0.0
    for upper, lower in zip(speeds[:-1], speeds[1:]):
        midpoint = 0.5 * (upper + lower)
        for _ in range(12):
            capacity = longitudinal_capacity(
                midpoint,
                angle_deg,
                cfg,
                braking=True,
                long_accel_guess_mps2=-decel_guess,
            )
            new_decel = (
                capacity.available_force_n + resistance_force(midpoint, angle_deg, cfg)
            ) / cfg.vehicle.mass_kg
            if abs(new_decel - decel_guess) < 1e-6:
                break
            decel_guess = 0.5 * (decel_guess + new_decel)
        if new_decel <= 0:
            raise InfeasibleVehicleState("vehicle cannot decelerate under requested conditions")
        dt = (upper - lower) / new_decel
        ds = 0.5 * (upper + lower) * dt
        times.append(times[-1] + dt)
        distances.append(distances[-1] + ds)
        decelerations.append(new_decel)
        forces.append(capacity.available_force_n)
        decel_guess = new_decel
    return BrakingResult(
        time_s=times[-1],
        distance_m=distances[-1],
        speed_mps=speeds,
        time_trace_s=np.asarray(times),
        distance_trace_m=np.asarray(distances),
        deceleration_mps2=np.asarray(decelerations),
        brake_force_n=np.asarray(forces),
    )
