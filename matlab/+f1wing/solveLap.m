function result = solveLap(track, cfg, angle_deg)
%SOLVELAP Fixed-angle quasi-steady forward/backward lap solver. % SI units
arguments
    track struct
    cfg struct
    angle_deg (1,1) double
end
n = numel(track.ds_m);
localLimit_mps = zeros(1, n);
vmax_mps = localTopSpeed(angle_deg, cfg);
for index = 1:n
    lateral_mps = localLateralLimit(track.curvature_1pm(index), angle_deg, ...
        track.gradient_rad(index), cfg);
    localLimit_mps(index) = min([cfg.solver.maximum_speed_mps, ...
        track.speed_limit_mps(index), vmax_mps, lateral_mps]);
end
speed_mps = max(cfg.solver.minimum_speed_mps, localLimit_mps);
converged = false;
for iteration = 1:cfg.solver.max_iterations
    previous_mps = speed_mps;
    for index = 1:n
        target = mod(index, n) + 1;
        speed = max(speed_mps(index), cfg.solver.minimum_speed_mps);
        lateralForce_n = cfg.vehicle.mass_kg * speed^2 * abs(track.curvature_1pm(index));
        wheel = f1wing.wheelForce(speed, cfg);
        resistance_n = localResistance(speed, angle_deg, track.gradient_rad(index), cfg);
        acceleration_mps2 = 0;
        for inner = 1:12
            capacity_n = localLongitudinalCapacity(speed, angle_deg, lateralForce_n, ...
                false, acceleration_mps2, cfg);
            tractive_n = min(wheel.force_n, capacity_n);
            updated_mps2 = max(0, (tractive_n - resistance_n) / cfg.vehicle.mass_kg);
            if abs(updated_mps2 - acceleration_mps2) < 1e-6
                acceleration_mps2 = updated_mps2;
                break;
            end
            acceleration_mps2 = 0.5 * (acceleration_mps2 + updated_mps2);
        end
        reachable_mps = sqrt(max(cfg.solver.minimum_speed_mps^2, ...
            speed^2 + 2 * acceleration_mps2 * track.ds_m(index)));
        speed_mps(target) = min(speed_mps(target), reachable_mps);
    end
    for offset = 0:(n-1)
        target = n - offset;
        source = target - 1;
        if source < 1
            source = n;
        end
        speed = max(speed_mps(source), cfg.solver.minimum_speed_mps);
        lateralForce_n = cfg.vehicle.mass_kg * speed^2 * abs(track.curvature_1pm(source));
        resistance_n = localResistance(speed, angle_deg, track.gradient_rad(source), cfg);
        deceleration_mps2 = 0;
        for inner = 1:12
            capacity_n = localLongitudinalCapacity(speed, angle_deg, lateralForce_n, ...
                true, -deceleration_mps2, cfg);
            updated_mps2 = max(0, (capacity_n + resistance_n) / cfg.vehicle.mass_kg);
            if abs(updated_mps2 - deceleration_mps2) < 1e-6
                deceleration_mps2 = updated_mps2;
                break;
            end
            deceleration_mps2 = 0.5 * (deceleration_mps2 + updated_mps2);
        end
        allowed_mps = sqrt(max(cfg.solver.minimum_speed_mps^2, ...
            speed_mps(target)^2 + 2 * deceleration_mps2 * track.ds_m(source)));
        speed_mps(source) = min(speed_mps(source), allowed_mps);
    end
    speed_mps = max(cfg.solver.minimum_speed_mps, min(speed_mps, localLimit_mps));
    if max(abs(speed_mps - previous_mps)) < cfg.solver.speed_tolerance_mps
        converged = true;
        break;
    end
end
if ~converged
    error('f1wing:Convergence', 'Lap solver did not converge.');
end
nextSpeed_mps = [speed_mps(2:end), speed_mps(1)];
segmentTime_s = 2 .* track.ds_m ./ max(speed_mps + nextSpeed_mps, 1e-9);
time_s = [0, cumsum(segmentTime_s(1:end-1))];
longAccel_mps2 = (nextSpeed_mps.^2 - speed_mps.^2) ./ (2 .* track.ds_m);
gear = zeros(1, n);
tractiveForce_n = zeros(1, n);
brakeForce_n = zeros(1, n);
for index = 1:n
    wheel = f1wing.wheelForce(speed_mps(index), cfg);
    gear(index) = wheel.gear;
    resistance_n = localResistance(speed_mps(index), angle_deg, track.gradient_rad(index), cfg);
    if longAccel_mps2(index) >= 0
        tractiveForce_n(index) = max(0, cfg.vehicle.mass_kg * longAccel_mps2(index) + resistance_n);
    else
        brakeForce_n(index) = max(0, -cfg.vehicle.mass_kg * longAccel_mps2(index) - resistance_n);
    end
end
result = struct('track_name', track.name, 'angle_deg', angle_deg, ...
    'lap_time_s', sum(segmentTime_s), 'distance_m', track.distance_m, ...
    'speed_mps', speed_mps, 'time_s', time_s, ...
    'local_limit_mps', localLimit_mps, ...
    'longitudinal_accel_mps2', longAccel_mps2, 'gear', gear, ...
    'tractive_force_n', tractiveForce_n, 'brake_force_n', brakeForce_n, ...
    'tractive_energy_j', sum(tractiveForce_n .* track.ds_m), ...
    'maximum_speed_mps', max(speed_mps), 'minimum_speed_mps', min(speed_mps), ...
    'maximum_braking_demand_n', max(brakeForce_n), ...
    'iterations', iteration, 'converged', converged);
