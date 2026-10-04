function state = aeroState(angle_deg, speed_mps, cfg, yaw_deg, ride_height_m, headwind_mps)
%AEROSTATE Return full-car coefficients, forces, and aero balance. % SI units
arguments
    angle_deg (1,1) double
    speed_mps (1,1) double {mustBeNonnegative}
    cfg struct
    yaw_deg (1,1) double = 0
    ride_height_m (1,1) double = NaN
    headwind_mps (1,1) double = 0
end
if isnan(ride_height_m)
    ride_height_m = cfg.aero.nominal_ride_height_m;
end
relativeSpeed_mps = speed_mps + headwind_mps;
if relativeSpeed_mps < 0
    error('f1wing:RelativeSpeed', 'Relative air speed cannot be negative.');
end
wing = f1wing.wingCoefficients(angle_deg, relativeSpeed_mps, yaw_deg, ride_height_m, cfg.aero);
areaRatio = cfg.aero.wing_area_m2 / cfg.aero.reference_area_m2;
wingClCar = wing.cl * areaRatio;
wingCdCar = wing.cd * areaRatio;
clTotal = cfg.aero.baseline_cl + wingClCar;
cdTotal = cfg.aero.baseline_cd + wingCdCar;
frontCl = cfg.aero.baseline_cl * cfg.aero.baseline_front_downforce_fraction;
rearCl = cfg.aero.baseline_cl * (1 - cfg.aero.baseline_front_downforce_fraction) + wingClCar;
dynamicPressure_pa = 0.5 * cfg.environment.air_density_kgpm3 * relativeSpeed_mps^2;
forceScale_n = dynamicPressure_pa * cfg.aero.reference_area_m2;
frontDownforce_n = forceScale_n * frontCl;
rearDownforce_n = forceScale_n * rearCl;
centerOfPressure_m = (frontCl * cfg.aero.front_aero_application_from_front_m + ...
    rearCl * cfg.aero.rear_aero_application_from_front_m) / clTotal;
state = struct('relative_air_speed_mps', relativeSpeed_mps, ...
    'dynamic_pressure_pa', dynamicPressure_pa, 'cl_total', clTotal, ...
    'cd_total', cdTotal, 'wing', wing, ...
    'downforce_n', frontDownforce_n + rearDownforce_n, ...
    'drag_n', forceScale_n * cdTotal, ...
    'front_downforce_n', frontDownforce_n, 'rear_downforce_n', rearDownforce_n, ...
    'front_downforce_fraction', frontCl / clTotal, ...
    'center_of_pressure_from_front_m', centerOfPressure_m);
end

