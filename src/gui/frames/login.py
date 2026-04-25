import customtkinter
from store.users import UserManifest


class LoginFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler, on_login, manifest: UserManifest, first_run: bool = False):
        super().__init__(parent, fg_color="transparent")
        self.handler = handler
        self.on_login = on_login
        self._manifest = manifest
        self._first_run = first_run
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
            text="Project Voice Librarian",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=36, pady=(30, 4))

        customtkinter.CTkLabel(
            card,
            text="People Investing In People Foundation",
            font=customtkinter.CTkFont(size=11),
            text_color="gray",
        ).grid(row=1, column=0, columnspan=2, padx=36, pady=(0, 22))

        # Username
        customtkinter.CTkLabel(card, text="Username", anchor="w").grid(
            row=2, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._username = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Enter username"
        )
        self._username.grid(row=2, column=1, padx=(0, 36), pady=8)

        # Password
        customtkinter.CTkLabel(card, text="Password", anchor="w").grid(
            row=3, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._password = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Enter password", show="•"
        )
        self._password.grid(row=3, column=1, padx=(0, 36), pady=8)
        self._password.bind("<Return>", lambda _e: self._submit())

        # Error
        self._error = customtkinter.CTkLabel(card, text="", text_color="#FF5555")
        self._error.grid(row=4, column=0, columnspan=2, padx=36, pady=(4, 0))

        # Login button
        customtkinter.CTkButton(
            card, text="Login", width=220, command=self._submit
        ).grid(row=5, column=0, columnspan=2, padx=36, pady=(12, 20 if not self._first_run else 8))

        # First-run hint — shown only when the default account was just created
        if self._first_run:
            customtkinter.CTkLabel(
                card,
                text="First run — default credentials: admin / admin123",
                text_color="#F0A500",
                font=customtkinter.CTkFont(size=11),
            ).grid(row=6, column=0, columnspan=2, padx=36, pady=(0, 20))

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _submit(self) -> None:
        username = self._username.get().strip()
        password = self._password.get()

        if not username:
            self._error.configure(text="Username is required.")
            return
        if not password:
            self._error.configure(text="Password is required.")
            return
        if not self._manifest.user_exists(username):
            self._error.configure(text="Invalid username or password.")
            return
        if not self._manifest.verify_password(username, password):
            self._error.configure(text="Invalid username or password.")
            self._password.delete(0, "end")
            return

        self._error.configure(text="")
        self._password.delete(0, "end")
        self.on_login(username)
