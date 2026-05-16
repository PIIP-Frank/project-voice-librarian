import io
import threading
import wave
import tempfile
import os
import pygame
import customtkinter

from store.prompts import PromptSet, load_prompt_set, list_prompt_sets
from store.progress import UserProgress
from store.recordings import RecordingStore
from store.arduino import ArduinoSerial, list_ports, is_available
from store.word_translations import SUPPORTED_LANGUAGES

_RECORD_SECONDS = 3

if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)


class AddWordFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler, get_config):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self._get_config = get_config

        self._username: str = ""
        self._prompt_set: PromptSet | None = None
        self._progress: UserProgress | None = None
        self._recordings: RecordingStore | None = None

        self._record_started = threading.Event()
        self._record_cancel = threading.Event()

        self._pending_pcm: bytes | None = None
        self._pending_sample_rate: int | None = None
        self._pending_word: str | None = None
        self._pending_lang: str | None = None
        self._is_preview_playing: bool = False

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        card = customtkinter.CTkFrame(self)
        card.grid(row=1, column=0, padx=30, pady=24, sticky="n")
        card.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            card, text="Add Word",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(20, 4))

        self._set_lbl = customtkinter.CTkLabel(
            card, text="", text_color="gray",
            font=customtkinter.CTkFont(size=11),
        )
        self._set_lbl.grid(row=1, column=0, padx=30, pady=(0, 12))

        # Word display
        word_panel = customtkinter.CTkFrame(card)
        word_panel.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")
        word_panel.grid_columnconfigure(1, weight=1)

        customtkinter.CTkButton(word_panel, text="←", width=40, command=self._prev_word).grid(row=0, column=0, padx=(10, 6), pady=12)
        self._word_lbl = customtkinter.CTkLabel(word_panel, text="—", font=customtkinter.CTkFont(size=28, weight="bold"))
        self._word_lbl.grid(row=0, column=1, padx=4, pady=12, sticky="ew")
        customtkinter.CTkButton(word_panel, text="→", width=40, command=self._next_word).grid(row=0, column=2, padx=(6, 10), pady=12)
        self._word_meta_lbl = customtkinter.CTkLabel(word_panel, text="", text_color="gray", font=customtkinter.CTkFont(size=11))
        self._word_meta_lbl.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10))

        # Arduino port picker
        port_panel = customtkinter.CTkFrame(card)
        port_panel.grid(row=3, column=0, padx=20, pady=(0, 12), sticky="ew")
        port_panel.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(port_panel, text="Arduino", anchor="w").grid(row=0, column=0, padx=(14, 8), pady=10, sticky="w")
        self._port_var = customtkinter.StringVar(value="")
        self._port_menu = customtkinter.CTkOptionMenu(port_panel, values=[""], variable=self._port_var, width=180, command=self._on_port_change)
        self._port_menu.grid(row=0, column=1, padx=(0, 6), pady=10, sticky="ew")
        customtkinter.CTkButton(port_panel, text="↻", width=40, command=self._refresh_ports).grid(row=0, column=2, padx=(0, 14), pady=10)

        # Language selector for this recording
        lang_panel = customtkinter.CTkFrame(card)
        lang_panel.grid(row=4, column=0, padx=20, pady=(0, 12), sticky="ew")
        lang_panel.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(lang_panel, text="Language", anchor="w").grid(row=0, column=0, padx=(14, 8), pady=10, sticky="w")
        lang_options = [f"{code} - {name}" for code, name in SUPPORTED_LANGUAGES.items()]
        self._lang_var = customtkinter.StringVar(value=lang_options[0])
        self._lang_menu = customtkinter.CTkOptionMenu(lang_panel, values=lang_options, variable=self._lang_var, width=180)
        self._lang_menu.grid(row=0, column=1, padx=(0, 6), pady=10, sticky="ew")

        # Record button
        self._record_btn = customtkinter.CTkButton(card, text=f"● Record {_RECORD_SECONDS} sec", width=240, height=40,
                                                   fg_color="#B33A3A", hover_color="#8C2A2A", command=self._record)
        self._record_btn.grid(row=5, column=0, padx=20, pady=(8, 4))

        # Verify panel
        self._verify_panel = customtkinter.CTkFrame(card, fg_color="transparent")
        self._verify_panel.grid_columnconfigure((0, 1, 2), weight=1)
        self._verify_lbl = customtkinter.CTkLabel(self._verify_panel, text="Verify recording before saving", font=customtkinter.CTkFont(size=12, weight="bold"))
        self._verify_lbl.grid(row=0, column=0, columnspan=3, padx=8, pady=(4, 6))
        self._play_pending_btn = customtkinter.CTkButton(self._verify_panel, text="▶ Play", width=78, command=self._play_pending)
        self._play_pending_btn.grid(row=1, column=0, padx=4, pady=(0, 4))
        self._redo_btn = customtkinter.CTkButton(self._verify_panel, text="↻ Redo", width=78, fg_color="gray30", hover_color="gray20", command=self._redo_pending)
        self._redo_btn.grid(row=1, column=1, padx=4, pady=(0, 4))
        self._save_btn = customtkinter.CTkButton(self._verify_panel, text="✓ Save", width=78, fg_color="#2A8C2A", hover_color="#226B22", command=self._save_pending)
        self._save_btn.grid(row=1, column=2, padx=4, pady=(0, 4))

        self._progress_bar = customtkinter.CTkProgressBar(card, width=240)
        self._progress_bar.set(0)
        self._progress_bar.grid(row=6, column=0, padx=20, pady=(4, 4))
        self._status_lbl = customtkinter.CTkLabel(card, text="", text_color="gray", font=customtkinter.CTkFont(size=11))
        self._status_lbl.grid(row=7, column=0, padx=20, pady=(0, 8))
        customtkinter.CTkButton(card, text="Back", width=120, fg_color="gray30", hover_color="gray20", command=lambda: self.handler.show("main_menu")).grid(row=8, column=0, padx=20, pady=(4, 20))

    # ---------- Public API ----------
    def set_user(self, username: str) -> None:
        self._username = username
        self._progress = UserProgress(username)
        self._recordings = RecordingStore(username)
        sets = list_prompt_sets()
        target = self._progress.prompt_set if self._progress.prompt_set in sets else (sets[0] if sets else None)
        if target is None:
            self._prompt_set = None
            self._set_lbl.configure(text="No prompt sets available in src/prompts/")
            self._record_btn.configure(state="disabled")
            return
        self._prompt_set = load_prompt_set(target)
        self._progress.prompt_set = target
        self._set_lbl.configure(text=f"Prompt set: {target}  ·  {len(self._prompt_set)} word(s)")
        self._refresh_word()
        self._refresh_ports()

    def refresh(self) -> None:
        if self._username:
            self._refresh_word()
            self._refresh_ports()

    # ---------- Word navigation ----------
    def _prev_word(self) -> None:
        if not self._prompt_set or not self._progress: return
        idx = max(0, self._progress.current_index - 1)
        if idx == self._progress.current_index: return
        self._discard_pending_for_navigation()
        self._progress.current_index = idx
        self._refresh_word()

    def _next_word(self) -> None:
        if not self._prompt_set or not self._progress: return
        idx = min(len(self._prompt_set) - 1, self._progress.current_index + 1)
        if idx == self._progress.current_index: return
        self._discard_pending_for_navigation()
        self._progress.current_index = idx
        self._refresh_word()

    def _discard_pending_for_navigation(self) -> None:
        if self._pending_pcm is None: return
        self._clear_pending()
        self._set_status("Pending recording discarded.", error=False)

    def _refresh_word(self) -> None:
        if not self._prompt_set or not self._progress or not self._recordings: return
        idx = self._progress.current_index
        word = self._prompt_set.get(idx) or "—"
        total = len(self._prompt_set)
        recorded = self._recordings.sample_count(word)
        self._progress.set_sample_count(word, recorded)
        self._word_lbl.configure(text=word)
        self._word_meta_lbl.configure(text=f"Word {idx + 1} of {total}  ·  {recorded} sample(s)")

    # ---------- Port handling ----------
    def _refresh_ports(self) -> None:
        if not is_available():
            self._port_menu.configure(values=["pyserial not installed"])
            self._port_var.set("pyserial not installed")
            self._record_btn.configure(state="disabled")
            return
        ports = list_ports()
        if not ports:
            self._port_menu.configure(values=["(no ports detected)"])
            self._port_var.set("(no ports detected)")
            self._record_btn.configure(state="disabled")
            return
        self._port_menu.configure(values=ports)
        saved = self._read_cfg("Port", "")
        if saved in ports:
            self._port_var.set(saved)
        elif self._port_var.get() not in ports:
            self._port_var.set(ports[0])
            self._on_port_change(ports[0])
        self._record_btn.configure(state="normal")

    def _on_port_change(self, value: str) -> None:
        if not value or value.startswith("("): return
        self._write_cfg("Port", value)

    # ---------- Recording ----------
    def _record(self) -> None:
        if not self._prompt_set or not self._progress or not self._recordings: return
        word = self._prompt_set.get(self._progress.current_index)
        if not word: return
        port = self._port_var.get()
        if not port or port.startswith("("):
            self._set_status("Select an Arduino port.", error=True)
            return
        baud = int(self._read_cfg("BaudRate", "115200") or "115200")
        self._record_started.clear()
        self._record_cancel.clear()
        self._record_btn.configure(state="disabled")
        t = threading.Thread(target=self._do_record, args=(word, port, baud), daemon=True)
        t.start()
        if self._record_started.wait(timeout=2):
            self._set_status(f"Recording {_RECORD_SECONDS}s on {port}…", error=False)
            self._progress_bar.configure(mode="indeterminate")
            self._progress_bar.start()
        else:
            self._record_cancel.set()
            self._record_btn.configure(state="normal")
            raise RuntimeWarning("Could not start recording. Timed out.")

    def _do_record(self, word: str, port: str, baud: int) -> None:
        if self._record_cancel.is_set(): return
        try:
            with ArduinoSerial(port, baud=baud) as ard:
                self._record_started.set()
                if self._record_cancel.is_set(): return
                pcm, sample_rate = ard.record(_RECORD_SECONDS)
            if self._record_cancel.is_set(): return
            self.after(0, self._on_record_done, word, pcm, sample_rate, None)
        except Exception as e:
            self.after(0, self._on_record_done, None, None, None, e)

    def _on_record_done(self, word, pcm, sample_rate, err) -> None:
        self._progress_bar.stop()
        self._progress_bar.configure(mode="determinate")
        self._progress_bar.set(1.0 if err is None else 0.0)
        self._record_btn.configure(state="normal")
        if err is not None:
            self._set_status(f"Error: {err}", error=True)
            return
        self._pending_pcm = pcm
        self._pending_sample_rate = sample_rate
        self._pending_word = word
        lang_full = self._lang_var.get()
        self._pending_lang = lang_full.split(" - ")[0]
        self._show_verify_panel()
        self._set_status(f"Captured {_RECORD_SECONDS}s for '{word}' in {self._pending_lang}. Play to verify, Redo to retry, Save to keep.", error=False)

    # ---------- Verify phase ----------
    def _show_verify_panel(self) -> None:
        self._record_btn.grid_remove()
        self._verify_panel.grid(row=5, column=0, padx=20, pady=(8, 4), sticky="ew")

    def _hide_verify_panel(self) -> None:
        self._verify_panel.grid_remove()
        self._record_btn.grid(row=5, column=0, padx=20, pady=(8, 4))

    def _clear_pending(self) -> None:
        self._stop_preview()
        self._pending_pcm = None
        self._pending_sample_rate = None
        self._pending_word = None
        self._pending_lang = None
        self._hide_verify_panel()

    # ---------- Preview using pygame ----------
    def _play_pending(self) -> None:
        if not self._pending_pcm or not self._pending_sample_rate:
            return
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._pending_sample_rate)
            w.writeframes(self._pending_pcm)
        buf.seek(0)
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(buf.getvalue())
                tmp_path = tmp.name
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.music.stop()
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            self._is_preview_playing = True
            self.after(int(_RECORD_SECONDS * 1000) + 500, lambda: self._cleanup_temp(tmp_path))
        except Exception as e:
            self._set_status(f"Preview error: {e}", error=True)

    def _cleanup_temp(self, path):
        try:
            os.unlink(path)
        except:
            pass

    def _stop_preview(self) -> None:
        if not self._is_preview_playing:
            return
        try:
            pygame.mixer.music.stop()
        except:
            pass
        self._is_preview_playing = False

    def _redo_pending(self) -> None:
        self._clear_pending()
        self._set_status("Discarded — recording again…", error=False)
        self._record()

    def _save_pending(self) -> None:
        if (self._pending_pcm is None or self._pending_sample_rate is None or
            not self._pending_word or not self._recordings or not self._progress):
            return
        word = self._pending_word
        lang_code = self._pending_lang or "en"
        try:
            path = self._recordings.save_sample(word, self._pending_pcm, self._pending_sample_rate, lang_code)
        except OSError as e:
            self._set_status(f"Save failed: {e}", error=True)
            return
        self._progress.increment(word)
        self._write_cfg("SampleRate", str(self._pending_sample_rate))
        self._clear_pending()
        self._refresh_word()
        self._set_status(f"Saved {path.name}", error=False)

    # ---------- Config helpers ----------
    def _read_cfg(self, key: str, default: str) -> str:
        cfg = self._get_config()
        if cfg is None: return default
        try: return cfg.parser.get("arduino", key, fallback=default)
        except: return default

    def _write_cfg(self, key: str, value: str) -> None:
        cfg = self._get_config()
        if cfg is None: return
        if not cfg.parser.has_section("arduino"): cfg.parser.add_section("arduino")
        cfg.parser.set("arduino", key, value)

    def _set_status(self, msg: str, *, error: bool) -> None:
        self._status_lbl.configure(text=msg, text_color="#FF5555" if error else "#4CAF50")
