function tableOut = fixedAngleSweep(track, cfg, angles_deg)
%FIXEDANGLESWEEP Evaluate fixed wing angles on one circuit. % SI units
arguments
    track struct
    cfg struct
    angles_deg (1,:) double = 0:30
end
n = numel(angles_deg);
lapTime_s = zeros(n,1);
maximumSpeed_kph = zeros(n,1);
tractiveEnergy_mj = zeros(n,1);
iterations = zeros(n,1);
for index = 1:n
    result = f1wing.solveLap(track, cfg, angles_deg(index));
    lapTime_s(index) = result.lap_time_s;
    maximumSpeed_kph(index) = result.maximum_speed_mps * 3.6;
    tractiveEnergy_mj(index) = result.tractive_energy_j / 1e6;
    iterations(index) = result.iterations;
end
tableOut = table(reshape(angles_deg,[],1), lapTime_s, maximumSpeed_kph, ...
    tractiveEnergy_mj, iterations, 'VariableNames', ...
    {'angle_deg','lap_time_s','maximum_speed_kph','tractive_energy_mj','iterations'});
end

