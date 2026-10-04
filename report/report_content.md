# Abstract

Rear-wing incidence is one of the clearest examples of a motorsport design trade-off: increasing angle generally raises downforce and cornering potential, while also raising drag and reducing straight-line performance. This project quantifies that trade-off for a representative Formula 1-style car using a reproducible quasi-steady vehicle model, three synthetic circuit archetypes, fixed and active aerodynamic strategies, bounded optimization, and uncertainty analysis. The complete workflow is implemented in Python and mirrored in MATLAB R2022b+-compatible source, with an optional programmatic Simulink demonstration.

The nominal fixed-wing optima are {OPT_LOW_ANGLE} degrees for the low-downforce circuit, {OPT_BAL_ANGLE} degrees for the balanced circuit, and {OPT_HIGH_ANGLE} degrees for the high-downforce circuit. Their corresponding predicted lap times are {OPT_LOW_TIME} s, {OPT_BAL_TIME} s, and {OPT_HIGH_TIME} s. The difference between circuits is more important than the label attached to a setup: optimum incidence emerges from the distribution of straights, corner radii, braking zones, tyre limits, and power-limited speed. The ideal-active model can improve selected cases, whereas actuator delay, finite slew rate, and simple switching logic may remove that benefit. Accordingly, the study's main conclusion is not that one angle is universally best, but that wing angle must be optimized as part of a coupled car–track–control system.

All numerical values are traceable to run ID {RUN_ID}. This is a representative educational model; it does not use proprietary team data, measured wind-tunnel maps, full-car CFD, or real circuit telemetry. Its purpose is comparative engineering analysis, transparent derivation, and a defensible platform for future physical validation.

{{TABLE:project_scope}}

# 1. Introduction and Research Question

## 1.1 Motivation

A racing car's aerodynamic package converts vehicle speed into forces that can enlarge the tyre force envelope. Downforce is valuable because it increases normal load without the same inertial penalty as adding mass. Drag is costly because it consumes tractive power and reduces acceleration and maximum speed. A rear wing influences both terms and also shifts aerodynamic balance toward the rear axle. The engineering problem is therefore coupled: the setting that is attractive in a slow corner may be unattractive on a long straight, and an aggressive setting can reach diminishing returns or stall.

Modern regulations reinforce the relevance of this question. FIA technical rules tightly define aerodynamic component volumes, construction, flexibility, and operation [1]. The 2026 framework also introduced coordinated movable front and rear aerodynamic states, described publicly as a higher-downforce cornering mode and a lower-drag straight-line mode [2]. This project does not claim regulatory fidelity to any season; the rules are used to establish context for why configurable aerodynamics and actuation limits matter.

## 1.2 Research question

The principal question is: how does rear-wing angle between 0 and 30 degrees affect aerodynamic coefficients, axle loads, straight-line acceleration, braking, cornering speed, energy demand, and total lap time for different circuit characteristics? Supporting questions ask whether an ideal active wing is materially superior to the best fixed setting, whether a rate- and delay-limited actuator preserves that gain, and which uncertain parameters most affect the selected optimum.

## 1.3 Objectives and success criteria

The work develops a transparent coefficient model, couples it to tyre and powertrain limits, solves closed laps through spatial forward/backward passes, and exports every plotted result as machine-readable data. Success requires physically interpretable trends, numerical convergence, deterministic regeneration, cross-format consistency, explicit limitations, and a MATLAB/Simulink handoff. Absolute agreement with a current Formula 1 car is not a success criterion because the required proprietary data are unavailable.

{{TABLE:nomenclature}}

# 2. Literature Review

## 2.1 Race-car aerodynamic trade-offs

The conventional force definitions express lift and drag as coefficients multiplied by dynamic pressure and reference area [3]. For a racing car, the useful vertical force is downward; this report therefore uses a positive downforce coefficient magnitude. Finite wings also generate induced drag. A standard parabolic relation scales induced drag with the square of lift coefficient and inversely with aspect ratio and span efficiency [4]. These relations do not replace detailed aerodynamics, but they are appropriate building blocks for a transparent conceptual model.

