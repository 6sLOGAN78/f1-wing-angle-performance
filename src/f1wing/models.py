"""Typed inputs and result containers shared by the simulation modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class Metadata:
    name: str
    version: str
    parameter_classification: str


@dataclass(frozen=True)
class EnvironmentConfig:
    air_density_kgpm3: float
    gravity_mps2: float


@dataclass(frozen=True)
class VehicleConfig:
    mass_kg: float
    wheelbase_m: float
    cg_height_m: float
    front_static_fraction: float
    tyre_radius_m: float
    rolling_resistance_coefficient: float


@dataclass(frozen=True)
class AeroConfig:
    reference_area_m2: float
    wing_area_m2: float
    wing_span_m: float
    span_efficiency: float
    lift_curve_slope_2d_per_rad: float
    zero_lift_angle_deg: float
    stall_angle_deg: float
    post_stall_width_deg: float
    wing_cd0: float
    stall_drag_gain: float
    baseline_cl: float
    baseline_cd: float
    baseline_front_downforce_fraction: float
    front_aero_application_from_front_m: float
    rear_aero_application_from_front_m: float
    nominal_ride_height_m: float
    ride_height_sensitivity_per_m: float
    yaw_sensitivity_per_deg2: float
    minimum_multiplier: float
    maximum_multiplier: float
    minimum_angle_deg: float
    maximum_angle_deg: float


@dataclass(frozen=True)
class TyreConfig:
    mu_longitudinal_ref: float
    mu_lateral_ref: float
    reference_load_n: float
    load_sensitivity_exponent: float
    friction_ellipse_exponent: float
    max_brake_force_n: float


@dataclass(frozen=True)
class PowertrainConfig:
    rpm_points: tuple[float, ...]
    torque_nm: tuple[float, ...]
    gear_ratios: tuple[float, ...]
    final_drive_ratio: float
    driveline_efficiency: float
    idle_rpm: float
    redline_rpm: float
    driven_rear_fraction: float


@dataclass(frozen=True)
class SolverConfig:
    track_spacing_m: float
    speed_tolerance_mps: float
    force_tolerance_n: float
    max_iterations: int
    minimum_speed_mps: float
    maximum_speed_mps: float


@dataclass(frozen=True)
class StrategyConfig:
    open_angle_deg: float
    corner_angle_deg: float
    activation_delay_s: float
    deactivation_delay_s: float
    max_actuator_rate_degps: float
    activation_speed_mps: float
    deactivation_long_accel_mps2: float


@dataclass(frozen=True)
class ProjectConfig:
    metadata: Metadata
    environment: EnvironmentConfig
    vehicle: VehicleConfig
    aero: AeroConfig
    tyres: TyreConfig
    powertrain: PowertrainConfig
    solver: SolverConfig
    strategy: StrategyConfig
    parameter_register: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class UncertaintyParameter:
    distribution: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class UncertaintyConfig:
    seed: int
    samples: int
    parameters: Mapping[str, UncertaintyParameter]


@dataclass(frozen=True)
class TrackPoint:
    distance_m: float
    ds_m: float
    curvature_1pm: float
    gradient_rad: float
    aero_eligible: bool
    speed_limit_mps: float


@dataclass(frozen=True)
class Track:
    name: str
    description: str
    closed: bool
    distance_m: np.ndarray
    ds_m: np.ndarray
    curvature_1pm: np.ndarray
    gradient_rad: np.ndarray
    aero_eligible: np.ndarray
    speed_limit_mps: np.ndarray

    @property
    def length_m(self) -> float:
        return float(np.sum(self.ds_m))

    @property
    def points(self) -> tuple[TrackPoint, ...]:
        return tuple(
            TrackPoint(
                distance_m=float(self.distance_m[i]),
                ds_m=float(self.ds_m[i]),
                curvature_1pm=float(self.curvature_1pm[i]),
                gradient_rad=float(self.gradient_rad[i]),
                aero_eligible=bool(self.aero_eligible[i]),
                speed_limit_mps=float(self.speed_limit_mps[i]),
            )
            for i in range(self.ds_m.size)
        )

