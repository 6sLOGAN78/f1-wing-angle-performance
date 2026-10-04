function simTable = run_simulink(outputDir)
%RUN_SIMULINK Build and simulate the F1WingAeroDemo Simulink model. % SI units
matlabDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(matlabDir);
if nargin < 1 || strlength(string(outputDir)) == 0
    outputDir = fullfile(projectRoot, 'results', 'simulink');
end
outputDir = string(outputDir);
if ~isfolder(outputDir)
    mkdir(outputDir);
end

% 1. Ensure model is built
modelName = "F1WingAeroDemo";
modelPath = fullfile(outputDir, modelName + ".slx");
if ~isfile(modelPath)
    modelPath = build_simulink_demo(outputDir);
end

% 2. Load and simulate
load_system(modelPath);
simOut = sim(modelPath);

% 3. Extract To Workspace signals
speed_struct = simOut.get('simSpeed_mps');
angle_struct = simOut.get('simWingAngle_deg');
df_struct = simOut.get('simDownforce_n');
drag_struct = simOut.get('simDrag_n');

t = speed_struct.time;
v_mps = speed_struct.signals.values;
v_kph = v_mps * 3.6;
angle_deg = angle_struct.signals.values;
downforce_n = df_struct.signals.values;
drag_n = drag_struct.signals.values;

simTable = table(t, v_mps, v_kph, angle_deg, downforce_n, drag_n, ...
    'VariableNames', {'time_s', 'speed_mps', 'speed_kph', 'wing_angle_deg', 'downforce_n', 'drag_n'});
csvPath = fullfile(outputDir, 'simulink_simulation_output.csv');
writetable(simTable, csvPath);

fprintf('Simulink simulation completed: %d samples, saved to %s\n', numel(t), csvPath);
close_system(modelName, 0);
end
