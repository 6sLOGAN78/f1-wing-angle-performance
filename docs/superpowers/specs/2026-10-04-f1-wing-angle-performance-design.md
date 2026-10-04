# Advanced F1 Wing-Angle Performance Project — Design Specification

## 1. Purpose

Build a complete academic project titled **“Simulation and Analysis of the Effect of Rear-Wing Angle on Formula 1 Car Performance.”** The project will replace the previous ECU fuel-injection topic while retaining the sample project’s deliverable pattern: an explanatory report, an executable MATLAB-oriented simulation, result plots and tables, and a presentation.

The work must answer one central research question:

> How does rear-wing angle change the aerodynamic forces, straight-line performance, braking, cornering capability, energy demand, aerodynamic balance, and minimum achievable lap time of a representative Formula 1-style car under different circuit conditions?

The result is an educational engineering model, not a reconstruction of any team’s proprietary car. Every assumed or calibrated quantity must be identified as such.

## 2. Success Criteria

The completed package must:

1. Sweep fixed rear-wing angles from 0° through 30° and resolve at least 1° increments.
2. Model the expected pre-stall increase in downforce, the associated drag penalty, and post-stall loss of wing effectiveness.
3. Propagate aerodynamic changes into top speed, acceleration, braking, cornering, lap time, energy use, and front/rear aerodynamic balance.
4. Compare low-, medium-, and high-downforce circuit profiles using one consistent vehicle model.
5. Find the minimum-lap-time fixed wing angle for each circuit rather than declaring one universal optimum.
6. Compare fixed-wing operation with an idealized DRS/open-wing mode and a two-state active-aerodynamics strategy.
7. Quantify uncertainty and identify which assumptions most strongly influence the optimum.
8. Generate all headline figures and tables from code with a fixed random seed.
9. Include a detailed, submission-ready report and a concise presentation whose numerical claims match the exported simulation results.
10. State limitations prominently and avoid presenting synthetic data as measured F1 data or CFD results.

## 3. Technical Approach

### 3.1 Aerodynamic model

The rear wing is represented as an inverted, finite-span, multi-element wing. Its effective angle combines the commanded geometric angle with configurable incidence, wake, yaw, and ride-height corrections. The pre-stall lift slope starts from thin-airfoil theory and is reduced for finite aspect ratio:

\[
a_{3D}=\frac{a_0}{1+\frac{a_0}{\pi e AR}}
\]

The wing downforce coefficient rises nonlinearly to a configurable stall angle. A smooth post-stall continuation prevents discontinuities and reduces lift while increasing pressure drag. Wing drag contains profile, induced, and separation terms:

\[
C_{D,w}=C_{D0,w}+\frac{C_{L,w}^{2}}{\pi e AR}+C_{D,stall}
\]

Aerodynamic force magnitudes use relative air speed:

\[
F_{down}=\frac{1}{2}\rho V_{rel}^{2} A_{ref}C_L,
\qquad
F_{drag}=\frac{1}{2}\rho V_{rel}^{2} A_{ref}C_D
\]

The total-car map combines baseline body/floor/front-wing coefficients with the rear-wing contribution. Front and rear loads are tracked separately so that the centre of pressure and aerodynamic balance change with rear-wing angle. The model also applies bounded correction factors for ride height and yaw. No contour plot may be described as CFD unless it is actually produced by a CFD solver.

### 3.2 Vehicle and tyre model

The vehicle model contains configurable mass, wheelbase, centre-of-gravity location and height, tyre radius, rolling resistance, power/torque curve, gears, final drive, driveline efficiency, brake limit, and static weight distribution.

Tyre friction is load sensitive rather than constant:

\[
\mu(F_z)=\mu_{ref}\left(\frac{F_z}{F_{z,ref}}\right)^{-\lambda}
\]

Separate longitudinal and lateral parameters are permitted. Axle normal loads include static distribution, aerodynamic distribution, and longitudinal load transfer. Combined acceleration and cornering are constrained by a friction ellipse. The model remains quasi-steady; it does not claim to simulate transient tyre temperature, suspension modes, or driver control.

### 3.3 Powertrain and straight-line performance

Wheel force is calculated from a representative torque curve, gear ratios, final drive, tyre radius, and driveline efficiency, then limited by traction. Gear selection chooses the greatest admissible wheel force below the engine-speed limit. Resistant force includes aerodynamic drag, rolling resistance, and track grade.

Top speed is the positive equilibrium at which available wheel force equals resistance. Acceleration tests report 0–100 km/h and 100–200 km/h times. Braking distance is integrated from speed-dependent aerodynamic and tyre forces rather than calculated from one constant deceleration value.

