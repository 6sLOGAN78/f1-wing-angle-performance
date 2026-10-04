from __future__ import annotations

import numpy as np
import pytest

from f1wing.dynamics import (
    InfeasibleVehicleState,
    acceleration_time,
    axle_loads,
    best_wheel_force,
    braking_distance,
    load_sensitive_mu,
    longitudinal_capacity,
    resistance_force,
    top_speed,
)


def test_tyre_is_load_sensitive():
    mu1 = load_sensitive_mu(3000, 1.8, 3000, 0.08)
    mu2 = load_sensitive_mu(6000, 1.8, 3000, 0.08)
    assert mu1 == pytest.approx(1.8)
    assert mu2 == pytest.approx(1.8 * 2.0**-0.08)
    assert mu2 < mu1


def test_nonpositive_tyre_load_is_rejected():
    with pytest.raises(InfeasibleVehicleState, match="normal load"):
        load_sensitive_mu(0.0, 1.8, 3000, 0.08)


def test_axle_loads_conserve_weight_plus_downforce(config):
    loads = axle_loads(60.0, 0.0, 15.0, config)
    expected = config.vehicle.mass_kg * config.environment.gravity_mps2 + loads.aero_downforce_n
    assert loads.total_n == pytest.approx(expected)
    assert loads.front_n + loads.rear_n == pytest.approx(loads.total_n)


def test_positive_acceleration_transfers_load_rearward(config):
    steady = axle_loads(30.0, 0.0, 10.0, config)
    accelerating = axle_loads(30.0, 8.0, 10.0, config)
    assert accelerating.front_n < steady.front_n
    assert accelerating.rear_n > steady.rear_n


def test_powertrain_selects_valid_gear_and_reports_force(config):
    state = best_wheel_force(50.0, config)
    assert 1 <= state.gear <= len(config.powertrain.gear_ratios)
    assert config.powertrain.idle_rpm <= state.engine_rpm <= config.powertrain.redline_rpm
    assert state.force_n == pytest.approx(state.raw_force_n)
    assert state.force_n > 0


def test_combined_cornering_reduces_longitudinal_capacity(config):
    pure = longitudinal_capacity(45.0, 10.0, config, lateral_force_n=0.0)
    combined = longitudinal_capacity(45.0, 10.0, config, lateral_force_n=9000.0)
    assert combined.available_force_n < pure.available_force_n
    assert combined.available_force_n >= 0.0


def test_top_speed_closes_force_balance(config):
    speed = top_speed(10.0, config)
    residual = best_wheel_force(speed, config).force_n - resistance_force(speed, 10.0, config)
    assert abs(residual) < config.solver.force_tolerance_n
    assert 250.0 < speed * 3.6 < 400.0


def test_more_wing_reduces_top_speed(config):
    assert top_speed(18.0, config) < top_speed(0.0, config)


def test_acceleration_trace_is_finite_and_monotonic(config):
    result = acceleration_time(0.0, 100.0 / 3.6, 10.0, config)
    assert 1.0 < result.time_s < 10.0
    assert np.isfinite(result.distance_m)
    assert np.all(np.diff(result.speed_mps) > 0)
    assert np.all(np.diff(result.time_trace_s) > 0)


def test_acceleration_target_above_top_speed_is_rejected(config):
    with pytest.raises(InfeasibleVehicleState, match="top speed"):
        acceleration_time(0.0, 450.0 / 3.6, 10.0, config)


def test_braking_trace_is_finite_and_monotonic(config):
    result = braking_distance(300.0 / 3.6, 0.0, 15.0, config)
    assert np.isfinite(result.distance_m)
    assert result.distance_m > 0
    assert np.all(np.diff(result.speed_mps) <= 1e-9)
    assert np.all(np.diff(result.time_trace_s) > 0)


def test_high_downforce_shortens_high_speed_braking(config):
    low = braking_distance(300.0 / 3.6, 100.0 / 3.6, 0.0, config)
    high = braking_distance(300.0 / 3.6, 100.0 / 3.6, 18.0, config)
    assert high.distance_m < low.distance_m
