# crypto_utils.py
from cryptography.fernet import Fernet
import os

# Ideally store this key securely in environment variable or a vault
FERNET_SECRET_KEY = os.getenv("FERNET_SECRET_KEY")

if not FERNET_SECRET_KEY:
    raise Exception("Please set FERNET_SECRET_KEY in your environment.")

fernet = Fernet(FERNET_SECRET_KEY.encode())

class CryptoUtility:
    def encrypt(self, data: str) -> str:
        return fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return fernet.decrypt(token.encode()).decode()

def get_crypto():
    return CryptoUtility()
