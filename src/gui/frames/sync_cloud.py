import customtkinter
from tkinter import messagebox
from pathlib import Path
from store.progress import UserProgress
from store.recordings import RecordingStore
from store.supabase_sync import pull_all_samples_to_local
from store.word_translations import WordTranslations


class SyncCloudFrame(customtkinter.CTkFrame):
    def __init__(self, parent, handler):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self._translations = WordTranslations()
        self._is_syncing = False
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header
        header = customtkinter.CTkFrame(self, fg_color="transparent", height=50)
        header.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        customtkinter.CTkButton(
            header, text="← Back", width=60, font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self._back
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")

        customtkinter.CTkLabel(
            header, text="🌩️ Sync Cloud Samples", font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=1, sticky="w")

        # Content area
        content = customtkinter.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
        content.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            content, text="This will synchronize all samples with the cloud:",
            font=customtkinter.CTkFont(size=14), text_color="#1A1A1A"
        ).grid(row=0, column=0, pady=10, sticky="w")

        info_text = (
            "• Upload all local samples to cloud\n"
            "• Sync translations with cloud\n"
            "• Download cloud samples to local"
        )
        customtkinter.CTkLabel(
            content, text=info_text, font=customtkinter.CTkFont(size=12),
            text_color="#666666", justify="left"
        ).grid(row=1, column=0, pady=10, sticky="w")

        button_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        button_frame.grid(row=2, column=0, pady=20, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        self._sync_btn = customtkinter.CTkButton(
            button_frame, text="Start Sync", width=120, height=40,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            fg_color="#2A6BAA", hover_color="#1F5A91", command=self._perform_sync
        )
        self._sync_btn.grid(row=0, column=0, padx=5, sticky="ew")

        customtkinter.CTkButton(
            button_frame, text="Cancel", width=120, height=40,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            fg_color="#6B7280", hover_color="#5A6670", command=self._back
        ).grid(row=0, column=1, padx=5, sticky="ew")

        self._status_label = customtkinter.CTkLabel(
            self, text="", text_color="#666666", font=customtkinter.CTkFont(size=12)
        )
        self._status_label.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

    def _perform_sync(self):
        if self._is_syncing:
            return
        
        self._is_syncing = True
        self._sync_btn.configure(state="disabled")
        self._status_label.configure(text="Syncing... please wait")
        self.update()

        try:
            # Upload all local samples to cloud
            self._status_label.configure(text="Uploading samples...")
            self.update()
            upload_count = 0
            for username in RecordingStore.list_users_with_samples():
                store = RecordingStore(username)
                for entry in store.list_all_samples():
                    if store.upload_sample(entry.path):
                        upload_count += 1

            # Sync translations with the cloud
            self._status_label.configure(text="Syncing translations...")
            self.update()
            translations_synced = self._translations.sync_with_cloud()
            if not translations_synced:
                raise RuntimeError("Failed to sync translations with the cloud.")

            # Download cloud samples to local
            self._status_label.configure(text="Downloading samples...")
            self.update()
            download_count = pull_all_samples_to_local()
            
            # Update progress tracking for all downloaded files
            if download_count > 0:
                recordings_dir = Path("data") / "recordings"
                if recordings_dir.exists():
                    for user_dir in recordings_dir.iterdir():
                        if user_dir.is_dir():
                            username = user_dir.name
                            try:
                                progress = UserProgress(username)
                                # Scan all audio files and update progress
                                for audio_file in user_dir.glob("*.wav"):
                                    # Extract word name from filename (assuming format: word_attempt_N.wav)
                                    filename = audio_file.stem  # Remove .wav
                                    parts = filename.rsplit("_", 1)  # Split from right: word_attempt_N
                                    if len(parts) >= 1:
                                        word = parts[0]
                                        # Count samples for this word
                                        store = RecordingStore(username)
                                        sample_count = store.sample_count(word)
                                        if sample_count > 0:
                                            progress.set_sample_count(word, sample_count)
                            except Exception as e:
                                print(f"[sync_cloud] Warning: Could not update progress for {username}: {e}")

            self._status_label.configure(text="Sync complete!")
            messagebox.showinfo(
                "Cloud Sync Complete",
                f"Uploaded {upload_count} file(s), downloaded {download_count} file(s), and synced translations."
            )
            self._back()
        except Exception as exc:
            self._status_label.configure(text="Sync failed!")
            messagebox.showerror("Cloud Sync Failed", str(exc))
        finally:
            self._is_syncing = False
            self._sync_btn.configure(state="normal")

    def _back(self):
        self.handler.show("main_menu")

    def refresh(self):
        """Called when this frame becomes active"""
        self._status_label.configure(text="")
        self._sync_btn.configure(state="normal")
        self._is_syncing = False