### 3.4 Quasi-steady lap-time solver

Each track is discretized into distance stations of no more than 5 m. A station stores curvature, gradient, straight/activation eligibility, and speed limit. Lateral speed limits are found from curvature, downforce, aero balance, and tyre capacity. A forward pass applies powertrain and combined-grip acceleration limits; a backward pass applies braking limits. The passes iterate until speed changes fall below a documented tolerance.

Lap time is integrated from segment distance and average speed. Tractive energy, time spent at full throttle, braking demand, maximum speed, minimum speed, and speed distribution are exported. Three synthetic but clearly documented circuit archetypes are supplied:

- **Low-downforce:** long straights, few high-speed corners.
- **Balanced:** mixed straights and medium/high-speed corners.
- **High-downforce:** short straights and many low/medium-speed corners.

Synthetic profiles make the experiment reproducible and avoid claiming exact licensed circuit geometry. The configuration format must allow a user to add a measured or publicly available circuit later.

### 3.5 Wing operating modes

The following modes are compared:

- **Fixed:** one angle is held for the complete lap.
- **DRS/open wing:** the configured angle is reduced on eligible straights, with activation, deactivation, and actuator-rate constraints.
- **Two-state active aero:** a low-drag state is used on eligible straights and a high-downforce state under braking/cornering, inspired by the functional distinction between 2026 X-Mode and Z-Mode but not represented as an exact FIA control implementation.

Active modes must respect the same vehicle and tyre constraints as fixed modes. Idealized and actuator-limited results must not be mixed.

### 3.6 Optimization and uncertainty

The fixed-angle sweep evaluates every integer angle from 0° to 30°. A bounded continuous optimizer then refines the best angle for each circuit. Active-aero state angles are optimized within the same physical bounds and with a minimum separation between low- and high-downforce states.

A reproducible Monte Carlo study uses seed `3106` and at least 1,000 samples. Bounded distributions cover air density, headwind, tyre friction, engine power, wing lift slope, profile drag, stall angle, and baseline floor downforce. The output includes median, 2.5th and 97.5th percentiles for optimum angle and lap-time improvement, plus a rank-correlation sensitivity chart. A deterministic ±10% one-at-a-time sensitivity sweep provides an easily explained companion result.

## 4. Software Architecture

### 4.1 Primary MATLAB implementation

The MATLAB project will use small functions grouped by responsibility:

- parameter and circuit loading;
- aerodynamic coefficient and force calculation;
- tyre capacity and friction-ellipse calculation;
- powertrain and braking calculation;
- lap-time forward/backward solver;
- fixed and active wing strategies;
- optimization, Monte Carlo, and sensitivity analysis;
- figure, table, and summary export.

One top-level `run_project.m` command must reproduce the complete analysis into a clean output directory. A separate MATLAB script will construct an optional Simulink demonstration model for speed-dependent wing actuator and force response. The quasi-steady lap solver remains script-based because it is clearer and more appropriate than forcing the entire optimization into block diagrams.

### 4.2 Executable verification implementation

MATLAB and GNU Octave are not installed in the authoring environment. Therefore, a numerically equivalent Python reference implementation will generate and verify the submitted results. Shared JSON/CSV inputs, matched equations, and parity tables will keep the MATLAB and Python versions aligned. The report will disclose this verification arrangement. MATLAB-only code will also receive static checks and focused review, but it must not be described as runtime-tested here.

### 4.3 Configuration and reproducibility

Human-readable configuration files hold the representative vehicle, tyre, aerodynamic, solver, uncertainty, and track parameters. Units are SI internally; plot labels may additionally show km/h. Generated files must contain metadata including configuration name, generation timestamp, code version identifier if available, and random seed.

## 5. Deliverables

The project directory will contain:

1. `README.md` with prerequisites, one-command execution, directory map, and interpretation warnings.
2. MATLAB source code and the optional Simulink model-builder script.
3. A Python reference implementation and automated tests.
4. JSON/CSV configuration and track data.
5. Exported CSV and XLSX result tables.
6. Publication-quality PNG and SVG figures.
7. A detailed Word report and PDF export.
8. An editable PowerPoint presentation and PDF export.
9. A concise assumptions-and-limitations register.
10. A result manifest linking every report figure/table to its generating data file.

## 6. Required Results and Figures

At minimum, the automated analysis must produce:

