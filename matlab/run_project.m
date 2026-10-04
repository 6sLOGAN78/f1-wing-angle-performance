function results = run_project(configPath, outputDir)
%RUN_PROJECT Execute the complete MATLAB fixed-wing analysis. % SI units
matlabDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(matlabDir);
if nargin < 1 || strlength(string(configPath)) == 0
    configPath = fullfile(projectRoot, 'config', 'project.json');
end
if nargin < 2 || strlength(string(outputDir)) == 0
    outputDir = fullfile(projectRoot, 'results', 'matlab');
end
configPath = string(configPath);
outputDir = string(outputDir);
cfg = f1wing.loadConfig(configPath);
trackDir = fullfile(projectRoot, 'tracks');
keys = {'low_downforce','balanced','high_downforce'};
results = struct();
results.metadata = struct('model', string(cfg.metadata.name), ...
    'classification', string(cfg.metadata.parameter_classification), ...
    'matlab_version', string(version), 'units', "SI");
results.sweeps = struct();
results.optima = table();
for index = 1:numel(keys)
    key = keys{index};
    trackPath = string(fullfile(trackDir, [key '.json']));
    track = f1wing.loadTrack(trackPath, cfg.solver.track_spacing_m);
    sweep = f1wing.fixedAngleSweep(track, cfg, 0:30);
    results.sweeps.(key) = sweep;
    [minimumTime_s, optimumIndex] = min(sweep.lap_time_s);
    row = table(string(key), sweep.angle_deg(optimumIndex), minimumTime_s, ...
        'VariableNames', {'track','optimum_angle_deg','minimum_lap_time_s'});
    results.optima = [results.optima; row]; %#ok<AGROW>
end
f1wing.exportResults(results, outputDir);
fprintf('MATLAB analysis complete: %s\n', outputDir);
end
