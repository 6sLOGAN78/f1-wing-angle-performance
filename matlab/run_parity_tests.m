function run_parity_tests(parityPath, configPath, trackDir)
%RUN_PARITY_TESTS Compare MATLAB outputs with Python reference fixtures. % SI units
matlabDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(matlabDir);
if nargin < 1 || strlength(string(parityPath)) == 0
    parityPath = fullfile(projectRoot, 'results', 'parity', 'reference_cases.csv');
end
if nargin < 2 || strlength(string(configPath)) == 0
    configPath = fullfile(projectRoot, 'config', 'project.json');
end
if nargin < 3 || strlength(string(trackDir)) == 0
    trackDir = fullfile(projectRoot, 'tracks');
end
cfg = f1wing.loadConfig(string(configPath));
cases = readtable(parityPath, 'TextType', 'string');
for index = 1:height(cases)
    row = cases(index,:);
    if row.case_type == "aero"
        state = f1wing.aeroState(row.angle_deg, row.speed_mps, cfg);
        assertRelative(state.cl_total, row.cl_total, 1e-6, 'cl_total');
        assertRelative(state.cd_total, row.cd_total, 1e-6, 'cd_total');
        assertRelative(state.downforce_n, row.downforce_n, 1e-6, 'downforce_n');
        assertRelative(state.drag_n, row.drag_n, 1e-6, 'drag_n');
    elseif row.case_type == "lap"
        track = f1wing.loadTrack(fullfile(trackDir, row.track + ".json"), cfg.solver.track_spacing_m);
        result = f1wing.solveLap(track, cfg, row.angle_deg);
        assertRelative(result.lap_time_s, row.lap_time_s, 0.015, 'lap_time_s');
    end
end
fprintf('MATLAB/Python parity: PASS (%d cases)\n', height(cases));
end

function assertRelative(actual, expected, tolerance, label)
scale = max(abs(expected), 1);
if abs(actual - expected) / scale > tolerance
    error('f1wing:Parity', '%s mismatch: MATLAB %.12g, reference %.12g', ...
        label, actual, expected);
end
end

