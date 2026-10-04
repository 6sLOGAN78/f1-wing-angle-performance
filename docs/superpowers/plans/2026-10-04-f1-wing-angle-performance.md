# Advanced F1 Wing-Angle Performance Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a reproducible, submission-ready project that quantifies how rear-wing angle changes the aerodynamic and lap-time performance of a representative Formula 1-style car.

**Architecture:** A tested Python reference engine will implement the physics, optimization, uncertainty analysis, exports, and document generation. A matching MATLAB implementation will consume the same JSON/CSV inputs and parity fixtures; an optional MATLAB script will construct a Simulink demonstration. All report and presentation claims will be generated from one versioned result bundle and manifest.

**Tech Stack:** Python 3.10+, NumPy, SciPy, pandas, Matplotlib, python-docx, python-pptx, openpyxl, pytest, MATLAB R2022b+ source compatibility, optional Simulink, LibreOffice for PDF conversion.

**Spec:** `docs/superpowers/specs/2026-10-04-f1-wing-angle-performance-design.md`

## Global Constraints

- Treat all vehicle and aerodynamic values as representative educational parameters, never proprietary or measured current-team data.
- Sweep fixed rear-wing angles from 0° through 30° at 1° resolution and retain continuous bounded optimization within the same range.
- Use SI units internally and label every exported axis and table column with units.
- Use Monte Carlo seed `3106` and at least 1,000 samples.
- Discretize every supplied circuit archetype at no more than 5 m spacing.
- Generate low-, medium-, and high-downforce circuit results with one common vehicle configuration.
- Keep fixed, open-wing/DRS, ideal active-aero, and actuator-limited active-aero results explicitly separated.
- Do not label any synthetic graphic or coefficient map as CFD or wind-tunnel data.
- The Python reference implementation is runtime-tested; MATLAB code is statically checked and supplied with runtime parity tests because MATLAB/Octave is unavailable in the authoring environment.
- A clean top-level run must regenerate tables, figures, document source files, PDFs, and the result manifest.

## Review Focus

- **Near-zero speed:** force, gearing, lap-time, and division operations must remain finite; covered in Tasks 2–4 tests.
- **Stall transition:** coefficients must remain continuous and drag non-negative at and beyond the configured stall angle; covered in Task 2 tests.
- **Infeasible grip or balance:** the solver must report a descriptive failure rather than emit NaNs or negative normal loads; covered in Tasks 3–4 tests.
- **Active-aero transitions:** actuator lag and eligibility boundaries must not produce illegal instantaneous state changes; covered in Task 5 tests.
- **Cross-artifact mismatch:** report, slides, plots, CSV/XLSX, and manifest must share the same run identifier and headline values; covered in Tasks 6, 8, and 9 tests.

---

## File Map

The implementation will create a self-contained `f1-wing-angle-performance/` directory:

- `README.md` — setup, execution, directory map, interpretation, and limitations.
- `pyproject.toml` — Python package metadata and dependencies.
- `config/project.json` — representative vehicle, aero, tyre, powertrain, solver, and strategy parameters.
- `config/uncertainty.json` — Monte Carlo and one-at-a-time ranges.
- `tracks/*.json` — segment descriptions for three synthetic circuit archetypes.
- `references/references.json` — reference metadata and stable URLs used by document generators.
- `src/f1wing/models.py` — immutable configuration and result dataclasses.
- `src/f1wing/config.py` — validated JSON loading and track discretization.
- `src/f1wing/aero.py` — nonlinear wing and full-car aerodynamic model.
- `src/f1wing/dynamics.py` — load-sensitive tyres, powertrain, acceleration, braking, and top speed.
- `src/f1wing/lap.py` — lateral limits and iterative forward/backward lap solver.
- `src/f1wing/strategies.py` — fixed, open-wing, and active-aero schedules.
- `src/f1wing/analysis.py` — sweeps, optimization, sensitivity, and Monte Carlo.
- `src/f1wing/exports.py` — result bundle, CSV/XLSX, figure, and manifest generation.
- `src/f1wing/documents.py` — Word report, PowerPoint deck, and PDF conversion.
- `scripts/run_analysis.py` — one-command numerical pipeline.
- `scripts/build_documents.py` — one-command report and slide generation.
- `scripts/verify_project.py` — end-to-end acceptance checks.
- `scripts/check_matlab_static.py` — MATLAB file/signature/static-policy validation.
- `matlab/run_project.m` — MATLAB analysis entry point.
- `matlab/+f1wing/*.m` — MATLAB functions matching the Python reference interfaces.
- `matlab/build_simulink_demo.m` — optional programmatic Simulink demonstration builder.
- `matlab/run_parity_tests.m` — MATLAB assertions against shared parity fixtures.
- `tests/` — Python unit, integration, export, and document tests.
- `results/` — generated data, figures, manifest, report, presentation, and verification log.

