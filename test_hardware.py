import joblib
from features import extract_features

model = joblib.load("model.pkl")

bits = [1,0,1,1,0,1,0,1,1,0] * 100   

features = extract_features(bits)

prediction = model.predict([features])

print("Randomness Quality:", prediction[0])