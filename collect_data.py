import serial
import pandas as pd
import secrets

# Open serial port
ser = serial.Serial('COM19', 115200, timeout=1)

hardware_bits = []
random_bits = []
final_bits = []

print("Collecting data...")

# Skip garbage data
for _ in range(50):
    ser.readline()

while len(hardware_bits) < 10000:   # increase for better ML
    try:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

        if line in ['0', '1']:
            hw_bit = int(line)
            hardware_bits.append(hw_bit)

            # Secure random bit
            rand_bit = secrets.randbits(1)
            random_bits.append(rand_bit)

            # XOR
            final_bit = hw_bit ^ rand_bit
            final_bits.append(final_bit)

    except:
        continue

ser.close()

print("Collected:", len(final_bits))

# Save data
df = pd.DataFrame({
    "hardware_bit": hardware_bits,
    "random_bit": random_bits,
    "final_bit": final_bits
})

df.to_csv("hybrid_random_bits.csv", index=False)

print("Saved to hybrid_random_bits.csv")