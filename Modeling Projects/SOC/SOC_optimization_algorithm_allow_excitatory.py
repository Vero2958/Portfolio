import numpy as np
from scipy.linalg import solve_continuous_lyapunov


def optimize_W(W):
    # params
    N = 200
    C = 1.5
    B = 0.2
    target_density = 0.4
    M = N // 2
    eta = 10
    i = 1

    # reach target density on the full matrix (no self-connections)
    no_self = ~np.eye(N, dtype=bool)
    mask = W != 0
    n_to_add = int(target_density * N * N) - mask.sum()
    if n_to_add > 0:
        candidates = np.argwhere(~mask & no_self)
        chosen = np.random.choice(len(candidates), size=n_to_add, replace=False)
        mask[candidates[chosen, 0], candidates[chosen, 1]] = True

    # training loop
    while True:
        eigenvalues = np.linalg.eigvals(W)
        alpha = np.max(np.real(eigenvalues))
        print(f"iteration {i}, alpha = {alpha:.4f}")

        # check convergence
        if alpha < 0.5:
            print(f"alpha converged at iteration number {i}")
            break

        # smoothed shift to make A stable
        smoothed_alpha = max(alpha * C, alpha + B)

        # solve Lyapunov equations and compute gradient
        A = W - smoothed_alpha * np.eye(N)
        Z = -2 * np.eye(N)
        Q = solve_continuous_lyapunov(A.T, Z)
        P = solve_continuous_lyapunov(A, Z)
        grad = (Q @ P) / np.trace(Q @ P)

        # update ALL weights
        W[mask] -= eta * grad[mask]

        # --- enforce sign constraints ---
        # excitatory columns (first M): weights must stay positive
        went_negative = mask[:, :M] & (W[:, :M] < 0)
        W[:, :M][went_negative] = 0

        # inhibitory columns (last M): weights must stay negative
        went_positive = mask[:, M:] & (W[:, M:] > 0)
        W[:, M:][went_positive] = 0

        # --- enforce E/I ratio: inh strength = 3x exc strength (identical to original) ---
        W[:M, M:] *= (-3 * np.mean(W[:M, :M]) / np.mean(W[:M, M:]))
        W[M:, M:] *= (-3 * np.mean(W[M:, :M]) / np.mean(W[M:, M:]))

        # enforce density: replace zeroed connections with new random ones
        amount_to_replace = np.sum(went_negative) + np.sum(went_positive)
        if amount_to_replace > 0:
            mask[:, :M][went_negative] = False
            mask[:, M:][went_positive] = False

            candidates = np.argwhere(~mask & no_self)
            selector = np.random.choice(len(candidates), size=amount_to_replace, replace=False)
            new_rows = candidates[selector, 0]
            new_cols = candidates[selector, 1]
            mask[new_rows, new_cols] = True
            W[new_rows, new_cols] = 0

        i += 1

    return W