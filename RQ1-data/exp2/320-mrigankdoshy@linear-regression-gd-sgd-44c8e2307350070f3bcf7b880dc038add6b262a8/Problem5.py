import math
import random
import numpy as np


def objective_function(data, y, w, delta):
    f = 0
    for j in range(0, 100):
        wx = (w[0] * data[j][0]) + (w[1] * data[j][1])
        if y[j] >= wx + delta:
            f += (y[j] - wx - delta) ** 2
        elif abs(y[j] - wx) < delta:
            f += 0
        elif y[j] <= wx - delta:
            f += (y[j] - wx + delta) ** 2
    return f / 100


def regularization(w, lam):
    return lam * ((w[0] ** 2) + (w[1] ** 2))


def bgd_l2(data, y, w, eta, delta, lam, num_iter):
    history_fw = []
    for j in range(0, num_iter):
        w0_gradient = 0
        w1_gradient = 0

        for i in range(0, 100):
            wx = (w[0] * data[i][0]) + (w[1] * data[i][1])
            if y[i] >= wx + delta:
                w0_gradient += -(2/100) * data[i][0] * (y[i] - wx - delta)
                w1_gradient += -(2/100) * (y[i] - wx - delta)
            elif abs(y[i] - wx) < delta:
                w0_gradient += 0
                w1_gradient += 0
            elif y[i] <= wx - delta:
                w0_gradient += -(2/100) * data[i][0] * (y[i] - wx + delta)
                w1_gradient += -(2/100) * (y[i] - wx + delta)

        w0_gradient += 2 * lam * w[0]
        w1_gradient += 2 * lam * w[1]
        w[0] -= (eta * w0_gradient)
        w[1] -= (eta * w1_gradient)

        history_fw.append(objective_function(data, y, w, delta)
                          + regularization(w, lam))
    new_w = [w[0], w[1]]
    return new_w, history_fw


def sgd_l2(data, y, w, eta, delta, lam, num_iter, i=-1):
    history_fw = []
    if (i == -1):
        for j in range(0, num_iter):
            i = random.randint(0, 99)
            w = sgd_calculate(data, y, w, eta, delta, i, j)
            history_fw.append(objective_function(data, y, w, delta)
                              + regularization(w, lam))
    else:
        w = sgd_calculate(data, y, w, eta, delta, i, 0)
        history_fw.append(objective_function(data, y, w, delta)
                          + regularization(w, lam))
    new_w = [w[0], w[1]]
    return new_w, history_fw


def sgd_calculate(data, y, w, eta, delta, i, j):
    w0_gradient = 0
    w1_gradient = 0

    wx = (w[0] * data[i][0]) + (w[1] * data[i][1])
    if y[i] >= wx + delta:
        w0_gradient += -2 * data[i][0] * (y[i] - wx - delta)
        w1_gradient += -2 * (y[i] - wx - delta)
    elif abs(y[i] - wx) < delta:
        w0_gradient += 0
        w1_gradient += 0
    elif y[i] <= wx - delta:
        w0_gradient += -2 * data[i][0] * (y[i] - wx + delta)
        w1_gradient += -2 * (y[i] - wx + delta)
    w0_gradient += 2 * lam * w[0]
    w1_gradient += 2 * lam * w[1]

    w[0] -= ((eta / math.sqrt(j+1)) * w0_gradient)
    w[1] -= ((eta / math.sqrt(j+1)) * w1_gradient)

    return w