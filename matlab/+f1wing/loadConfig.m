function cfg = loadConfig(configPath)
%LOADCONFIG Load the shared JSON project configuration. % SI units
arguments
    configPath (1,1) string
end
if ~isfile(configPath)
    error('f1wing:MissingConfig', 'Configuration file not found: %s', configPath);
end
cfg = jsondecode(fileread(configPath));
required = {'metadata','environment','vehicle','aero','tyres','powertrain','solver','strategy'};
for index = 1:numel(required)
    if ~isfield(cfg, required{index})
        error('f1wing:InvalidConfig', 'Missing configuration section: %s', required{index});
    end
end
if cfg.aero.minimum_angle_deg >= cfg.aero.maximum_angle_deg
    error('f1wing:InvalidConfig', 'Invalid wing-angle bounds.');
end
cfg.powertrain.rpm_points = reshape(cfg.powertrain.rpm_points, 1, []);
cfg.powertrain.torque_nm = reshape(cfg.powertrain.torque_nm, 1, []);
cfg.powertrain.gear_ratios = reshape(cfg.powertrain.gear_ratios, 1, []);
if numel(cfg.powertrain.rpm_points) ~= numel(cfg.powertrain.torque_nm)
    error('f1wing:InvalidConfig', 'rpm_points and torque_nm must have equal lengths.');
end
end

