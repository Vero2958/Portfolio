"""
Implementation of the model from Ben-Yishai paper
Ideas:
1. make functions to calculate all equations at each step
2. It's a rate fire model, so we need a vector of neurons
3. How do we assign favorite orientations? each neuron is of course a column (so it's actually a group of neurons
characterized by the same preferred orientation. One column for each angle? so 180 favorite orientations? bho)
4. We need a connectivity matrix, how do we choose inhibitory neurons tho? we assume the connection is inhibitory?
should I respect Dale's law? How do we connect the columns? are columns only connected with other columns with similar PO?
Or are they also connected with other columns but with lower probability? if so, how much lower?
5. How do I test it? I just plain right give it an orientation? like I don't know 30 degrees and then see what it does?
6. How do I visualize what's happening? Is a graph good enough? I mean I think rate/time of each column is good enough
7. Should I add some fluctuations in order to model noise?
8. Should I model inhibition and excitation more explicitly?
9. Basic architecture:
   1) function to calculate synaptic input
   2) function to calculate external input
   Note: 1 and 2 might be just fused into a "calculate input" function, or we add a third step to sum them up, I'd go
   for the second option so that we don't need to recalculate the external input everytime, but maybe the first option
   makes the logic easier, and it is a fast an easy step anyway.
   3) non-linear gain function
   4) E function
   5) I function
   (Or just a function to calculate J? I mean I have the parameters J0 and J2, I don't have I0, E0, I2 and I2 tho...)
   6) mean-field function
   7) function to create a connectivity matrix
   8) Main loop
10. Neurons have 3 states:
   1) S(theta) = 0 : background activity, quiescent state (this is also going to be the initial state of the network)
   2) S(theta) = 1 : active state with saturated activity
   3) 0 < S(theta) < 1 : active state
   All these 3 steps are governed by the gain function, which sets the activity based on the total input h.
"""
import numpy as np
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

#===========================================
#  PARAMETERS
#===========================================
T = 1
Beta = 0.1
c = 1.678
eps = 0.01
J0 = 86
J2 = 112
dt = 1
tau = 5
N_NEURONS = 180
N_STEPS = 8000

#===========================================
#  FUNCTIONS
#===========================================
def g_vec(h_arr):
    out = np.zeros_like(h_arr)
    out = np.where(h_arr >= T + 1/Beta, 1.0, out)
    out = np.where((h_arr > T) & (h_arr < T + 1/Beta), Beta * (h_arr - T), out)
    return out


# senza rumore
def h_all(theta_0, m):
    delta = thetas_rad[:, None] - thetas_rad[None, :]
    J_matrix = -J0 + J2 * np.cos(2 * delta)
    h_syn = (1 / N_NEURONS) * J_matrix @ m
    h_ext = c * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))
    return h_syn + h_ext


# con rumore additivo
"""def h_all(theta_0, m, noise_std=0):
    delta = thetas_rad[:, None] - thetas_rad[None, :]
    J_matrix = -J0 + J2 * np.cos(2 * delta)

    # Calcolo h_syn originale
    h_syn = (1 / N_NEURONS) * J_matrix @ m

    # Aggiunta di rumore bianco gaussiano con media 0 e deviazione standard noise_std
    noise = np.random.normal(0, noise_std, size=h_syn.shape)
    h_syn_noisy = h_syn + noise

    h_ext = c * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))

    return h_syn_noisy + h_ext"""


# con rumore moltiplicativo
"""def h_all(theta_0, m, noise_coeff=0):
    delta = thetas_rad[:, None] - thetas_rad[None, :]
    J_matrix = -J0 + J2 * np.cos(2 * delta)

    # Segnale deterministico
    h_syn = (1 / N_NEURONS) * J_matrix @ m

    # Rumore moltiplicativo: l'entità del rumore scala con h_syn
    # np.random.randn genera numeri dalla distribuzione normale standard
    noise = noise_coeff * h_syn * np.random.randn(*h_syn.shape)

    h_ext = c * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))

    return (h_syn + noise) + h_ext"""


