import re
import wave
from pathlib import Path

from .supabase_sync import upload_file_to_supabase

_RE_SAMPLE = re.compile(r"^(?P<word>.+)-sample(?P<num>\d+)\.wav$", re.IGNORECASE)
_ROOT = Path("data") / "recordings"


class SampleEntry:
    """Lightweight record describing one sample on disk."""

    __slots__ = ("user", "word", "number", "path")

    def __init__(self, user: str, word: str, number: int, path: Path):
        self.user = user
        self.word = word
        self.number = number
        self.path = path


class RecordingStore:
    """Locates and inspects recorded samples for a user.

    Files: data/recordings/<username>/<word>-sample<#>.wav
    """

    def __init__(self, username: str):
        self.username = username
        self.dir = Path("data") / "recordings" / username
        self.dir.mkdir(parents=True, exist_ok=True)

    def list_samples(self, word: str) -> list[Path]:
        pairs: list[tuple[int, Path]] = []
        for p in self.dir.glob("*.wav"):
            m = _RE_SAMPLE.match(p.name)
            if not m or m.group("word").lower() != word.lower():
                continue
            try:
                pairs.append((int(m.group("num")), p))
            except ValueError:
                continue
        pairs.sort(key=lambda t: t[0])
        return [p for _, p in pairs]

    def list_all_samples(self) -> list[SampleEntry]:
        """All samples on disk for this user, sorted by word then sample number."""
        out: list[SampleEntry] = []
        for p in self.dir.glob("*.wav"):
            m = _RE_SAMPLE.match(p.name)
            if not m:
                continue
            try:
                num = int(m.group("num"))
            except ValueError:
                continue
            out.append(SampleEntry(self.username, m.group("word"), num, p))
        out.sort(key=lambda e: (e.word.lower(), e.number))
        return out

    def words_recorded(self) -> list[str]:
        """Distinct words this user has at least one sample for."""
        seen: dict[str, str] = {}
        for entry in self.list_all_samples():
            key = entry.word.lower()
            if key not in seen:
                seen[key] = entry.word
        return sorted(seen.values(), key=str.lower)

    def sample_count(self, word: str) -> int:
        return len(self.list_samples(word))

    def delete_sample(self, path: Path) -> bool:
        """Remove a sample file owned by this user. Returns True if removed."""
        try:
            resolved = path.resolve()
            owner = self.dir.resolve()
        except OSError:
            return False
        if owner not in resolved.parents:
            return False
        if not resolved.exists():
            return False
        try:
            resolved.unlink()
            return True
        except OSError:
            return False

    def next_sample_number(self, word: str) -> int:
        existing = self.list_samples(word)
        if not existing:
            return 1
        m = _RE_SAMPLE.match(existing[-1].name)
        return int(m.group("num")) + 1 if m else len(existing) + 1

    def sample_path(self, word: str, sample_num: int) -> Path:
        return self.dir / f"{word}-sample{sample_num}.wav"

    def save_sample(
        self,
        word: str,
        pcm_bytes: bytes,
        sample_rate: int,
        channels: int = 1,
        sample_width: int = 2,
    ) -> Path:
        n = self.next_sample_number(word)
        path = self.sample_path(word, n)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(sample_width)
            w.setframerate(sample_rate)
            w.writeframes(pcm_bytes)
        return path

    def upload_sample(self, path: Path) -> bool:
        try:
            upload_file_to_supabase(path, self.username)
            return True
        except Exception:
            return False

    @staticmethod
    def list_users_with_samples() -> list[str]:
        """Usernames that have a recordings subdirectory on disk."""
        if not _ROOT.exists():
            return []
        return sorted(p.name for p in _ROOT.iterdir() if p.is_dir())

    @staticmethod
    def list_samples_for_word(word: str) -> list[SampleEntry]:
        """All samples for a given word, across every user."""
        if not _ROOT.exists():
            return []
        out: list[SampleEntry] = []
        target = word.lower()
        for user_dir in _ROOT.iterdir():
            if not user_dir.is_dir():
                continue
            for p in user_dir.glob("*.wav"):
                m = _RE_SAMPLE.match(p.name)
                if not m or m.group("word").lower() != target:
                    continue
                try:
                    num = int(m.group("num"))
                except ValueError:
                    continue
                out.append(SampleEntry(user_dir.name, m.group("word"), num, p))
        out.sort(key=lambda e: (e.user.lower(), e.number))
        return out

    @staticmethod
    def list_all_words() -> list[str]:
        """Distinct words that have at least one recorded sample anywhere."""
        if not _ROOT.exists():
            return []
        seen: dict[str, str] = {}
        for user_dir in _ROOT.iterdir():
            if not user_dir.is_dir():
                continue
            for p in user_dir.glob("*.wav"):
                m = _RE_SAMPLE.match(p.name)
                if not m:
                    continue
                key = m.group("word").lower()
                if key not in seen:
                    seen[key] = m.group("word")
        return sorted(seen.values(), key=str.lower)

    @staticmethod
    def clip_info(path: Path) -> dict:
        info: dict = {"path": str(path), "exists": path.exists()}
        if not path.exists():
            return info
        info["size_bytes"] = path.stat().st_size
        try:
            with wave.open(str(path), "rb") as wav:
                info["channels"] = wav.getnchannels()
                info["sample_rate"] = wav.getframerate()
                info["sample_width"] = wav.getsampwidth()
                info["frames"] = wav.getnframes()
                rate = wav.getframerate()
                if rate:
                    info["length"] = wav.getnframes() / float(rate)
        except wave.Error:
            pass
        return info
