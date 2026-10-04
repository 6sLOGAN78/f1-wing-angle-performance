from pathlib import Path

import pytest

from f1wing.config import load_project_config, load_track, load_uncertainty_config


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def config():
    return load_project_config(ROOT / "config" / "project.json")


@pytest.fixture(scope="session")
def low_downforce_track(config):
    return load_track(ROOT / "tracks" / "low_downforce.json", config.solver.track_spacing_m)


@pytest.fixture(scope="session")
def balanced_track(config):
    return load_track(ROOT / "tracks" / "balanced.json", config.solver.track_spacing_m)


@pytest.fixture(scope="session")
def high_downforce_track(config):
    return load_track(ROOT / "tracks" / "high_downforce.json", config.solver.track_spacing_m)


@pytest.fixture(scope="session")
def uncertainty_config():
    return load_uncertainty_config(ROOT / "config" / "uncertainty.json")
