import numpy as np
import math
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ===========================================
#  PARAMETERS
# ===========================================
T = 1
Beta = 0.1
c = 1.678
eps = 0.1
dt = 1
tau = 20
N_NEURONS = 180
N_STEPS = 100000
t_stim_on = 2000
t_stim_off = 40000
theta_0 = math.radians(30)

A_E = 180
sigma_E = 0.2
A_I = 50
sigma_I = 2

# ===========================================
#  NOISE PARAMETERS  ← nuovi
# ===========================================
# Ogni termine è un'ampiezza scalare (std del rumore bianco).
# Poni a 0.0 per disabilitarlo.

sigma_syn  = 0.05   # Rumore sinaptico: aggiunto al campo h prima di g()
                    # Modella variabilità nella trasmissione sinaptica.
                    # (Brunel & Wang 2001 usano termini analoghi)

sigma_proc = 0.02   # Rumore di processo: termine di Langevin sull'eq. del rate
                    # τ dm/dt = -m + g(h) + σ_proc · ξ(t)
                    # Modella variabilità intrinseca nel firing del neurone.

sigma_stim = 0.03   # Rumore sull'input esterno: c → c + σ_stim · ξ(t)
                    # Modella l'incertezza nella rappresentazione sensoriale.

sigma_J    = 0.01   # Rumore di connettività: J_ij += σ_J · N(0,1) (fisso nel tempo)
                    # Modella eterogeneità biologica nelle sinapsi.
                    # Nota: rende il bump "asimmetrico" → può causare drift sistematico.

# ===========================================

thetas_rad = np.linspace(-math.pi/2, math.pi/2, N_NEURONS)

def g_vec(h_arr):
    out = np.zeros_like(h_arr)
    out = np.where(h_arr >= T + 1/Beta, 1.0, out)
    out = np.where((h_arr > T) & (h_arr < T + 1/Beta), Beta * (h_arr - T), out)
    return out

# --- Matrice di connettività con rumore di connettività ---
theta_i = thetas_rad[:, None]
theta_j = thetas_rad[None, :]
dtheta = (theta_i - theta_j + np.pi) % (2 * np.pi) - np.pi

J_matrix = (
    A_E * np.exp(-dtheta**2 / (2 * sigma_E**2))
    - A_I * np.exp(-dtheta**2 / (2 * sigma_I**2))
)

# Aggiungi rumore di connettività (fisso: perturbazione quenched)
if sigma_J > 0:
    rng = np.random.default_rng(seed=58)
    J_noise = sigma_J * rng.standard_normal(J_matrix.shape)
    J_noise = (J_noise + J_noise.T) / 2  # Mantieni simmetria
    J_matrix = J_matrix + J_noise
    print(f"[Noise] Connettività: σ_J={sigma_J:.3f}, "
          f"perturbazione max={np.max(np.abs(J_noise)):.3f}")

def h_all(m, stim_on=True, rng=None):
    h_syn = (1 / N_NEURONS) * (J_matrix @ m)

    # Rumore sinaptico (varianza indipendente per ogni neurone e step)
    if sigma_syn > 0 and rng is not None:
        h_syn += sigma_syn * rng.standard_normal(N_NEURONS)

    if stim_on:
        c_eff = c
        if sigma_stim > 0 and rng is not None:
            # Rumore globale sull'ampiezza dello stimolo
            c_eff = c + sigma_stim * rng.standard_normal()
        h_ext = c_eff * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))
        return h_syn + h_ext
    else:
        return h_syn

def population_vector_decoder(m, thetas):
    """
    Decodifica l'angolo memorizzato dal bump tramite il vettore
    di popolazione: θ_est = angle( Σ m_i · e^{2i·θ_i} ) / 2
    Restituisce NaN se l'attività totale è troppo bassa.
    """
    total = np.sum(m)
    if total < 1e-6:
        return np.nan
    z = np.sum(m * np.exp(2j * thetas))
    return np.angle(z) / 2   # in radianti

# ===========================================
#  SIMULATION
# ===========================================
rng = np.random.default_rng(seed=0)

m = np.zeros(N_NEURONS)
results      = np.zeros((N_NEURONS, N_STEPS))
decoded_theta = np.zeros(N_STEPS)

for step in range(N_STEPS):
    is_stim_on = t_stim_on <= step < t_stim_off

    total_input = h_all(m, stim_on=is_stim_on, rng=rng)
    gain = g_vec(total_input)

    dm = (-m + gain) * dt / tau

    # Rumore di processo (Langevin)
    if sigma_proc > 0:
        dm += (sigma_proc / np.sqrt(tau)) * rng.standard_normal(N_NEURONS)

    m = np.clip(m + dm, 0.0, 1.0)   # Il rate è in [0,1]
    results[:, step] = m
    decoded_theta[step] = population_vector_decoder(m, thetas_rad)

print("Simulazione completata.")
print(f"  Sigma syn={sigma_syn}, proc={sigma_proc}, "
      f"stim={sigma_stim}, J={sigma_J}")

# ===========================================
#  ANALYSIS: drift del bump nella fase di mantenimento
# ===========================================
maintenance_slice = slice(t_stim_off, N_STEPS)
theta_hold = decoded_theta[maintenance_slice]
theta_hold_clean = theta_hold[~np.isnan(theta_hold)]

if len(theta_hold_clean) > 100:
    drift_std  = np.nanstd(np.degrees(theta_hold_clean))
    drift_mean = np.nanmean(np.degrees(theta_hold_clean))
    print(f"\n  Bump persistance:")
    print(f"    mean position : {drift_mean:.2f}°  (target: {math.degrees(theta_0):.1f}°)")
    print(f"    SD (fluctuations): {drift_std:.2f}°")

