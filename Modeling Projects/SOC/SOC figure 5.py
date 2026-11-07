import math
import numpy as np
import matplotlib.pyplot as plt
from SOC_Optimization_algorithm import optimize_W
from scipy.linalg import solve_continuous_lyapunov, eigh

# ===========================
# PARAMETERS (same as main)
# ===========================
N = 200
r0 = 5
r_max = 100
delta_t = 1
sigma = 0.2
tau = 200
tau_xi = 50
tau_rise = 400
tau_decay = 2
t_go = 8000
t_start = 2000
Radius = 10
p = 0.1
y = 3

steps = 10000
t_movement_end = t_go + 1000  # 500 ms post go-cue for readout


def g(potential):
    if potential < 0:
        arg = potential / r0
        gain = r0 * np.tanh(arg)
    else:
        delta = r_max - r0
        arg = potential / delta
        gain = delta * np.tanh(arg)
    return gain


def generate_W(N, p, gamma, radius):
    M = N // 2
    w0 = math.sqrt((2 * radius ** 2) / (p * (1 - p) * (1 + gamma ** 2))) / math.sqrt(N)
    mask = np.random.rand(N, N) < p
    W = np.zeros((N, N))
    W[:, :M] = w0 * mask[:, :M]
    W[:, M:] = -gamma * w0 * mask[:, M:]
    np.fill_diagonal(W, 0)
    return W


# ===========================
# BUILD NETWORK
# ===========================
W = generate_W(N, p, y, Radius)
W = optimize_W(W)
A = W - np.eye(N)
Q = np.array(solve_continuous_lyapunov(A.T, -2 * np.eye(N)))
eigenvalues, eigenvectors = eigh(Q)
idx = np.argsort(eigenvalues)[::-1]

a1 = eigenvectors[:, idx[0]]
a1 = a1 / np.std(a1) * 1.5

a2 = eigenvectors[:, idx[1]]
a2 = a2 / np.std(a2) * 1.5

# ===========================
# TARGET TRAJECTORIES
# ===========================
n_movement_steps = 1000  # 500 ms post go-cue

t_traj = np.linspace(0, 1, n_movement_steps)

# Snake: sinusoidal path
snake_x = t_traj
snake_y = np.sin(3 * np.pi * t_traj) * np.exp(-t_traj * 1.5)
snake_target = np.stack([snake_x, snake_y], axis=1)  # (500, 2)

# Butterfly: figure-8 / lemniscate-like
butterfly_x = np.sin(2 * np.pi * t_traj) * np.exp(-t_traj * 1.5)
butterfly_y = np.sin(4 * np.pi * t_traj) * np.exp(-t_traj * 1.5)
butterfly_target = np.stack([butterfly_x, butterfly_y], axis=1)  # (500, 2)


# ===========================
# SIMULATION FUNCTION
# ===========================
def run_trial(a_init, add_noise=True):
    """
    Simulate one trial: preparatory ramp input drives network to a_init,
    then go cue releases network into free dynamics.
    Returns activity matrix of shape (steps, N).
    """
    global_noise = np.zeros(N)
    x = np.zeros(N)
    results = np.zeros((steps, N))

    for t_idx in range(steps):
        t_current = t_idx * delta_t

        # Noise term (Ornstein-Uhlenbeck)
        if add_noise:
            eta = np.random.standard_normal(size=N)
            global_noise = (global_noise
                            - global_noise * delta_t / tau_xi
                            + math.sqrt((2 * sigma ** 2 * (tau + tau_xi) * delta_t) / tau_xi ** 2) * eta)
        else:
            global_noise = np.zeros(N)

        # Ramp R(t)
        if t_current < t_start:
            R = 0.0
        elif t_current < t_go:
            R = 1.0 - math.exp(-(t_current - t_start) / tau_rise)
        else:
            R = math.exp(-(t_current - t_go) / tau_decay)

        # Preparatory input: Pk = a - W g(a)
        g_a = np.array([g(v) for v in a_init])
        Pk = a_init - W @ g_a
        S = R * Pk

        input_I = global_noise + S

        gx = np.array([g(v) for v in x])
        dx = (-x + W @ gx + input_I) * (delta_t / tau)
        x += dx
        results[t_idx, :] = np.array([g(v) for v in x])

    return results


# ===========================
# COLLECT TRAINING DATA
# ===========================
n_train = 100  # trials per movement