### Task 1: Project Foundation, Typed Models, and Validated Inputs

**Files:**
- Create: `f1-wing-angle-performance/pyproject.toml`
- Create: `f1-wing-angle-performance/README.md`
- Create: `f1-wing-angle-performance/src/f1wing/__init__.py`
- Create: `f1-wing-angle-performance/src/f1wing/models.py`
- Create: `f1-wing-angle-performance/src/f1wing/config.py`
- Create: `f1-wing-angle-performance/config/project.json`
- Create: `f1-wing-angle-performance/config/uncertainty.json`
- Create: `f1-wing-angle-performance/tracks/low_downforce.json`
- Create: `f1-wing-angle-performance/tracks/balanced.json`
- Create: `f1-wing-angle-performance/tracks/high_downforce.json`
- Test: `f1-wing-angle-performance/tests/test_config.py`

**Interfaces:**
- Consumes: Approved design specification and JSON files owned by this task.
- Produces: `ProjectConfig`, `AeroConfig`, `TyreConfig`, `PowertrainConfig`, `SolverConfig`, `UncertaintyConfig`, `Track`, `TrackPoint`; `load_project_config(path: Path) -> ProjectConfig`; `load_uncertainty_config(path: Path) -> UncertaintyConfig`; `load_track(path: Path, spacing_m: float) -> Track`.

- [x] **Step 1: Write failing configuration tests**

```python
def test_all_tracks_are_closed_and_resolve_to_five_metres_or_less():
    for name in ("low_downforce", "balanced", "high_downforce"):
        track = load_track(TRACKS / f"{name}.json", spacing_m=5.0)
        assert track.closed
        assert track.ds_m.max() <= 5.0 + 1e-9
        assert track.length_m > 4_000

def test_invalid_wing_bounds_are_rejected(tmp_path):
    path = write_project_json(tmp_path, min_angle_deg=30, max_angle_deg=0)
    with pytest.raises(ValueError, match="wing-angle bounds"):
        load_project_config(path)
```

- [x] **Step 2: Run the tests and confirm they fail before the package exists**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_config.py -q`

Expected: FAIL during import of `f1wing.config`.

- [x] **Step 3: Implement dataclasses, strict unit-aware JSON validation, and track discretization**

Use immutable dataclasses; reject missing keys, non-finite values, negative masses/areas, invalid angle bounds, inconsistent gear arrays, uncertainty ranges outside physical bounds, and track segments with non-positive length.

- [x] **Step 4: Add representative project and track configurations**

Document every parameter’s meaning, SI unit, source category (`assumed`, `derived`, or `reference-informed`), and supported range. Store track geometry as synthetic constant/linearly varying curvature segments with grade and aero-mode eligibility flags.

- [x] **Step 5: Run foundation tests**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_config.py -q`

Expected: all configuration tests PASS.

- [x] **Step 6: Initialize the self-contained project repository and commit**

```bash
cd f1-wing-angle-performance
git init
git add pyproject.toml README.md src config tracks tests
git commit -m "chore: establish F1 wing analysis project"
```

### Task 2: Nonlinear Rear-Wing and Full-Car Aerodynamic Model

**Files:**
- Create: `f1-wing-angle-performance/src/f1wing/aero.py`
- Create: `f1-wing-angle-performance/tests/test_aero.py`

**Interfaces:**
- Consumes: `AeroConfig`, `VehicleConfig` from Task 1.
- Produces: `wing_coefficients(angle_deg: float, speed_mps: float, yaw_deg: float, ride_height_m: float, cfg: AeroConfig) -> WingCoefficients`; `aero_state(angle_deg: float, speed_mps: float, cfg: ProjectConfig, *, yaw_deg: float = 0.0, ride_height_m: float | None = None, headwind_mps: float = 0.0) -> AeroState`.

