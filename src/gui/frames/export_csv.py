import csv
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter

from store.progress import UserProgress
from store.users import UserManifest


class ExportCSVFrame(customtkinter.CTkFrame):
    """Export frame for completed word progress with user role filters."""

    def __init__(self, parent, handler, manifest: UserManifest):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self.manifest = manifest
        self._role_var = customtkinter.StringVar(value="All")
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
            text=("Select a user type filter and create a CSV containing each account's completed words. "
                  "The export includes username, role, language, prompt set, word, and sample count."),
            font=customtkinter.CTkFont(size=12), text_color="#4B5563", wraplength=440,
            justify="left"
        ).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        filter_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        filter_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
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
        self._summary_label.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="w")

        button_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)

        export_button = customtkinter.CTkButton(
            button_frame, text="Export CSV", fg_color="#2A8C2A",
            hover_color="#237038", text_color="white",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            command=self._export_csv
        )
        export_button.grid(row=0, column=0, sticky="ew")

        self._status_label = customtkinter.CTkLabel(
            self, text="Ready to export completed word progress.",
            text_color="#6B7280", font=customtkinter.CTkFont(size=12), wraplength=480,
            justify="left"
        )
        self._status_label.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")

        self._update_summary()

    def _update_summary(self) -> None:
        selected_role = self._role_var.get()
        users = self._filtered_users(selected_role)
        total_completed = 0
        for username in users:
            progress = UserProgress(username)
            total_completed += sum(1 for entry in progress.words_with_samples().values() if bool(entry.get("completed")))

        label_text = (
            f"Filtered to {selected_role} users. {len(users)} account(s) match the filter. "
            f"{total_completed} completed word entries are available to export."
        )
        self._summary_label.configure(text=label_text)
        if len(users) == 0:
            self._status_label.configure(text="No accounts match the selected filter. Choose a different user type.")
        else:
            self._status_label.configure(text="Ready to export completed word progress.")

    def _filtered_users(self, selected_role: str) -> list[str]:
        if selected_role == "All":
            return self.manifest.list_users()
        return [user for user in self.manifest.list_users() if self.manifest.get_role(user) == selected_role]

    def _export_csv(self) -> None:
        selected_role = self._role_var.get()
        users = self._filtered_users(selected_role)
        rows = []

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
        if not save_path:
            return

        try:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "username",
                    "role",
                    "preferred_language",
                    "prompt_set",
                    "word",
                    "samples"
                ])
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
