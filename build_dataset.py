import pandas as pd
import numpy as np
from features import extract_features
import random

dataset = []

for _ in range(100):
    bits = [random.choice([0, 1, 1]) for _ in range(1000)]
    dataset.append(extract_features(bits) + ["Weak"])

for _ in range(100):
    bits = [random.randint(0, 1) for _ in range(1000)]
    dataset.append(extract_features(bits) + ["Good"])

df = pd.DataFrame(dataset, columns=[
    "entropy", "mean", "variance", "autocorr", "run_length", "label"
])

df.to_csv("dataset.csv", index=False)

print("Dataset ready")