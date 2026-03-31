import numpy as np
from collections import Counter
import math

def extract_features(bits):
    bits = np.array(bits)

    # Shannon entropy
    count = Counter(bits)
    total = len(bits)
    entropy = 0

    for c in count.values():
        p = c / total
        entropy -= p * math.log2(p)

    mean = float(np.mean(bits))
    variance = float(np.var(bits))

    # Lag-1 autocorrelation; return 0 if undefined (constant sequence).
    x = bits[:-1]
    y = bits[1:]
    if np.std(x) == 0 or np.std(y) == 0:
        autocorr = 0.0
    else:
        autocorr = float(np.corrcoef(x, y)[0, 1])

    # Average run length.
    run_lengths = []
    current_run = 1
    for i in range(1, len(bits)):
        if bits[i] == bits[i - 1]:
            current_run += 1
        else:
            run_lengths.append(current_run)
            current_run = 1
    run_lengths.append(current_run)
    run_length = float(np.mean(run_lengths))

    return [entropy, mean, variance, autocorr, run_length]