Race-car literature emphasizes that aerodynamics must be evaluated through vehicle performance rather than coefficient magnitude alone [7]. A configuration with maximum downforce need not minimize lap time because its drag penalty acts over every high-speed metre. Conversely, maximum lift-to-drag ratio need not be the lap-time optimum because braking and cornering depend on absolute load as well as efficiency. This distinction motivates the integrated simulations used here.

## 2.2 Lap-time simulation

Published work has connected CFD-derived wing coefficients to transient or quasi-steady lap models to estimate the effect of adding wings [5]. Established lap-time methods range from steady-state envelopes through quasi-static spatial solvers to full transient optimal-control formulations [10,11]. The chosen forward/backward method occupies the middle ground: it retains local track curvature, speed-dependent forces, gearing, acceleration, and braking, while remaining auditable and fast enough for angle sweeps and uncertainty studies.

## 2.3 Movable wings and actuator realism

Research on Formula Student drag-reduction systems demonstrates that movable elements can reduce drag, but also shows that actuator packaging itself can disturb lift and drag [6]. This is a useful caution: an aerodynamic state change cannot be assessed independently from the mechanism, command delay, transition time, and safety logic. The present study therefore reports both an ideal-active upper bound and an actuator-limited case. The latter is intentionally simple, but it prevents the common mistake of assigning instantaneous, cost-free switching.

## 2.4 Tyre and vehicle coupling

Tyre force capacity varies with normal load and combined-slip demand [8,9]. Increasing downforce raises available tyre force, but tyre load sensitivity means the gain is sub-linear. Aerodynamic balance also matters because the limiting axle can saturate before the sum of nominal front and rear capacities. This project evaluates front and rear normal loads separately, then applies a load-sensitive friction ellipse. It thereby captures the first-order reason why rear-wing angle can change stability margin and performance even at identical total downforce.

## 2.5 Identified gap and contribution

Many educational demonstrations stop at plots of lift and drag versus angle. This project extends the chain from wing setting to coefficient, force, axle load, tyre envelope, wheel force, speed trace, lap time, energy, optimization, uncertainty, and reportable evidence. It contributes an open, reproducible multi-language workflow rather than a claim of high-fidelity Formula 1 prediction.

# 3. Aerodynamic Theory

## 3.1 Dynamic pressure and force coefficients

For air density rho and vehicle speed v, dynamic pressure q is:

{{EQUATION:1|q = 1/2 rho v^2}}

Downforce and drag follow from the full-car coefficients and reference area A:

{{EQUATION:2|F_down = q A C_L}}

{{EQUATION:3|F_drag = q A C_D}}

These expressions explain the strong speed dependence visible in the force sweeps. Doubling speed multiplies the aerodynamic force by four if coefficients remain fixed. The effect of wing angle therefore grows rapidly in the fastest corners and braking zones.

## 3.2 Finite-wing lift slope

The rear wing is represented by a corrected finite-wing lift-curve slope. With two-dimensional slope a0, aspect ratio AR, and span efficiency e:

{{EQUATION:4|a = a0 / (1 + a0/(pi e AR))}}

Aspect ratio is obtained from span b and wing planform area S_w:

{{EQUATION:5|AR = b^2 / S_w}}

The pre-stall wing coefficient is linear in effective incidence relative to zero lift. Beyond the configured stall angle, a smooth exponential decay avoids a non-physical discontinuity. An additional smooth drag rise represents separated-flow losses. These post-stall terms are empirical assumptions and should be replaced with measured polar data when available.

## 3.3 Drag polar

Before stall, wing drag is modeled as profile drag plus induced drag:

{{EQUATION:6|C_D,w = C_D0,w + C_L,w^2/(pi e AR)}}

The wing coefficients are area-scaled and added to fixed full-car baseline coefficients. The total model is deliberately modular: a CFD or wind-tunnel lookup table can replace the analytical polar without rewriting the vehicle solver.

{{FIGURE:01_aero_polar}}

{{FIGURE:02_aero_efficiency}}

## 3.4 Aerodynamic balance

