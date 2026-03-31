import pandas as pd
import joblib
from features import extract_features

# Load data
df = pd.read_csv("hybrid_random_bits.csv")

print("Columns:", df.columns)

# Select correct column
if "final_bit" in df.columns:
    bits = df["final_bit"].tolist()
elif "bit" in df.columns:
    bits = df["bit"].tolist()
else:
    raise Exception("No valid bit column found!")

print("Total bits:", len(bits))

# Chunking
chunk_size = 1000
chunks = []

for i in range(0, len(bits), chunk_size):
    chunk = bits[i:i + chunk_size]
    if len(chunk) == chunk_size:
        chunks.append(chunk)

print("Total chunks:", len(chunks))

# Extract features
features_list = []
for chunk in chunks:
    features = extract_features(chunk)
    features_list.append(features)

# Load model
model = joblib.load("model.pkl")

# Must match training schema from dataset/model.
feature_names = ["entropy", "mean", "variance", "autocorr", "run_length"]
features_df = pd.DataFrame(features_list, columns=feature_names)

expected_feature_names = list(getattr(model, "feature_names_in_", feature_names))
missing_features = [c for c in expected_feature_names if c not in features_df.columns]
if missing_features:
    raise ValueError(f"Missing required feature columns for model: {missing_features}")

features_df = features_df[expected_feature_names]

print("Feature sample:\n", features_df.head())

predictions = model.predict(features_df)

print("Predictions:", predictions)

# Result summary
good = list(predictions).count("Good")
weak = list(predictions).count("Weak")

print("Good:", good)
print("Weak:", weak)

if good > weak:
    print("FINAL RESULT: GOOD RANDOMNESS ✅")
else:
    print("FINAL RESULT: WEAK RANDOMNESS ❌")