"""Fixed, open-wing, and two-state active aerodynamic schedules."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .lap import FixedAngleSchedule, LapState
from .models import ProjectConfig, Track


@dataclass(frozen=True)
class OpenWingSchedule:
    """Idealized instantaneous low-drag mode on eligible fast straights."""

    open_angle_deg: float
    closed_angle_deg: float
    activation_speed_mps: float
    deactivation_long_accel_mps2: float

    @classmethod
    def from_config(cls, cfg: ProjectConfig) -> "OpenWingSchedule":
        return cls(
            open_angle_deg=cfg.strategy.open_angle_deg,
            closed_angle_deg=cfg.strategy.corner_angle_deg,
            activation_speed_mps=cfg.strategy.activation_speed_mps,
            deactivation_long_accel_mps2=cfg.strategy.deactivation_long_accel_mps2,
        )

    def angle_at(self, index: int, state: LapState) -> float:
        del index
        eligible = (
            state.aero_eligible
            and state.speed_mps >= self.activation_speed_mps
            and state.longitudinal_accel_mps2 >= self.deactivation_long_accel_mps2
        )
        return self.open_angle_deg if eligible else self.closed_angle_deg

    def angle_profile(
        self,
        track: Track,
        speed_mps: np.ndarray,
        long_accel_mps2: np.ndarray,
        elapsed_s: np.ndarray,
        cfg: ProjectConfig,
    ) -> np.ndarray:
        del elapsed_s, cfg
        eligible = (
            track.aero_eligible
            & (speed_mps >= self.activation_speed_mps)
            & (long_accel_mps2 >= self.deactivation_long_accel_mps2)
        )
        return np.where(eligible, self.open_angle_deg, self.closed_angle_deg).astype(float)

    def state_profile(
        self, track: Track, angles: np.ndarray, cfg: ProjectConfig
    ) -> np.ndarray:
        del track, cfg
        return np.where(
            np.isclose(angles, self.open_angle_deg),
            "low-drag",
            "high-downforce",
        ).astype(object)


@dataclass(frozen=True)
class ActiveAeroSchedule(OpenWingSchedule):
    """Two-state active wing with optional delay, hysteresis, and rate limits."""

    activation_delay_s: float
    deactivation_delay_s: float
    max_actuator_rate_degps: float
    actuator_limited: bool = True

    @classmethod
    def from_config(
        cls,
        cfg: ProjectConfig,
        *,
        actuator_limited: bool = True,
        open_angle_deg: float | None = None,
        closed_angle_deg: float | None = None,
    ) -> "ActiveAeroSchedule":
        return cls(
            open_angle_deg=(
                cfg.strategy.open_angle_deg if open_angle_deg is None else open_angle_deg
            ),
            closed_angle_deg=(
                cfg.strategy.corner_angle_deg if closed_angle_deg is None else closed_angle_deg
            ),
            activation_speed_mps=cfg.strategy.activation_speed_mps,
            deactivation_long_accel_mps2=cfg.strategy.deactivation_long_accel_mps2,
            activation_delay_s=cfg.strategy.activation_delay_s,
            deactivation_delay_s=cfg.strategy.deactivation_delay_s,
            max_actuator_rate_degps=cfg.strategy.max_actuator_rate_degps,
            actuator_limited=actuator_limited,
        )

    def angle_profile(
        self,
        track: Track,
        speed_mps: np.ndarray,
        long_accel_mps2: np.ndarray,
        elapsed_s: np.ndarray,
        cfg: ProjectConfig,
    ) -> np.ndarray:
        desired_low_drag = (
            track.aero_eligible
            & (speed_mps >= self.activation_speed_mps)
            & (long_accel_mps2 >= self.deactivation_long_accel_mps2)
        )
        if not self.actuator_limited:
            return np.where(
                desired_low_drag,
                self.open_angle_deg,
                self.closed_angle_deg,
            ).astype(float)

        profile = np.full(speed_mps.size, self.closed_angle_deg, dtype=float)
        low_drag_timer = 0.0
        high_downforce_timer = 0.0
        mode_low_drag = False
        for index in range(1, speed_mps.size):
            dt = max(0.0, float(elapsed_s[index] - elapsed_s[index - 1]))
            if desired_low_drag[index]:
                low_drag_timer += dt
                high_downforce_timer = 0.0
                if low_drag_timer >= self.activation_delay_s:
                    mode_low_drag = True
            else:
                high_downforce_timer += dt
                low_drag_timer = 0.0
                if high_downforce_timer >= self.deactivation_delay_s:
                    mode_low_drag = False
            target = self.open_angle_deg if mode_low_drag else self.closed_angle_deg
            max_change = self.max_actuator_rate_degps * dt
            profile[index] = profile[index - 1] + np.clip(
                target - profile[index - 1],
                -max_change,
                max_change,
            )
        return np.clip(
            profile,
            cfg.aero.minimum_angle_deg,
            cfg.aero.maximum_angle_deg,
        )

    def state_profile(
        self, track: Track, angles: np.ndarray, cfg: ProjectConfig
    ) -> np.ndarray:
        del track, cfg
        labels = np.full(angles.size, "transition", dtype=object)
        labels[np.isclose(angles, self.closed_angle_deg, atol=1e-6)] = "high-downforce"
        labels[np.isclose(angles, self.open_angle_deg, atol=1e-6)] = "low-drag"
        return labels


__all__ = ["FixedAngleSchedule", "OpenWingSchedule", "ActiveAeroSchedule"]