Baseline and wing forces act at declared longitudinal application points. Static moments about the axles distribute aerodynamic load between front and rear. Raising rear-wing incidence increases total downforce and typically shifts the aerodynamic load fraction rearward. This can increase rear traction but make the front axle the cornering constraint. The model therefore retains axle-resolved loads rather than using only total downforce.

{{FIGURE:03_downforce_speed}}

{{FIGURE:04_drag_speed}}

{{FIGURE:05_aero_balance}}

# 4. Vehicle and Tyre Dynamics

## 4.1 Normal load and load transfer

Static axle loads are determined by mass distribution. Longitudinal acceleration introduces a load-transfer term based on mass m, acceleration a_x, centre-of-gravity height h, and wheelbase L:

{{EQUATION:7|Delta F_z = m a_x h / L}}

Speed-dependent aerodynamic loads are then added at each axle. Grade changes the gravity component along the path and slightly changes the normal component. Pitch-heave aerodynamic coupling is omitted at nominal conditions, which should be remembered when interpreting very high-speed braking.

## 4.2 Load-sensitive tyre capacity

The reference friction coefficient is scaled using an exponent n:

{{EQUATION:8|mu(F_z) = mu_ref (F_z/F_z,ref)^(-n)}}

Because n is positive, friction coefficient falls as load rises. Total force still increases with load, but less than proportionally. This is why downforce remains valuable while showing diminishing returns. Combined longitudinal and lateral demands use a generalized friction ellipse:

{{EQUATION:9|(F_x/F_x,max)^p + (F_y/F_y,max)^p <= 1}}

Separate front and rear checks prevent the model from borrowing unused capacity from one axle after the other axle has saturated.

## 4.3 Powertrain and resistance

Engine torque is linearly interpolated across a representative speed curve. Each gear maps vehicle speed to engine speed; the solver selects the admissible gear giving maximum wheel force. Wheel force is limited by rear-axle traction. Longitudinal resistance is:

{{EQUATION:10|F_res = F_drag + C_rr (mg cos(theta) + F_down) + mg sin(theta)}}

Top speed occurs where available wheel force equals total resistance. Acceleration integrates the net force; braking combines the friction envelope and aerodynamic/rolling resistance. Energy reported here is positive tractive wheel work, not fuel energy.

{{FIGURE:06_top_speed}}

{{FIGURE:07_acceleration}}

{{FIGURE:08_braking}}

{{FIGURE:09_cornering}}

# 5. Model Architecture and Implementation

## 5.1 Data flow

The configuration is stored in versioned JSON, validated into typed Python data structures, and consumed by independent aerodynamic, dynamics, lap, strategy, analysis, and export modules. Track files use segments with length, entry and exit curvature, grade, active-aero eligibility, and optional speed limit. Each segment is discretized at no more than 5 m. The output manifest binds inputs, source tables, plots, headline metrics, random seed, and SHA-256 hashes to a deterministic run identifier.

## 5.2 Spatial lap solver

For each spatial cell, a lateral-speed limit is found from axle tyre capacity. A forward pass then limits the speed reachable under power and traction; a backward pass limits the speed from which the next cell can be reached under braking. Passes repeat around the closed track until the maximum speed change falls below the tolerance. Segment time is computed using the trapezoidal speed relation:

{{EQUATION:11|Delta t_i = 2 Delta s_i / (v_i + v_(i+1))}}

Lap time is the sum over all cells:

{{EQUATION:12|t_lap = Sum_i Delta t_i}}

This method is deterministic, interpretable, and efficient for many setup evaluations. It does not solve for the racing line or steering trajectory.

## 5.3 Circuit archetypes

Three synthetic closed circuits isolate contrasting demands. The low-downforce case emphasizes long high-speed sections, the balanced case mixes straights and medium-speed corners, and the high-downforce case increases corner density and curvature. Names describe intended character rather than guaranteeing a particular optimum; the actual optimum remains a result of the full speed/force distribution.

{{TABLE:tracks}}

## 5.4 Fixed and active strategies

