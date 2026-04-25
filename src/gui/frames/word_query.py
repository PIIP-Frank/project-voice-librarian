import customtkinter
import winsound
from pathlib import Path
from tkinter import messagebox

from store.prompts import PromptSet, load_prompt_set, list_prompt_sets
from store.progress import UserProgress
from store.recordings import RecordingStore


class WordQueryFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler):
        super().__init__(parent, fg_color="transparent")
        self.handler = handler

        self._username: str = ""
        self._prompt_set: PromptSet | None = None
        self._progress: UserProgress | None = None
        self._recordings: RecordingStore | None = None
        self._sample_index: int = 0
        self._is_playing: bool = False

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        card = customtkinter.CTkFrame(self)
        card.grid(row=1, column=0, padx=30, pady=24, sticky="n")
        card.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            card, text="Word Query",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(20, 4))

        self._set_lbl = customtkinter.CTkLabel(
            card, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._set_lbl.grid(row=1, column=0, padx=30, pady=(0, 12))

        # ── Word display ─────────────────────────────────────────────────────
        word_panel = customtkinter.CTkFrame(card)
        word_panel.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")
        word_panel.grid_columnconfigure(1, weight=1)

        customtkinter.CTkButton(
            word_panel, text="←", width=40, command=self._prev_word
        ).grid(row=0, column=0, padx=(10, 6), pady=12)

        self._word_lbl = customtkinter.CTkLabel(
            word_panel, text="—",
            font=customtkinter.CTkFont(size=28, weight="bold"),
        )
        self._word_lbl.grid(row=0, column=1, padx=4, pady=12, sticky="ew")

        customtkinter.CTkButton(
            word_panel, text="→", width=40, command=self._next_word
        ).grid(row=0, column=2, padx=(6, 10), pady=12)

        self._word_meta_lbl = customtkinter.CTkLabel(
            word_panel, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._word_meta_lbl.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10))

        # ── Playback Manager ─────────────────────────────────────────────────
        pb = customtkinter.CTkFrame(card)
        pb.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")
        pb.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            pb, text="Playback Manager",
            font=customtkinter.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        sample_row = customtkinter.CTkFrame(pb, fg_color="transparent")
        sample_row.grid(row=1, column=0, padx=14, pady=(2, 6), sticky="ew")
        sample_row.grid_columnconfigure(1, weight=1)

        customtkinter.CTkButton(
            sample_row, text="◀", width=36, command=self._prev_sample
        ).grid(row=0, column=0, padx=(0, 8))

        self._sample_lbl = customtkinter.CTkLabel(
            sample_row, text="No samples",
            font=customtkinter.CTkFont(size=12, weight="bold"),
        )
        self._sample_lbl.grid(row=0, column=1, sticky="ew")

        customtkinter.CTkButton(
            sample_row, text="▶", width=36, command=self._next_sample
        ).grid(row=0, column=2, padx=(8, 0))

        self._length_lbl = customtkinter.CTkLabel(
            pb, text="Length: —", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._length_lbl.grid(row=2, column=0, padx=14, pady=(2, 0), sticky="w")

        self._meta_lbl = customtkinter.CTkLabel(
            pb, text="Sample Rate: —    Channels: —    Size: —",
            text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._meta_lbl.grid(row=3, column=0, padx=14, pady=(0, 0), sticky="w")

        self._file_lbl = customtkinter.CTkLabel(
            pb, text="File: —", text_color="gray",
            font=customtkinter.CTkFont(size=10),
        )
        self._file_lbl.grid(row=4, column=0, padx=14, pady=(0, 4), sticky="w")

        ctrl_row = customtkinter.CTkFrame(pb, fg_color="transparent")
        ctrl_row.grid(row=5, column=0, padx=14, pady=(6, 12))

        self._play_btn = customtkinter.CTkButton(
            ctrl_row, text="▶ Play", width=100, command=self._play
        )
        self._play_btn.grid(row=0, column=0, padx=(0, 6))

        self._stop_btn = customtkinter.CTkButton(
            ctrl_row, text="■ Stop", width=100,
            fg_color="gray30", hover_color="gray20", command=self._stop
        )
        self._stop_btn.grid(row=0, column=1, padx=6)

        self._delete_btn = customtkinter.CTkButton(
            ctrl_row, text="🗑 Delete", width=100,
            fg_color="#B33A3A", hover_color="#8C2A2A",
            command=self._delete_current_sample,
        )
        self._delete_btn.grid(row=0, column=2, padx=(6, 0))

        self._status_lbl = customtkinter.CTkLabel(
            card, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._status_lbl.grid(row=4, column=0, padx=20, pady=(0, 6))

        customtkinter.CTkButton(
            card, text="Back", width=120,
            fg_color="gray30", hover_color="gray20",
            command=self._back,
        ).grid(row=5, column=0, padx=20, pady=(4, 20))

    # ── Public API ───────────────────────────────────────────────────────────

    def set_user(self, username: str) -> None:
        self._username = username
        self._progress = UserProgress(username)
        self._recordings = RecordingStore(username)

        sets = list_prompt_sets()
        target = self._progress.prompt_set if self._progress.prompt_set in sets else (sets[0] if sets else None)

        if target is None:
            self._prompt_set = None
            self._set_lbl.configure(text="No prompt sets available in src/prompts/")
            self._word_lbl.configure(text="—")
            self._word_meta_lbl.configure(text="")
            self._refresh_playback()
            return

        self._prompt_set = load_prompt_set(target)
        self._progress.prompt_set = target
        self._set_lbl.configure(
            text=f"Prompt set: {target}  ·  {len(self._prompt_set)} word(s)"
        )
        self._sample_index = 0
        self._refresh_word()

    def refresh(self) -> None:
        """Re-read recordings from disk; call when re-entering the screen."""
        if self._username:
            self._refresh_word()

    # ── Word navigation ──────────────────────────────────────────────────────

    def _prev_word(self) -> None:
        if not self._prompt_set or not self._progress:
            return
        idx = max(0, self._progress.current_index - 1)
        if idx == self._progress.current_index:
            return
        self._stop()
        self._progress.current_index = idx
        self._sample_index = 0
        self._refresh_word()

    def _next_word(self) -> None:
        if not self._prompt_set or not self._progress:
            return
        idx = min(len(self._prompt_set) - 1, self._progress.current_index + 1)
        if idx == self._progress.current_index:
            return
        self._stop()
        self._progress.current_index = idx
        self._sample_index = 0
        self._refresh_word()

    def _refresh_word(self) -> None:
        if not self._prompt_set or not self._progress or not self._recordings:
            return
        idx = self._progress.current_index
        word = self._prompt_set.get(idx) or "—"
        total = len(self._prompt_set)
        recorded = self._recordings.sample_count(word)
        self._progress.set_sample_count(word, recorded)

        done_txt = "✓ Done" if recorded > 0 else "Not yet recorded"
        self._word_lbl.configure(text=word)
        self._word_meta_lbl.configure(
            text=f"Word {idx + 1} of {total}  ·  {recorded} sample(s)  ·  {done_txt}"
        )
        self._refresh_playback()

    # ── Sample navigation ────────────────────────────────────────────────────

    def _current_samples(self) -> list[Path]:
        if not self._prompt_set or not self._progress or not self._recordings:
            return []
        word = self._prompt_set.get(self._progress.current_index)
        if not word:
            return []
        return self._recordings.list_samples(word)

    def _prev_sample(self) -> None:
        samples = self._current_samples()
        if not samples or self._sample_index <= 0:
            return
        self._stop()
        self._sample_index -= 1
        self._refresh_playback()

    def _next_sample(self) -> None:
        samples = self._current_samples()
        if not samples or self._sample_index >= len(samples) - 1:
            return
        self._stop()
        self._sample_index += 1
        self._refresh_playback()

    def _refresh_playback(self) -> None:
        samples = self._current_samples()
        total = len(samples)
        if total == 0:
            self._sample_lbl.configure(text="No samples recorded")
            self._length_lbl.configure(text="Length: —")
            self._meta_lbl.configure(text="Sample Rate: —    Channels: —    Size: —")
            self._file_lbl.configure(text="File: —")
            self._play_btn.configure(state="disabled")
            self._delete_btn.configure(state="disabled")
            return

        self._sample_index = max(0, min(self._sample_index, total - 1))
        path = samples[self._sample_index]
        info = RecordingStore.clip_info(path)

        self._sample_lbl.configure(text=f"Sample {self._sample_index + 1} of {total}")

        length = info.get("length")
        self._length_lbl.configure(
            text=f"Length: {length:.2f} s" if length is not None else "Length: unknown"
        )

        rate = info.get("sample_rate")
        chans = info.get("channels")
        size = info.get("size_bytes")
        self._meta_lbl.configure(
            text=(
                f"Sample Rate: {rate} Hz" if rate else "Sample Rate: —"
            ) + "    " + (
                f"Channels: {chans}" if chans else "Channels: —"
            ) + "    " + (
                f"Size: {self._fmt_size(size)}" if size else "Size: —"
            )
        )

        self._file_lbl.configure(text=f"File: {path.name}")
        self._play_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    @staticmethod
    def _fmt_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        kb = n / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.1f} MB"

    # ── Playback ─────────────────────────────────────────────────────────────

    def _play(self) -> None:
        samples = self._current_samples()
        if not samples:
            return
        path = samples[self._sample_index]
        if not path.exists():
            self._status_lbl.configure(text="File not found.", text_color="#FF5555")
            return
        try:
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            self._is_playing = True
            self._status_lbl.configure(
                text=f"Playing: {path.name}", text_color="#4CAF50"
            )
        except RuntimeError as e:
            self._status_lbl.configure(text=f"Playback error: {e}", text_color="#FF5555")

    def _stop(self) -> None:
        if not self._is_playing:
            return
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass
        self._is_playing = False
        self._status_lbl.configure(text="Stopped.", text_color="gray")

    def _delete_current_sample(self) -> None:
        if not self._prompt_set or not self._progress or not self._recordings:
            return
        samples = self._current_samples()
        if not samples:
            return
        path = samples[self._sample_index]
        if not messagebox.askyesno(
            "Delete sample",
            f"Permanently delete {path.name}?",
            parent=self,
        ):
            return

        self._stop()
        if not self._recordings.delete_sample(path):
            self._status_lbl.configure(
                text=f"Could not delete {path.name}.", text_color="#FF5555"
            )
            return

        word = self._prompt_set.get(self._progress.current_index)
        if word:
            self._progress.set_sample_count(word, self._recordings.sample_count(word))
        if self._sample_index > 0:
            self._sample_index -= 1
        self._refresh_word()
        self._status_lbl.configure(
            text=f"Deleted {path.name}", text_color="#4CAF50"
        )

    def _back(self) -> None:
        self._stop()
        self.handler.show("main_menu")