- [x] **Step 1: Write failing aerodynamic invariant tests**

```python
def test_aero_force_is_zero_at_zero_relative_speed(config):
    state = aero_state(15.0, 0.0, config)
    assert state.downforce_n == pytest.approx(0.0)
    assert state.drag_n == pytest.approx(0.0)

def test_force_scales_with_speed_squared(config):
    slow = aero_state(10.0, 40.0, config)
    fast = aero_state(10.0, 80.0, config)
    assert fast.downforce_n / slow.downforce_n == pytest.approx(4.0)
    assert fast.drag_n / slow.drag_n == pytest.approx(4.0)

def test_stall_transition_is_continuous_and_finite(config):
    values = [aero_state(a, 60.0, config) for a in np.linspace(17.9, 18.1, 41)]
    assert np.isfinite([v.cl_total for v in values]).all()
    assert max(np.abs(np.diff([v.cl_total for v in values]))) < 0.03
    assert min(v.cd_total for v in values) >= 0.0
```

- [x] **Step 2: Run tests and confirm missing-function failures**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_aero.py -q`

Expected: FAIL because `f1wing.aero` is not implemented.

- [x] **Step 3: Implement finite-wing, induced-drag, stall, yaw, ride-height, and balance calculations**

Use a finite-wing-corrected pre-stall slope, a continuously differentiable blend through stall, induced drag `CL²/(pi*e*AR)`, bounded yaw/ride-height multipliers, and separate front/rear force application points. Clip only at documented physical bounds and raise on negative relative air speed after wind resolution.

- [x] **Step 4: Add regression fixtures for angles 0°, 10°, 18°, 25°, and 30° at 200 km/h**

Assert downforce increases to the stall region, post-stall lift falls, drag remains non-negative, and centre-of-pressure moves rearward as rear-wing loading increases.

- [x] **Step 5: Run aerodynamic tests**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_aero.py -q`

Expected: all aerodynamic tests PASS.

- [x] **Step 6: Commit**

```bash
git add src/f1wing/aero.py tests/test_aero.py
git commit -m "feat: model nonlinear rear-wing aerodynamics"
```

### Task 3: Tyres, Powertrain, Acceleration, Braking, and Top Speed

**Files:**
- Create: `f1-wing-angle-performance/src/f1wing/dynamics.py`
- Create: `f1-wing-angle-performance/tests/test_dynamics.py`

**Interfaces:**
- Consumes: `ProjectConfig`, `AeroState`.
- Produces: `load_sensitive_mu(normal_load_n: float, mu_ref: float, ref_load_n: float, exponent: float) -> float`; `axle_loads(speed_mps: float, long_accel_mps2: float, angle_deg: float, cfg: ProjectConfig) -> AxleLoads`; `best_wheel_force(speed_mps: float, cfg: ProjectConfig) -> PowertrainState`; `longitudinal_capacity(...) -> ForceCapacity`; `top_speed(angle_deg: float, cfg: ProjectConfig) -> float`; `acceleration_time(v0_mps: float, v1_mps: float, angle_deg: float, cfg: ProjectConfig) -> AccelerationResult`; `braking_distance(v0_mps: float, v1_mps: float, angle_deg: float, cfg: ProjectConfig) -> BrakingResult`.

- [x] **Step 1: Write failing dynamics tests**

```python
def test_tyre_is_load_sensitive(config):
    mu1 = load_sensitive_mu(3000, 1.8, 3000, 0.08)
    mu2 = load_sensitive_mu(6000, 1.8, 3000, 0.08)
    assert mu2 < mu1

def test_top_speed_closes_force_balance(config):
    speed = top_speed(10.0, config)
    residual = best_wheel_force(speed, config).force_n - resistance_force(speed, 10.0, config)
    assert abs(residual) < 5.0

def test_braking_trace_is_finite_and_monotonic(config):
    result = braking_distance(300 / 3.6, 0.0, 15.0, config)
    assert np.isfinite(result.distance_m)
    assert np.all(np.diff(result.speed_mps) <= 1e-9)
```

