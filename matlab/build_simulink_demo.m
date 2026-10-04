function modelPath = build_simulink_demo(outputDir)
%BUILD_SIMULINK_DEMO Create a runnable wing-actuator/aero/vehicle model. % SI units
matlabDir = fileparts(mfilename('fullpath'));
projectRoot = fileparts(matlabDir);
if nargin < 1 || strlength(string(outputDir)) == 0
    outputDir = fullfile(projectRoot, 'results', 'simulink');
end
outputDir = string(outputDir);
if ~license('test', 'Simulink') || isempty(which('new_system'))
    fprintf(['Simulink is not available. Install/activate Simulink, then run ' ...
        'build_simulink_demo again.\n']);
    modelPath = "";
    return;
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end
modelName = "F1WingAeroDemo";
modelPath = fullfile(outputDir, modelName + ".slx");
if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
new_system(modelName);
open_system(modelName);
set_param(modelName, 'StopTime', '20', 'Solver', 'ode45', ...
    'SignalLogging', 'on', 'SignalLoggingName', 'logsout');

add_block('simulink/Sources/Constant', modelName + "/Tractive Force", ...
    'Value', '9000', 'Position', [35 80 100 110]);
add_block('simulink/Sources/Step', modelName + "/Wing Angle Command", ...
    'Time', '5', 'Before', '5', 'After', '18', 'Position', [35 190 100 220]);
add_block('simulink/Discontinuities/Rate Limiter', modelName + "/Rate Limiter", ...
    'RisingSlewLimit', '90', 'FallingSlewLimit', '-90', 'Position', [140 185 230 225]);
add_block('simulink/User-Defined Functions/MATLAB Function', modelName + "/MATLAB Function Aero", ...
    'Position', [330 135 500 235]);
aeroCode = sprintf([ ...
    'function [cl,cd,downforce_n,drag_n] = aero(v_mps,angle_deg)\n' ...
    '%% Representative educational model; SI units.\n' ...
    'rho=1.225; A=1.5; Aw=0.72; AR=1.0^2/Aw; e=0.78; a0=6.1;\n' ...
    'a=a0/(1+a0/(pi*e*AR)); stall=18; width=7;\n' ...
    'clw=a*deg2rad(min(angle_deg,stall)+2);\n' ...
    'if angle_deg>stall, clw=a*deg2rad(stall+2)*exp(-(angle_deg-stall)/width); end\n' ...
    'cdw=0.055+clw^2/(pi*e*AR)+0.55*(1-exp(-(max(angle_deg-stall,0)/width)^2));\n' ...
    'cl=2.4+clw*Aw/A; cd=0.78+cdw*Aw/A; q=0.5*rho*max(v_mps,0)^2;\n' ...
    'downforce_n=q*A*cl; drag_n=q*A*cd;\n' ...
    'end']);
s = sfroot;
chart = s.find('Path', char(modelName + "/MATLAB Function Aero"), '-isa', 'Stateflow.EMChart');
chart.Script = aeroCode;
add_block('simulink/Math Operations/Sum', modelName + "/Net Force", ...
    'Inputs', '+-', 'Position', [560 70 590 125]);
add_block('simulink/Math Operations/Gain', modelName + "/Inverse Mass", ...
    'Gain', '1/798', 'Position', [635 78 710 117]);
add_block('simulink/Continuous/Integrator', modelName + "/Vehicle Speed", ...
    'InitialCondition', '20', 'LimitOutput', 'on', 'LowerSaturationLimit', '0', ...
    'Position', [755 75 790 120]);
add_block('simulink/Signal Routing/Mux', modelName + "/Scope Mux", ...
    'Inputs', '4', 'Position', [850 135 855 250]);
add_block('simulink/Sinks/Scope', modelName + "/Performance Scope", ...
    'Position', [915 145 975 205]);

workspaceBlocks = ["Speed To Workspace","Wing Angle To Workspace", ...
    "Downforce To Workspace","Drag To Workspace"];
workspaceVars = ["simSpeed_mps","simWingAngle_deg","simDownforce_n","simDrag_n"];
workspacePositions = {[900 45 1010 75],[270 255 390 285], ...
    [540 255 660 285],[675 255 795 285]};
for index = 1:numel(workspaceBlocks)
    add_block('simulink/Sinks/To Workspace', modelName + "/" + workspaceBlocks(index), ...
        'VariableName', workspaceVars(index), 'SaveFormat', 'Structure With Time', ...
        'Position', workspacePositions{index});
end

add_line(modelName, 'Tractive Force/1', 'Net Force/1', 'autorouting', 'on');
add_line(modelName, 'Net Force/1', 'Inverse Mass/1', 'autorouting', 'on');
add_line(modelName, 'Inverse Mass/1', 'Vehicle Speed/1', 'autorouting', 'on');
add_line(modelName, 'Vehicle Speed/1', 'MATLAB Function Aero/1', 'autorouting', 'on');
add_line(modelName, 'Vehicle Speed/1', 'Scope Mux/1', 'autorouting', 'on');
add_line(modelName, 'Vehicle Speed/1', 'Speed To Workspace/1', 'autorouting', 'on');
add_line(modelName, 'Wing Angle Command/1', 'Rate Limiter/1', 'autorouting', 'on');
add_line(modelName, 'Rate Limiter/1', 'MATLAB Function Aero/2', 'autorouting', 'on');
add_line(modelName, 'Rate Limiter/1', 'Scope Mux/2', 'autorouting', 'on');
add_line(modelName, 'Rate Limiter/1', 'Wing Angle To Workspace/1', 'autorouting', 'on');
add_line(modelName, 'MATLAB Function Aero/3', 'Scope Mux/3', 'autorouting', 'on');
add_line(modelName, 'MATLAB Function Aero/3', 'Downforce To Workspace/1', 'autorouting', 'on');
add_line(modelName, 'MATLAB Function Aero/4', 'Net Force/2', 'autorouting', 'on');
add_line(modelName, 'MATLAB Function Aero/4', 'Scope Mux/4', 'autorouting', 'on');
add_line(modelName, 'MATLAB Function Aero/4', 'Drag To Workspace/1', 'autorouting', 'on');
add_line(modelName, 'Scope Mux/1', 'Performance Scope/1', 'autorouting', 'on');

Simulink.BlockDiagram.arrangeSystem(modelName);
save_system(modelName, modelPath);
close_system(modelName);
fprintf('Created Simulink model: %s\n', modelPath);
end
