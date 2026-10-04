from __future__ import annotations

import math

import numpy as np
import pytest

from f1wing.aero import aero_state, wing_coefficients


def test_aero_force_is_zero_at_zero_relative_speed(config):
    state = aero_state(15.0, 0.0, config)
    assert state.downforce_n == pytest.approx(0.0)
    assert state.drag_n == pytest.approx(0.0)
    assert state.dynamic_pressure_pa == pytest.approx(0.0)


def test_force_scales_with_speed_squared(config):
    slow = aero_state(10.0, 40.0, config)
    fast = aero_state(10.0, 80.0, config)
    assert fast.downforce_n / slow.downforce_n == pytest.approx(4.0)
    assert fast.drag_n / slow.drag_n == pytest.approx(4.0)


def test_finite_wing_lift_slope_matches_hand_calculation(config):
    result = wing_coefficients(
        10.0,
        60.0,
        0.0,
        config.aero.nominal_ride_height_m,
        config.aero,
    )
    aspect_ratio = 1.0**2 / 0.72
    expected_slope = 6.1 / (1.0 + 6.1 / (math.pi * 0.78 * aspect_ratio))
    expected_cl = expected_slope * math.radians(12.0)
    assert result.aspect_ratio == pytest.approx(aspect_ratio)
    assert result.lift_curve_slope_3d_per_rad == pytest.approx(expected_slope)
    assert result.cl == pytest.approx(expected_cl)


def test_stall_transition_is_continuous_and_finite(config):
    values = [aero_state(a, 60.0, config) for a in np.linspace(17.9, 18.1, 41)]
    assert np.isfinite([value.cl_total for value in values]).all()
    assert max(np.abs(np.diff([value.cl_total for value in values]))) < 0.03
    assert min(value.cd_total for value in values) >= 0.0


def test_selected_angles_show_pre_stall_gain_and_post_stall_loss(config):
    states = {angle: aero_state(angle, 200.0 / 3.6, config) for angle in (0, 10, 18, 25, 30)}
    assert states[0].wing.cl < states[10].wing.cl < states[18].wing.cl
    assert states[18].wing.cl > states[25].wing.cl > states[30].wing.cl
    assert states[25].wing.cd > states[18].wing.cd
    assert states[30].wing.cd > states[25].wing.cd
    assert all(state.drag_n > 0 for state in states.values())


def test_rear_wing_load_moves_aero_balance_rearward(config):
    low = aero_state(0.0, 200.0 / 3.6, config)
    high = aero_state(18.0, 200.0 / 3.6, config)
    assert high.front_downforce_fraction < low.front_downforce_fraction
    assert high.center_of_pressure_from_front_m > low.center_of_pressure_from_front_m


def test_yaw_and_ride_height_corrections_remain_bounded(config):
    nominal = wing_coefficients(15, 60, 0, config.aero.nominal_ride_height_m, config.aero)
    extreme = wing_coefficients(15, 60, 90, 2.0, config.aero)
    ratio = extreme.cl / nominal.cl
    assert config.aero.minimum_multiplier**2 <= ratio <= config.aero.maximum_multiplier**2
    assert extreme.cd >= 0.0


def test_negative_relative_air_speed_is_rejected(config):
    with pytest.raises(ValueError, match="relative air speed"):
        aero_state(10.0, 5.0, config, headwind_mps=-10.0)


@pytest.mark.parametrize("angle", [-0.1, 30.1])
def test_wing_angle_outside_supported_range_is_rejected(config, angle):
    with pytest.raises(ValueError, match="wing angle"):
        aero_state(angle, 50.0, config)