# ===========================================
#  PLOT (5 pannelli: 4 analisi + 3D)
# ===========================================
fig = plt.figure(figsize=(20, 14))
gs = gridspec.GridSpec(2, 3, hspace=0.45, wspace=0.38)

# --- Pannello 1: Attività 2D ---
ax1 = fig.add_subplot(gs[0, 0])
cmap = plt.cm.rainbow
norm = plt.Normalize(-math.pi/2, math.pi/2)
for j in range(0, N_NEURONS, 5):
    ax1.plot(results[j, :], color=cmap(norm(thetas_rad[j])), alpha=0.5, lw=0.8)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
plt.colorbar(sm, ax=ax1, label='θ neuron (rad)')
ax1.axvline(x=t_stim_on,  color='k', linestyle='--', lw=1.2, label='Stim ON')
ax1.axvline(x=t_stim_off, color='k', linestyle='-.', lw=1.2, label='Stim OFF')
ax1.set_title("Activity over time (with noise)", fontsize=11)
ax1.set_xlabel("Time steps")
ax1.set_ylabel("Activity m")
ax1.legend(fontsize=8)

# --- Pannello 2: Decoded position ---
ax2 = fig.add_subplot(gs[0, 1])
t_axis = np.arange(N_STEPS)
ax2.plot(t_axis, np.degrees(decoded_theta), color='steelblue', lw=0.7, alpha=0.8)
ax2.axhline(y=math.degrees(theta_0), color='tomato', lw=1.5,
            linestyle='--', label=f'Target θ₀={math.degrees(theta_0):.1f}°')
ax2.axvline(x=t_stim_on,  color='k', linestyle='--', lw=1, label='Stim ON')
ax2.axvline(x=t_stim_off, color='k', linestyle='-.', lw=1, label='Stim OFF')
ax2.set_title("Bum position", fontsize=11)
ax2.set_xlabel("Time steps")
ax2.set_ylabel("θ̂ (deg)")
ax2.legend(fontsize=8)
ax2.set_ylim(-90, 90)

# --- Pannello 3: Profilo istantaneo bump (3 momenti) ---
ax3 = fig.add_subplot(gs[1, 0])
moments = {
    'During stim (t=20000)':      20000,
    'Just after OFF (t=42000)':   42000,
    'Late maintenance (t=65000)': 65000,
}
colors_m = ['dodgerblue', 'darkorange', 'mediumpurple']
for (label, t_idx), col in zip(moments.items(), colors_m):
    if t_idx < N_STEPS:
        ax3.plot(np.degrees(thetas_rad), results[:, t_idx],
                 label=label, color=col, lw=1.5)
ax3.axvline(x=math.degrees(theta_0), color='tomato',
            linestyle='--', lw=1, label='θ₀ target')
ax3.set_title("Bump profile", fontsize=11)
ax3.set_xlabel("θ neuron (deg)")
ax3.set_ylabel("Activity m")
ax3.legend(fontsize=8)

# --- Pannello 4: Distribuzione del drift ---
"""ax4 = fig.add_subplot(gs[1, 1])
if len(theta_hold_clean) > 100:
    ax4.hist(np.degrees(theta_hold_clean), bins=60,
             color='steelblue', alpha=0.75, edgecolor='white', lw=0.4)
    ax4.axvline(x=math.degrees(theta_0), color='tomato', lw=1.5,
                linestyle='--', label=f'Target={math.degrees(theta_0):.1f}°')
    ax4.axvline(x=drift_mean, color='navy', lw=1.5,
                linestyle='-', label=f'Media={drift_mean:.1f}°')
    ax4.set_title(f"Position distribution (during bump persistence)\nSD={drift_std:.2f}°", fontsize=11)
    ax4.set_xlabel("θ̂ (deg)")
    ax4.set_ylabel("Count")
    ax4.legend(fontsize=8)
else:
    ax4.text(0.5, 0.5, "Bump estinto durante\nil mantenimento",
             ha='center', va='center', transform=ax4.transAxes, fontsize=12)
    ax4.set_title("Position distribution (during bump persistence)")"""

# --- Pannello 5: Plot 3D (occupa tutta la colonna destra) ---
fig2 = plt.figure(figsize=(14, 8))
ax5 = fig2.add_subplot(111, projection='3d')

time_steps = np.arange(N_STEPS)
T_mesh, Theta_mesh = np.meshgrid(time_steps, thetas_rad)

surf = ax5.plot_surface(T_mesh, Theta_mesh, results,
                        cmap='rainbow',
                        rstride=5,
                        cstride=100,
                        antialiased=False)

ax5.set_xlabel('Time (ms)', labelpad=15)
ax5.set_ylabel('Orientation θ (rad)', labelpad=15)
ax5.set_zlabel('Activity m', labelpad=10)
ax5.set_title('Spatio-Temporal evolution of activity (with noise)', fontsize=11)
fig.colorbar(surf, ax=ax5, shrink=0.4, aspect=10, label='Activity m')
ax5.view_init(elev=30, azim=-60)

fig.suptitle(
    f"Continuous Attractor with realistic noise\n"
    f"(σ_syn={sigma_syn}, σ_proc={sigma_proc}, σ_stim={sigma_stim}, σ_J={sigma_J})",
    fontsize=13, y=1.01
)
plt.tight_layout()
plt.show()