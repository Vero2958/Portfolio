import math
import random
import matplotlib.pyplot as plt


class LIFNeuron:
    def __init__(self, V_rest, random_activity, R, C):
        self.V_rest = V_rest
        self.V = random.uniform(V_rest, -55)
        self.random_activity = random_activity
        self.R, self.C = R, C
        self.tau = R * C
        self.dt = 1
        self.alpha = math.exp(-self.dt / self.tau)
        self.spike_train = []
        self.ref_t = 0

    def update_single_step(self, synaptic_input):
        membrane_noise = random.uniform(-1.5, 1.5)
        total_I = synaptic_input + self.random_activity + membrane_noise

        if self.ref_t <= 0:
            self.V = (self.V_rest + (self.V - self.V_rest) * self.alpha
                      + self.R * total_I * (1 - self.alpha))

            if self.V > -55:
                self.spike_train.append(1)
                self.V = self.V_rest
                self.ref_t = random.randint(10, 20)
                return 1
        else:
            self.ref_t -= 1
            self.V = self.V_rest

        self.spike_train.append(0)
        return 0


#NETWORK:
N = 40
T = 600
W = [[random.uniform(2, 35) if i != j else 0 for j in range(N)] for i in range(N)]
network = [LIFNeuron(V_rest=-70, random_activity=8, R=5, C=1) for _ in range(N)]

#SIMULATION:
for t in range(T):
    prev_spikes = [n.spike_train[-1] if t > 0 else 0 for n in network]
    for i in range(N):
        syn_in = sum(W[i][j] * prev_spikes[j] for j in range(N))
        network[i].update_single_step(syn_in)

#RASTER PLOT:
plt.figure(figsize=(10, 6))
for i in range(N):
    spikes = [t for t, val in enumerate(network[i].spike_train) if val == 1]
    plt.scatter(spikes, [i] * len(spikes), s=4, c='black', marker='o')

plt.title("Raster Plot: Activity")
plt.xlabel("Time (ms)")
plt.ylabel("Neuron ID")
plt.show()




