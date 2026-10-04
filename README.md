# Simulation and Analysis of the Effect of Rear-Wing Angle on Formula 1 Car Performance

[![Verification Status](https://img.shields.io/badge/Verification-ALL%20PASSED-success)](#verification-and-reproducibility)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![MATLAB Compatibility](https://img.shields.io/badge/MATLAB-R2022b%2B-orange)](#matlab-and-simulink-parity)
[![Classification](https://img.shields.io/badge/Classification-Educational%20Model-lightgrey)](#important-interpretation--educational-disclosure)

This project provides a comprehensive, reproducible engineering study that quantifies how rear-wing incidence angle (0° to 30°) alters the aerodynamic balance, longitudinal dynamics, cornering limits, and lap-time performance of a representative modern Formula 1-style single-seater.

The codebase features a tested Python reference engine paired with an independent MATLAB R2022b+ parity package and an automated Simulink demonstration builder. All findings, figures, reports, and presentation slides are deterministically derived from a versioned execution manifest and SHA-256 artifact bundle.

---

## Headline Findings

Across an angle sweep from 0° to 30° at 1° resolution, vehicle performance was evaluated across three distinct circuit archetypes with a single shared vehicle parameter configuration:

| Circuit Archetype | Characteristics | Fixed Optimum Angle $\alpha^*$ | Fixed Min Lap Time | Actuator-Limited Active Lap Time | Primary Limiting Factor |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Balanced** | Silverstone / Barcelona style | **4.997°** | **58.812 s** | **59.353 s** | Grip vs drag balance |
| **High Downforce** | Monaco / Hungaroring style | **18.000°** | **64.528 s** | **64.615 s** | Cornering traction (stall limit) |
| **Low Downforce** | Monza style | **17.996°** | **68.150 s** | **68.599 s** | Corner exit speed onto long straights |

### Key Aerodynamic & Dynamic Insights
1. **Efficiency vs. Maximum Downforce Disconnect:** Peak aerodynamic efficiency ($L/D \approx 3.42$) occurs at **6.0°**, whereas peak total vehicle downforce ($18.38\text{ kN}$ at $300\text{ km/h}$) peaks at the stall boundary (**18.0°**).
2. **Terminal Velocity Penalty:** Terminal velocity drops monotonically from **348.6 km/h** at 0° to **304.5 km/h** at 18° and **278.4 km/h** at 30° (a 70.2 km/h deficit across the sweep).
3. **Catastrophic Post-Stall Drag:** Increasing wing angle past the 18° stall boundary produces continuous flow separation, escalating drag by up to +185% without delivering additional vertical load, resulting in severe lap time degradation across all circuit types.
4. **Actuator Latency & Active Aero Trade-off:** While idealized instantaneous active aero provides lap-time gains (up to -0.544 s on the low-downforce circuit), an actuator rate-limited (90°/s) schedule with transition delays incurs net lap-time penalties (+0.087 s to +0.541 s slower than fixed-optimum) under simple threshold switching, showing that predictive control is required.

---

## Important Interpretation & Educational Disclosure

- **Representative Educational Parameters:** All vehicle, powertrain, tyre, and aerodynamic values are representative educational figures informed by public FIA technical regulations and published motorsport vehicle dynamics literature.
- **No Proprietary Telemetry or CFD:** No confidential Formula 1 team telemetry, wind tunnel measurements, or 3D CFD flow fields are used or claimed.
- **Quasi-Steady Modeling Scope:** The lap solver operates quasi-steadily along 2D circuit centerlines discretized at $\le 5\text{ m}$. Transient damper dynamics, tyre temperature/wear, driver steering styles, and aeroelastic wing flexing are abstracted.

---

## Deliverable Manifest

The project generates a complete suite of submission-ready academic artifacts in `results/`:

- **Comprehensive Technical Report:**
  - `results/report/F1_Wing_Angle_Performance_Report.docx` (~35 pages, styled with Aptos typography, numbered equations, embedded figures, parameter registers, and citations).
  - `results/report/F1_Wing_Angle_Performance_Report.pdf` (Rendered PDF).
- **Executive Presentation Deck:**
  - `results/presentation/F1_Wing_Angle_Performance_Presentation.pptx` (18-slide 16:9 widescreen presentation deck with embedded figures, key metric tables, and clean motorsport styling).
  - `results/presentation/F1_Wing_Angle_Performance_Presentation.pdf` (Converted slide deck PDF).
- **Numerical Datasets & Workbooks:**
  - `results/workbooks/F1_Wing_Angle_Results.xlsx` (Multi-tab formatted Excel workbook containing all 16 study results).
  - `results/data/F1_Wing_Angle_Results.mat` (MATLAB v7.3 compatible binary data structure).
  - `results/data/*.csv` (16 tidy CSV files covering polars, force vs speed, straight-line, cornering, circuit sweeps, active optimization, Monte Carlo, and sensitivity).
- **High-Resolution Figures (PNG & SVG):**
  - 16 publication figures stored in both vector (`.svg`) and raster (`.png`) formats in `results/figures/`.
- **Cryptographic Provenance:**
  - `results/manifest.json` (SHA-256 checksums of all inputs and generated outputs, run ID, and random seed).
  - `results/verification/verification_report.json` (Full end-to-end consistency and contract verification report).

---

## Quickstart & Reproduction Pipeline

### 1. Requirements & Setup

```bash
# Python 3.10 or higher
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. End-to-End One-Command Execution

```bash
# Step 1: Run complete numerical physics, optimization, and uncertainty pipeline
MPLCONFIGDIR=/tmp/f1wing-mpl PYTHONPATH=src python3 scripts/run_analysis.py \
  --config config/project.json \
  --tracks tracks \
  --output results \
  --clean

# Step 2: Build DOCX report, PPTX slides, and headless PDF conversions
PYTHONPATH=src python3 scripts/build_documents.py --manifest results/manifest.json

# Step 3: Run comprehensive cross-artifact consistency verification
PYTHONPATH=src python3 scripts/verify_project.py --project-root .
```

### 3. Automated Test Suite

```bash
# Run the complete test suite (unit, dynamics, lap solver, report, presentation, end-to-end)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q
```

---

## Repository Map

```
f1-wing-angle-performance/
├── config/
│   ├── project.json              # Vehicle, aero, powertrain, tyre, and solver parameters
│   └── uncertainty.json          # Monte Carlo distribution specifications (seed 3106)
├── docs/
│   └── superpowers/              # Design specifications and detailed implementation plans
├── matlab/
│   ├── +f1wing/                  # MATLAB package functions matching Python reference
│   ├── run_project.m             # Top-level MATLAB analysis script
│   ├── run_parity_tests.m        # MATLAB assertions against reference CSV fixtures
│   └── build_simulink_demo.m     # Programmatic Simulink model builder
├── presentation/
│   └── slide_content.json        # 18-slide structured presentation content specification
├── references/
│   └── references.json           # Primary academic and regulatory literature citations
├── report/
│   ├── report_content.md         # Source technical narrative and derivations
│   └── assumptions_and_limitations.md # Full engineering assumption register
├── results/                      # Generated data, figures, documents, and verification logs
│   ├── data/                     # 16 CSV result tables and F1_Wing_Angle_Results.mat
│   ├── figures/                  # 16 PNG and SVG figures
│   ├── parity/                   # Shared parity reference cases (0°, 10°, 18°, 25°, 30°)
│   ├── presentation/             # PPTX and PDF presentations
│   ├── report/                   # DOCX and PDF technical reports
│   ├── verification/             # verification_report.json
│   ├── workbooks/                # F1_Wing_Angle_Results.xlsx
│   └── manifest.json             # SHA-256 cryptographic provenance manifest
├── scripts/
│   ├── run_analysis.py           # Numerical analysis pipeline entry point
│   ├── build_documents.py        # Report and slide deck generation script
│   ├── check_matlab_static.py    # Static contract checker for MATLAB code
│   └── verify_project.py         # End-to-end cross-artifact validation script
├── src/
│   └── f1wing/                   # Python reference simulation engine
│       ├── aero.py               # Nonlinear wing aerodynamics and stall blending
│       ├── analysis.py           # Sweeps, optimization, and Monte Carlo engine
│       ├── config.py             # Validated input ingestion and track discretization
│       ├── documents.py          # DOCX report and PDF generation engine
│       ├── dynamics.py           # Tyre load sensitivity, powertrain, and braking
│       ├── exports.py            # Manifest, table, figure, and workbook exporter
│       ├── lap.py                # Quasi-steady forward/backward lap solver
│       ├── models.py             # Immutable dataclasses and typing definitions
│       ├── presentation.py       # PPTX presentation generation engine
│       └── strategies.py         # Fixed, open-wing (DRS), and active aero schedules
├── tests/                        # Comprehensive pytest test suite (79+ passing tests)
├── tracks/                       # Circuit geometry files (low_downforce, balanced, high_downforce)
├── pyproject.toml                # Package metadata and dependencies
└── README.md                     # Project overview, results, and user guide
```

---

## MATLAB and Simulink Parity

An independent MATLAB R2022b+ implementation is provided in `matlab/`:

```matlab
cd matlab
results = run_project();         % Run angle sweeps and lap optimizations
run_parity_tests();              % Validate outputs against Python reference cases within 1e-4 tolerance
modelPath = build_simulink_demo(); % Programmatically construct F1WingAeroDemo.slx
```

### Simulink Demonstration Architecture
`build_simulink_demo.m` constructs `results/simulink/F1WingAeroDemo.slx` programmatically:
- Dynamic wing angle command input with configurable **Rate Limiter** block (90°/s).
- Core **MATLAB Function** block executing nonlinear lift/drag/stall equations.
- Dynamic pressure multiplier ($q = \frac{1}{2} \rho V^2$) and longitudinal force summation.
- Continuous 1-DOF vehicle longitudinal speed integrator ($m \cdot \dot{V} = F_{\text{traction}} - F_{\text{drag}}$).
- Logged output scopes for vehicle speed, downforce, drag, and wing angle.

*Notice: MATLAB and Simulink are not installed in the authoring environment, so these `.m` files are statically checked but **not runtime-tested** here. Full runtime parity execution should be performed in a licensed MATLAB R2022b+ environment using `run_parity_tests` to validate against `results/parity/reference_cases.csv`.*
