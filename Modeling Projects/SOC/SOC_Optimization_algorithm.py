import math
import numpy as np
from scipy.linalg import solve_continuous_lyapunov


def optimize_W(W):
    # params
    N = 100
    C = 1.5
    B = 0.2
    target_density = 0.4
    M = int(N * 0.5)
    eta = 10
    i = 1

    # add 30% more inhibitory connections and build tagged mask
    inh_mask = W[:, M:] != 0
    total = inh_mask.size
    n_to_add = int(target_density * total) - inh_mask.sum()
    false_indices = np.argwhere(~inh_mask)
    chosen = np.random.choice(len(false_indices), size=n_to_add, replace=False)
    inh_mask[false_indices[chosen, 0], false_indices[chosen, 1]] = True
    W[:, M:][~inh_mask] = 0

    # training loop
    while True:
        print(f"iteration {i}, alpha = {np.max(np.real(np.linalg.eigvals(W))):.4f}")

        # calculate alpha and smoothed alpha
        eigenvalues = np.linalg.eigvals(W)
        alpha = np.max(np.real(eigenvalues))
        smoothed_alpha = max(alpha * C, alpha + B)

        # check convergence
        if alpha < 0.7:
            print(f"alpha converged at iteration number {i}")
            break

        # calculate P, Q and gradient
        A = W - smoothed_alpha * np.eye(N)
        Z = -2 * np.eye(N)
        Q = np.array(solve_continuous_lyapunov(A.T, Z))
        P = np.array(solve_continuous_lyapunov(A, Z))
        grad = (Q @ P) / np.trace(Q @ P)

        # move inhibitory weights using tagged mask
        inh_weights = W[:, M:]
        inh_weights[inh_mask] -= eta * grad[:, M:][inh_mask]

        # save mask of weights that went positive before zeroing them
        went_positive = inh_mask & (inh_weights > 0)
        amount_to_replace = np.sum(went_positive)

        # enforce negativity
        inh_weights[went_positive] = 0

        # enforce ratio excitation/inhibition
        W[:M, M:] *= (-3 * np.mean(W[:M, :M]) / np.mean(W[:M, M:]))
        W[M:, M:] *= (-3 * np.mean(W[M:, :M]) / np.mean(W[M:, M:]))

        # enforce density: replace zeroed connections with new random ones
        if amount_to_replace > 0:
            inh_mask[went_positive] = False
            candidates = np.argwhere(~inh_mask & ~np.eye(N, dtype=bool)[:, M:])
            selector = np.random.choice(len(candidates), size=amount_to_replace, replace=False)
            new_rows = candidates[selector, 0]
            new_cols = candidates[selector, 1]
            inh_mask[new_rows, new_cols] = True
            W[new_rows, new_cols + M] = 0

        i += 1

    return W
