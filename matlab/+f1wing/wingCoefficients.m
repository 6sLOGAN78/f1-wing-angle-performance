function wing = wingCoefficients(angle_deg, speed_mps, yaw_deg, ride_height_m, aeroCfg)
%WINGCOEFFICIENTS Nonlinear finite-wing polar with smooth post-stall loss. % SI units
arguments
    angle_deg (1,1) double {mustBeFinite}
    speed_mps (1,1) double {mustBeNonnegative}
    yaw_deg (1,1) double {mustBeFinite}
    ride_height_m (1,1) double {mustBeFinite}
    aeroCfg struct
end
if angle_deg < aeroCfg.minimum_angle_deg || angle_deg > aeroCfg.maximum_angle_deg
    error('f1wing:WingAngle', 'Wing angle is outside the configured range.');
end
aspectRatio = aeroCfg.wing_span_m^2 / aeroCfg.wing_area_m2;
slope3D = aeroCfg.lift_curve_slope_2d_per_rad / ...
    (1 + aeroCfg.lift_curve_slope_2d_per_rad / (pi * aeroCfg.span_efficiency * aspectRatio));
effectiveAngle_deg = angle_deg - aeroCfg.zero_lift_angle_deg;
stallEffective_deg = aeroCfg.stall_angle_deg - aeroCfg.zero_lift_angle_deg;
clStall = slope3D * deg2rad(stallEffective_deg);
if angle_deg <= aeroCfg.stall_angle_deg
    clBase = slope3D * deg2rad(effectiveAngle_deg);
    stallExcess_deg = 0;
else
    stallExcess_deg = angle_deg - aeroCfg.stall_angle_deg;
    clBase = clStall * exp(-stallExcess_deg / aeroCfg.post_stall_width_deg);
end
yawMultiplier = min(aeroCfg.maximum_multiplier, max(aeroCfg.minimum_multiplier, ...
    1 - aeroCfg.yaw_sensitivity_per_deg2 * yaw_deg^2));
rideMultiplier = min(aeroCfg.maximum_multiplier, max(aeroCfg.minimum_multiplier, ...
    1 - aeroCfg.ride_height_sensitivity_per_m * ...
    (ride_height_m - aeroCfg.nominal_ride_height_m)));
cl = max(0, clBase * yawMultiplier * rideMultiplier);
cdProfile = aeroCfg.wing_cd0;
cdInduced = cl^2 / (pi * aeroCfg.span_efficiency * aspectRatio);
normalizedExcess = stallExcess_deg / aeroCfg.post_stall_width_deg;
cdStall = aeroCfg.stall_drag_gain * (1 - exp(-(normalizedExcess^2)));
cd = max(0, cdProfile + cdInduced + cdStall);
wing = struct('angle_deg', angle_deg, 'effective_angle_deg', effectiveAngle_deg, ...
    'aspect_ratio', aspectRatio, 'lift_curve_slope_3d_per_rad', slope3D, ...
    'cl', cl, 'cd_profile', cdProfile, 'cd_induced', cdInduced, ...
    'cd_stall', cdStall, 'cd', cd, 'efficiency', cl / cd, ...
    'yaw_multiplier', yawMultiplier, 'ride_height_multiplier', rideMultiplier);
end

