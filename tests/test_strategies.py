from __future__ import annotations

import numpy as np
import pytest

from f1wing.lap import solve_lap
from f1wing.strategies import (
    ActiveAeroSchedule,
    FixedAngleSchedule,
    OpenWingSchedule,
)


def test_fixed_schedule_is_reexported_and_constant():
    schedule = FixedAngleSchedule(13.0)
    assert schedule.angle_deg == 13.0


def test_open_wing_uses_low_drag_only_on_eligible_fast_straights(config, low_downforce_track):
    schedule = OpenWingSchedule.from_config(config)
    n = low_downforce_track.ds_m.size
    speed = np.full(n, config.strategy.activation_speed_mps + 5.0)
    accel = np.zeros(n)
    elapsed = np.arange(n, dtype=float) * 0.1
    profile = schedule.angle_profile(low_downforce_track, speed, accel, elapsed, config)
    assert np.all(profile[low_downforce_track.aero_eligible] == config.strategy.open_angle_deg)
    assert np.all(profile[~low_downforce_track.aero_eligible] == config.strategy.corner_angle_deg)


def test_open_wing_stays_closed_below_activation_speed(config, low_downforce_track):
    schedule = OpenWingSchedule.from_config(config)
    n = low_downforce_track.ds_m.size
    profile = schedule.angle_profile(
        low_downforce_track,
        np.full(n, config.strategy.activation_speed_mps - 1.0),
        np.zeros(n),
        np.arange(n, dtype=float) * 0.1,
        config,
    )
    assert np.all(profile == config.strategy.corner_angle_deg)


def test_actuator_rate_is_never_exceeded(config, low_downforce_track):
    result = solve_lap(
        low_downforce_track,
        config,
        ActiveAeroSchedule.from_config(config, actuator_limited=True),
    )
    rate = np.abs(np.diff(result.angle_deg) / np.diff(result.time_s))
    assert rate.max() <= config.strategy.max_actuator_rate_degps + 1e-6
    assert result.strategy_state.size == result.speed_mps.size


def test_actuator_limited_schedule_starts_in_safe_high_downforce_state(
    config, low_downforce_track
):
    result = solve_lap(
        low_downforce_track,
        config,
        ActiveAeroSchedule.from_config(config, actuator_limited=True),
    )
    assert result.angle_deg[0] == pytest.approx(config.strategy.corner_angle_deg)
    assert result.strategy_state[0] == "high-downforce"

