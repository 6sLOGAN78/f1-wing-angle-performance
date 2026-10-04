function state = wheelForce(speed_mps, cfg)
%WHEELFORCE Select the gear producing maximum admissible wheel force. % SI units
arguments
    speed_mps (1,1) double {mustBeNonnegative}
    cfg struct
end
bestForce_n = -inf;
bestGear = numel(cfg.powertrain.gear_ratios);
bestRpm = cfg.powertrain.redline_rpm;
bestTorque_nm = 0;
for gear = 1:numel(cfg.powertrain.gear_ratios)
    ratio = cfg.powertrain.gear_ratios(gear);
    actualRpm = speed_mps / cfg.vehicle.tyre_radius_m * ratio * ...
        cfg.powertrain.final_drive_ratio * 60 / (2 * pi);
    if actualRpm > cfg.powertrain.redline_rpm
        continue;
    end
    engineRpm = max(cfg.powertrain.idle_rpm, actualRpm);
    torque_nm = interp1(cfg.powertrain.rpm_points, cfg.powertrain.torque_nm, ...
        engineRpm, 'linear', 'extrap');
    force_n = torque_nm * ratio * cfg.powertrain.final_drive_ratio * ...
        cfg.powertrain.driveline_efficiency / cfg.vehicle.tyre_radius_m;
    if force_n > bestForce_n
        bestForce_n = force_n;
        bestGear = gear;
        bestRpm = engineRpm;
        bestTorque_nm = torque_nm;
    end
end
if ~isfinite(bestForce_n)
    bestForce_n = 0;
end
state = struct('gear', bestGear, 'engine_rpm', bestRpm, ...
    'torque_nm', bestTorque_nm, 'raw_force_n', bestForce_n, ...
    'force_n', bestForce_n, 'limiting_mechanism', "powertrain");
end

