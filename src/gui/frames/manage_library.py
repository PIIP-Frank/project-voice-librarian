import customtkinter
import pygame
from pathlib import Path
from tkinter import messagebox
from store.prompts import list_prompt_sets, load_prompt_set
from store.progress import UserProgress
from store.recordings import RecordingStore
from store.word_translations import WordTranslations, SUPPORTED_LANGUAGES

if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)


class ManageLibraryFrame(customtkinter.CTkFrame):
    def __init__(self, parent, handler):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self._all_words: list[str] = []
        self._voiced_words: set[str] = set()
        self._filtered_words: list[str] = []
        self._current_filter = "ALL"
        self._current_start_index = 0
        self._batch_size = 100
        self._is_loading = False
        self._detail_window = None
        self._translations = WordTranslations()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(3, weight=0)

        # Header
        header = customtkinter.CTkFrame(self, fg_color="transparent", height=50)
        header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=0)

        customtkinter.CTkButton(
            header, text="← Back", width=60, font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self._back
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")

        customtkinter.CTkLabel(
            header, text="📊 Manage Library (Admin)", font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=1, sticky="w")

        self._info_label = customtkinter.CTkLabel(
            header, text="", text_color="gray", font=customtkinter.CTkFont(size=12), anchor="e"
        )
        self._info_label.grid(row=0, column=2, padx=10, sticky="e")

        # Filter buttons
        filter_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        for i, (label, fid) in enumerate([("📚 ALL", "ALL"), ("✅ VOICED", "VOICED"), ("❌ UNVOICED", "UNVOICED")]):
            btn = customtkinter.CTkButton(
                filter_frame, text=label, width=100, height=35,
                fg_color="#2A6BAA" if fid == "ALL" else "#6B7280",
                command=lambda f=fid: self._set_filter(f)
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
            setattr(self, f"_filter_{fid.lower()}_btn", btn)

        # Word list (with play button on each row)
        self._words_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self._words_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self._words_frame.grid_columnconfigure(0, weight=1)
        self._words_frame._parent_canvas.bind_all("<MouseWheel>", self._on_scroll, add="+")

        self._loading_label = customtkinter.CTkLabel(
            self._words_frame, text="Loading more words...", text_color="gray", font=customtkinter.CTkFont(size=11)
        )
        self._no_results_label = customtkinter.CTkLabel(
            self._words_frame, text="No words match the filter", text_color="gray",
            font=customtkinter.CTkFont(size=14), anchor="center"
        )

        # Bottom navigation
        bottom = customtkinter.CTkFrame(self, height=50, fg_color="#FFFFFF", corner_radius=0,
                                        border_width=1, border_color="#D0D5DC")
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.grid_propagate(False)
        for i in range(2):
            bottom.grid_columnconfigure(i, weight=1)

        customtkinter.CTkButton(
            bottom, text="🏠 Home", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=lambda: self.handler.show("main_menu")
        ).grid(row=0, column=0, padx=5, pady=8, sticky="ew")

        customtkinter.CTkButton(
            bottom, text="← Back", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self._back
        ).grid(row=0, column=1, padx=5, pady=8, sticky="ew")

    def refresh(self):
        # Collect all unique words from all prompt sets
        all_sets = list_prompt_sets()
        word_set = set()
        for sname in all_sets:
            ps = load_prompt_set(sname)
            word_set.update(ps.words)
        self._all_words = sorted(word_set)

        # Find which words have any recording (from any user)
        self._voiced_words.clear()
        users = RecordingStore.list_users_with_samples()
        for user in users:
            store = RecordingStore(user)
            for w in self._all_words:
                if store.sample_count(w) > 0:
                    self._voiced_words.add(w)
        self._apply_filter()

    def _set_filter(self, filter_id):
        self._current_filter = filter_id
        for fid in ("ALL", "VOICED", "UNVOICED"):
            btn = getattr(self, f"_filter_{fid.lower()}_btn", None)
            if btn:
                btn.configure(fg_color="#2A6BAA" if fid == self._current_filter else "#6B7280")
        self._apply_filter()

    def _apply_filter(self):
        if self._current_filter == "ALL":
            self._filtered_words = self._all_words.copy()
        elif self._current_filter == "VOICED":
            self._filtered_words = [w for w in self._all_words if w in self._voiced_words]
        else:  # UNVOICED
            self._filtered_words = [w for w in self._all_words if w not in self._voiced_words]

        self._current_start_index = 0
        self._clear_word_list()
        if not self._filtered_words:
            self._no_results_label.grid(row=0, column=0, padx=20, pady=40, sticky="ew")
            self._info_label.configure(text="0 words")
        else:
            self._no_results_label.grid_remove()
            self._load_more_words()
            self._update_info_label()

    def _update_info_label(self):
        total = len(self._filtered_words)
        voiced_in = sum(1 for w in self._filtered_words if w in self._voiced_words)
        self._info_label.configure(text=f"{total} words | {voiced_in} voiced")

    def _load_more_words(self):
        if self._is_loading:
            return
        end = self._current_start_index + self._batch_size
        if self._current_start_index >= len(self._filtered_words):
            return
        self._is_loading = True
        self._loading_label.grid_forget()
        for w in self._filtered_words[self._current_start_index:end]:
            self._add_word_row(w)
        self._current_start_index = end
        if self._current_start_index < len(self._filtered_words):
            self._loading_label.grid(row=len(self._words_frame.winfo_children()), column=0, padx=10, pady=10, sticky="ew")
        self._is_loading = False

    def _add_word_row(self, word: str):
        has_audio = word in self._voiced_words
        row_frame = customtkinter.CTkFrame(self._words_frame, fg_color="transparent")
        row_frame.grid_columnconfigure(1, weight=1)
        row_frame.grid(sticky="ew", padx=5, pady=2)

        # Play button (if audio exists)
        if has_audio:
            play_btn = customtkinter.CTkButton(
                row_frame, text="▶", width=40, height=40,
                fg_color="#2A6BAA", hover_color="#3A7BBA",
                command=lambda w=word: self._play_sample(w)
            )
            play_btn.grid(row=0, column=0, padx=(5, 5))
        else:
            play_btn = customtkinter.CTkFrame(row_frame, width=40, height=40, fg_color="transparent")
            play_btn.grid(row=0, column=0, padx=(5, 5))

        word_btn = customtkinter.CTkButton(
            row_frame, text=f"🔊 {word}" if has_audio else f"📄 {word}", font=customtkinter.CTkFont(size=13),
            fg_color="#2A6BAA" if has_audio else "#9CA3AF",
            hover_color="#3A7BBA" if has_audio else "#B0B5BC",
            anchor="w", height=40,
            command=lambda w=word: self._open_word_admin(w)
        )
        word_btn.grid(row=0, column=1, padx=5, sticky="ew")

        row_frame.play_btn = play_btn
        row_frame.word = word
        row_frame.has_audio = has_audio

    def _play_sample(self, word: str):
        users = RecordingStore.list_users_with_samples()
        for user in users:
            store = RecordingStore(user)
            samples = store.list_samples(word)
            if samples:
                path = samples[0]
                if path.exists():
                    try:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(str(path.absolute()))
                        pygame.mixer.music.play()
                        # Since we don't have a single button reference here, we just play.
                        # No need to reset button because we don't have a "PLAYING" state in list.
                    except Exception as e:
                        messagebox.showerror("Playback error", str(e))
                return
        messagebox.showinfo("No audio", f"No audio recordings found for '{word}'.")

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

    def _open_word_admin(self, word: str):
        if self._detail_window and self._detail_window.winfo_exists():
            self._detail_window.destroy()
        self._detail_window = WordAdminWindow(self, word, self._translations, self._voiced_words, self.refresh)

    def _back(self):
        self.handler.show("main_menu")


class WordAdminWindow(customtkinter.CTkToplevel):
    def __init__(self, parent, word: str, translations: WordTranslations, voiced_words: set, refresh_callback):
        super().__init__(parent)
        self.word = word
        self.translations = translations
        self.voiced_words = voiced_words
        self.refresh_callback = refresh_callback
        self._samples = []  # not used for playing; we'll fetch dynamically

        self.title(f"✏️ Admin: {word}")
        self.geometry("500x600")
        self.resizable(False, False)
        self.grab_set()
        self.configure(fg_color="#F0F4F8")

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        self._build()
        self._load_translations()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=30, pady=(30, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(header, text=self.word, font=customtkinter.CTkFont(size=32, weight="bold"),
                               text_color="#1A1A1A").grid(row=0, column=0)

        has_audio = self.word in self.voiced_words
        status = "✅ Has audio recordings" if has_audio else "❌ No audio recordings"
        self.status_label = customtkinter.CTkLabel(self, text=status, font=customtkinter.CTkFont(size=13),
                                                   text_color="#10B981" if has_audio else "#F59E0B")
        self.status_label.grid(row=1, column=0, pady=(0, 15))

        # Play button (only if audio exists)
        if has_audio:
            self.play_btn = customtkinter.CTkButton(
                self, text="▶ Play Sample", width=150, height=40,
                fg_color="#2A6BAA", command=self._play_sample
            )
            self.play_btn.grid(row=2, column=0, pady=(0, 10))
        else:
            self.play_btn = None

        # Translations editor
        self.trans_frame = customtkinter.CTkScrollableFrame(self, height=280, label_text="Edit Translations",
                                                            fg_color="white", border_width=1)
        self.trans_frame.grid(row=3, column=0, padx=30, pady=10, sticky="nsew")
        self.trans_frame.grid_columnconfigure(1, weight=1)
        self.entry_vars = {}

        # Delete buttons
        btn_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=(10, 10))
        self.del_audio_btn = customtkinter.CTkButton(
            btn_frame, text="🗑 Delete Audio Only", fg_color="#D97706", hover_color="#B45309",
            command=self._delete_audio_only
        )
        self.del_audio_btn.pack(side="left", padx=5)
        self.del_word_btn = customtkinter.CTkButton(
            btn_frame, text="🗑 Delete Word & Audio", fg_color="#B33A3A", hover_color="#8C2A2A",
            command=self._delete_word_and_audio
        )
        self.del_word_btn.pack(side="left", padx=5)

        # Save & Close
        action_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=5, column=0, pady=(0, 20))
        customtkinter.CTkButton(action_frame, text="Save Translations", command=self._save_translations).pack(side="left", padx=5)
        customtkinter.CTkButton(action_frame, text="Close", command=self.destroy).pack(side="left", padx=5)

    def _load_translations(self):
        for w in self.trans_frame.winfo_children():
            w.destroy()
        self.entry_vars.clear()
        word_data = self.translations.get_word(self.word) or {}
        row = 0
        for code, name in SUPPORTED_LANGUAGES.items():
            current = word_data.get(code, "")
            var = customtkinter.StringVar(value=current)
            self.entry_vars[code] = var
            customtkinter.CTkLabel(self.trans_frame, text=f"{name}:", anchor="e", width=140).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            entry = customtkinter.CTkEntry(self.trans_frame, textvariable=var, width=200)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
            row += 1

    # ---------- Playback with reset ----------
    def _play_sample(self):
        users = RecordingStore.list_users_with_samples()
        for user in users:
            store = RecordingStore(user)
            samples = store.list_samples(self.word)
            if samples:
                path = samples[0]
                if path.exists():
                    try:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
                        pygame.mixer.music.stop()
                        pygame.mixer.music.load(str(path.absolute()))
                        pygame.mixer.music.play()
                        self.play_btn.configure(text="▶ PLAYING...", state="disabled")
                        self._check_playback_finished()
                    except Exception as e:
                        messagebox.showerror("Playback error", str(e))
                return
        messagebox.showinfo("No audio", f"No audio recordings found for '{self.word}'.")

    def _check_playback_finished(self):
        if not pygame.mixer.music.get_busy():
            self.play_btn.configure(text="▶ Play Sample", state="normal")
        else:
            self.after(200, self._check_playback_finished)

    # ---------- Delete operations ----------
    def _delete_audio_only(self):
        if not messagebox.askyesno("Confirm Delete", f"Delete ALL audio recordings for '{self.word}' from ALL users?\nThe word and its translations will remain.", parent=self):
            return
        users = RecordingStore.list_users_with_samples()
        deleted = 0
        for user in users:
            store = RecordingStore(user)
            samples = store.list_samples(self.word)
            for p in samples:
                if store.delete_sample(p):
                    deleted += 1
            try:
                prog = UserProgress(user)
                prog.set_sample_count(self.word, 0)
            except:
                pass
        if self.refresh_callback:
            self.refresh_callback()
        messagebox.showinfo("Deleted", f"{deleted} audio file(s) deleted for '{self.word}'.")
        self.destroy()

    def _delete_word_and_audio(self):
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete word '{self.word}' and ALL its audio recordings from ALL users?\nThis cannot be undone.", parent=self):
            return
        users = RecordingStore.list_users_with_samples()
        deleted_audio = 0
        for user in users:
            store = RecordingStore(user)
            samples = store.list_samples(self.word)
            for p in samples:
                if store.delete_sample(p):
                    deleted_audio += 1
            try:
                prog = UserProgress(user)
                prog.set_sample_count(self.word, 0)
            except:
                pass
        self.translations.delete_word(self.word)
        if self.refresh_callback:
            self.refresh_callback()
        messagebox.showinfo("Deleted", f"Word '{self.word}' removed.\n{deleted_audio} audio file(s) deleted.")
        self.destroy()

    def _save_translations(self):
        for code, var in self.entry_vars.items():
            new_text = var.get().strip()
            if new_text:
                self.translations.set_translation(self.word, code, new_text)
        messagebox.showinfo("Saved", f"Translations for '{self.word}' saved.")
        if self.refresh_callback:
            self.refresh_callback()

    def destroy(self):
        try:
            pygame.mixer.music.stop()
        except:
            pass
        if self.refresh_callback:
            self.refresh_callback()
        super().destroy()