# con rumore random ma sbilanciato a destra e sinistra:
"""def h_all(theta_0, m):
    # --- Codice originale ---
    delta = thetas_rad[:, None] - thetas_rad[None, :]
    J_matrix = -J0 + J2 * np.cos(2 * delta)
    h_syn = (1 / N_NEURONS) * J_matrix @ m

    # --- AGGIUNTA: Rumore di diffusione "pigro" ---
    # Generiamo una piccola spinta casuale diversa OGNI VOLTA che h_all viene chiamata
    # Usiamo una deviazione standard alta (es. 0.5) per vincere l'inerzia
    drift_noise = 0.5 * np.random.randn() * np.sin(thetas_rad)

    # --- Input esterno ---
    h_ext = c * (1 - eps + eps * np.cos(2 * (thetas_rad - theta_0)))

    # Restituiamo tutto sommato
    return h_syn + drift_noise + h_ext"""


#===========================================
#  SIMULATION
#===========================================
thetas_rad = np.linspace(-math.pi/2, math.pi/2, N_NEURONS)
#thetas_deg = np.degrees(thetas_rad)
m = np.zeros(180)
inputs = [0, 60]
inputs = [math.radians(x) for x in inputs]
print(inputs)
T_total = len(inputs) * N_STEPS
results = np.zeros((N_NEURONS, T_total))

"""
sigma = math.radians(30)
m = 0.1 * np.exp(-((thetas_rad - inputs[0])**2) / (2 * sigma**2))
"""

for i, theta_0 in enumerate(inputs):
    for step in range(N_STEPS):
        total_input = h_all(theta_0, m)
        gain = g_vec(total_input)
        dm = (-m + gain) * dt / tau
        m = m + dm
        results[:, i * N_STEPS + step] = m
"""
#===========================================
#  PLOT
#===========================================
cmap = plt.cm.rainbow

norm = plt.Normalize(-math.pi/2, math.pi/2)  # I radianti vanno normalizzati sennò la colormap si sballa
colors = [cmap(norm(td)) for td in thetas_rad]

plt.figure(figsize=(14, 5))
for j in range(N_NEURONS):
    plt.plot(results[j, :], color=colors[j], alpha=0.4, linewidth=0.5)

for i in range(1, len(inputs)):
    plt.axvline(x=i * N_STEPS, color='black', linestyle='--', alpha=0.3)

sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
plt.colorbar(sm, ax=plt.gca(), label='neuron θ (rad)')

plt.xlabel('time (ms)')
plt.ylabel('activity m')
plt.title('Neuron activity over time - Marginal Phase (Ben-Yishai 1995)')
plt.tight_layout()
plt.show()
"""
#===========================================
#  PLOT 3D
#===========================================
fig = plt.figure(figsize=(14, 8))
ax = fig.add_subplot(111, projection='3d')

# Creiamo le mesh per il tempo e le orientazioni
time_steps = np.arange(T_total)
# T_mesh avrà forma (N_NEURONS, T_total)
# Theta_mesh avrà forma (N_NEURONS, T_total)
T_mesh, Theta_mesh = np.meshgrid(time_steps, thetas_rad)

# Plot della superficie
# rstride e cstride campionano i dati ogni tot righe/colonne per non appesantire il 3D
surf = ax.plot_surface(T_mesh, Theta_mesh, results,
                       cmap='rainbow',
                       rstride=5,     # Campionamento ogni 5 neuroni
                       cstride=100,   # Campionamento ogni 100 step temporali
                       antialiased=False)

# Etichette
ax.set_xlabel('Time (ms)', labelpad=15)
ax.set_ylabel('Orientation θ (rad)', labelpad=15)
ax.set_zlabel('Activity m', labelpad=10)
ax.set_title('Spatio-Temporal evolution of activity')

# Aggiungiamo una colorbar
fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label='Activity m')

# Ottimizziamo la vista iniziale
ax.view_init(elev=30, azim=-60)

plt.tight_layout()
plt.show()



