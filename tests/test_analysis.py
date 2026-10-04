from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from f1wing.analysis import (
    fixed_angle_sweep,
    monte_carlo,
    oat_sensitivity,
    optimize_active_angles,
    optimize_fixed_angle,
)
from f1wing.models import Track


def _coarsen(track: Track, stride: int = 20) -> Track:
    starts = np.arange(0, track.ds_m.size, stride)
    ds = np.add.reduceat(track.ds_m, starts)
    return Track(
        name=f"{track.name} test mesh",
        description=track.description,
        closed=track.closed,
        distance_m=np.concatenate(([0.0], np.cumsum(ds[:-1]))),
        ds_m=ds,
        curvature_1pm=track.curvature_1pm[starts],
        gradient_rad=track.gradient_rad[starts],
        aero_eligible=track.aero_eligible[starts],
        speed_limit_mps=track.speed_limit_mps[starts],
    )


@pytest.fixture(scope="module")
def balanced_sweep(config, balanced_track):
    return fixed_angle_sweep(balanced_track, config, range(31))


def test_fixed_sweep_contains_every_integer_angle(balanced_sweep):
    assert balanced_sweep.angle_deg.tolist() == list(range(31))
    assert np.isfinite(balanced_sweep.lap_time_s).all()
    assert (balanced_sweep.maximum_speed_kph > 0).all()
    assert balanced_sweep.converged.all()


def test_fixed_sweep_reuses_duplicate_angle_evaluation(config, balanced_track):
    table = fixed_angle_sweep(balanced_track, config, [10, 10])
    pd.testing.assert_series_equal(table.iloc[0], table.iloc[1], check_names=False)


def test_continuous_optimum_stays_inside_bounds(config, balanced_track, balanced_sweep):
    optimum = optimize_fixed_angle(
        balanced_track,
        config,
        sweep_table=balanced_sweep,
    )
    assert 0.0 <= optimum.angle_deg <= 30.0
    assert np.isfinite(optimum.lap_time_s)
    assert optimum.success
    assert not optimum.evaluated_points.empty


def test_active_optimization_audits_strategy_mode_and_angle_order(config, low_downforce_track):
    optimum = optimize_active_angles(
        _coarsen(low_downforce_track),
        config,
        actuator_limited=False,
    )
    assert optimum.success
    assert optimum.open_angle_deg < optimum.closed_angle_deg
    assert optimum.evaluated_points["actuator_limited"].eq(False).all()


def test_oat_sensitivity_retains_baseline_for_audit(config, balanced_track):
    table = oat_sensitivity(
        _coarsen(balanced_track),
        config,
        15.0,
        parameters=("aero.wing_cd0",),
    )
    assert table.shape[0] == 2
    assert set(table.perturbation_percent) == {-10.0, 10.0}
    assert table.baseline_lap_time_s.nunique() == 1
    assert np.isfinite(table[["baseline_lap_time_s", "lap_time_s"]]).all().all()


def test_monte_carlo_is_reproducible_and_reports_required_statistics(
    config, uncertainty_config, balanced_sweep
):
    first = monte_carlo(
        config,
        uncertainty_config,
        balanced_sweep,
        samples=1000,
    )
    second = monte_carlo(
        config,
        uncertainty_config,
        balanced_sweep,
        samples=1000,
    )
    pd.testing.assert_frame_equal(first.samples, second.samples, check_exact=True)
    pd.testing.assert_frame_equal(first.summary, second.summary, check_exact=True)
    pd.testing.assert_frame_equal(first.correlations, second.correlations, check_exact=True)
    assert set(first.summary["percentile"]) == {2.5, 50.0, 97.5}
    assert {"optimum_angle_deg", "minimum_lap_time_s", "gain_vs_10deg_s"}.issubset(
        first.samples
    )
