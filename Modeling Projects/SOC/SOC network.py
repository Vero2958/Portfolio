import math
import numpy as np
import matplotlib.pyplot as plt
from SOC_Optimization_algorithm import optimize_W
from scipy.linalg import solve_continuous_lyapunov, eigh
import pickle as pkl
import os

#===========================
# PARAMETERS
#===========================
N = 100
r0 = 5
r_max = 100
Noise = np.zeros(N)
delta_t = 1
sigma = 0.2  # Hz
tau = 200
tau_xi = 50
tau_rise = 400
tau_decay = 2
t_go = 8000
t_start = 2000
Radius = 10
p = 0.1
y = 3


def g_linear(potential):
    if potential < 0:
        gain = max(-r0, potential)
    else:
        gain = min(r_max - r0, potential)
    return gain


def g_sigmoid(potential):
    s = 1 / (1 + np.exp(-potential))
    gain = 4 * (s - 0.5)
    if potential < 0:
        return max(-r0, gain)
    else:
        return min(r_max - r0, gain)


def g_parametrized_sigmoid(potential, a=0.5, b=0.1, c=2.0):
    val = c / (b + np.exp(-a * potential))
    center = c / (b + 1)
    slope_at_0 = a * c / (b + 1)**2
    gain = (val - center) / slope_at_0
    if potential < 0:
        return max(-r0, gain)
    else:
        return min(r_max - r0, gain)


def g(potential):
    if potential < 0:
        arg = potential / r0
        gain = r0*np.tanh(arg)
    else:
        delta = r_max - r0
        arg = potential/delta
        gain = delta*np.tanh(arg)
    return gain


def I(t, a):
    global Noise

    eta = np.random.standard_normal(size=Noise.shape)

    Noise = Noise - Noise*delta_t/tau_xi + math.sqrt((2*sigma**2*(tau + tau_xi)*delta_t)/tau_xi**2)*eta

    if t < t_start:
        R = 0
    elif t < t_go:
        R = 1 - math.exp(-(t - t_start) / tau_rise)
    else:
        R = math.exp(-(t - t_go) / tau_decay)

    g_a = np.array([g(val) for val in a])

    Pk = a - (W @ g_a)
    S = R * Pk

    return Noise + S


def generate_W(N, p, gamma, radius):
    M = int(N * 0.5)

    w0 = math.sqrt((2 * radius ** 2) / (p * (1 - p) * (1 + gamma ** 2))) / math.sqrt(N)

    mask = np.random.rand(N, N) < p

    W = np.zeros((N, N))

    W[:, :M] = w0 * mask[:, :M]
    W[:, M:] = -gamma * w0 * mask[:, M:]
    np.fill_diagonal(W, 0)

    return W


x_test = np.linspace(-20, 20, 1000)
plt.plot(x_test, [g(v) for v in x_test], label='tanh')
plt.plot(x_test, [g_sigmoid(v) for v in x_test], label='sigmoid')
plt.plot(x_test, [g_parametrized_sigmoid(v) for v in x_test], label='param sigmoid')
plt.plot(x_test, [g_linear(v) for v in x_test], label='linear')
plt.axhline(0, color='k', linewidth=0.5)
plt.axvline(0, color='k', linewidth=0.5)
plt.legend()
plt.show()


steps = 15000
results = np.zeros((steps, N))
exc_input = np.zeros((steps, N))
inh_input = np.zeros((steps, N))

W = generate_W(N, p, y, Radius)
W_before = W.copy()
W = optimize_W(W)

print("Shape di W prima del salvataggio:", W.shape)
# save matrices:
# Create the full path to save the pickle file in the specified directory
output_dir = "./"
output_filename = os.path.join(output_dir, f"W_SOC.pkl")

# Save the result to a pickle file
with open(output_filename, 'wb') as f:
    pkl.dump([W], f)

A = W - np.eye(N)
Q = np.array(solve_continuous_lyapunov(A.T, -2 * np.eye(N)))
eigenvalues, eigenvectors = eigh(Q)
idx = np.argsort(eigenvalues)[::-1]
a1 = eigenvectors[:, idx[0]]
a1 = a1 / np.std(a1) * 1.5
var_xi = (sigma**2) * (tau + tau_xi) / tau_xi

x = np.zeros(N)

M = int(N*0.5)

for t_idx in range(steps):
    t_current = t_idx * delta_t
    input_I = I(t_current, a1)
    gx = np.array([g(val) for val in x])

    # contributi sinaptici completi (N x N)
    synaptic_inputs = W * gx  # broadcasting: ogni colonna j moltiplicata per gx[j]

    # separazione per segno (NON per tipo neurone)
    exc_contribution = np.sum(np.maximum(synaptic_inputs, 0), axis=1)
    inh_contribution = np.sum(np.minimum(synaptic_inputs, 0), axis=1)

    exc_input[t_idx, :] = exc_contribution
    inh_input[t_idx, :] = inh_contribution

    # totale corretto
    W_contribution = exc_contribution + inh_contribution
    # ===========================

    dx = (-x + W_contribution + input_I) * (delta_t / tau)
    x += dx
    results[t_idx, :] = np.array([g(val) for val in x])


