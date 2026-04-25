import customtkinter
import winsound
from tkinter import messagebox

from store.progress import UserProgress
from store.recordings import RecordingStore, SampleEntry

_ALL = "All"


class ManageLibraryFrame(customtkinter.CTkFrame):
    """Browse every recorded sample, filter by user and/or word."""

    def __init__(self, parent, handler):
        super().__init__(parent, fg_color="transparent")
        self.handler = handler

        self._users: list[str] = []
        self._words: list[str] = []
        self._entries: list[SampleEntry] = []
        self._is_playing: bool = False

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        customtkinter.CTkLabel(
            self, text="Manage Library",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 4))

        # ── Filter row ───────────────────────────────────────────────────────
        filt = customtkinter.CTkFrame(self)
        filt.grid(row=1, column=0, padx=20, pady=(8, 8), sticky="ew")
        for c in (1, 3):
            filt.grid_columnconfigure(c, weight=1)

        customtkinter.CTkLabel(filt, text="User").grid(
            row=0, column=0, padx=(14, 6), pady=10, sticky="w"
        )
        self._user_var = customtkinter.StringVar(value=_ALL)
        self._user_menu = customtkinter.CTkOptionMenu(
            filt, values=[_ALL], variable=self._user_var,
            width=160, command=lambda _v: self._refresh_entries(),
        )
        self._user_menu.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")

        customtkinter.CTkLabel(filt, text="Word").grid(
            row=0, column=2, padx=(6, 6), pady=10, sticky="w"
        )
        self._word_var = customtkinter.StringVar(value=_ALL)
        self._word_menu = customtkinter.CTkOptionMenu(
            filt, values=[_ALL], variable=self._word_var,
            width=160, command=lambda _v: self._refresh_entries(),
        )
        self._word_menu.grid(row=0, column=3, padx=(0, 6), pady=10, sticky="ew")

        customtkinter.CTkButton(
            filt, text="↻", width=40, command=self.refresh,
        ).grid(row=0, column=4, padx=(6, 14), pady=10)

        # ── Sample list ──────────────────────────────────────────────────────
        self._list = customtkinter.CTkScrollableFrame(self, label_text="")
        self._list.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

        self._summary_lbl = customtkinter.CTkLabel(
            self, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._summary_lbl.grid(row=3, column=0, padx=20, pady=(0, 4))

        self._status_lbl = customtkinter.CTkLabel(
            self, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._status_lbl.grid(row=4, column=0, padx=20, pady=(0, 6))

        customtkinter.CTkButton(
            self, text="Back", width=120,
            fg_color="gray30", hover_color="gray20",
            command=self._back,
        ).grid(row=5, column=0, padx=20, pady=(4, 20))

    # ── Public API ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Re-scan disk for users and words, then refresh the list."""
        self._users = RecordingStore.list_users_with_samples()
        self._words = RecordingStore.list_all_words()

        prev_user = self._user_var.get()
        prev_word = self._word_var.get()

        user_values = [_ALL] + self._users
        word_values = [_ALL] + self._words
        self._user_menu.configure(values=user_values)
        self._word_menu.configure(values=word_values)

        if prev_user not in user_values:
            self._user_var.set(_ALL)
        if prev_word not in word_values:
            self._word_var.set(_ALL)

        self._refresh_entries()

    # ── Filtering ────────────────────────────────────────────────────────────

    def _refresh_entries(self) -> None:
        user = self._user_var.get()
        word = self._word_var.get()

        entries: list[SampleEntry] = []
        if word != _ALL:
            entries = RecordingStore.list_samples_for_word(word)
            if user != _ALL:
                entries = [e for e in entries if e.user == user]
        elif user != _ALL:
            entries = RecordingStore(user).list_all_samples()
        else:
            for u in self._users:
                entries.extend(RecordingStore(u).list_all_samples())

        entries.sort(key=lambda e: (e.user.lower(), e.word.lower(), e.number))
        self._entries = entries
        self._render_list()

    def _render_list(self) -> None:
        self._stop()
        for w in self._list.winfo_children():
            w.destroy()

        if not self._entries:
            customtkinter.CTkLabel(
                self._list, text="No samples match the current filters.",
                text_color="gray",
            ).grid(row=0, column=0, padx=12, pady=12, sticky="w")
            self._summary_lbl.configure(text="0 sample(s)")
            return

        for i, entry in enumerate(self._entries):
            self._render_row(i, entry)

        users = {e.user for e in self._entries}
        words = {e.word.lower() for e in self._entries}
        self._summary_lbl.configure(
            text=f"{len(self._entries)} sample(s)  ·  "
                 f"{len(users)} user(s)  ·  {len(words)} word(s)"
        )

    def _render_row(self, row: int, entry: SampleEntry) -> None:
        info = RecordingStore.clip_info(entry.path)
        length = info.get("length")
        size = info.get("size_bytes")

        wrapper = customtkinter.CTkFrame(self._list)
        wrapper.grid(row=row, column=0, padx=4, pady=4, sticky="ew")
        wrapper.grid_columnconfigure(1, weight=1)

        customtkinter.CTkButton(
            wrapper, text="▶", width=40,
            command=lambda p=entry.path: self._play(p),
        ).grid(row=0, column=0, rowspan=2, padx=(10, 12), pady=10)

        customtkinter.CTkLabel(
            wrapper,
            text=f"{entry.user}  ·  {entry.word}  ·  sample {entry.number}",
            font=customtkinter.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 10), pady=(8, 0), sticky="ew")

        meta_bits = []
        if length is not None:
            meta_bits.append(f"{length:.2f} s")
        if size:
            meta_bits.append(self._fmt_size(size))
        meta_bits.append(entry.path.name)
        customtkinter.CTkLabel(
            wrapper, text="   ·   ".join(meta_bits),
            text_color="gray", font=customtkinter.CTkFont(size=11),
            anchor="w",
        ).grid(row=1, column=1, padx=(0, 10), pady=(0, 8), sticky="ew")

        customtkinter.CTkButton(
            wrapper, text="🗑", width=40,
            fg_color="#B33A3A", hover_color="#8C2A2A",
            command=lambda e=entry: self._delete_entry(e),
        ).grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=10)

    # ── Playback ─────────────────────────────────────────────────────────────

    def _play(self, path) -> None:
        if not path.exists():
            self._set_status("File not found.", error=True)
            return
        try:
            winsound.PlaySound(
                str(path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            self._is_playing = True
            self._set_status(f"Playing: {path.name}", error=False)
        except RuntimeError as e:
            self._set_status(f"Playback error: {e}", error=True)

    def _stop(self) -> None:
        if not self._is_playing:
            return
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except RuntimeError:
            pass
        self._is_playing = False

    # ── Delete ───────────────────────────────────────────────────────────────

    def _delete_entry(self, entry: SampleEntry) -> None:
        if not messagebox.askyesno(
            "Delete sample",
            f"Permanently delete {entry.path.name} for user '{entry.user}'?",
            parent=self,
        ):
            return
        self._stop()
        store = RecordingStore(entry.user)
        if not store.delete_sample(entry.path):
            self._set_status(f"Could not delete {entry.path.name}.", error=True)
            return
        try:
            UserProgress(entry.user).set_sample_count(
                entry.word, store.sample_count(entry.word)
            )
        except OSError:
            pass
        self.refresh()
        self._set_status(f"Deleted {entry.path.name}", error=False)

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_size(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        kb = n / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.1f} MB"

    def _set_status(self, msg: str, *, error: bool) -> None:
        self._status_lbl.configure(
            text=msg,
            text_color="#FF5555" if error else "#4CAF50",
        )

    def _back(self) -> None:
        self._stop()
        self.handler.show("main_menu")
