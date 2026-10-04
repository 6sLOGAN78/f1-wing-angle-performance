# F1 Rear-Wing Angle Performance Project

This project studies how rear-wing angle changes the performance of a representative Formula 1-style car. It combines a nonlinear aerodynamic model, load-sensitive tyres, a geared powertrain, and a quasi-steady lap-time solver. The final package generates circuit-specific optimization, active-aero comparisons, uncertainty analysis, report-ready figures, a detailed report, and a presentation.

## Important interpretation

The inputs are **representative educational parameters**. They are not proprietary Formula 1 team data, wind-tunnel measurements, or full-car CFD results. The three included tracks are synthetic circuit archetypes intended for controlled comparison, not official circuit reproductions.

## Planned one-command workflow

```bash
MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src python3 scripts/run_analysis.py \
  --config config/project.json --tracks tracks --output results --clean
PYTHONPATH=src python3 scripts/build_documents.py --manifest results/manifest.json
PYTHONPATH=src python3 scripts/verify_project.py --project-root .
```

During development, run tests with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q
```

The explicit pytest setting avoids environment-installed plugins that require sandbox-forbidden network sockets.

## Directory map

- `config/` — vehicle, aerodynamic, solver, strategy, and uncertainty inputs.
- `tracks/` — synthetic low-, balanced-, and high-downforce circuit definitions.
- `src/f1wing/` — Python reference implementation.
- `matlab/` — MATLAB parity implementation and optional Simulink builder.
- `scripts/` — analysis, document, static-check, and verification entry points.
- `tests/` — unit and integration tests.
- `results/` — generated data, figures, report, presentation, and manifest.

## Units

All internal calculations use SI units. Configuration keys encode their units where practical, and every exported plot/table must label units explicitly.

## MATLAB and Simulink

The `matlab/` directory provides an independent MATLAB R2022b+ implementation that reads the same JSON configurations and track definitions as Python:

```matlab
cd matlab
results = run_project();
run_parity_tests();
modelPath = build_simulink_demo();
```

`build_simulink_demo` programmatically creates `results/simulink/F1WingAeroDemo.slx`. The model includes an angle command, actuator **Rate Limiter**, nonlinear aerodynamic **MATLAB Function**, tractive/drag force balance, vehicle-speed integrator, scope, signal logging, and four workspace outputs.

MATLAB and Simulink are not installed in the authoring environment, so these `.m` files are statically checked but **not runtime-tested** here. Run `run_parity_tests` in MATLAB R2022b+ to compare aerodynamic results at 0°, 10°, 18°, 25°, and 30° and the three circuit lap results against `results/parity/reference_cases.csv`.