prep_activity = results[t_start:t_go, :]
print(f"std durante preparazione: {np.std(prep_activity):.3f} Hz")
print(f"amplificazione rispetto a sigma: {np.std(prep_activity)/sigma:.1f}x")

time_axis = np.arange(steps) * delta_t

# --- Plot firing rates ---
plt.figure(figsize=(12, 6))

highlight_idx = np.random.choice(results.shape[1], size=4, replace=False)
highlight_colors = ['tab:red', 'tab:cyan', 'tab:green', 'tab:orange']

for i in range(results.shape[1]):
    if i not in highlight_idx:
        plt.plot(time_axis, results[:, i], color='#444444', alpha=0.3, linewidth=0.5)

for color, i in zip(highlight_colors, highlight_idx):
    plt.plot(time_axis, results[:, i], color=color, linewidth=1, label=f'Neuron {i}')

plt.axvline(x=t_go, color='r', linestyle='--', label='Go Cue')
plt.xlabel('Time (ms)')
plt.ylabel('Firing Rate (Hz)')
plt.title('Free response from a1 - transient amplification')
plt.legend()

# --- Plot eigenvalue spectrum ---
eigenvalues_W = np.linalg.eigvals(W)
plt.figure(figsize=(8, 8))
plt.scatter(np.real(eigenvalues_W), np.imag(eigenvalues_W), s=10)
plt.axvline(x=1, color='r', linestyle='--', label='stability boundary')
plt.xlabel('Real part')
plt.ylabel('Imaginary part')
plt.title('Eigenvalue spectrum of W')
plt.legend()

# --- Plot exc/inh input singolo neurone + media ---
neuron_idx = 0

fig, axes = plt.subplots(2, 1, figsize=(10, 7))

ax = axes[0]
ax.plot(time_axis, exc_input[:, neuron_idx], color='tab:red',  label='Excitatory input', alpha=0.8)
ax.plot(time_axis, inh_input[:, neuron_idx], color='tab:blue', label='Inhibitory input', alpha=0.8)
ax.plot(time_axis, exc_input[:, neuron_idx] + inh_input[:, neuron_idx], color='k', label='Net input (E-I)', linewidth=1.5)
ax.axhline(y=0, color='k', linewidth=0.8)
ax.axvline(x=t_go, color='k', linestyle='--', label='Go Cue')
ax.fill_between(time_axis, exc_input[:, neuron_idx], 0, color='tab:red',  alpha=0.2)
ax.fill_between(time_axis, inh_input[:, neuron_idx], 0, color='tab:blue', alpha=0.2)
ax.set_xlabel('Time (ms)')
ax.set_ylabel('Input (a.u.)')
ax.set_title(f'Excitatory vs Inhibitory input — Neuron {neuron_idx}')
ax.legend()

ax = axes[1]
ax.plot(time_axis, exc_input.mean(axis=1), color='tab:red',  label='Mean excitatory input', alpha=0.8)
ax.plot(time_axis, inh_input.mean(axis=1), color='tab:blue', label='Mean inhibitory input', alpha=0.8)
ax.plot(time_axis, exc_input.mean(axis=1) + inh_input.mean(axis=1), color='k', label='Net input (E-I)', linewidth=1.5)
ax.axhline(y=0, color='k', linewidth=0.8)
ax.axvline(x=t_go, color='k', linestyle='--', label='Go Cue')
ax.fill_between(time_axis, exc_input.mean(axis=1), 0, color='tab:red',  alpha=0.2)
ax.fill_between(time_axis, inh_input.mean(axis=1), 0, color='tab:blue', alpha=0.2)
ax.set_xlabel('Time (ms)')
ax.set_ylabel('Input (a.u.)')
ax.set_title('Excitatory vs Inhibitory input — Average over all neurons')
ax.legend()

plt.tight_layout()

# --- Plot weight matrices ---
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

vmax = max(np.abs(W_before).max(), np.abs(W).max())

im1 = axes[0].imshow(W_before, cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='auto')
axes[0].set_title('Weight matrix — Before optimization')
axes[0].set_xlabel('Neuron j')
axes[0].set_ylabel('Neuron i')
plt.colorbar(im1, ax=axes[0])

im2 = axes[1].imshow(W, cmap='RdBu_r', vmin=-vmax, vmax=vmax, aspect='auto')
axes[1].set_title('Weight matrix — After optimization')
axes[1].set_xlabel('Neuron j')
axes[1].set_ylabel('Neuron i')
plt.colorbar(im2, ax=axes[1])

plt.tight_layout()
plt.show()

"""Aggiungi:
1. Funzione per calcolare I al tempo t
Per farlo serve calcolare R(t), Pk ed il rumore ξ(t)

2. funzione per calcolare i pesi in base ai parametri:
w₀/√N: eccitatori 
γw₀/√N: inibitori
i pesi non zero sono scalati come w₀/√N dove w₀ è determinato dal raggio spettrale desiderato (R=10 nel mio caso):
w₀² = 2R²/(p(1-p)(1+γ²))
dove 
p=0.1 è la densità di connessione 
γ=3 è il ratio tra pesi inibitori ed eccitatori medi.
N=200 ovviamente"""

