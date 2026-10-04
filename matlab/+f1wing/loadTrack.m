function track = loadTrack(trackPath, spacing_m)
%LOADTRACK Load and discretize one synthetic circuit definition. % SI units
arguments
    trackPath (1,1) string
    spacing_m (1,1) double {mustBePositive}
end
raw = jsondecode(fileread(trackPath));
if ~raw.closed
    error('f1wing:OpenTrack', 'The lap solver requires a closed track.');
end
distance_m = [];
ds_m = [];
curvature_1pm = [];
gradient_rad = [];
aero_eligible = [];
speed_limit_mps = [];
for segmentIndex = 1:numel(raw.segments)
    segment = raw.segments(segmentIndex);
    if segment.length_m <= 0
        error('f1wing:InvalidTrack', 'Segment length must be positive.');
    end
    count = ceil(segment.length_m / spacing_m);
    segmentDs_m = segment.length_m / count;
    fractions = ((1:count) - 0.5) / count;
    curvature = segment.curvature_start_1pm + fractions .* ...
        (segment.curvature_end_1pm - segment.curvature_start_1pm);
    ds_m = [ds_m, repmat(segmentDs_m, 1, count)]; %#ok<AGROW>
    curvature_1pm = [curvature_1pm, curvature]; %#ok<AGROW>
    gradient_rad = [gradient_rad, repmat(atan(segment.gradient_percent / 100), 1, count)]; %#ok<AGROW>
    aero_eligible = [aero_eligible, repmat(logical(segment.aero_eligible), 1, count)]; %#ok<AGROW>
    if isempty(segment.speed_limit_kph)
        limit_mps = inf;
    else
        limit_mps = segment.speed_limit_kph / 3.6;
    end
    speed_limit_mps = [speed_limit_mps, repmat(limit_mps, 1, count)]; %#ok<AGROW>
end
distance_m = [0, cumsum(ds_m(1:end-1))];
track = struct('name', string(raw.name), 'description', string(raw.description), ...
    'closed', logical(raw.closed), 'distance_m', distance_m, 'ds_m', ds_m, ...
    'curvature_1pm', curvature_1pm, 'gradient_rad', gradient_rad, ...
    'aero_eligible', aero_eligible, 'speed_limit_mps', speed_limit_mps, ...
    'length_m', sum(ds_m));
end