- [x] **Step 2: Run tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_dynamics.py -q`

Expected: FAIL because dynamics interfaces are missing.

- [x] **Step 3: Implement load-sensitive tyre and friction-ellipse helpers**

Guard zero/negative axle normal load with a descriptive `InfeasibleVehicleState`. Include static distribution, aerodynamic distribution, and bounded longitudinal load transfer.

- [x] **Step 4: Implement torque interpolation, gears, traction limit, rolling resistance, and grade**

Return the selected gear, engine speed, raw wheel force, traction-limited force, and limiting mechanism at every query.

- [x] **Step 5: Implement root-solved top speed and distance-domain acceleration/braking integrations**

Use SciPy bounded root finding/integration tolerances from `SolverConfig`; handle targets above top speed with an explicit infeasibility result.

- [x] **Step 6: Run dynamics tests**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_dynamics.py -q`

Expected: all dynamics tests PASS.

- [x] **Step 7: Commit**

```bash
git add src/f1wing/dynamics.py tests/test_dynamics.py
git commit -m "feat: add tyre and longitudinal vehicle dynamics"
```

### Task 4: G–G Limits and Forward/Backward Lap Solver

**Files:**
- Create: `f1-wing-angle-performance/src/f1wing/lap.py`
- Create: `f1-wing-angle-performance/tests/test_lap.py`

**Interfaces:**
- Consumes: `Track`, `ProjectConfig`, Task 2 aerodynamics, Task 3 dynamics, and an angle schedule callable `angle_at(index: int, state: LapState) -> float`.
- Produces: `lateral_speed_limit(curvature_1pm: float, angle_deg: float, cfg: ProjectConfig, *, grade_rad: float = 0.0) -> float`; `solve_lap(track: Track, cfg: ProjectConfig, schedule: AngleSchedule) -> LapResult`.

- [x] **Step 1: Write failing lap-solver tests**

```python
def test_straight_has_no_lateral_speed_cap(config):
    assert math.isinf(lateral_speed_limit(0.0, 15.0, config))

def test_solver_respects_every_local_limit(config, balanced_track):
    result = solve_lap(balanced_track, config, FixedAngleSchedule(15.0))
    assert result.converged
    assert np.all(result.speed_mps <= result.local_limit_mps + 1e-6)
    assert np.isfinite(result.lap_time_s)

def test_impossible_negative_normal_load_raises(config, bad_track):
    with pytest.raises(InfeasibleVehicleState):
        solve_lap(bad_track, config, FixedAngleSchedule(15.0))
```

- [x] **Step 2: Run tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_lap.py -q`

Expected: FAIL because lap interfaces are missing.

- [x] **Step 3: Implement lateral limits with load-sensitive axle capacity and aero balance**

Solve the implicit speed/downforce/grip equation with a bounded scalar root; enforce axle-level capacity so an aerodynamically imbalanced car cannot use impossible total grip.

- [x] **Step 4: Implement iterative forward acceleration and backward braking passes**

Work in distance domain, apply track grade and speed limits, use the friction ellipse when longitudinal and lateral demand coexist, and stop only when maximum speed change is below `SolverConfig.convergence_mps` or raise `SolverConvergenceError` at the iteration limit.

- [x] **Step 5: Integrate lap metrics and diagnostics**

Return lap time, tractive energy, full-throttle fraction, maximum/minimum speed, braking demand, convergence count, selected gear, limiting mechanism, force histories, and wing-angle history.

- [x] **Step 6: Run lap tests and the first three-track smoke simulation**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_lap.py -q`

Expected: all lap tests PASS; each archetype solves at 15° with finite lap time.

- [x] **Step 7: Commit**

```bash
git add src/f1wing/lap.py tests/test_lap.py
git commit -m "feat: implement quasi-steady lap solver"
```

### Task 5: Wing Strategies and Circuit-Specific Optimization

**Files:**
- Create: `f1-wing-angle-performance/src/f1wing/strategies.py`
- Create: `f1-wing-angle-performance/src/f1wing/analysis.py`
- Create: `f1-wing-angle-performance/tests/test_strategies.py`
- Create: `f1-wing-angle-performance/tests/test_analysis.py`

**Interfaces:**
- Consumes: Task 4 `solve_lap` and the shared configuration/tracks.
- Produces: `FixedAngleSchedule`; `OpenWingSchedule`; `ActiveAeroSchedule`; `fixed_angle_sweep(track, cfg, angles_deg: Sequence[float]) -> pd.DataFrame`; `optimize_fixed_angle(track, cfg) -> OptimizationResult`; `optimize_active_angles(track, cfg, *, actuator_limited: bool) -> OptimizationResult`; `oat_sensitivity(...) -> pd.DataFrame`; `monte_carlo(...) -> MonteCarloResult`.