Fixed-angle analysis evaluates every integer angle from 0 to 30 degrees and refines the best region with bounded interpolation. Open-wing is a prescribed low-drag reference. Ideal-active switches without actuation cost and is interpreted only as an upper bound. Actuator-limited active aero applies delay, rate limit, and eligibility logic, then solves the resulting schedule. These strategies are compared using time, maximum speed, tractive energy, and full-throttle fraction.

# 6. Verification and Reproducibility

## 6.1 Verification hierarchy

Verification is layered. Unit tests check configuration validation, aerodynamic trends, stall behavior, force balances, load sensitivity, gearing, track closure, solver convergence, strategy constraints, uncertainty determinism, and exports. Analytical checks confirm the v-squared force relationship and basic limits. Regression fixtures lock representative aerodynamic and lap outputs. Cross-artifact checks compare the CSV, XLSX, MAT, manifest, report, and presentation values.

## 6.2 Numerical controls

The spatial step is 5 m, solver speed tolerance is 0.001 m/s, and the maximum iteration count is 200. Input ranges are validated before analysis. Optimization is bounded to the physical study domain. The Monte Carlo seed is fixed at 3106, so the same inputs produce identical samples and headline statistics. A deterministic run ID is derived from input hashes instead of time.

## 6.3 MATLAB parity and Simulink scope

MATLAB package functions load the same JSON configuration and tracks and reproduce the aerodynamic, tyre, wheel-force, lap, sweep, and export interfaces. `run_parity_tests.m` reads Python-generated reference cases covering all circuits and pre-/post-stall angles. Because MATLAB is unavailable in the authoring environment, this source is statically checked but not runtime-tested. Final parity should be executed in MATLAB R2022b+ [12]. `build_simulink_demo.m` programmatically creates a focused model of wing-angle command, rate limiting, aerodynamic forces, vehicle acceleration, logging, and scope output when Simulink is licensed.

{{TABLE:verification}}

# 7. Results

## 7.1 Aerodynamic response

The analytical polar increases downforce with angle before the 18-degree stall threshold. Drag rises throughout and grows more sharply as separation is introduced. Aerodynamic efficiency peaks earlier than maximum downforce, illustrating why coefficient efficiency and lap-time optimum are different objectives. Force-speed curves confirm that setup differences become most consequential at high speed.

## 7.2 Straight-line and cornering effects

Higher wing angle reduces the power-limited top speed and generally lengthens high-speed acceleration. It can shorten braking distance because higher downforce enlarges tyre capacity while drag adds direct deceleration. Maximum corner speed rises where aerodynamic load is valuable, but axle balance and tyre load sensitivity prevent unlimited gains. These competing trends create the lap-time minima.

## 7.3 Fixed-wing optimization

The optimized fixed settings are summarized below. The low-downforce circuit selects {OPT_LOW_ANGLE} degrees and {OPT_LOW_TIME} s; the balanced circuit selects {OPT_BAL_ANGLE} degrees and {OPT_BAL_TIME} s; and the high-downforce circuit selects {OPT_HIGH_ANGLE} degrees and {OPT_HIGH_TIME} s. The balanced optimum is broad: its reported neighbor sensitivity is small, so a nearby setting can be operationally preferable if it improves stability, cooling, or robustness. The two 18-degree results lie at the modeled pre-stall peak; angles beyond this region are penalized by both lift decay and drag rise.

{{TABLE:optima}}

{{FIGURE:10_lap_time_sweep}}

{{FIGURE:11_speed_traces}}

## 7.4 Strategy comparison

The ideal-active strategy is best on the low- and high-downforce archetypes in this model, demonstrating the theoretical value of changing the drag/downforce compromise along the lap. Yet the actuator-limited strategy records {ACTIVE_LOW_TIME} s, {ACTIVE_BAL_TIME} s, and {ACTIVE_HIGH_TIME} s—slower than the optimum fixed setting on all three circuits. This is a meaningful negative result. Delay, slew, and the intentionally simple schedule cause time to be lost during transitions and can place the wing in a poor intermediate state. Active hardware alone does not guarantee lap-time benefit; the command policy must be co-designed and validated.

{{TABLE:strategies}}

{{FIGURE:12_strategy_comparison}}

{{FIGURE:13_energy_strategy}}

