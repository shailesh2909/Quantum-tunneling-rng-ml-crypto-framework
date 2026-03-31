"""
crypto_engine.py — AES‑256‑GCM encryption/decryption engine
═══════════════════════════════════════════════════════════════
Generates keys from hybrid random bits and provides
file‑level encrypt / decrypt operations.
"""

import os
import hashlib
import time
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ─── Key generation ─────────────────────────────────────────

def bits_to_key(bits: list[int]) -> bytes:
    """
    Derive a 256‑bit (32‑byte) AES key from a list of binary bits.

    Strategy:
      1. Pack bits into raw bytes.
      2. Run SHA‑256 over the raw bytes to produce exactly 32 bytes.
         This ensures uniform distribution even if source bits are
         slightly biased.
    """
    # pack bits → bytes  (pad last byte with zeros if needed)
    byte_list = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        # pad to 8 bits
        while len(chunk) < 8:
            chunk.append(0)
        byte_val = 0
        for bit in chunk:
            byte_val = (byte_val << 1) | (bit & 1)
        byte_list.append(byte_val)

    raw = bytes(byte_list)
    return hashlib.sha256(raw).digest()          # 32 bytes = 256 bits


def key_to_hex(key: bytes) -> str:
    """Return the key as a lowercase hex string."""
    return key.hex()


def hex_to_key(hex_str: str) -> bytes:
    """Parse a hex string back into a 32‑byte key. Raises ValueError on bad input."""
    key = bytes.fromhex(hex_str.strip())
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes (got {len(key)})")
    return key


# ─── File encryption (AES‑256‑GCM) ──────────────────────────

def encrypt_file(src_path: str, key: bytes) -> Tuple[str, float]:
    """
    Encrypt *src_path* using AES‑256‑GCM.

    Returns (dest_path, elapsed_seconds).

    File format of .enc file:
        [12‑byte nonce][ciphertext + 16‑byte GCM tag]
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)                        # 96‑bit nonce

    with open(src_path, "rb") as f:
        plaintext = f.read()

    t0 = time.perf_counter()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    elapsed = time.perf_counter() - t0

    dest_path = src_path + ".enc"
    with open(dest_path, "wb") as f:
        f.write(nonce + ciphertext)

    return dest_path, elapsed


def decrypt_file(enc_path: str, key: bytes) -> Tuple[str, float]:
    """
    Decrypt a .enc file written by *encrypt_file*.

    Returns (dest_path, elapsed_seconds).
    """
    with open(enc_path, "rb") as f:
        data = f.read()

    if len(data) < 12 + 16:
        raise ValueError("File too small to be a valid .enc file")

    nonce = data[:12]
    ciphertext = data[12:]

    aesgcm = AESGCM(key)
    t0 = time.perf_counter()
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    elapsed = time.perf_counter() - t0

    # remove .enc extension to restore original name
    if enc_path.endswith(".enc"):
        dest_path = enc_path[:-4]
    else:
        dest_path = enc_path + ".dec"

    # avoid overwriting the original if it still exists
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(dest_path)
        dest_path = f"{base}_decrypted{ext}"

    with open(dest_path, "wb") as f:
        f.write(plaintext)

    return dest_path, elapsed


def save_key_to_file(key: bytes, path: str) -> None:
    """Write the hex key to a plain‑text file."""
    with open(path, "w") as f:
        f.write(key_to_hex(key))


def load_key_from_file(path: str) -> bytes:
    """Read a hex key from a plain‑text file."""
    with open(path, "r") as f:
        return hex_to_key(f.read())