- [x] **Step 1: Write failing strategy and optimization tests**

```python
def test_fixed_sweep_contains_every_integer_angle(config, balanced_track):
    table = fixed_angle_sweep(balanced_track, config, range(31))
    assert table.angle_deg.tolist() == list(range(31))
    assert np.isfinite(table.lap_time_s).all()

def test_actuator_rate_is_never_exceeded(config, low_downforce_track):
    result = solve_lap(low_downforce_track, config, ActiveAeroSchedule.from_config(config))
    rate = np.abs(np.diff(result.angle_deg) / np.diff(result.time_s))
    assert rate.max() <= config.strategy.max_actuator_rate_degps + 1e-6

def test_continuous_optimum_stays_inside_bounds(config, balanced_track):
    optimum = optimize_fixed_angle(balanced_track, config)
    assert 0.0 <= optimum.angle_deg <= 30.0
```

- [x] **Step 2: Run tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_strategies.py tests/test_analysis.py -q`

Expected: FAIL because strategies and analysis are missing.

- [x] **Step 3: Implement fixed, eligible-straight open-wing, ideal two-state, and actuator-limited schedules**

Model eligibility, threshold hysteresis, activation/deactivation delay, rate limit, and safe high-downforce default. Store state transitions in `LapResult` for audit.

- [x] **Step 4: Implement 0°–30° sweeps and bounded fixed/active optimization**

Cache identical lap evaluations. Return the optimum, neighbouring sensitivity, convergence information, and all evaluated points; never hide an unsuccessful solve.

- [x] **Step 5: Implement deterministic ±10% and seeded Monte Carlo analysis**

Read distributions from `uncertainty.json`, use `numpy.random.default_rng(3106)`, run at least 1,000 samples, export 2.5/50/97.5 percentiles, and compute Spearman rank correlations for optimum angle and lap-time gain.

- [x] **Step 6: Run strategy and analysis tests**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_strategies.py tests/test_analysis.py -q`

Expected: all tests PASS and repeated Monte Carlo subsets are byte-for-byte deterministic.

- [x] **Step 7: Commit**

```bash
git add src/f1wing/strategies.py src/f1wing/analysis.py tests/test_strategies.py tests/test_analysis.py
git commit -m "feat: optimize fixed and active wing strategies"
```

### Task 6: Reproducible Result Bundle, Figures, Tables, and Manifest

**Files:**
- Create: `f1-wing-angle-performance/src/f1wing/exports.py`
- Create: `f1-wing-angle-performance/scripts/run_analysis.py`
- Create: `f1-wing-angle-performance/tests/test_exports.py`
- Create: `f1-wing-angle-performance/results/.gitkeep`
- Generate: `f1-wing-angle-performance/results/parity/reference_cases.csv`
- Generate: `f1-wing-angle-performance/results/data/F1_Wing_Angle_Results.mat`

**Interfaces:**
- Consumes: All numerical interfaces from Tasks 1–5.
- Produces: `run_full_analysis(project_path: Path, track_dir: Path, output_dir: Path) -> ResultBundle`; `export_result_bundle(bundle: ResultBundle, output_dir: Path) -> Path`; `build_all_figures(bundle: ResultBundle, output_dir: Path) -> list[Path]`; manifest schema `manifest.json` with run ID, seed, input hashes, artifact hashes, figure-data mapping, units, and headline metrics; MATLAB-compatible `.mat` data and parity CSV fixtures.

- [x] **Step 1: Write failing export-consistency tests**

```python
def test_manifest_links_every_figure_to_data(result_bundle, tmp_path):
    manifest_path = export_result_bundle(result_bundle, tmp_path)
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["figures"]) >= 14
    for figure in manifest["figures"]:
        assert (tmp_path / figure["path"]).is_file()
        assert (tmp_path / figure["source_data"]).is_file()

def test_xlsx_and_csv_headline_values_match(result_bundle, tmp_path):
    export_result_bundle(result_bundle, tmp_path)
    assert read_csv_optima(tmp_path) == read_xlsx_optima(tmp_path)
```

- [x] **Step 2: Run tests and confirm failure**

Run: `cd f1-wing-angle-performance && MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src pytest tests/test_exports.py -q`

