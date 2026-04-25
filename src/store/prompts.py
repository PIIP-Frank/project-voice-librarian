import csv
import json
from pathlib import Path

_PROMPTS_DIR = Path("prompts")


class PromptSet:

    def __init__(self, name: str, words: list[str]):
        self.name = name
        self.words = words

    def __len__(self) -> int:
        return len(self.words)

    def get(self, index: int) -> str | None:
        if 0 <= index < len(self.words):
            return self.words[index]
        return None


def list_prompt_sets() -> list[str]:
    """Return the names (without extension) of prompt sets in src/prompts/."""
    if not _PROMPTS_DIR.exists():
        return []
    out: list[str] = []
    for p in sorted(_PROMPTS_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".csv", ".json"):
            out.append(p.stem)
    return out


def load_prompt_set(name: str) -> PromptSet:
    """Load a prompt set by name (without extension). CSV preferred over JSON."""
    csv_path = _PROMPTS_DIR / f"{name}.csv"
    json_path = _PROMPTS_DIR / f"{name}.json"

    if csv_path.exists():
        words = _load_csv(csv_path)
    elif json_path.exists():
        words = _load_json(json_path)
    else:
        raise FileNotFoundError(f"Prompt set '{name}' not found in {_PROMPTS_DIR}")

    return PromptSet(name, words)


def _load_csv(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    start = 1 if rows[0] and rows[0][0].strip().lower() == "word" else 0
    words: list[str] = []
    for row in rows[start:]:
        if not row:
            continue
        word = row[0].strip()
        if word:
            words.append(word)
    return words


def _load_json(path: Path) -> list[str]:
    if path.stat().st_size == 0:
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [str(w).strip() for w in data if str(w).strip()]
    if isinstance(data, dict) and "words" in data:
        return [str(w).strip() for w in data["words"] if str(w).strip()]
    return []
