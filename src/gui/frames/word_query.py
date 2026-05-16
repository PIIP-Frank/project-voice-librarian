import customtkinter
import pygame
from pathlib import Path
from tkinter import messagebox
from store.prompts import PromptSet, load_prompt_set, list_prompt_sets
from store.progress import UserProgress
from store.recordings import RecordingStore
from store.word_translations import WordTranslations, SUPPORTED_LANGUAGES

if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)


class WordQueryFrame(customtkinter.CTkFrame):
    """Dictionary-style word list with search, pagination and word detail view."""

    def __init__(self, parent, handler):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler

        self._username: str = ""
        self._prompt_set: PromptSet | None = None
        self._all_words: list[str] = []
        self._filtered_words: list[str] = []
        self._words_with_audio: set[str] = set()
        self._current_start_index: int = 0
        self._batch_size: int = 100
        self._is_loading: bool = False
        self._search_query: str = ""
        self._detail_window: "WordDetailWindow" | None = None

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(3, weight=0)

        header_frame = customtkinter.CTkFrame(self, fg_color="transparent", height=50)
        header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        self.back_btn = customtkinter.CTkButton(
            header_frame, text="← Back", width=60, font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self._back
        )
        self.back_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")

        customtkinter.CTkLabel(
            header_frame, text="📖 Word Library", font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=1, sticky="w")

        self._info_label = customtkinter.CTkLabel(
            header_frame, text="", text_color="gray", font=customtkinter.CTkFont(size=11), anchor="e"
        )
        self._info_label.grid(row=0, column=2, padx=10, sticky="e")

        search_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = customtkinter.CTkEntry(
            search_frame, placeholder_text="🔍 Search for a word...", font=customtkinter.CTkFont(size=13),
            height=40, corner_radius=20, border_color="#D0D5DC", fg_color="white", text_color="#1A1A1A"
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.clear_search_btn = customtkinter.CTkButton(
            search_frame, text="✖", width=40, height=40, font=customtkinter.CTkFont(size=14),
            fg_color="transparent", text_color="#9CA3AF", hover_color="#E0E5EA", corner_radius=20,
            command=self._clear_search
        )
        self.clear_search_btn.grid(row=0, column=1)
        self.clear_search_btn.grid_remove()

        self.search_entry.bind("<KeyRelease>", self._on_search)
        self.search_entry.bind("<Return>", self._on_search_submit)

        self._words_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self._words_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self._words_frame.grid_columnconfigure(0, weight=1)

        self._words_frame._parent_canvas.bind_all("<MouseWheel>", self._on_scroll, add="+")

        self._loading_label = customtkinter.CTkLabel(
            self._words_frame, text="Loading more words...", text_color="gray", font=customtkinter.CTkFont(size=11)
        )
        self._no_results_label = customtkinter.CTkLabel(
            self._words_frame, text="🔍 No words found matching your search",
            text_color="gray", font=customtkinter.CTkFont(size=14), anchor="center"
        )

        # Bottom navigation
        self.bottom_nav = customtkinter.CTkFrame(
            self, height=50, fg_color="#FFFFFF", corner_radius=0, border_width=1, border_color="#D0D5DC"
        )
        self.bottom_nav.grid(row=3, column=0, sticky="ew")
        self.bottom_nav.grid_propagate(False)
        for i in range(2):
            self.bottom_nav.grid_columnconfigure(i, weight=1)

        customtkinter.CTkButton(
            self.bottom_nav, text="🏠 Home", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=lambda: self.handler.show("main_menu")
        ).grid(row=0, column=0, padx=5, pady=8, sticky="ew")

        customtkinter.CTkButton(
            self.bottom_nav, text="← Back", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self._back
        ).grid(row=0, column=1, padx=5, pady=8, sticky="ew")

    # ---------- Search ----------
    def _on_search(self, event=None):
        self._search_query = self.search_entry.get().strip().lower()
        if self._search_query:
            self.clear_search_btn.grid()
        else:
            self.clear_search_btn.grid_remove()
        self._perform_search()

    def _on_search_submit(self, event=None):
        self._perform_search()

    def _perform_search(self):
        if not self._search_query:
            self._filtered_words = self._all_words.copy()
        else:
            self._filtered_words = [w for w in self._all_words if self._search_query in w.lower()]
        self._current_start_index = 0
        self._clear_word_list()
        if not self._filtered_words:
            self._no_results_label.grid(row=0, column=0, padx=20, pady=40, sticky="ew")
            self._info_label.configure(text=f"0 results for '{self._search_query}'")
        else:
            self._no_results_label.grid_remove()
            self._load_more_words()
            total = len(self._filtered_words)
            matched_audio = sum(1 for w in self._filtered_words if w in self._words_with_audio)
            self._info_label.configure(text=f"{total} results for '{self._search_query}' | {matched_audio} have audio")

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._search_query = ""
        self.clear_search_btn.grid_remove()
        self._perform_search()

    # ---------- Word list ----------
    def _load_more_words(self):
        if self._is_loading:
            return
        end = self._current_start_index + self._batch_size
        if self._current_start_index >= len(self._filtered_words):
            return
        self._is_loading = True
        self._loading_label.grid_forget()
        for w in self._filtered_words[self._current_start_index:end]:
            self._add_word_button(w)
        self._current_start_index = end
        if self._current_start_index < len(self._filtered_words):
            self._loading_label.grid(row=len(self._words_frame.winfo_children()), column=0, padx=10, pady=10, sticky="ew")
        self._is_loading = False

    def _add_word_button(self, word: str):
        has_audio = word in self._words_with_audio
        frame = customtkinter.CTkFrame(self._words_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        btn = customtkinter.CTkButton(
            frame, text=f"🔊 {word}" if has_audio else f"📄 {word}", font=customtkinter.CTkFont(size=13),
            fg_color="#2A6BAA" if has_audio else "#9CA3AF",
            hover_color="#3A7BBA" if has_audio else "#B0B5BC",
            anchor="w", height=40, corner_radius=8,
            command=lambda w=word: self._open_word_detail(w)
        )
        btn.grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        frame.button = btn
        frame.word = word
        frame.grid(row=len(self._words_frame.winfo_children()), column=0, padx=10, pady=2, sticky="ew")

    def _clear_word_list(self):
        for w in self._words_frame.winfo_children():
            if w not in (self._loading_label, self._no_results_label):
                w.destroy()
        self._loading_label.grid_forget()
        self._no_results_label.grid_remove()

    def _on_scroll(self, event):
        canvas = self._words_frame._parent_canvas
        if canvas.yview()[1] >= 0.95:
            self._load_more_words()

    # ---------- Data ----------
    def set_user(self, username: str):
        self._username = username
        self._progress = UserProgress(username)
        self._recordings = RecordingStore(username)
        sets = list_prompt_sets()
        target = self._progress.prompt_set if self._progress.prompt_set in sets else (sets[0] if sets else None)
        if target is None:
            self._info_label.configure(text="No prompt sets available")
            return
        self._prompt_set = load_prompt_set(target)
        self._progress.prompt_set = target
        self._all_words = sorted([w for w in self._prompt_set.words if w])
        self._refresh_audio_status()
        self._search_query = ""
        self.search_entry.delete(0, "end")
        self.clear_search_btn.grid_remove()
        self._filtered_words = self._all_words.copy()
        self._current_start_index = 0
        self._clear_word_list()
        self._load_more_words()
        self._info_label.configure(text=f"{len(self._all_words)} words total | {len(self._words_with_audio)} have audio")

    def refresh(self):
        if self._username:
            self._refresh_audio_status()
            self._refresh_word_list_colors()

    def _refresh_audio_status(self):
        if not self._recordings:
            return
        self._words_with_audio.clear()
        for w in self._all_words:
            if self._recordings.sample_count(w) > 0:
                self._words_with_audio.add(w)

    def _refresh_word_list_colors(self):
        for widget in self._words_frame.winfo_children():
            if widget not in (self._loading_label, self._no_results_label) and hasattr(widget, 'button'):
                word = widget.word
                has_audio = word in self._words_with_audio
                widget.button.configure(
                    text=f"🔊 {word}" if has_audio else f"📄 {word}",
                    fg_color="#2A6BAA" if has_audio else "#9CA3AF",
                    hover_color="#3A7BBA" if has_audio else "#B0B5BC"
                )
        total = len(self._filtered_words) if self._search_query else len(self._all_words)
        matched = sum(1 for w in self._filtered_words if w in self._words_with_audio)
        if self._search_query:
            self._info_label.configure(text=f"{total} results for '{self._search_query}' | {matched} have audio")
        else:
            self._info_label.configure(text=f"{total} words total | {matched} have audio")

    def _open_word_detail(self, word: str):
        if self._detail_window and self._detail_window.winfo_exists():
            self._detail_window.destroy()
        self._detail_window = WordDetailWindow(self, word, self._recordings, self._refresh_audio_status_callback)

    def _refresh_audio_status_callback(self):
        self._refresh_audio_status()
        self._refresh_word_list_colors()

    def _back(self):
        if self._detail_window:
            self._detail_window.destroy()
        self.handler.show("main_menu")


class WordDetailWindow(customtkinter.CTkToplevel):
    """Full word detail window with play button and translation editor."""

    def __init__(self, parent, word: str, recordings: RecordingStore, refresh_callback):
        super().__init__(parent)
        self.word = word
        self.recordings = recordings
        self.refresh_callback = refresh_callback
        self._is_playing = False
        self._current_sample_index = 0
        self._samples: list[Path] = []
        self._translations = WordTranslations()
        self._edit_mode = False

        self.title(f"🔊 {word}")
        self.geometry("500x600")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color="#F0F4F8")

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        self._build()
        self._refresh_samples()
        self._show_view_mode()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        self.word_label = customtkinter.CTkLabel(
            header, text=self.word, font=customtkinter.CTkFont(size=32, weight="bold"),
            text_color="#1A1A1A", anchor="center"
        )
        self.word_label.grid(row=0, column=0)

        self.status_label = customtkinter.CTkLabel(self, text="", font=customtkinter.CTkFont(size=13), anchor="center")
        self.status_label.grid(row=1, column=0, padx=30, pady=(0, 15), sticky="n")

        self.play_btn = customtkinter.CTkButton(
            self, text="▶ PLAY", width=160, height=50,
            font=customtkinter.CTkFont(size=16, weight="bold"),
            command=self._play, corner_radius=12
        )
        self.play_btn.grid(row=2, column=0, pady=(0, 10))

        self.sample_info = customtkinter.CTkLabel(self, text="", text_color="gray", font=customtkinter.CTkFont(size=11))
        self.sample_info.grid(row=3, column=0, pady=(0, 15))

        self.trans_label = customtkinter.CTkLabel(self, text="📖 Translations", font=customtkinter.CTkFont(size=14, weight="bold"))
        self.trans_label.grid(row=4, column=0, padx=30, pady=(5, 5), sticky="w")

        self.trans_frame = customtkinter.CTkScrollableFrame(self, height=250, fg_color="white", border_width=1, border_color="#D0D5DC")
        self.trans_frame.grid(row=5, column=0, padx=30, pady=(0, 10), sticky="nsew")
        self.trans_frame.grid_columnconfigure(1, weight=1)

        btn_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, pady=(0, 20))
        self.edit_btn = customtkinter.CTkButton(btn_frame, text="✏️ Edit Translations", command=self._enter_edit_mode)
        self.edit_btn.pack(side="left", padx=5)

        self.save_btn = customtkinter.CTkButton(btn_frame, text="💾 Save", fg_color="#2A8C2A", command=self._save_translations)
        self.save_btn.pack(side="left", padx=5)
        self.save_btn.pack_forget()

        self.cancel_btn = customtkinter.CTkButton(btn_frame, text="Cancel", fg_color="gray", command=self._show_view_mode)
        self.cancel_btn.pack(side="left", padx=5)
        self.cancel_btn.pack_forget()

        close_btn = customtkinter.CTkButton(btn_frame, text="Close", fg_color="#9CA3AF", command=self.destroy)
        close_btn.pack(side="left", padx=5)

        self._update_ui_state()

    def _show_view_mode(self):
        self._edit_mode = False
        self.edit_btn.pack(side="left", padx=5)
        self.save_btn.pack_forget()
        self.cancel_btn.pack_forget()
        self._populate_translations_view()
        self.trans_frame.configure(fg_color="white", border_width=1)

    def _enter_edit_mode(self):
        self._edit_mode = True
        self.edit_btn.pack_forget()
        self.save_btn.pack(side="left", padx=5)
        self.cancel_btn.pack(side="left", padx=5)
        self._populate_translations_edit()
        self.trans_frame.configure(fg_color="white", border_width=1)

    def _populate_translations_view(self):
        for w in self.trans_frame.winfo_children():
            w.destroy()
        word_data = self._translations.get_word(self.word) or {}
        row = 0
        for code, name in SUPPORTED_LANGUAGES.items():
            translated = word_data.get(code, "—")
            customtkinter.CTkLabel(self.trans_frame, text=f"{name}:", anchor="e", width=140).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            customtkinter.CTkLabel(self.trans_frame, text=translated, anchor="w").grid(row=row, column=1, padx=5, pady=5, sticky="w")
            row += 1

    def _populate_translations_edit(self):
        for w in self.trans_frame.winfo_children():
            w.destroy()
        self.entry_vars = {}
        word_data = self._translations.get_word(self.word) or {}
        row = 0
        for code, name in SUPPORTED_LANGUAGES.items():
            current = word_data.get(code, "")
            var = customtkinter.StringVar(value=current)
            self.entry_vars[code] = var
            customtkinter.CTkLabel(self.trans_frame, text=f"{name}:", anchor="e", width=140).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            entry = customtkinter.CTkEntry(self.trans_frame, textvariable=var, width=200)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
            row += 1

    def _save_translations(self):
        for code, var in self.entry_vars.items():
            new_text = var.get().strip()
            if new_text:
                self._translations.set_translation(self.word, code, new_text)
        messagebox.showinfo("Saved", f"Translations for '{self.word}' saved.")
        self._show_view_mode()
        if self.refresh_callback:
            self.refresh_callback()

    def _refresh_samples(self):
        self._samples = self.recordings.list_samples(self.word)
        self._samples.sort(key=lambda p: p.stem)
        self._current_sample_index = 0 if self._samples else -1

    def _update_ui_state(self):
        self._refresh_samples()
        if not self._samples:
            self.status_label.configure(text="⚠️ This word has not been voiced", text_color="#F59E0B")
            self.play_btn.configure(state="disabled", fg_color="#9CA3AF", text="▶ PLAY")
            self.sample_info.configure(text="No recordings available")
        else:
            count = len(self._samples)
            self.status_label.configure(text=f"✅ This word has been voiced ({count} sample{'s' if count > 1 else ''})", text_color="#10B981")
            self.play_btn.configure(state="normal", fg_color="#2A6BAA", text="▶ PLAY")
            if count > 1:
                self.sample_info.configure(text=f"Sample {self._current_sample_index + 1} of {count}")
            else:
                self.sample_info.configure(text="")

    # ---------- Playback with automatic reset ----------
    def _play(self):
        if not self._samples:
            self._update_ui_state()
            return
        if self._current_sample_index >= len(self._samples):
            self._current_sample_index = 0
        path = self._samples[self._current_sample_index]
        if not path.exists():
            self.status_label.configure(text=f"File not found: {path.name}", text_color="#EF4444")
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(path.absolute()))
            pygame.mixer.music.play()
            self.play_btn.configure(text="▶ PLAYING...", state="disabled")
            self._check_playback_finished()
        except Exception as e:
            self.status_label.configure(text=f"Playback error: {e}", text_color="#EF4444")

    def _check_playback_finished(self):
        if not pygame.mixer.music.get_busy():
            self.play_btn.configure(text="▶ PLAY", state="normal")
            if len(self._samples) > 1:
                self._current_sample_index = (self._current_sample_index + 1) % len(self._samples)
                self.sample_info.configure(text=f"Sample {self._current_sample_index + 1} of {len(self._samples)}")
        else:
            self.after(200, self._check_playback_finished)

    def destroy(self):
        try:
            pygame.mixer.music.stop()
        except:
            pass
        if self.refresh_callback:
            self.refresh_callback()
        super().destroy()