print("Running training trials for snake (a1)...")
# Collect post-go-cue activity for snake
go_idx = t_go  # index where go cue happens (t_go ms / delta_t ms per step)
move_slice = slice(go_idx, go_idx + n_movement_steps)

X_snake_list = []
for i in range(n_train):
    if i % 20 == 0:
        print(f"  Trial {i}/{n_train}")
    r = run_trial(a1, add_noise=True)
    X_snake_list.append(r[move_slice, :])  # (500, N)

print("Running training trials for butterfly (a2)...")
X_butterfly_list = []
for i in range(n_train):
    if i % 20 == 0:
        print(f"  Trial {i}/{n_train}")
    r = run_trial(a2, add_noise=True)
    X_butterfly_list.append(r[move_slice, :])  # (500, N)

# Stack all trials
# X shape: (n_train * 500, N), y shape: (n_train * 500, 2)
X_train = np.vstack(
    [np.vstack(X_snake_list),
     np.vstack(X_butterfly_list)]
)  # (2 * n_train * 500, N)

y_train = np.vstack(
    [np.tile(snake_target, (n_train, 1)),
     np.tile(butterfly_target, (n_train, 1))]
)  # (2 * n_train * 500, 2)

# Add bias column
X_train_bias = np.hstack([X_train, np.ones((X_train.shape[0], 1))])

# Least-squares regression: solve X_train_bias @ W_out = y_train
W_out, _, _, _ = np.linalg.lstsq(X_train_bias, y_train, rcond=None)
print(f"Readout weights shape: {W_out.shape}")

# ===========================
# TEST TRIALS
# ===========================
n_test = 5
print("Running test trials...")

test_snake_activities = []
test_butterfly_activities = []

for i in range(n_test):
    r = run_trial(a1, add_noise=True)
    test_snake_activities.append(r)

    r = run_trial(a2, add_noise=True)
    test_butterfly_activities.append(r)


def decode_trajectory(activity_full):
    """Decode muscle trajectory from full trial activity."""
    act = activity_full[move_slice, :]  # (500, N)
    act_bias = np.hstack([act, np.ones((act.shape[0], 1))])
    return act_bias @ W_out  # (500, 2)


# ===========================
# PLOTTING (Figure 5 style)
# ===========================
n_neurons_plot = 10
neuron_idx = np.linspace(0, N - 1, n_neurons_plot, dtype=int)

time_axis = np.arange(steps) * delta_t
# Zoom window: from t_start - 200ms to t_go + 600ms
plot_start = t_start - 200
plot_end = t_go + 600
plot_slice = slice(plot_start, plot_end)
t_plot = time_axis[plot_slice] - t_go  # center on go cue

fig = plt.figure(figsize=(16, 10))
fig.suptitle('Figure 5 — Generation of complex movements through SOC dynamics', fontsize=13)

# Color scheme: test trials in different colors
trial_colors = ['tab:orange', 'tab:green', 'tab:purple', 'tab:cyan', 'tab:pink']

# ---- SNAKE: firing rates ----
ax1 = fig.add_subplot(2, 4, 1)
for neuron in neuron_idx:
    baseline = 0
    for trial_i, act in enumerate(test_snake_activities):
        trace = act[plot_slice, neuron]
        ax1.plot(t_plot, baseline + trace, color=trial_colors[trial_i], alpha=0.6, linewidth=0.8)
    baseline += 15

ax1.axvline(0, color='k', linestyle='--', linewidth=1, label='Go cue')
ax1.set_xlabel('Time from go cue (ms)')
ax1.set_ylabel('Neurons (offset)')
ax1.set_title('Snake — Firing rates')
ax1.set_xlim([t_plot[0], t_plot[-1]])
# Scale bar
ax1.annotate('', xy=(t_plot[0], 5), xytext=(t_plot[0], 10),
             arrowprops=dict(arrowstyle='-', color='k', lw=2))
ax1.text(t_plot[0] - 100, 7.5, '5Hz', ha='right', fontsize=8)

# ---- BUTTERFLY: firing rates ----
ax2 = fig.add_subplot(2, 4, 5)
for neuron in neuron_idx:
    baseline = 0
    for trial_i, act in enumerate(test_butterfly_activities):
        trace = act[plot_slice, neuron]
        ax2.plot(t_plot, baseline + trace, color=trial_colors[trial_i], alpha=0.6, linewidth=0.8)
    baseline += 15

