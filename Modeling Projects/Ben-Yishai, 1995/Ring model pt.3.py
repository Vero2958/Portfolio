import numpy as np
import math
import matplotlib.pyplot as plt

#===========================================
#  PARAMETERS
#===========================================
T = 1
Beta = 0.1
c = 1.678
#c = 2.5
eps = 0.1
dt = 1
tau = 20
N_NEURONS = 180
N_STEPS = 70000
t_stim_on = 2000
t_stim_off = 40000
theta_0 = math.radians(30)
print(theta_0)
pinning_strength = 0.0  # Forza del "difetto" nella rete

# --- NUOVI PARAMETRI MEXICAN HAT ---
# Modifica questi per cambiare Altezza e Larghezza
A_E = 180     # Altezza Eccitazione
sigma_E = 0.2  # Larghezza Eccitazione (rad)
A_I = 50    # Altezza Inibizione
sigma_I = 2  # Larghezza Inibizione (rad)
# NB: Per tornare al Ben-Yishai puro, il coseno è una forma fissa.
#===========================================

thetas_rad = np.linspace(-math.pi/2, math.pi/2, N_NEURONS)

def get_mexican_hat():
    # Calcola il profilo di connettività centrato su 0
    # Usiamo la distanza angolare minima sull'anello
    diff = thetas_rad
    # Eccitazione - Inibizione (Gaussiane)
    J = A_E * np.exp(-diff**2 / (2 * sigma_E**2)) - A_I * np.exp(-diff**2 / (2 * sigma_I**2))
    return J

def plot_mexican_hat():
    J = get_mexican_hat()
    plt.figure(figsize=(8, 4))
    plt.plot(np.degrees(thetas_rad), J, color='black', lw=2)
    plt.axhline(0, color='gray', linestyle='--')
    plt.title(f"Mexican Hat profile (σE={sigma_E}, σI={sigma_I})")
    plt.xlabel("Distance (deg)")
    plt.ylabel("Connection strength")
    plt.grid(True, alpha=0.3)

def g_vec(h_arr):
    out = np.zeros_like(h_arr)
    # Approssimazione della funzione di guadagno del paper
    out = np.where(h_arr >= T + 1/Beta, 1.0, out)
    out = np.where((h_arr > T) & (h_arr < T + 1/Beta), Beta * (h_arr - T), out)
    return out

# Pre-calcoliamo la matrice di interazione circolante
J_profile = get_mexican_hat()

theta_i = thetas_rad[:, None]
theta_j = thetas_rad[None, :]

dtheta = theta_i - theta_j
dtheta = (dtheta + np.pi) % (2 * np.pi) - np.pi

J_matrix = (
    A_E * np.exp(-dtheta**2 / (2 * sigma_E**2))
    - A_I * np.exp(-dtheta**2 / (2 * sigma_I**2))
)

def h_all(m, stim_on=True):
    h_syn = (1 / N_NEURONS) * (J_matrix @ m)
    if stim_on:
        h_ext = c * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))
        return h_syn + h_ext
    else:
        return h_syn

#===========================================
#  SIMULATION
#===========================================
plot_mexican_hat() # Visualizza il profilo prima di partire

m = np.zeros(N_NEURONS)
results = np.zeros((N_NEURONS, N_STEPS))

for step in range(N_STEPS):
    is_stim_on = t_stim_on <= step < t_stim_off
    total_input = h_all(m, stim_on=is_stim_on)
    gain = g_vec(total_input)
    dm = (-m + gain) * dt / tau
    m = m + dm
    results[:, step] = m

#===========================================
#  PLOT RESULTS (2D)
#===========================================
fig1, ax1 = plt.subplots(figsize=(12, 5))
cmap = plt.cm.rainbow
norm = plt.Normalize(-math.pi/2, math.pi/2)
for j in range(0, N_NEURONS, 5):  # Plot ogni 5 neuroni per chiarezza
    ax1.plot(results[j, :], color=cmap(norm(thetas_rad[j])), alpha=0.6)

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
plt.colorbar(sm, ax=plt.gca(), label='neuron θ (rad)')
ax1.axvline(x=t_stim_on, color='k', linestyle='--', label='Stim ON')
ax1.axvline(x=t_stim_off, color='k', linestyle='-.', label='Stim OFF')
ax1.set_title("Activity over Time")
ax1.set_xlabel("Time steps")
ax1.set_ylabel("Activity m")
#plt.show()


#===========================================
#  PLOT 3D
#===========================================
fig2 = plt.figure(figsize=(14, 8))
ax2 = fig2.add_subplot(111, projection='3d')

time_steps = np.arange(N_STEPS)
T_mesh, Theta_mesh = np.meshgrid(time_steps, thetas_rad)

surf = ax2.plot_surface(T_mesh, Theta_mesh, results,
                        cmap='rainbow',
                        rstride=5,
                        cstride=100,
                        antialiased=False)

ax2.set_xlabel('Time (ms)', labelpad=15)
ax2.set_ylabel('Orientation θ (rad)', labelpad=15)
ax2.set_zlabel('Activity m', labelpad=10)
ax2.set_title('Spatio-Temporal evolution of the Activity')

fig2.colorbar(surf, ax=ax2, shrink=0.5, aspect=10, label='Activity m')
ax2.view_init(elev=30, azim=-60)

plt.tight_layout()
plt.show()
