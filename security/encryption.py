import os
import json
from cryptography.fernet import Fernet

class EncryptedCache:
    def __init__(self, key_path: str = "./secrets/cache.key"):
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        if not os.path.exists(key_path):
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            os.chmod(key_path, 0o600)
            
        with open(key_path, "rb") as f:
            self.fernet = Fernet(f.read())
    
    def save(self, path: str, data: dict):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        encrypted = self.fernet.encrypt(json.dumps(data).encode('utf-8'))
        with open(path, "wb") as f:
            f.write(encrypted)
    
    def load(self, path: str) -> dict:
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            encrypted = f.read()
        return json.loads(self.fernet.decrypt(encrypted).decode('utf-8'))
