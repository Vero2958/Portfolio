import numpy as np
import matplotlib.pyplot as plt

# PARAMETERS:
N = 40
T = 200
dt = 1
V_rest = -70
V_thresh = -55
tau = 20
alpha = np.exp(-dt / tau)
W = np.random.randn(N, N) * 1.5

# initial state
V = np.full(N, V_rest)
spike_trains = []

# --- Simulation ---
for t in range(T):
    # 1. Synaptic input (W @ spike at t-1)
    if t == 0:
        spikes_prev = np.zeros(N)
    else:
        spikes_prev = spike_trains[-1]

    I_syn = np.dot(W, spikes_prev)

    # 2. External input:
    I_ext = [30, 60, 40, 27, 18, 13, 33, 25, 19, 19, 30, 60, 40, 27, 18, 13, 33, 25, 19, 19, 30, 60, 40, 27, 18, 13, 33, 25, 19, 19,30, 60, 40, 27, 18, 13, 33, 25, 19, 19]  # assuming constant external input

    # 3. Update potentials
    V = V_rest + (V - V_rest) * alpha + (I_syn + I_ext) * (1 - alpha)

    # 4. Reset
    current_spikes = (V >= V_thresh)
    V[current_spikes == 1] = V_rest

    spike_trains.append(current_spikes)

# To numpy array
spike_data = np.array(spike_trains)

# --- Raster Plot ---
plt.figure(figsize=(10, 6))
t_idx, neuron_idx = np.where(spike_data == 1)  # spikes
plt.scatter(t_idx, neuron_idx, s=10, c='black', marker='|')
plt.title(f"Raster Plot of a LIF network (N={N})")
plt.xlabel("Time (ms)")
plt.ylabel("Neuron index")
plt.ylim(-1, N)
plt.grid(axis='x', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.show()


# add plots with potential, stats and change W to be consistant with Dale's law. Do a network of 100 N with
# 20% excitatory and 80% inhibitory neurons.

