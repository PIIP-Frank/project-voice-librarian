import json
import os
import hashlib
import binascii
from pathlib import Path
from datetime import datetime

_MANIFEST_PATH = Path("data") / "users" / "user_manifest.json"


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return (
        f"pbkdf2:sha256:260000"
        f":{binascii.hexlify(salt).decode()}"
        f":{binascii.hexlify(dk).decode()}"
    )


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, algo, iters, salt_hex, hash_hex = stored.split(":")
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, int(iters))
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False


class UserManifest:

    def __init__(self):
        self._data: dict = {"users": {}}
        self._load()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if _MANIFEST_PATH.exists():
            try:
                with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                if "users" not in self._data:
                    self._data["users"] = {}
            except (json.JSONDecodeError, KeyError):
                self._data = {"users": {}}
        else:
            self._data = {"users": {}}

    def save(self) -> None:
        _MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)

    # ── Queries ───────────────────────────────────────────────────────────────

    def user_exists(self, username: str) -> bool:
        return username in self._data["users"]

    def get_role(self, username: str) -> str:
        entry = self._data["users"].get(username)
        return entry["role"] if entry else "Student Librarian"

    def list_users(self) -> list:
        return list(self._data["users"].keys())

    def verify_password(self, username: str, password: str) -> bool:
        entry = self._data["users"].get(username)
        if not entry:
            return False
        return _verify_password(password, entry["password_hash"])

    # ── Mutations ─────────────────────────────────────────────────────────────

    def create_user(self, username: str, password: str, role: str) -> None:
        if self.user_exists(username):
            raise ValueError(f"Username '{username}' is already taken.")
        self._data["users"][username] = {
            "role": role,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "password_hash": _hash_password(password),
        }
        self._ensure_user_dir(username)
        self.save()

    def reset_password(self, username: str, new_password: str) -> None:
        if not self.user_exists(username):
            raise ValueError(f"User '{username}' not found.")
        self._data["users"][username]["password_hash"] = _hash_password(new_password)
        self.save()

    def ensure_defaults(self) -> bool:
        """Create a default admin account if no users exist. Returns True on first run."""
        if not self._data["users"]:
            self.create_user("admin", "admin123", "Chief Librarian")
            return True
        return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _ensure_user_dir(self, username: str) -> None:
        (Path("data") / "users" / username).mkdir(parents=True, exist_ok=True)
