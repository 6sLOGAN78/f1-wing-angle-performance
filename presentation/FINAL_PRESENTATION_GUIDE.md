# Final Presentation: What to Put In and What to Say

Use the editable PowerPoint in results/final_presentation/. All numerical plots are regenerated from corrected audit data. Target duration: 12–15 minutes. Spend more time on slides 9–14; summarize the equations rather than reading every bullet. This deck finalizes the presentation only, not the unfinished complete-project verification.

## Slide 1: Effect of Rear-Wing Angle on F1 Car Performance

On the slide:

- An analytical simulation of a representative Formula 1-style vehicle.
- Rear-wing sweep: 0–30° on three synthetic circuit archetypes.
- Corrected force-feasible lap solver and full-bound active-aero search.
- Verified numerical results; not CFD, measured telemetry, or a team setup.

What to say: Introduce the project as a comparative engineering experiment, not an exact F1 digital twin. The central question is whether added downforce compensates for drag over a complete lap.

## Slide 2: Research Question and Objectives

On the slide:

- How does rear-wing incidence affect aerodynamic forces and minimum lap time?
- Quantify the trade-off between straight-line resistance and cornering grip.
- Compare low-downforce, balanced, and high-downforce circuit geometries.
- Compare a fixed wing with ideal and actuator-limited two-state strategies.

What to say: Explain that a wing with maximum lift-to-drag ratio is not necessarily the fastest setup. All comparisons use identical vehicle inputs and track meshes.

## Slide 3: Study Scope and Modeling Assumptions

On the slide:

- Quasi-steady point-mass motion with front/rear axle load resolution.
- Analytical rear-wing polar combined with a fixed baseline full-car map.
- Load-sensitive tyres, combined grip, longitudinal load transfer, torque and gearing.
- No tyre-temperature dynamics, suspension transients, driver telemetry, or CFD.

What to say: State the scope before discussing results. Axle forces are resolved, but yaw handling and transient suspension behavior are not modeled. Circuit labels describe synthetic geometry, not real venues.

## Slide 4: Aerodynamic Model: Lift, Drag and Stall

On the slide:

- Finite-wing slope: a = a0 / [1 + a0 / (pi e AR)].
- Wing drag includes profile, induced and assumed post-stall terms.
- Pre-stall lift rises linearly; post-stall lift decays exponentially.
- The join is continuous, but its slope can kink at the assumed stall angle.

What to say: Explain why finite span reduces the ideal two-dimensional lift slope. The stall angle is an assumed model parameter, not an experimentally measured property of a real F1 wing.

## Slide 5: Speed-Dependent Downforce and Drag

On the slide:

- Dynamic pressure: q = 0.5 rho V_air squared.
- Downforce = q A CL,total; drag = q A CD,total.
- Relative air speed matters when wind is present.
- Added rear-wing force changes axle loading and the available tyre grip.

What to say: Show that force rises with air speed squared for unchanged coefficients. Distinguish the wing coefficients from the area-scaled full-car coefficients. Downforce is positive downward in this project.

## Slide 6: Tyre Grip and Longitudinal Load Transfer

On the slide:

- Load sensitivity: mu = mu_ref (Fz / Fz_ref)^(-n).
- Combined demand: (Fx/Fx,max)^p + (Fy/Fy,max)^p <= 1.
- Lateral demand is normalized by lateral friction, not longitudinal friction.
- Actual acceleration shifts axle normal loads and alters traction/braking capacity.

What to say: Describe the corrected friction-ellipse normalization. An axle already using most lateral grip cannot independently provide its full longitudinal force. Load transfer must use the achieved acceleration.

## Slide 7: Powertrain and Force Balance

On the slide:

- Available wheel thrust follows the interpolated engine torque curve and eight gears.
- Resistance combines aerodynamic drag, rolling resistance and track gradient.
- Each segment must satisfy thrust - brake - resistance = mass x acceleration.
- Constant-speed cornering must reserve enough longitudinal grip to overcome drag.

What to say: Explain the main physics correction: a purely lateral speed limit can permit unsustainable speed if no tyre force remains to overcome drag. The corrected solver rejects that state. No battery or hybrid deployment is modeled.

## Slide 8: Closed-Track Lap Simulation Workflow

On the slide:

- Load validated car configuration and discretize the track at <=5 m.
- Construct a sustainable local speed envelope for the commanded wing profile.
- Apply forward acceleration and backward braking passes until convergence.
- Include the closing segment, then check achieved acceleration and force closure.

What to say: Walk through the distance-domain solver. The start/finish cell is part of the physics, not a special unchecked edge. Numerical guards establish feasibility within the model, not experimental accuracy.

## Slide 9: Fixed-Wing Sweep Across Three Circuits

On the slide:

- 93 physical laps: 31 integer angles x three synthetic circuits.
- Every case checked for convergence, force feasibility and closed-segment integration.
- All angle cases retain the original 5 m track discretization.
- The best wing setting depends on this car model and the circuit geometry.

What to say: Use the fresh fixed-lap sweep plot, not the legacy result bundle. Discuss how curve minima differ across circuits. Do not rename the synthetic circuits as real tracks.

