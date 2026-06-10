# encrypt.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()

def get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY", "")
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in .env")
    # Derive a proper 32-byte Fernet key from the hex string
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"dmv_notifier_salt",
        iterations=100000,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return Fernet(derived)

def encrypt(text: str) -> str:
    if not text:
        return ""
    f = get_fernet()
    return f.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    if not token:
        return ""
    f = get_fernet()
    return f.decrypt(token.encode()).decode()

if __name__ == "__main__":
    test = "A1234567"
    enc = encrypt(test)
    dec = decrypt(enc)
    print(f"Original:  {test}")
    print(f"Encrypted: {enc[:40]}...")
    print(f"Decrypted: {dec}")
    print("✓ Encryption working" if test == dec else "✗ Encryption failed")