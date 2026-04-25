import json
from pathlib import Path


class UserProgress:
    """Tracks which prompt words a user has recorded samples for.

    Stored at data/users/<username>/progress.json:
        {
            "prompt_set": "prompt-set-1",
            "current_index": 0,
            "words": {
                "hello": {"samples": 3, "completed": true}
            }
        }
    """

    def __init__(self, username: str):
        self.username = username
        self.path = Path("data") / "users" / username / "progress.json"
        self._data: dict = {"prompt_set": None, "current_index": 0, "words": {}}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        self._data.setdefault("prompt_set", None)
        self._data.setdefault("current_index", 0)
        self._data.setdefault("words", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4)

    @property
    def prompt_set(self) -> str | None:
        return self._data.get("prompt_set")

    @prompt_set.setter
    def prompt_set(self, name: str) -> None:
        if self._data.get("prompt_set") != name:
            self._data["prompt_set"] = name
            self._data["current_index"] = 0
        self.save()

    @property
    def current_index(self) -> int:
        return int(self._data.get("current_index", 0))

    @current_index.setter
    def current_index(self, index: int) -> None:
        self._data["current_index"] = max(0, int(index))
        self.save()

    def sample_count(self, word: str) -> int:
        return int(self._data["words"].get(word, {}).get("samples", 0))

    def is_done(self, word: str) -> bool:
        return bool(self._data["words"].get(word, {}).get("completed", False))

    def set_sample_count(self, word: str, count: int) -> None:
        entry = self._data["words"].setdefault(word, {"samples": 0, "completed": False})
        entry["samples"] = max(0, int(count))
        entry["completed"] = entry["samples"] > 0
        self.save()

    def increment(self, word: str) -> int:
        entry = self._data["words"].setdefault(word, {"samples": 0, "completed": False})
        entry["samples"] = int(entry.get("samples", 0)) + 1
        entry["completed"] = True
        self.save()
        return entry["samples"]

    def words_with_samples(self) -> dict:
        return dict(self._data["words"])
