from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pytest

from f1wing.dynamics import InfeasibleVehicleState
from f1wing.lap import FixedAngleSchedule, lateral_speed_limit, solve_lap


def test_straight_has_no_lateral_speed_cap(config):
    assert math.isinf(lateral_speed_limit(0.0, 15.0, config))


def test_tighter_corner_has_lower_lateral_speed_limit(config):
    open_corner = lateral_speed_limit(1.0 / 300.0, 15.0, config)
    tight_corner = lateral_speed_limit(1.0 / 90.0, 15.0, config)
    assert tight_corner < open_corner
    assert tight_corner > 0


def test_more_pre_stall_wing_raises_cornering_limit(config):
    low = lateral_speed_limit(1.0 / 150.0, 0.0, config)
    high = lateral_speed_limit(1.0 / 150.0, 18.0, config)
    assert high > low


def test_solver_respects_every_local_limit(config, balanced_track):
    result = solve_lap(balanced_track, config, FixedAngleSchedule(15.0))
    assert result.converged
    assert np.all(result.speed_mps <= result.local_limit_mps + 1e-6)
    assert np.isfinite(result.lap_time_s)
    assert result.lap_time_s > 0


@pytest.mark.parametrize(
    "fixture_name",
    ["low_downforce_track", "balanced_track", "high_downforce_track"],
)
def test_all_track_archetypes_solve_at_fifteen_degrees(request, config, fixture_name):
    track = request.getfixturevalue(fixture_name)
    result = solve_lap(track, config, FixedAngleSchedule(15.0))
    assert result.converged
    assert np.isfinite(result.lap_time_s)
    assert result.maximum_speed_mps > result.minimum_speed_mps > 0
    assert result.iterations <= config.solver.max_iterations


def test_lap_metrics_and_diagnostics_are_complete(config, balanced_track):
    result = solve_lap(balanced_track, config, FixedAngleSchedule(12.0))
    n = balanced_track.ds_m.size
    assert result.speed_mps.size == n
    assert result.time_s.size == n
    assert result.angle_deg.tolist() == pytest.approx([12.0] * n)
    assert result.gear.size == n
    assert result.limiting_mechanism.size == n
    assert result.tractive_energy_j > 0
    assert 0 <= result.full_throttle_fraction <= 1
    assert result.maximum_braking_demand_n >= 0


def test_impossible_negative_normal_load_raises(config, balanced_track):
    bad_vehicle = replace(config.vehicle, front_static_fraction=1.2)
    bad_config = replace(config, vehicle=bad_vehicle)
    with pytest.raises(InfeasibleVehicleState, match="normal load"):
        solve_lap(balanced_track, bad_config, FixedAngleSchedule(15.0))


def test_angle_outside_configuration_is_rejected(config, balanced_track):
    with pytest.raises(ValueError, match="wing angle"):
        solve_lap(balanced_track, config, FixedAngleSchedule(31.0))
