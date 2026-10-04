function exportResults(results, outputDir)
%EXPORTRESULTS Write MATLAB tables, MAT data, and comparison plots. % SI units
arguments
    results struct
    outputDir (1,1) string
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end
fields = fieldnames(results.sweeps);
for index = 1:numel(fields)
    key = fields{index};
    writetable(results.sweeps.(key), fullfile(outputDir, string(key) + "_sweep.csv"));
end
save(fullfile(outputDir, 'F1_Wing_Angle_MATLAB_Results.mat'), 'results');
figure('Color','w','Name','F1 Wing Angle Lap-Time Sweep');
hold on;
for index = 1:numel(fields)
    tableData = results.sweeps.(fields{index});
    plot(tableData.angle_deg, tableData.lap_time_s, 'LineWidth', 1.5, ...
        'DisplayName', strrep(fields{index}, '_', ' '));
end
xlabel('Rear-wing angle (deg)');
ylabel('Lap time (s)');
title('Circuit-specific fixed-wing optimization');
grid on;
legend('Location','best');
exportgraphics(gcf, fullfile(outputDir, 'matlab_lap_time_sweep.png'), 'Resolution', 200);
close(gcf);
end
