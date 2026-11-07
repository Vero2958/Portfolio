
"""
Implementation of models and learning algorithm from "Generating Coherent Patterns of Activity
from Chaotic Neural Networks"

3 networks:
1A : generator + readout unit (only connections from the generator to the readout are trained)
1B : generator + feedback network + readout unit (connections from the generator to the readout and to the feedback are trained)
1C : generator + readout unit (all connections are trained)
"""

"""
1B:
1. a firing rate vector
2. a membrane potential vector
3. a connectivity matrix
4. a feedback network smaller than the main one
4. a weight vector of length N expressing every neuron's connection with z's weight
5. x is initialized with values different from 0
6. r transforms the potentials into firing rates by applying tanh(x) to every element of x
7. use the usual dynamic equation to update x. 
"""


import numpy as np
import matplotlib.pyplot as plt

# PARAMETRI
N = 500
NF = 100

g_GG = 1.5
g_GF = 1.0
g_FG = 1.0
g_FF = 1.2

tau = 10
dt = 1
t_learning = 600
T = 1000
alpha = 1

steps = 10000
steps_update = 10

dw_threshold = 1e-6
learning_done = False
t_stop = None

# INIT
x = np.random.normal(0, 0.5, N)
r = np.tanh(x)

y = np.random.normal(0, 0.5, NF)
s = np.tanh(y)

JGG = np.random.normal(0, 1/np.sqrt(N), (N, N))
JGF = np.random.normal(0, 1/np.sqrt(NF), (N, NF))
JFF = np.random.normal(0, 1/np.sqrt(NF), (NF, NF))
JFG = np.random.normal(0, 1/np.sqrt(N), (NF, N))  # TRAINED

w = np.random.normal(0, 1/np.sqrt(N), N)

P = np.eye(N) / alpha

train_subset = np.random.choice(NF, size=50, replace=False)
P_FG = {i: np.eye(N) / alpha for i in train_subset}

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
    t = t_idx * dt
    z = w @ r

    if (not learning_done) and t > t_learning and t_idx % steps_update == 0:
        e = z - target(t)

        # ---- READOUT UPDATE ----
        P = update_P(P, r)
        old_w = w.copy()
        w = w - e * (P @ r)

        # ---- FEEDBACK UPDATE (subset) ----
        for i in train_subset:
            P_FG[i] = update_P(P_FG[i], r)
            JFG[i] = JFG[i] - e * (P_FG[i] @ r)

        # ---- STOP CONDITION ----
        dw = np.linalg.norm(w - old_w)
        if dw < dw_threshold:
            learning_done = True
            t_stop = t_idx
            print(f"Learning finished at step {t_idx}")

    # ---- DYNAMICS ----
    dx = (-x + g_GG * JGG @ r + g_GF * JGF @ s)
    x = x + (dt/tau) * dx
    r = np.tanh(x)

    dy = (-y + g_FF * JFF @ s + g_FG * JFG @ r)
    y = y + (dt/tau) * dy
    s = np.tanh(y)

    results.append(r.copy())
    z_results.append(z)

    # ---- POST TRAINING STOP ----
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
