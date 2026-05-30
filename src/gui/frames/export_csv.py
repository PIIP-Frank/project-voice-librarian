import csv
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter

from store.progress import UserProgress
from store.users import UserManifest
from store.recordings import RecordingStore


class ExportCSVFrame(customtkinter.CTkFrame):
    """Export frame for completed word progress with user role filters."""

    def __init__(self, parent, handler, manifest: UserManifest):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self.manifest = manifest
        self._role_var = customtkinter.StringVar(value="All")
        self._type_var = customtkinter.StringVar(value="Completed Words")
        self._status_label = None
        self._summary_label = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header_frame = customtkinter.CTkFrame(self, fg_color="transparent", height=50)
        header_frame.grid(row=0, column=0, pady=(15, 5), padx=15, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        back_button = customtkinter.CTkButton(
            header_frame, text="← Back", width=80, fg_color="transparent",
            text_color="#1A1A1A", hover_color="#E0E5EA",
            font=customtkinter.CTkFont(size=12), command=lambda: self.handler.show("main_menu")
        )
        back_button.grid(row=0, column=0, sticky="w")

        customtkinter.CTkLabel(
            header_frame, text="Export CSV", font=customtkinter.CTkFont(size=20, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        card = customtkinter.CTkFrame(self, fg_color="white", corner_radius=15,
                                     border_width=1, border_color="#D0D5DC")
        card.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            card, text="Export completed word progress by account.",
            font=customtkinter.CTkFont(size=15, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        customtkinter.CTkLabel(
            card,
            text=("Choose an export type, optionally filter by user type, and create a CSV. "
                  "Options: Completed Words (per account), Overall User Stats, Per-Word Sample Counts."),
            font=customtkinter.CTkFont(size=12), text_color="#4B5563", wraplength=440,
            justify="left"
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        type_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        type_frame.grid(row=2, column=0, padx=20, pady=(0, 12), sticky="ew")
        type_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            type_frame, text="Export type:", anchor="w",
            font=customtkinter.CTkFont(size=13), text_color="#1A1A1A"
        ).grid(row=0, column=0, sticky="w")

        self._type_menu = customtkinter.CTkOptionMenu(
            type_frame,
            values=["Completed Words", "Overall User Stats", "Per-Word Sample Counts"],
            variable=self._type_var,
            width=260,
            command=lambda _: self._update_summary()
        )
        self._type_menu.grid(row=0, column=1, sticky="w", padx=(10, 0))

        filter_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        filter_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        filter_frame.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            filter_frame, text="User type filter:", anchor="w",
            font=customtkinter.CTkFont(size=13), text_color="#1A1A1A"
        ).grid(row=0, column=0, sticky="w")

        self._role_menu = customtkinter.CTkOptionMenu(
            filter_frame,
            values=["All", "Student Librarian", "Chief Librarian"],
            variable=self._role_var,
            width=220,
            command=lambda _: self._update_summary()
        )
        self._role_menu.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self._summary_label = customtkinter.CTkLabel(
            card, text="", font=customtkinter.CTkFont(size=12), text_color="#4B5563",
            wraplength=440, justify="left"
        )
        self._summary_label.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")

        button_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        button_frame.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        export_button = customtkinter.CTkButton(
            button_frame, text="Export CSV", fg_color="#2A8C2A",
            hover_color="#237038", text_color="white",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            command=self._export_csv
        )
        export_button.grid(row=0, column=0, sticky="ew")

        self._status_label = customtkinter.CTkLabel(
            self, text="Ready to export.",
            text_color="#6B7280", font=customtkinter.CTkFont(size=12), wraplength=480,
            justify="left"
        )
        self._status_label.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")

        self._update_summary()

    def _update_summary(self) -> None:
        export_type = self._type_var.get()
        selected_role = self._role_var.get()
        users = self._filtered_users(selected_role)

        if export_type == "Completed Words":
            total_completed = 0
            for username in users:
                progress = UserProgress(username)
                total_completed += sum(1 for entry in progress.words_with_samples().values() if bool(entry.get("completed")))
            label_text = (
                f"Filtered to {selected_role} users. {len(users)} account(s) match the filter. "
                f"{total_completed} completed word entries are available to export."
            )
            status = "Ready to export completed word progress." if users else "No accounts match the selected filter. Choose a different user type."

        elif export_type == "Overall User Stats":
            rows = []
            for username in users:
                progress = UserProgress(username)
                words = progress.words_with_samples()
                total_samples = sum(int(e.get("samples", 0)) for e in words.values())
                completed_words = sum(1 for e in words.values() if bool(e.get("completed")))
                rows.append((username, total_samples, completed_words, len(words)))
            label_text = (
                f"Filtered to {selected_role} users. {len(users)} account(s) match the filter. "
                f"{len(rows)} user stat rows available to export."
            )
            status = "Ready to export overall user stats." if users else "No accounts match the selected filter. Choose a different user type."

        else:  # Per-Word Sample Counts
            all_words = RecordingStore.list_all_words()
            label_text = (
                f"Per-word sample export across {len(all_words)} distinct words. "
                f"Filtered to {selected_role} users. {len(users)} account(s) match the filter."
            )
            status = "Ready to export per-word sample counts." if users and all_words else "No accounts or recorded words available for this export."

        self._summary_label.configure(text=label_text)
        self._status_label.configure(text=status)

    def _filtered_users(self, selected_role: str) -> list[str]:
        if selected_role == "All":
            return self.manifest.list_users()
        return [user for user in self.manifest.list_users() if self.manifest.get_role(user) == selected_role]

    def _export_csv(self) -> None:
        export_type = self._type_var.get()
        selected_role = self._role_var.get()
        users = self._filtered_users(selected_role)

        rows = []

        if export_type == "Completed Words":
            for username in users:
                role = self.manifest.get_role(username) or "Unknown"
                preferred_language = self.manifest.get_preferred_language(username)
                progress = UserProgress(username)
                prompt_set = progress.prompt_set or ""
                for word, entry in progress.words_with_samples().items():
                    if not bool(entry.get("completed")):
                        continue
                    rows.append([
                        username,
                        role,
                        preferred_language,
                        prompt_set,
                        word,
                        int(entry.get("samples", 0)),
                    ])

            if not rows:
                messagebox.showinfo(
                    title="No completed words",
                    message=(f"No completed word records were found for {selected_role} users. "
                             "Try a different filter or make sure users have completed words.")
                )
                self._status_label.configure(text="No completed words available for the selected filter.")
                return

            save_path = filedialog.asksaveasfilename(
                title="Save CSV Export",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                initialfile=f"completed_words_{selected_role.replace(' ', '_').lower()}.csv"
            )

        elif export_type == "Overall User Stats":
            for username in users:
                role = self.manifest.get_role(username) or "Unknown"
                preferred_language = self.manifest.get_preferred_language(username)
                progress = UserProgress(username)
                words = progress.words_with_samples()
                total_samples = sum(int(e.get("samples", 0)) for e in words.values())
                completed_words = sum(1 for e in words.values() if bool(e.get("completed")))
                distinct_words = len(words)
                rows.append([
                    username,
                    role,
                    preferred_language,
                    progress.prompt_set or "",
                    total_samples,
                    completed_words,
                    distinct_words,
                ])

            if not rows:
                messagebox.showinfo(title="No user stats", message=(f"No user stats available for {selected_role} users."))
                self._status_label.configure(text="No user stats available for the selected filter.")
                return

            save_path = filedialog.asksaveasfilename(
                title="Save CSV Export",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                initialfile=f"user_stats_{selected_role.replace(' ', '_').lower()}.csv"
            )

        else:  # Per-Word Sample Counts
            all_words = RecordingStore.list_all_words()
            if not all_words:
                messagebox.showinfo(title="No words", message="No recorded words found in the system.")
                self._status_label.configure(text="No recorded words available for export.")
                return

            # header will be: username, role, preferred_language, prompt_set, <word1>, <word2>, ...
            for username in users:
                role = self.manifest.get_role(username) or "Unknown"
                preferred_language = self.manifest.get_preferred_language(username)
                progress = UserProgress(username)
                row = [username, role, preferred_language, progress.prompt_set or ""]
                for w in all_words:
                    row.append(int(progress.sample_count(w)))
                rows.append(row)

            if not rows:
                messagebox.showinfo(title="No data", message=(f"No per-word data available for {selected_role} users."))
                self._status_label.configure(text="No per-word data available for the selected filter.")
                return

            save_path = filedialog.asksaveasfilename(
                title="Save CSV Export",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                initialfile=f"per_word_samples_{selected_role.replace(' ', '_').lower()}.csv"
            )
        if not save_path:
            return

        try:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                if export_type == "Completed Words":
                    writer.writerow([
                        "username",
                        "role",
                        "preferred_language",
                        "prompt_set",
                        "word",
                        "samples"
                    ])
                elif export_type == "Overall User Stats":
                    writer.writerow([
                        "username",
                        "role",
                        "preferred_language",
                        "prompt_set",
                        "total_samples",
                        "completed_words",
                        "distinct_words_recorded",
                    ])
                else:
                    # Per-word header
                    all_words = RecordingStore.list_all_words()
                    header = ["username", "role", "preferred_language", "prompt_set"] + all_words
                    writer.writerow(header)

                writer.writerows(rows)

            messagebox.showinfo(
                title="Export Complete",
                message=f"Exported {len(rows)} completed word entries to:\n{save_path}"
            )
            self._status_label.configure(
                text=f"Export complete: {len(rows)} completed word entries written to {save_path}."
            )
        except Exception as exc:
            self._status_label.configure(text="Export failed: unable to write the CSV file.")
            messagebox.showerror(title="Export Failed", message=str(exc))