1. Rear-wing \(C_L\), \(C_D\), and aerodynamic efficiency versus angle.
2. Downforce and drag versus speed for selected angles.
3. Front aerodynamic balance and centre-of-pressure shift versus angle and speed.
4. Top speed versus angle.
5. 0–100 and 100–200 km/h acceleration time versus angle.
6. Braking distance from 300 km/h versus angle.
7. Maximum cornering speed for representative corner radii versus angle.
8. Lap time versus angle for all three circuit archetypes.
9. Speed traces for low, optimum, and high wing settings on each circuit.
10. Fixed, DRS/open-wing, and active-aero strategy comparison.
11. Energy demand and time-at-full-throttle comparison.
12. Monte Carlo distributions and 95% intervals.
13. Sensitivity ranking/tornado chart.
14. A summary decision matrix explaining the performance trade-off.

## 7. Report Structure

The report will include:

1. Title page and project metadata.
2. Abstract and keywords.
3. Introduction and motivation.
4. Research question, objectives, scope, and contribution.
5. Literature review covering wing aerodynamics, downforce/drag trade-offs, race-car lap simulation, and active aerodynamics.
6. Governing theory and equation derivations.
7. Model architecture and data flow.
8. Parameters, assumptions, and uncertainty definitions.
9. Simulation procedure and verification method.
10. Results with numbered figures and tables.
11. Engineering interpretation and circuit-specific optimization.
12. Validation, sensitivity, and uncertainty discussion.
13. Limitations and ethical presentation of synthetic data.
14. Conclusions and future work.
15. References and appendices containing parameter tables, algorithm pseudocode, and execution instructions.

The presentation will follow the same argument in approximately 16–20 slides and emphasize the research question, methodology, main trade-off, optimum angles, uncertainty, and conclusions.

## 8. Validation and Acceptance Tests

The software must demonstrate:

- zero aerodynamic force at zero relative air speed;
- force proportionality to \(V^2\) when coefficients remain fixed;
- non-negative drag and normal loads throughout supported inputs;
- increasing pre-stall wing downforce and induced drag with angle;
- smooth, finite coefficients at stall and post-stall angles;
- a top-speed equilibrium residual within the numerical tolerance;
- acceleration and braking traces that remain finite and monotonic in distance;
- lap speeds that do not exceed local lateral, power, braking, or configured speed limits;
- convergence of the forward/backward passes;
- deterministic outputs when the same seed and inputs are used;
- sensitivity and Monte Carlo tables with no missing or non-finite values;
- agreement between headline report numbers, CSV/XLSX tables, plots, and slides;
- correct opening of generated DOCX, PPTX, PDF, CSV, XLSX, PNG, and SVG artifacts.

The Python test suite must cover physics invariants, edge cases, solver convergence, active-mode state transitions, optimization bounds, and export consistency. A final verification command must regenerate outputs and run all tests.

## 9. Sources and Technical Basis

The report will prioritize authoritative and primary sources, including:

- FIA Formula 1 technical regulations and FIA explanations of 2026 active aerodynamics;
- NASA references for lift, drag, finite-wing aspect ratio, and induced drag;
- Brayshaw and Harrison’s quasi-steady race-car lap simulation research;
- SAE research on nonlinear race-car aerodynamics and lap-time simulation;
- peer-reviewed or university-hosted work on race-car aerodynamic optimization and validated wing simulations.

Any inaccessible paywalled source will be cited only for claims visible in its abstract or replaced with an accessible source. References will not be used to imply that the representative parameters are measured from a current Formula 1 car.

## 10. Limitations

The project will explicitly acknowledge that:

- no proprietary F1 geometry, tyre data, power-unit map, or wind-tunnel data are available;
- the aerodynamic polar is physics-informed and calibrated for plausible trends, not obtained from full-car CFD;
- the lap solver is quasi-steady and omits transient suspension, tyre temperature/wear, driver behaviour, traffic, energy-recovery control, and detailed weather evolution;
- synthetic circuit archetypes are comparative experiments, not predictions of official race lap times;
- active-aero logic is a research abstraction, not a complete implementation of FIA control rules.

These limitations constrain absolute accuracy but still allow a rigorous comparison of how wing-angle trade-offs propagate through a consistent model.

## 11. Out of Scope

- Claiming exact performance for a named current F1 car or team.
- Fabricated wind-tunnel measurements or CFD flow fields.
- Full 3D RANS/LES CFD and mesh-convergence studies.
- Real-time hardware-in-the-loop testing.
- Safety-critical control software.
- Proprietary circuit telemetry or copyrighted track files.

## 12. Completion Definition

The project is complete only when a clean run regenerates the datasets and figures, the automated tests pass, the report and presentation open correctly, their headline values match the generated tables, and the limitations remain visible in both written deliverables.
