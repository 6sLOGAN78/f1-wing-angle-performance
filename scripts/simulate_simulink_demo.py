"""
Simulate the exact 1-DOF dynamic model defined in matlab/build_simulink_demo.m.
Uses SciPy RK45 (matching Simulink ode45) to solve:
    m * dv/dt = F_traction - F_drag(v, angle)
with rate-limited step angle command from 5 deg to 18 deg at t = 5 s (90 deg/s slew rate).
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from pathlib import Path

# Parameters from matlab/build_simulink_demo.m
m = 798.0  # kg
F_traction = 9000.0  # N
v0 = 20.0  # m/s (72 km/h)
t_span = (0.0, 20.0)
slew_rate = 90.0  # deg/s

rho = 1.225
A = 1.5
Aw = 0.72
AR = (1.0 ** 2) / Aw
e = 0.78
a0 = 6.1
a = a0 / (1.0 + a0 / (np.pi * e * AR))
stall = 18.0
width = 7.0

def wing_angle(t):
    """Dynamic wing angle with 90 deg/s rate limiter."""
    if t < 5.0:
        return 5.0
    else:
        # Steps towards 18 deg at 90 deg/s
        dt = t - 5.0
        return min(18.0, 5.0 + slew_rate * dt)

def aero_forces(v_mps, angle_deg):
    clw = a * np.deg2rad(min(angle_deg, stall) + 2.0)
    if angle_deg > stall:
        clw = a * np.deg2rad(stall + 2.0) * np.exp(-(angle_deg - stall) / width)
    
    cdw = 0.055 + (clw ** 2) / (np.pi * e * AR) + 0.55 * (1.0 - np.exp(-(max(angle_deg - stall, 0.0) / width) ** 2))
    cl = 2.4 + clw * (Aw / A)
    cd = 0.78 + cdw * (Aw / A)
    q = 0.5 * rho * max(v_mps, 0.0) ** 2
    downforce_n = q * A * cl
    drag_n = q * A * cd
    return cl, cd, downforce_n, drag_n

def derivatives(t, y):
    v = y[0]
    angle = wing_angle(t)
    _, _, _, drag_n = aero_forces(v, angle)
    dvdt = (F_traction - drag_n) / m
    return [dvdt]

t_eval = np.linspace(0.0, 20.0, 1000)
sol = solve_ivp(derivatives, t_span, [v0], t_eval=t_eval, method='RK45', rtol=1e-6, atol=1e-8)

time = sol.t
speed_mps = sol.y[0]
speed_kph = speed_mps * 3.6
wing_angles = np.array([wing_angle(t) for t in time])

downforces = []
drags = []
cls = []
cds = []
for v, ang in zip(speed_mps, wing_angles):
    cl, cd, df, dg = aero_forces(v, ang)
    cls.append(cl)
    cds.append(cd)
    downforces.append(df)
    drags.append(dg)

downforces = np.array(downforces)
drags = np.array(drags)

# Output summary metrics
print(f"=== SIMULINK DEMO NUMERICAL RESULTS (t=0 to 20 s) ===")
print(f"Initial Speed (t=0s):      {speed_kph[0]:.2f} km/h ({speed_mps[0]:.2f} m/s)")
idx_5 = np.argmin(np.abs(time - 5.0))
print(f"Pre-transition (t=5s):    {speed_kph[idx_5]:.2f} km/h, Wing Angle = {wing_angles[idx_5]:.1f} deg, Drag = {drags[idx_5]:.1f} N, Downforce = {downforces[idx_5]:.1f} N")
idx_5_2 = np.argmin(np.abs(time - 5.2))
print(f"Post-transition (t=5.2s):  {speed_kph[idx_5_2]:.2f} km/h, Wing Angle = {wing_angles[idx_5_2]:.1f} deg, Drag = {drags[idx_5_2]:.1f} N, Downforce = {downforces[idx_5_2]:.1f} N")
print(f"Final Speed (t=20s):       {speed_kph[-1]:.2f} km/h ({speed_mps[-1]:.2f} m/s), Drag = {drags[-1]:.1f} N, Downforce = {downforces[-1]:.1f} N")

# Generate 4-panel figure matching Simulink Performance Scope
fig, axs = plt.subplots(4, 1, figsize=(10, 11), sharex=True)

# Panel 1: Vehicle Speed
axs[0].plot(time, speed_kph, color='#0284c7', lw=2.2, label='Speed (km/h)')
axs[0].axvline(5.0, color='#dc2626', linestyle='--', alpha=0.7, label='Step Command (t=5s)')
axs[0].set_ylabel('Speed [km/h]', fontweight='bold')
axs[0].grid(True, linestyle=':', alpha=0.6)
axs[0].legend(loc='lower right')
axs[0].set_title('Simulink F1WingAeroDemo Scope Output: 1-DOF Longitudinal Acceleration', fontweight='bold', fontsize=12)

# Panel 2: Wing Angle
axs[1].plot(time, wing_angles, color='#16a34a', lw=2.2, label='Wing Angle (deg)')
axs[1].axvline(5.0, color='#dc2626', linestyle='--', alpha=0.7)
axs[1].set_ylabel('Angle [deg]', fontweight='bold')
axs[1].grid(True, linestyle=':', alpha=0.6)
axs[1].legend(loc='upper left')

# Panel 3: Downforce
axs[2].plot(time, downforces, color='#9333ea', lw=2.2, label='Downforce (N)')
axs[2].axvline(5.0, color='#dc2626', linestyle='--', alpha=0.7)
axs[2].set_ylabel('Downforce [N]', fontweight='bold')
axs[2].grid(True, linestyle=':', alpha=0.6)
axs[2].legend(loc='upper left')

# Panel 4: Aerodynamic Drag & Tractive Force
axs[3].plot(time, drags, color='#ea580c', lw=2.2, label='Aero Drag (N)')
axs[3].axhline(F_traction, color='#64748b', linestyle=':', lw=1.8, label=f'Traction Force ({int(F_traction)} N)')
axs[3].axvline(5.0, color='#dc2626', linestyle='--', alpha=0.7)
axs[3].set_ylabel('Force [N]', fontweight='bold')
axs[3].set_xlabel('Time [s]', fontweight='bold')
axs[3].grid(True, linestyle=':', alpha=0.6)
axs[3].legend(loc='center left')

plt.tight_layout()
out_fig = Path('results/figures/fig_simulink_scope_output.png')
fig.savefig(out_fig, dpi=300)
print(f"Saved scope output figure to {out_fig}")
