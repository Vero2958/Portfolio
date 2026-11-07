import math
import random
import matplotlib.pyplot as plt

class LIFNeuron:
    def __init__(self, V_rest, random_activity, R, C):
        self.V_rest = V_rest
        self.V = V_rest
        self.random_activity = random_activity
        self.R = R
        self.C = C
        self.tau = self.R * self.C
        self.dt = 1
        self.alpha = math.exp(-self.dt / self.tau)
        self.spike_train = []
        self.ref_t = 0  # timer refractory period

    def update_V(self, input):  # assuming input is already a list containing at any given t the sum of sensory input current and other neuron's activity.
        input = [(i + self.random_activity) for i in input]
        for It in input:
            self.V = (self.V_rest
                      + (self.V - self.V_rest) * self.alpha
                      + self.R * It * (1 - self.alpha))
            if self.ref_t < 1:
                if self.V > -55:
                    self.spike()
                    self.ref_t = 0
                    self.ref_t += 15
                else:
                    self.spike_train.append(0)
                    if self.ref_t >= 1:
                        self.ref_t -= 1
            elif 1 <= self.ref_t < 13:
                if self.V > -20:
                    self.spike()
                    self.ref_t = 0
                    self.ref_t += 15
                else:
                    self.spike_train.append(0)
                    if self.ref_t >= 1:
                        self.ref_t -= 1
            elif 13 <= self.ref_t <= 15:
                if self.ref_t >= 1:
                    self.ref_t -= 1
                self.spike_train.append(0)

    def spike(self):
        self.V = 50
        self.V = self.V_rest
        self.spike_train.append(1)



Neuron1 = LIFNeuron(-70, 2, 5, 1)
Input = [20, 10, 5, 2, 9, -18, -10, -3, 25, 19, 19]
Input_2 = [70, 20, 10, -7, -10, 40, 27, -2, 0, 50, 15, 10, 7, 1, 0, -3, -2, -5, -10, -18, -10, -6, -2, 0, 0, 0, 0, 10, 10, 10, 20, 25, 30, 40, 0, 12, 7, 1, 3, 2, 0, -2, -7, -9, -16, -18, 90, -15, -19, -11, 160]
Neuron1.update_V(Input_2)
print(Neuron1.spike_train, len(Input_2), len(Neuron1.spike_train))
