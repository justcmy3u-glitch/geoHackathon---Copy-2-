import os
import hashlib
import json
from filelock import FileLock
from security.encryption import EncryptedCache

class CacheManager:
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        self.index_path = os.path.join(self.cache_dir, "_page_index.json")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.encrypted_cache = EncryptedCache()

    def get_hash(self, file_bytes: bytes) -> str:
        return hashlib.md5(file_bytes).hexdigest()

    def get(self, file_hash: str) -> dict:
        cache_path = os.path.join(self.cache_dir, f"{file_hash}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        legacy_cache_path = os.path.join(self.cache_dir, f"{file_hash}.enc")
        if os.path.exists(legacy_cache_path):
            return self.encrypted_cache.load(legacy_cache_path)
        return None

    def set(self, file_hash: str, data: dict):
        cache_path = os.path.join(self.cache_dir, f"{file_hash}.json")
        lock_path = cache_path + ".lock"
        with FileLock(lock_path, timeout=10):
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get_page_hash(self, page_signature: str) -> str:
        if not os.path.exists(self.index_path):
            return None
        with open(self.index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
        return index.get(page_signature)

    def set_page_hash(self, page_signature: str, file_hash: str):
        lock_path = self.index_path + ".lock"
        with FileLock(lock_path, timeout=10):
            if os.path.exists(self.index_path):
                with open(self.index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            else:
                index = {}
            index[page_signature] = file_hash
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, ensure_ascii=True, indent=2)