ax2.axvline(0, color='k', linestyle='--', linewidth=1)
ax2.set_xlabel('Time from go cue (ms)')
ax2.set_ylabel('Neurons (offset)')
ax2.set_title('Butterfly — Firing rates')
ax2.set_xlim([t_plot[0], t_plot[-1]])

# ---- SNAKE: muscle trajectories ----
ax3 = fig.add_subplot(2, 4, 2)
for trial_i, act in enumerate(test_snake_activities):
    traj = decode_trajectory(act)
    ax3.plot(traj[:, 0], traj[:, 1], color=trial_colors[trial_i], alpha=0.7, linewidth=1.2)
    ax3.plot(traj[0, 0], traj[0, 1], 'o', color=trial_colors[trial_i], markersize=4)
ax3.plot(snake_target[:, 0], snake_target[:, 1], 'k-', linewidth=2.5, label='Target')
ax3.plot(snake_target[0, 0], snake_target[0, 1], 'ko', markersize=6)
ax3.set_title('Snake — Muscle trajectory')
ax3.set_xlabel('Muscle 1')
ax3.set_ylabel('Muscle 2')
ax3.legend(fontsize=8)
ax3.set_aspect('equal')

# ---- BUTTERFLY: muscle trajectories ----
ax4 = fig.add_subplot(2, 4, 6)
for trial_i, act in enumerate(test_butterfly_activities):
    traj = decode_trajectory(act)
    ax4.plot(traj[:, 0], traj[:, 1], color=trial_colors[trial_i], alpha=0.7, linewidth=1.2)
    ax4.plot(traj[0, 0], traj[0, 1], 'o', color=trial_colors[trial_i], markersize=4)
ax4.plot(butterfly_target[:, 0], butterfly_target[:, 1], 'k-', linewidth=2.5, label='Target')
ax4.plot(butterfly_target[0, 0], butterfly_target[0, 1], 'ko', markersize=6)
ax4.set_title('Butterfly — Muscle trajectory')
ax4.set_xlabel('Muscle 1')
ax4.set_ylabel('Muscle 2')
ax4.legend(fontsize=8)
ax4.set_aspect('equal')

# ---- SNAKE: snapshots at t=0, t=144ms, t=350ms ----
snapshot_times = [0, 144, 350]
snapshot_axes_snake = [fig.add_subplot(2, 4, 3), fig.add_subplot(2, 4, 4),
                       fig.add_subplot(1, 4, 4)]  # rough layout

# Simpler: just plot trajectory snapshots as dots
for k, t_snap in enumerate(snapshot_times):
    ax = fig.add_subplot(2, 4, 3 + k) if k < 2 else None
    if ax is None:
        continue
    snap_idx = t_snap  # ms = index since delta_t=1
    for trial_i, act in enumerate(test_snake_activities):
        traj = decode_trajectory(act)
        if snap_idx < len(traj):
            ax.plot(traj[:snap_idx + 1, 0], traj[:snap_idx + 1, 1],
                    color=trial_colors[trial_i], alpha=0.7, linewidth=1)
            ax.plot(traj[snap_idx, 0], traj[snap_idx, 1], 'o',
                    color=trial_colors[trial_i], markersize=5)
    ax.plot(snake_target[:snap_idx + 1, 0], snake_target[:snap_idx + 1, 1],
            'k-', linewidth=2)
    ax.set_title(f'Snake t={t_snap}ms')
    ax.set_aspect('equal')

# Butterfly snapshot
ax_snap_b = fig.add_subplot(2, 4, 8)
t_snap_b = 180
for trial_i, act in enumerate(test_butterfly_activities):
    traj = decode_trajectory(act)
    if t_snap_b < len(traj):
        ax_snap_b.plot(traj[:t_snap_b + 1, 0], traj[:t_snap_b + 1, 1],
                       color=trial_colors[trial_i], alpha=0.7, linewidth=1)
        ax_snap_b.plot(traj[t_snap_b, 0], traj[t_snap_b, 1], 'o',
                       color=trial_colors[trial_i], markersize=5)
ax_snap_b.plot(butterfly_target[:t_snap_b + 1, 0], butterfly_target[:t_snap_b + 1, 1],
               'k-', linewidth=2)
ax_snap_b.set_title(f'Butterfly t={t_snap_b}ms')
ax_snap_b.set_aspect('equal')

plt.tight_layout()
plt.show()