## 7.5 Decision significance

The decision is not solely the mathematical minimum. If the lap-time curve is flat around the optimum, teams can trade a few hundredths of a second for balance, tyre temperature, overtaking speed, or robustness. A steep optimum deserves tighter setup and actuator tolerances. The decision matrix therefore reports gains and penalties by circuit instead of collapsing the project into one universal recommended angle.

{{FIGURE:16_decision_matrix}}

# 8. Uncertainty and Sensitivity

## 8.1 Monte Carlo method

One thousand bounded samples per circuit perturb aerodynamic, tyre, mass, powertrain, and environmental parameters. To keep the study computationally practical while retaining full-solver anchoring, a first-order physics response surface is constructed from nominal and perturbed solver cases. The resulting distributions characterize uncertainty in this educational model—not frequencies expected from a real championship car.

## 8.2 Optimum-angle robustness

The optimum-angle distribution is circuit dependent. Its spread should be read alongside the flatness of the nominal lap-time curve: a wide angle distribution can still correspond to small time loss if multiple settings are nearly equivalent. Conversely, a tight distribution does not prove physical accuracy when all samples share the same simplified model structure.

{{TABLE:uncertainty}}

{{FIGURE:14_uncertainty_optimum}}

## 8.3 Local sensitivity

The balanced-circuit study perturbs selected inputs by plus and minus 10 percent. Air density, lateral tyre friction, and baseline downforce show the largest time changes among the tested terms. The signs require careful interpretation: more density adds both useful downforce and harmful drag; which dominates depends on the circuit and baseline coefficients. The asymmetry between positive and negative changes demonstrates that linear sensitivity is only local.

{{TABLE:sensitivity}}

{{FIGURE:15_sensitivity}}

# 9. Engineering Interpretation

## 9.1 Why the optimum moves

Rear-wing angle changes several linked quantities at once. More incidence raises rear downforce, changes total aerodynamic balance, increases corner and braking capacity, increases drag, changes achievable gear/speed combinations, and alters energy consumption. A circuit with long straights accumulates drag loss over time, while a circuit with repeated medium/high-speed corners repeatedly harvests the benefit of downforce. Low-speed hairpins depend less on aerodynamics because dynamic pressure is small.

The results also show that track labels cannot substitute for simulation. The synthetic low-downforce circuit still selects a relatively high angle because its particular curvature and braking distribution reward downforce up to the modeled stall boundary. That finding should prompt examination, not manual correction. It demonstrates the value of reporting track definitions and speed traces alongside a headline optimum.

## 9.2 Setup recommendation logic

For a real engineering program, the computed minimum should define the center of a validation window. Nearby angles would be tested in CFD or a tunnel, then on track, while monitoring front/rear balance, ride height, tyre state, wind, cooling, and actuator behavior. The broad balanced-circuit minimum suggests choosing a robust integer setting around 5 degrees. The 18-degree optima deserve special scrutiny because they coincide with the assumed stall threshold; uncertainty in the actual polar could move them materially.

## 9.3 Active-aero lesson

The ideal-active benefit and actuator-limited penalty together provide a control-design lesson. The plant has aerodynamic and longitudinal dynamics, but the command has delay and bounded rate. Poor switching can create transient drag without useful cornering load or remove load before braking is complete. Future control should optimize target angles, switching locations, hysteresis, and rate constraints jointly, ideally using predictive control or direct optimal control rather than threshold logic alone.

# 10. Assumptions and Limitations

The full limitations register is intentionally visible rather than relegated to code comments. Key restrictions are the absence of proprietary geometry and validation data, synthetic circuits, point-mass motion, quasi-steady forces, simplified tyre and powertrain behavior, empirical stall, constant nominal atmosphere, and reduced-order active-aero control. These restrictions mean that absolute lap times and optimum angles must not be presented as values for any real team or venue.

Model-form uncertainty is more important than numerical precision. The solver can repeat a result to many decimal places, but that does not add physical information beyond the assumptions. Reported headline numbers use three decimals for traceability; practical engineering decisions should use wider tolerances. The correct next step is validation, not additional decimal places.

