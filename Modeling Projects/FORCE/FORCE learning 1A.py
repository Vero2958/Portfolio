import numpy as np
import matplotlib.pyplot as plt

"""
Implementation of models and learning algorithm from "Generating Coherent Patterns of Activity
from Chaotic Neural Networks"

3 networks:
1A : generator + readout unit (only connections from the generator to the readout are trained)
1B : generator + feedback network + readout unit (connections from the generator to the readout and to the feedback are trained)
1C : generator + readout unit (all connections are trained)
"""

"""
1A:
1. a firing rate vector
2. a membrane potential vector
3. a connectivity matrix
4. a weight vector of length N expressing every neuron's connection with z's weight
5. x is initialized with values different from 0
6. r transforms the potentials into firing rates by applying tanh(x) to every element of x
7. use the usual dynamic equation to update x. 
"""


def update_network(x, r, z, JGG, JGz, I_ext=None):
    """
    x    : (N,)   state vector
    r    : (N,)   firing rates = tanh(x)
    z    : float  output readout
    JGG  : (N,N)  connectivity matrix (sparse ok)
    JGz  : (N,)   feedback weights from z to the network
    I_ext: (N,)   optional external input
    """
    dx = (-x + g_GG * JGG @ r + g_Gz * JGz * z)

    if I_ext is not None:
        dx += I_ext

    x_new = x + (dt / tau) * dx
    r_new = np.tanh(x_new)

    return x_new, r_new


def generate_jgg(N, p=0.1):
    W_raw = np.random.normal(0, 1/np.sqrt(p * N), (N, N))
    mask = np.random.rand(N, N) < p
    np.fill_diagonal(mask, False)  # no self-connections
    return W_raw * mask


def calculate_z(w, r):
    z = w @ r
    return z


def calculate_error(z):
    f = np.sin(2 * np.pi * t_current / T)  # per ora, poi creiamo una funzione a parte
    error = z - f
    return error


def update_matrix_p(p_current, rate):
    p_new = (p_current - (p_current @ np.outer(rate, rate) @ p_current) / (1 + rate @ p_current @ rate))
    return p_new


def update_w(weight_vector, error, P_matrix, rate):
    w_new = weight_vector - error * P_matrix @ rate
    return weight_vector, w_new  # save them as old_w, current_w


def calculate_dw(w_new, w_old):
    dw = w_new - w_old
    return dw


# 1. initialization and parameters
g_GG = 1.5
g_Gz = 1.0
tau = 10
dt = 1
steps_update = 1
N = 1000
p_z = 1.0
#steps = 100000
t_learning = 600
T = 1000
alpha = 1
P = np.eye(N) / alpha
#results = np.zeros((steps, N))  # Matrix Time x Neurons
#z_results = np.zeros(steps)
x = np.random.normal(0, 0.5, size=N)
r = np.tanh(x)
W = generate_jgg(N)
JGz = np.random.uniform(0, 1, size=N)  # feedback weights, ordine 1
w = np.random.normal(0, 1/np.sqrt(p_z * N), size=N)
dw_threshold = 1e-6
learning_done = False

results = []
z_results = []

# 2. Simulation
post_training_counter = 0
post_training_steps = 4000
t_stop = None

for t_idx in range(10000000):
    t_current = t_idx * dt
    z = calculate_z(w, r)

    if not learning_done and t_current >= t_learning and t_idx % steps_update == 0:
        e_ = calculate_error(z)
        P = update_matrix_p(P, r)
        old_w, w = update_w(w, e_, P, r)
        z = calculate_z(w, r)
        dw = calculate_dw(w, old_w)
        print(f"z: {z:.4f}, f: {np.sin(2 * np.pi * t_current / T):.4f}, e_: {e_:.4f}, norm_w: {np.linalg.norm(w):.4f}")
        if np.linalg.norm(dw) < dw_threshold:
            t_stop = t_idx
            learning_done = True

    x, r = update_network(x, r, z, W, JGz)
    results.append(r.copy())
    z_results.append(z)

    if learning_done:
        post_training_counter += 1
        if post_training_counter >= post_training_steps:
            break

results = np.array(results)
z_results = np.array(z_results)

# 3. Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# plot activity
ax1.plot(results[:, :10], alpha=0.7)
ax1.axvline(x=t_learning, color='blue', linestyle='--', label='Start learning')
ax1.axvline(x=t_stop, color='blue', linestyle='-.', label='Stop learning')
ax1.set_xlabel('Time steps')
ax1.set_ylabel('Firing Rate')
ax1.set_title('Network Activity')
ax1.legend()

# plot output vs target
ax2.plot(z_results, color='red', label='z')
ax2.plot([np.sin(2 * np.pi * t / T) for t in range(len(z_results))], color='green', label='target')
ax2.axvline(x=t_learning, color='blue', linestyle='--', label='Start learning')
ax2.axvline(x=t_stop, color='blue', linestyle='-.', label='Stop learning')
ax2.set_xlabel('Time steps')
ax2.set_ylabel('Output')
ax2.set_title('Output vs Target')
ax2.legend()

plt.tight_layout()
plt.show()