end

function limit_mps = localLateralLimit(curvature_1pm, angle_deg, grade_rad, cfg)
curvature = abs(curvature_1pm);
if curvature < 1e-12
    limit_mps = inf;
    return;
end
margin = @(speed_mps) localLateralMargin(speed_mps, curvature, angle_deg, grade_rad, cfg);
upper_mps = cfg.solver.maximum_speed_mps;
if margin(upper_mps) >= 0
    limit_mps = inf;
else
    limit_mps = fzero(margin, [0, upper_mps]);
end
end

function margin_n = localLateralMargin(speed_mps, curvature_1pm, angle_deg, grade_rad, cfg)
[frontLoad_n, rearLoad_n] = localAxleLoads(speed_mps, 0, angle_deg, cfg);
weight_n = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2;
lostNormal_n = weight_n * (1 - max(0, cos(grade_rad)));
frontLoad_n = frontLoad_n - lostNormal_n * cfg.vehicle.front_static_fraction;
rearLoad_n = rearLoad_n - lostNormal_n * (1 - cfg.vehicle.front_static_fraction);
totalLoad_n = frontLoad_n + rearLoad_n;
frontShare = frontLoad_n / totalLoad_n;
rearShare = rearLoad_n / totalLoad_n;
frontMu = f1wing.tyreMu(frontLoad_n, cfg.tyres.mu_lateral_ref, ...
    cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
rearMu = f1wing.tyreMu(rearLoad_n, cfg.tyres.mu_lateral_ref, ...
    cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
available_n = min(frontMu * frontLoad_n / frontShare, rearMu * rearLoad_n / rearShare);
required_n = cfg.vehicle.mass_kg * speed_mps^2 * curvature_1pm;
margin_n = available_n - required_n;
end

function [frontLoad_n, rearLoad_n] = localAxleLoads(speed_mps, accel_mps2, angle_deg, cfg)
aero = f1wing.aeroState(angle_deg, speed_mps, cfg);
weight_n = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2;
transfer_n = cfg.vehicle.mass_kg * accel_mps2 * cfg.vehicle.cg_height_m / cfg.vehicle.wheelbase_m;
frontLoad_n = weight_n * cfg.vehicle.front_static_fraction + aero.front_downforce_n - transfer_n;
rearLoad_n = weight_n * (1 - cfg.vehicle.front_static_fraction) + aero.rear_downforce_n + transfer_n;
if frontLoad_n <= 0 || rearLoad_n <= 0
    error('f1wing:NormalLoad', 'Non-positive axle normal load.');
end
end

function capacity_n = localLongitudinalCapacity(speed_mps, angle_deg, lateralForce_n, braking, accel_mps2, cfg)
[frontLoad_n, rearLoad_n] = localAxleLoads(speed_mps, accel_mps2, angle_deg, cfg);
frontShare = frontLoad_n / (frontLoad_n + rearLoad_n);
frontLat_n = lateralForce_n * frontShare;
rearLat_n = lateralForce_n - frontLat_n;
frontLongMu = f1wing.tyreMu(frontLoad_n, cfg.tyres.mu_longitudinal_ref, cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
rearLongMu = f1wing.tyreMu(rearLoad_n, cfg.tyres.mu_longitudinal_ref, cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
frontLatMu = f1wing.tyreMu(frontLoad_n, cfg.tyres.mu_lateral_ref, cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
rearLatMu = f1wing.tyreMu(rearLoad_n, cfg.tyres.mu_lateral_ref, cfg.tyres.reference_load_n, cfg.tyres.load_sensitivity_exponent);
p = cfg.tyres.friction_ellipse_exponent;
frontLong_n = localEllipse(frontLongMu * frontLoad_n, frontLat_n, frontLatMu * frontLoad_n, p);
rearLong_n = localEllipse(rearLongMu * rearLoad_n, rearLat_n, rearLatMu * rearLoad_n, p);
if braking
    capacity_n = min(frontLong_n + rearLong_n, cfg.tyres.max_brake_force_n);
else
    capacity_n = rearLong_n * cfg.powertrain.driven_rear_fraction;
end
end

function remaining_n = localEllipse(longCapacity_n, lateral_n, lateralCapacity_n, p)
usage = abs(lateral_n) / lateralCapacity_n;
if usage >= 1
    remaining_n = 0;
else
    remaining_n = longCapacity_n * (1 - usage^p)^(1 / p);
end
end

function resistance_n = localResistance(speed_mps, angle_deg, grade_rad, cfg)
aero = f1wing.aeroState(angle_deg, speed_mps, cfg);
weight_n = cfg.vehicle.mass_kg * cfg.environment.gravity_mps2;
rolling_n = cfg.vehicle.rolling_resistance_coefficient * ...
    (weight_n * cos(grade_rad) + aero.downforce_n);
resistance_n = aero.drag_n + rolling_n + weight_n * sin(grade_rad);
end

function speed_mps = localTopSpeed(angle_deg, cfg)
residual = @(speed) f1wing.wheelForce(speed, cfg).force_n - localResistance(speed, angle_deg, 0, cfg);
lower = cfg.solver.minimum_speed_mps;
upper = cfg.solver.maximum_speed_mps;
if residual(upper) >= 0
    error('f1wing:TopSpeed', 'Top speed lies above configured maximum.');
end
speed_mps = fzero(residual, [lower, upper]);
end

