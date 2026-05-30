import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from . import supabase_sync


class UserManifest:
    """Manages user accounts, roles, and preferred language."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self._data_dir = data_dir
        self._file_path = data_dir / "users.json"
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load user data from disk."""
        if self._file_path.exists():
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._data = {}
            self._save()

    def _save(self) -> None:
        """Save user data to disk."""
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Simple SHA-256 hash (use bcrypt in production)."""
        return hashlib.sha256(password.encode()).hexdigest()

    def ensure_defaults(self) -> bool:
        """
        Create default admin account if no users exist.
        Returns True if this is the first run (defaults were created).
        """
        first_run = len(self._data) == 0
        if first_run:
            self.create_user("admin", "admin123", "Chief Librarian", preferred_lang="en")
        return first_run

    def create_user(self, username: str, password: str, role: str, preferred_lang: str = "en") -> None:
        """
        Create a new user.
        :param username: Unique username
        :param password: Plain-text password (will be hashed)
        :param role: "Student Librarian" or "Chief Librarian"
        :param preferred_lang: Language code (e.g., "en", "ig", "yo", "ha", "tw", "pcm")
        """
        if username in self._data:
            raise ValueError(f"User '{username}' already exists")
        self._data[username] = {
            "password": self._hash_password(password),
            "role": role,
            "preferred_lang": preferred_lang
        }
        self._save()

    def user_exists(self, username: str) -> bool:
        return username in self._data

    def verify_password(self, username: str, password: str) -> bool:
        if username not in self._data:
            return False
        stored_hash = self._data[username]["password"]
        return stored_hash == self._hash_password(password)

    def get_password_hash(self, username: str) -> Optional[str]:
        return self._data.get(username, {}).get("password")

    def get_role(self, username: str) -> Optional[str]:
        return self._data.get(username, {}).get("role")

    def get_preferred_language(self, username: str) -> str:
        """Return preferred language code (default 'en')."""
        return self._data.get(username, {}).get("preferred_lang", "en")

    def set_preferred_language(self, username: str, lang_code: str) -> None:
        """Update user's preferred language."""
        if username not in self._data:
            raise ValueError(f"User '{username}' does not exist")
        self._data[username]["preferred_lang"] = lang_code
        self._save()

    def get_user_data(self, username: str) -> Optional[dict]:
        return self._data.get(username)

    def upsert_user(self, username: str, password_hash: str, role: str, preferred_lang: str = "en") -> None:
        self._data[username] = {
            "password": password_hash,
            "role": role,
            "preferred_lang": preferred_lang,
        }
        self._save()

    def sync_users(self) -> bool:
        try:
            cloud_users = supabase_sync.fetch_remote_users()
        except Exception:
            return False

        for row in cloud_users:
            username = row.get("username")
            if not username:
                continue
            password = row.get("password", "")
            role = row.get("role", "Student Librarian")
            preferred_lang = row.get("preferred_lang", "en")
            local = self._data.get(username)
            if local is None:
                if not password:
                    continue
                self._data[username] = {
                    "password": password,
                    "role": role,
                    "preferred_lang": preferred_lang,
                }
            else:
                if password:
                    local["password"] = password
                local["role"] = role
                local["preferred_lang"] = preferred_lang

        self._save()

        payload = []
        for username in self.list_users():
            data = self._data.get(username, {})
            password = data.get("password", "")
            payload.append({
                "username": username,
                "password": password,
                "role": data.get("role", "Student Librarian"),
                "preferred_lang": data.get("preferred_lang", "en"),
            })

        try:
            supabase_sync.upsert_users_to_cloud(payload)
        except Exception:
            return False

        return True

    def reset_password(self, username: str, new_password: str) -> None:
        if username not in self._data:
            raise ValueError(f"User '{username}' does not exist")
        self._data[username]["password"] = self._hash_password(new_password)
        self._save()

    def list_users(self) -> List[str]:
        """Return list of all usernames."""
        return list(self._data.keys())

    def delete_user(self, username: str) -> bool:
        """Delete a user (except the last admin)."""
        if username not in self._data:
            return False
        # Prevent deleting the only chief librarian
        if self._data[username]["role"] == "Chief Librarian" and len(self._data) == 1:
            return False
        del self._data[username]
        self._save()
        return True
