import customtkinter
from store.users import UserManifest


class ResetPasswordFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler, manifest: UserManifest):
        super().__init__(parent, fg_color="transparent")
        self.handler = handler
        self._manifest = manifest
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Card ────────────────────────────────────────────────────────────
        card = customtkinter.CTkFrame(self)
        card.grid(row=1, column=0, padx=60, pady=40)
        card.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            card,
            text="Reset Password",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=36, pady=(30, 22))

        # User selector
        customtkinter.CTkLabel(card, text="User", anchor="w").grid(
            row=1, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._user_var = customtkinter.StringVar()
        self._user_menu = customtkinter.CTkOptionMenu(
            card, values=[""], variable=self._user_var, width=220
        )
        self._user_menu.grid(row=1, column=1, padx=(0, 36), pady=8)

        # New password
        customtkinter.CTkLabel(card, text="New Password", anchor="w").grid(
            row=2, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._pwd = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Min 6 characters", show="•"
        )
        self._pwd.grid(row=2, column=1, padx=(0, 36), pady=8)

        # Confirm
        customtkinter.CTkLabel(card, text="Confirm", anchor="w").grid(
            row=3, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._confirm = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Repeat password", show="•"
        )
        self._confirm.grid(row=3, column=1, padx=(0, 36), pady=8)
        self._confirm.bind("<Return>", lambda _e: self._submit())

        # Status
        self._status = customtkinter.CTkLabel(card, text="", text_color="#FF5555")
        self._status.grid(row=4, column=0, columnspan=2, padx=36, pady=(4, 0))

        # Buttons
        btn_row = customtkinter.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=5, column=0, columnspan=2, padx=36, pady=(12, 30))

        customtkinter.CTkButton(
            btn_row, text="Reset Password", width=150, command=self._submit
        ).grid(row=0, column=0, padx=(0, 8))

        customtkinter.CTkButton(
            btn_row,
            text="Back",
            width=100,
            fg_color="gray30",
            hover_color="gray20",
            command=lambda: self.handler.show("main_menu"),
        ).grid(row=0, column=1, padx=(8, 0))

    # ── Public API ───────────────────────────────────────────────────────────

    def refresh_users(self) -> None:
        """Refresh the user dropdown. Call this before showing the screen."""
        users = self._manifest.list_users()
        self._user_menu.configure(values=users if users else [""])
        if users:
            self._user_var.set(users[0])
        self._pwd.delete(0, "end")
        self._confirm.delete(0, "end")
        self._status.configure(text="")

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        username = self._user_var.get()
        password = self._pwd.get()
        confirm = self._confirm.get()

        if not username:
            self._set_status("No user selected.", error=True)
            return
        if len(password) < 6:
            self._set_status("Password must be at least 6 characters.", error=True)
            return
        if password != confirm:
            self._set_status("Passwords do not match.", error=True)
            self._confirm.delete(0, "end")
            return

        self._manifest.reset_password(username, password)
        self._pwd.delete(0, "end")
        self._confirm.delete(0, "end")
        self._set_status(f"Password for '{username}' reset successfully.", error=False)

    def _set_status(self, msg: str, *, error: bool) -> None:
        self._status.configure(
            text=msg,
            text_color="#FF5555" if error else "#4CAF50",
        )