Expected: FAIL because export interfaces are missing.

- [x] **Step 3: Implement result orchestration and tidy data exports**

Create CSV tables for polars, force sweeps, straight-line metrics, cornering metrics, lap sweeps, strategy comparisons, uncertainty, sensitivities, and MATLAB parity cases; mirror the full result bundle in one formatted XLSX workbook and a SciPy-generated MATLAB `.mat` file.

- [x] **Step 4: Generate the required 14+ figures in PNG and SVG**

Use a consistent accessible style, colour-blind-safe palette, descriptive titles, SI/kph units, uncertainty bands, and captions stored in manifest metadata. Include no decorative chartjunk or unsupported CFD imagery.

- [x] **Step 5: Implement deterministic manifest and provenance hashes**

Hash inputs and generated artifacts with SHA-256. Keep the run ID deterministic for identical inputs by deriving it from the input-hash set rather than wall-clock time; record generation time separately.

- [x] **Step 6: Run the full numerical pipeline and export tests**

Run: `cd f1-wing-angle-performance && MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src python3 scripts/run_analysis.py --config config/project.json --tracks tracks --output results`

Run: `cd f1-wing-angle-performance && MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src pytest tests/test_exports.py -q`

Expected: analysis exits 0, all required tables/figures exist, and export tests PASS.

- [x] **Step 7: Commit**

```bash
git add src/f1wing/exports.py scripts/run_analysis.py tests/test_exports.py results/.gitkeep
git commit -m "feat: export reproducible analysis results"
```

### Task 7: MATLAB Parity Implementation and Simulink Demonstration Builder

**Files:**
- Create: `f1-wing-angle-performance/matlab/run_project.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/loadConfig.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/loadTrack.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/wingCoefficients.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/aeroState.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/tyreMu.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/wheelForce.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/solveLap.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/fixedAngleSweep.m`
- Create: `f1-wing-angle-performance/matlab/+f1wing/exportResults.m`
- Create: `f1-wing-angle-performance/matlab/build_simulink_demo.m`
- Create: `f1-wing-angle-performance/matlab/run_parity_tests.m`
- Create: `f1-wing-angle-performance/scripts/check_matlab_static.py`
- Test: `f1-wing-angle-performance/tests/test_matlab_contract.py`

**Interfaces:**
- Consumes: Shared Task 1 JSON/track files and Task 6 `results/parity/reference_cases.csv`.
- Produces: MATLAB functions equivalent to the named Python interfaces; `run_project.m` generating MATLAB CSV/figures; `build_simulink_demo.m` creating `F1WingAeroDemo.slx` when Simulink is available.

- [x] **Step 1: Export parity cases and write failing MATLAB contract tests**

```python
def test_required_matlab_functions_and_signatures_exist(project_root):
    report = check_matlab_tree(project_root / "matlab")
    assert report.missing_files == []
    assert report.signature_errors == []
    assert report.forbidden_absolute_paths == []

def test_parity_fixture_covers_stall_and_all_tracks(parity_csv):
    assert {0, 10, 18, 25, 30}.issubset(set(parity_csv.angle_deg))
    assert set(parity_csv.track.dropna()) == {"low_downforce", "balanced", "high_downforce"}
```