{{TABLE:limitations}}

# 11. Conclusions and Future Work

## 11.1 Conclusions

Rear-wing angle produces a nonlinear, circuit-specific performance compromise. Downforce, braking, and cornering benefits grow strongly with speed, while drag reduces acceleration and top speed. The integrated lap model identifies fixed optima of {OPT_LOW_ANGLE}, {OPT_BAL_ANGLE}, and {OPT_HIGH_ANGLE} degrees across the three archetypes. No single setting is universally superior.

The active-aero comparison is equally important. Instantaneous switching can offer a theoretical benefit, but the tested actuator-limited implementation is slower than the best fixed setup. Actuator speed, delay, state selection, and transition timing are therefore first-class performance variables. A movable wing should be assessed as a mechatronic control system, not as two static polars.

The project meets its educational objective by delivering a transparent chain from assumptions to equations, code, tables, figures, uncertainty, MATLAB parity fixtures, and a Simulink builder. Its strongest claim is reproducibility inside the declared model, not real-world prediction.

## 11.2 Future work

Priority improvements are: replace the analytical polar with full-car CFD or wind-tunnel maps; validate tyre and powertrain data; add pitch, heave, yaw, wind, ride-height coupling, thermal states, and racing-line optimization; model hybrid deployment; perform mesh/time-step and model-form studies; and validate against telemetry. For active aero, introduce constrained optimal control with fail-safe state logic and actuator power/thermal models. MATLAB parity should be executed on R2022b+ and the generated Simulink model should be simulated and archived with logged outputs.

# References

{{REFERENCES}}

# Appendix A — Parameter Register

The following register distinguishes reference-informed, assumed, and derived inputs. Supported ranges are guards for this educational model, not certification limits.

{{TABLE:parameters}}

# Appendix B — MATLAB and Simulink Workflow

From the project root, add the `matlab` directory to the MATLAB path and run `run_project`. This loads the shared JSON files, sweeps 0–30 degrees, solves all three circuits, and writes MATLAB-native CSV, MAT, and plot outputs. Then run `run_parity_tests` to compare aerodynamic and lap cases with `results/parity/reference_cases.csv`. Relative tolerances are 1e-6 for coefficients/forces and 1e-4 for lap metrics.

Run `build_simulink_demo` to generate `F1WingAeroDemo.slx`. The model includes tractive force, a step wing-angle command, a 90 degree/s Rate Limiter, a MATLAB Function aerodynamic block, net-force and inverse-mass blocks, a vehicle-speed integrator, a scope, and workspace logging for speed, angle, downforce, and drag. If Simulink is unavailable the builder exits non-fatally with an instruction. MATLAB source is not runtime-tested in the authoring environment; independent execution requires MATLAB R2022b+ and a Simulink license for the `.slx` model.

{{TABLE:software}}

# Appendix C — Reproducibility and Artifact Index

Run ID: {RUN_ID}. Random seed: {SEED}. The manifest records hashes for every configuration, track, table, figure, workbook, MATLAB data file, and parity fixture. CSV files are the canonical tabular source for figures; the XLSX workbook mirrors them for inspection, while the MAT file supports numerical exchange.

The Python build commands are documented in the README. A clean analysis rebuild regenerates the manifest and numerical assets. The document build consumes that manifest and embeds its run ID and headline values. The final verifier checks file readability, hashes, report and slide structure, and numeric consistency after documented rounding.

{{TABLE:artifacts}}

# Appendix D — Detailed Limitations Statement

This appendix reiterates the interpretation boundary because it is central to responsible use. The car, coefficients, tyre properties, torque curve, track geometry, and actuator behavior are representative assumptions. None is reverse engineered from a named entrant. Plots that resemble engineering deliverables are still reduced-order simulation outputs. They are appropriate for comparing hypotheses and teaching coupled performance analysis; they are not homologation evidence or a substitute for CFD, structural assessment, wind-tunnel work, driver-in-loop evaluation, or track validation.

The project should be cited by model name, version, and run ID. Any modified configuration creates a new evidence set. Conclusions should be restated after every material input change rather than carried forward from the nominal report.