## Slide 10: Continuously Refined Fixed-Wing Optima

On the slide:

- Physical lap solves refine candidate basins around the integer sweep.
- Bounds and neighboring integer points remain part of the search.
- Balanced-track optimum is near 2.819°; the other two are near 18°.
- These are nominal model optima, not uncertainty confidence intervals.

What to say: Report the refined optima to three decimals, then explain that more digits do not imply experimentally calibrated accuracy. The high-downforce optimum falls at the assumed stall angle.

## Slide 11: Speed and Energy: Secondary Performance Metrics

On the slide:

- Record maximum speed and positive tractive wheel work for every fixed lap.
- Energy is integrated from achieved tractive force over distance.
- Minimum lap time and minimum tractive energy are different objectives.
- Wheel tractive work is not fuel consumption or battery-energy demand.

What to say: Explain what the energy metric means. Avoid interpreting a tractive-work difference as a fuel-saving percentage; engine efficiency and hybrid energy flows are outside scope.

## Slide 12: Two-State Active Aerodynamics

On the slide:

- Use an open, lower-angle state on eligible straight sections.
- Use a closed, higher-angle state under the modeled switching conditions.
- Search every unique integer pair within 0–30°, with >=1° separation.
- Compare ideal state changes against finite-rate, delayed actuator behavior.

What to say: The active strategy is an educational control policy, not an exact FIA implementation. The ideal mode is a model comparison; the limited mode includes actuator timing. Grid-resolved optimality is not continuous-global optimality.

## Slide 13: Fixed Versus Ideal and Limited Active Aero

On the slide:

- Compare optimized strategies using the same car and original track meshes.
- Active search evaluates actual physical laps, not a coarsened surrogate.
- All completed cases must satisfy force, convergence and actuator checks.
- Interpret small differences relative to model assumptions and numerical resolution.

What to say: Read the corrected three-strategy comparison. Report the gain in seconds from the fixed optimum to the limited strategy. These nominal gains are not guaranteed real-world performance improvements.

## Slide 14: Validation and Reproducibility Evidence

On the slide:

- Fixed sweep: 93 checked laps, including force, time and energy closure.
- Active searches: 465 unique pairs per circuit and actuator mode.
- Scalar force checks include the track closing segment and achieved acceleration.
- Source hashes, input hashes, runtime versions and completion receipts preserve identity.

What to say: Distinguish the six active grids: the balanced ideal grid completed earlier, while the five monitored grids contribute 2,325 cases. Passing these guards does not make the whole software suite or native implementation complete.

## Slide 15: MATLAB and Simulink Implementation

On the slide:

- MATLAB source includes configuration, aero, dynamics and fixed-wing lap analysis.
- Simulink model/builder is supplied for a speed-dependent aero/actuator demonstration.
- The aero block chain is: speed and angle -> coefficients -> forces -> scopes.
- Full native active/uncertainty/sensitivity execution and strict runtime parity remain unverified.

What to say: Show the actual source/model files if demonstrating the project. Do not say all results were produced by MATLAB: the corrected numerical evidence here comes from Python. MATLAB startup failed in this environment, and full native scope is incomplete.

## Slide 16: Uncertainty and Sensitivity: What Remains

On the slide:

- A validated >=1,000-sample, nine-parameter uncertainty study is still required.
- The tested uncertainty surrogate failed independent validation and was rejected.
- Direct full-physics Monte Carlo is selected, but not yet implemented or executed.
- No confidence intervals or sensitivity rankings are claimed in this presentation.

What to say: Be direct: uncertainty results are unfinished. Explain the planned sample-angle physical simulations, but do not present the proposal as completed work. This transparency is stronger than displaying invalid confidence intervals.

## Slide 17: Main Findings and Engineering Interpretation

On the slide:

- There is no universal wing angle: optimize for the complete circuit, not one aerodynamic metric.
- Correct force balance changes the accepted lap speeds, optima and strategy comparisons.
- Two-state active aero provides a nominal model benefit when feasible switching is allowed.
- Final empirical calibration, native parity and validated uncertainty are necessary next steps.

What to say: Conclude with the engineering trade-off and the corrected feasibility requirement. Explain that the deliverable is a defensible presentation of verified nominal results, not a declaration that every original project requirement is satisfied.

## Slide 18: Evidence, Source Files and Questions

On the slide:

- Inputs: config/project.json and tracks/*.json define assumptions and geometry.
- Physics: src/f1wing/aero.py, dynamics.py, lap.py and strategies.py.
- Corrected results: docs/verification/*-20261005.csv and matching JSON audit receipts.
- Native files: matlab/ and results/simulink/; incomplete runtime scope is disclosed.

What to say: Invite questions about the equations, numerical guards, optimization and limits. If asked about a real F1 setup or robust optimum, say that calibrated aerodynamic/tyre data and validated uncertainty are still needed.

## Before presenting

- Enter your name, roll number, institution, supervisor, and presentation date if required by your department. These details were not provided and have not been invented.
- Read the notes attached to each PowerPoint slide.
- Do not use the historical uncertainty charts or claim full MATLAB runtime verification.
- Treat nominal optima as synthetic-model results, not actual race-team recommendations.