- [x] **Step 2: Run contract tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_matlab_contract.py -q`

Expected: FAIL with the list of missing MATLAB files.

- [x] **Step 3: Implement MATLAB configuration, aero, tyre, powertrain, and lap functions**

Use MATLAB R2022b-compatible language features, the same formulas and tolerances as Python, explicit SI units in variable names/comments, and tables compatible with CSV export.

- [x] **Step 4: Implement MATLAB project entry point and parity assertions**

`run_project.m` must accept optional config/output paths, sweep 0:30, solve all tracks, and export comparable tables. `run_parity_tests.m` must load `reference_cases.csv`, compare coefficients/forces within `1e-6` relative tolerance and lap metrics within `1e-4`, and print a clear PASS/FAIL summary.

- [x] **Step 5: Implement optional Simulink builder**

Programmatically create blocks for speed input, actuator-limited angle command, aerodynamic coefficient calculation, dynamic pressure, downforce/drag outputs, scopes, and logged signals. Detect missing Simulink and print a non-fatal instruction rather than failing the numerical project.

- [x] **Step 6: Run static checks and document runtime limitation**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src python3 scripts/check_matlab_static.py matlab`

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_matlab_contract.py -q`

Expected: static checker exits 0 and contract tests PASS. README/report must state that MATLAB runtime parity awaits execution on MATLAB R2022b+.

- [x] **Step 7: Commit**

```bash
git add matlab scripts/check_matlab_static.py tests/test_matlab_contract.py results/parity
git commit -m "feat: add MATLAB parity model and Simulink builder"
```

### Task 8: Detailed Report and Assumptions Register

**Files:**
- Create: `f1-wing-angle-performance/references/references.json`
- Create: `f1-wing-angle-performance/report/report_content.md`
- Create: `f1-wing-angle-performance/report/assumptions_and_limitations.md`
- Create: `f1-wing-angle-performance/src/f1wing/documents.py`
- Create: `f1-wing-angle-performance/scripts/build_documents.py`
- Create: `f1-wing-angle-performance/tests/test_report.py`
- Generate: `f1-wing-angle-performance/results/report/F1_Wing_Angle_Performance_Report.docx`
- Generate: `f1-wing-angle-performance/results/report/F1_Wing_Angle_Performance_Report.pdf`

**Interfaces:**
- Consumes: Task 6 manifest, tables, figures, references metadata, and approved specification.
- Produces: `build_report(manifest_path: Path, output_docx: Path) -> Path`; `convert_office_to_pdf(source: Path, output_dir: Path) -> Path`; a detailed report with numbered figures/tables, equations, citations, captions, appendices, and visible limitations.

- [x] **Step 1: Write failing report integrity tests**

```python
def test_report_contains_required_sections_and_run_id(generated_report, manifest):
    text = extract_docx_text(generated_report)
    for heading in REQUIRED_REPORT_HEADINGS:
        assert heading in text
    assert manifest["run_id"] in text
    assert "representative educational model" in text.lower()

def test_every_manifest_headline_value_appears_in_report(generated_report, manifest):
    text = extract_docx_text(generated_report)
    for formatted_value in formatted_headline_values(manifest):
        assert formatted_value in text
```

- [x] **Step 2: Run report tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_report.py -q`

Expected: FAIL because report generator and source content do not exist.

- [x] **Step 3: Write the full technical narrative and source-backed literature review**

Cover abstract, objectives, literature, derivations, architecture, parameters, method, verification, results, interpretation, uncertainty, limitations, conclusions, future work, references, and appendices. Distinguish source-backed facts, model assumptions, and simulation findings in the prose.

- [x] **Step 4: Implement DOCX generation from the manifest and content source**

Apply title/heading styles, numbered equations, cross-referenced figure/table captions, page numbers, headers/footers, table formatting, alt text where supported, and automatic insertion of all report figures. Target substantive detail rather than a fixed page count; expected rendered length is approximately 30–45 pages.

- [x] **Step 5: Generate PDF with LibreOffice and verify both formats**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src python3 scripts/build_documents.py --manifest results/manifest.json --report-only`

Expected: DOCX and PDF exist, LibreOffice exits 0, and PDF has at least 25 pages with no empty figure placeholders.

- [x] **Step 6: Run report tests**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_report.py -q`

Expected: all report integrity tests PASS.

- [x] **Step 7: Commit**

```bash
git add references report src/f1wing/documents.py scripts/build_documents.py tests/test_report.py
git commit -m "docs: generate detailed F1 wing analysis report"
```

### Task 9: Presentation and Cross-Artifact Verification

**Files:**
- Create: `f1-wing-angle-performance/presentation/slide_content.json`
- Create: `f1-wing-angle-performance/tests/test_presentation.py`
- Create: `f1-wing-angle-performance/tests/test_end_to_end.py`
- Create: `f1-wing-angle-performance/scripts/verify_project.py`
- Generate: `f1-wing-angle-performance/results/presentation/F1_Wing_Angle_Performance_Presentation.pptx`
- Generate: `f1-wing-angle-performance/results/presentation/F1_Wing_Angle_Performance_Presentation.pdf`
- Generate: `f1-wing-angle-performance/results/verification/verification_report.json`

**Interfaces:**
- Consumes: Task 6 manifest, figures/tables, Task 8 document engine and references.
- Produces: `build_presentation(manifest_path: Path, content_path: Path, output_pptx: Path) -> Path`; `verify_project(project_root: Path) -> VerificationReport`; an 18-slide editable deck and PDF.

