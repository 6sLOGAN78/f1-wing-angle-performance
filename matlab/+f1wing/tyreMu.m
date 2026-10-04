function mu = tyreMu(normal_load_n, mu_ref, ref_load_n, exponent)
%TYREMU Load-sensitive tyre friction coefficient. % SI units
arguments
    normal_load_n (1,1) double {mustBePositive}
    mu_ref (1,1) double {mustBePositive}
    ref_load_n (1,1) double {mustBePositive}
    exponent (1,1) double {mustBeNonnegative}
end
mu = mu_ref * (normal_load_n / ref_load_n)^(-exponent);
end

