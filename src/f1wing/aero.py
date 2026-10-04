"""Physics-informed nonlinear rear-wing and full-car aerodynamic model."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .models import AeroConfig, ProjectConfig


@dataclass(frozen=True)
class WingCoefficients:
    angle_deg: float
    effective_angle_deg: float
    aspect_ratio: float
    lift_curve_slope_3d_per_rad: float
    cl: float
    cd_profile: float
    cd_induced: float
    cd_stall: float
    cd: float
    efficiency: float
    yaw_multiplier: float
    ride_height_multiplier: float


@dataclass(frozen=True)
class AeroState:
    relative_air_speed_mps: float
    dynamic_pressure_pa: float
    cl_total: float
    cd_total: float
    wing: WingCoefficients
    downforce_n: float
    drag_n: float
    front_downforce_n: float
    rear_downforce_n: float
    front_downforce_fraction: float
    center_of_pressure_from_front_m: float


def _finite(name: str, value: float) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)


def wing_coefficients(
    angle_deg: float,
    speed_mps: float,
    yaw_deg: float,
    ride_height_m: float,
    cfg: AeroConfig,
) -> WingCoefficients:
    """Return nonlinear finite-wing coefficients for an inverted rear wing.

    ``cl`` is a positive downforce coefficient. ``speed_mps`` is validated for
    interface consistency but Reynolds-number effects are outside this model.
    """

    angle = _finite("wing angle", angle_deg)
    speed = _finite("speed_mps", speed_mps)
    yaw = _finite("yaw_deg", yaw_deg)
    ride_height = _finite("ride_height_m", ride_height_m)
    if speed < 0:
        raise ValueError("speed_mps must be non-negative")
    if not cfg.minimum_angle_deg <= angle <= cfg.maximum_angle_deg:
        raise ValueError(
            f"wing angle must lie between {cfg.minimum_angle_deg:g} and "
            f"{cfg.maximum_angle_deg:g} degrees"
        )

    aspect_ratio = cfg.wing_span_m**2 / cfg.wing_area_m2
    slope_3d = cfg.lift_curve_slope_2d_per_rad / (
        1.0 + cfg.lift_curve_slope_2d_per_rad / (math.pi * cfg.span_efficiency * aspect_ratio)
    )
    effective_angle = angle - cfg.zero_lift_angle_deg
    stall_effective_angle = cfg.stall_angle_deg - cfg.zero_lift_angle_deg
    cl_stall = slope_3d * math.radians(stall_effective_angle)

    if angle <= cfg.stall_angle_deg:
        cl_base = slope_3d * math.radians(effective_angle)
        stall_excess = 0.0
    else:
        stall_excess = angle - cfg.stall_angle_deg
        cl_base = cl_stall * math.exp(-stall_excess / cfg.post_stall_width_deg)

    yaw_multiplier = float(
        np.clip(
            1.0 - cfg.yaw_sensitivity_per_deg2 * yaw**2,
            cfg.minimum_multiplier,
            cfg.maximum_multiplier,
        )
    )
    ride_multiplier = float(
        np.clip(
            1.0 - cfg.ride_height_sensitivity_per_m * (ride_height - cfg.nominal_ride_height_m),
            cfg.minimum_multiplier,
            cfg.maximum_multiplier,
        )
    )
    cl = max(0.0, cl_base * yaw_multiplier * ride_multiplier)
    cd_profile = cfg.wing_cd0
    cd_induced = cl**2 / (math.pi * cfg.span_efficiency * aspect_ratio)
    normalized_excess = stall_excess / cfg.post_stall_width_deg
    cd_stall = cfg.stall_drag_gain * (1.0 - math.exp(-(normalized_excess**2)))
    cd = max(0.0, cd_profile + cd_induced + cd_stall)
    efficiency = cl / cd if cd > 0 else math.inf

    return WingCoefficients(
        angle_deg=angle,
        effective_angle_deg=effective_angle,
        aspect_ratio=aspect_ratio,
        lift_curve_slope_3d_per_rad=slope_3d,
        cl=cl,
        cd_profile=cd_profile,
        cd_induced=cd_induced,
        cd_stall=cd_stall,
        cd=cd,
        efficiency=efficiency,
        yaw_multiplier=yaw_multiplier,
        ride_height_multiplier=ride_multiplier,
    )


def aero_state(
    angle_deg: float,
    speed_mps: float,
    cfg: ProjectConfig,
    *,
    yaw_deg: float = 0.0,
    ride_height_m: float | None = None,
    headwind_mps: float = 0.0,
) -> AeroState:
    """Calculate full-car aerodynamic coefficients, forces, and load balance.

    Positive ``headwind_mps`` increases relative air speed; a negative value is
    a tailwind. All force values are positive magnitudes.
    """

    vehicle_speed = _finite("speed_mps", speed_mps)
    headwind = _finite("headwind_mps", headwind_mps)
    if vehicle_speed < 0:
        raise ValueError("speed_mps must be non-negative")
    relative_speed = vehicle_speed + headwind
    if relative_speed < 0:
        raise ValueError("relative air speed cannot be negative")
    actual_ride_height = (
        cfg.aero.nominal_ride_height_m
        if ride_height_m is None
        else _finite("ride_height_m", ride_height_m)
    )
    wing = wing_coefficients(
        angle_deg,
        relative_speed,
        yaw_deg,
        actual_ride_height,
        cfg.aero,
    )

    wing_area_ratio = cfg.aero.wing_area_m2 / cfg.aero.reference_area_m2
    wing_cl_on_car_reference = wing.cl * wing_area_ratio
    wing_cd_on_car_reference = wing.cd * wing_area_ratio
    cl_total = cfg.aero.baseline_cl + wing_cl_on_car_reference
    cd_total = cfg.aero.baseline_cd + wing_cd_on_car_reference

    front_cl = cfg.aero.baseline_cl * cfg.aero.baseline_front_downforce_fraction
    rear_cl = cfg.aero.baseline_cl * (1.0 - cfg.aero.baseline_front_downforce_fraction)
    rear_cl += wing_cl_on_car_reference
    front_fraction = front_cl / cl_total
    center_of_pressure = (
        front_cl * cfg.aero.front_aero_application_from_front_m
        + rear_cl * cfg.aero.rear_aero_application_from_front_m
    ) / cl_total

    dynamic_pressure = 0.5 * cfg.environment.air_density_kgpm3 * relative_speed**2
    force_scale = dynamic_pressure * cfg.aero.reference_area_m2
    front_downforce = force_scale * front_cl
    rear_downforce = force_scale * rear_cl
    downforce = front_downforce + rear_downforce
    drag = force_scale * cd_total

    return AeroState(
        relative_air_speed_mps=relative_speed,
        dynamic_pressure_pa=dynamic_pressure,
        cl_total=cl_total,
        cd_total=cd_total,
        wing=wing,
        downforce_n=downforce,
        drag_n=drag,
        front_downforce_n=front_downforce,
        rear_downforce_n=rear_downforce,
        front_downforce_fraction=front_fraction,
        center_of_pressure_from_front_m=center_of_pressure,
    )