- [x] **Step 1: Write failing presentation and end-to-end tests**

```python
def test_deck_has_expected_structure_and_no_overflow(generated_pptx):
    deck = Presentation(generated_pptx)
    assert 16 <= len(deck.slides) <= 20
    assert all_slide_text_within_safe_bounds(deck)
    assert required_slide_titles().issubset(extract_slide_titles(deck))

def test_all_artifacts_share_run_id(project_results):
    report = verify_project(project_results.parent)
    assert report.run_id_consistent
    assert report.headline_values_consistent
    assert report.missing_artifacts == []
    assert report.hash_mismatches == []
```

- [x] **Step 2: Run tests and confirm failure**

Run: `cd f1-wing-angle-performance && PYTHONPATH=src pytest tests/test_presentation.py tests/test_end_to_end.py -q`

Expected: FAIL because presentation and verifier do not exist.

- [x] **Step 3: Implement the 16–20 slide presentation**

Use a restrained motorsport visual system and cover title, motivation, research question, theory, architecture, assumptions, aerodynamic polar, force-speed results, straight-line results, cornering/braking, three circuit optima, strategy comparison, uncertainty/sensitivity, limitations, conclusions, and references. Use generated figures rather than screenshots of tables.

- [x] **Step 4: Implement PPTX-to-PDF conversion and layout checks**

Detect text outside slide safe bounds, missing images, low-resolution raster assets, blank slides, and unresolved placeholders before conversion.

- [x] **Step 5: Implement the final project verifier**

Verify input/output hashes, file readability, manifest coverage, shared run ID, headline numeric equality after documented rounding, plot source data, report section presence, slide structure, test result status, and MATLAB limitation disclosure. Write machine-readable JSON and a human-readable summary.

- [x] **Step 6: Run the clean end-to-end build**

Run: `cd f1-wing-angle-performance && MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src python3 scripts/run_analysis.py --config config/project.json --tracks tracks --output results --clean`

Run: `cd f1-wing-angle-performance && PYTHONPATH=src python3 scripts/build_documents.py --manifest results/manifest.json`

Run: `cd f1-wing-angle-performance && PYTHONPATH=src python3 scripts/verify_project.py --project-root .`

Expected: all commands exit 0; DOCX, PPTX, PDFs, CSVs, XLSX, PNGs, SVGs, manifest, and verification report are present and readable.

- [x] **Step 7: Run the complete automated test suite**

Run: `cd f1-wing-angle-performance && MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src pytest -q`

Expected: all tests PASS with no warnings promoted to errors and no skipped core-physics tests.

- [x] **Step 8: Manually inspect representative pages/slides and plots**

Render the report and presentation to images; inspect the title page, equations, widest tables, at least six plots, the three optimum-angle result sections, uncertainty page, limitations page, and all slides for clipping, unreadable labels, or inconsistent values.

- [x] **Step 9: Update README with final commands and known runtime limitation**

Record the exact successful verification commands, result directory, configuration editing instructions, MATLAB R2022b+ parity command, optional Simulink builder command, and the fact that MATLAB runtime validation was not available in the authoring environment.

- [x] **Step 10: Final commit**

```bash
git add README.md presentation scripts/verify_project.py tests results/manifest.json results/verification
git commit -m "feat: complete F1 wing-angle project package"
```

## Final Acceptance Checklist

- [x] `pytest -q` passes from a clean checkout with documented dependencies.
- [x] `scripts/run_analysis.py` recreates the 0°–30° sweeps, optimizations, uncertainty study, tables, figures, and manifest.
- [x] All three circuit archetypes produce finite, converged fixed and active-aero results.
- [x] Each of the 14 required result categories has both source data and PNG/SVG output.
- [x] CSV and XLSX headline values match.
- [x] DOCX and PDF report open, contain the complete technical narrative, and match the manifest.
- [x] PPTX and PDF presentation open, fit within slide bounds, and match the manifest.
- [x] MATLAB static/contract checks pass and runtime limitations are disclosed.
- [x] Optional Simulink builder fails gracefully without Simulink and is documented for MATLAB users.
- [x] Verification report shows no missing artifacts, hash mismatches, or cross-document numeric inconsistencies.
- [x] Assumptions and limitations are visible in README, report, and presentation.
