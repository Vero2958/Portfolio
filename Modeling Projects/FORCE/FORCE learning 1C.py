import numpy as np
import matplotlib.pyplot as plt

# PARAMETERS
N = 750
g_GG = 1.5

tau = 10
dt = 1
t_learning = 600
T = 1000
alpha = 1

steps = 4000
steps_update = 5

dw_threshold = 1e-6
learning_done = False
t_stop = None

p_recurrent = 0.5   # connection probability JGG (neuron -> neuron)
p_readout = 0.5     # connection probability w (neuron -> output)

# INIT
x = np.random.normal(0, 0.5, N)
r = np.tanh(x)

JGG = np.random.normal(0, 1/np.sqrt(N), (N, N))
mask_JGG = (np.random.rand(N, N) < p_recurrent).astype(float)
np.fill_diagonal(mask_JGG, 0)  # no self-connections
JGG = JGG * mask_JGG

w = np.random.normal(0, 1/np.sqrt(N), N)
mask_w = (np.random.rand(N) < p_readout).astype(float)
w = w * mask_w

P = np.eye(N) / alpha

train_subset = np.random.choice(N, size=750, replace=False)
P_GG = {i: np.eye(N) / alpha for i in train_subset}

# TARGET
def target(t):
    return np.sin(2*np.pi*t/T)

def update_P(P, r):
    return P - (P @ np.outer(r, r) @ P) / (1 + r @ P @ r)

# STORAGE
results = []
z_results = []

post_training_counter = 0
post_training_steps = 1000

# SIMULATION
for t_idx in range(steps):
    print(t_idx)
    t = t_idx * dt
    z = w @ r

    if (not learning_done) and t > t_learning and t_idx % steps_update == 0:
        e = z - target(t)

        # ---- READOUT ----
        P = update_P(P, r)
        old_w = w.copy()
        dw = -e * (P @ r)
        w = w + dw * mask_w          # update only existing connections

        # ---- RECURRENT TRAINING (subset) ----
        for i in train_subset:
            P_GG[i] = update_P(P_GG[i], r)
            dJ = -e * (P_GG[i] @ r)
            JGG[i] = JGG[i] + dJ * mask_JGG[i]   # update only existing connections

        # ---- STOP CONDITION ----
        dw_norm = np.linalg.norm(w - old_w)
        if dw_norm < dw_threshold:
            learning_done = True
            t_stop = t_idx
            print(f"Learning finished at step {t_idx}")

    # ---- DYNAMICS ----
    dx = (-x + g_GG * JGG @ r)
    x = x + (dt/tau) * dx
    r = np.tanh(x)

    results.append(r.copy())
    z_results.append(z)

    # ---- STOP POST TRAINING ----
    if learning_done:
        post_training_counter += 1
        if post_training_counter >= post_training_steps:
            break

# PLOT
plt.figure(figsize=(10,5))
plt.plot(z_results, label="z")
plt.plot([target(t) for t in range(len(z_results))], label="target")

if t_stop is not None:
    plt.axvline(x=t_stop, color='blue', linestyle='--', label='stop learning')

plt.legend()
plt.show()
