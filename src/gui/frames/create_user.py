import re
import customtkinter
from store.users import UserManifest
from store.word_translations import SUPPORTED_LANGUAGES

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{3,30}$")


class CreateUserFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler, manifest: UserManifest):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self._manifest = manifest
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        card = customtkinter.CTkFrame(self)
        card.grid(row=1, column=0, padx=60, pady=40)
        card.grid_columnconfigure(1, weight=1)

        customtkinter.CTkLabel(
            card,
            text="Create New User",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=36, pady=(30, 22))

        # Username
        customtkinter.CTkLabel(card, text="Username", anchor="e").grid(
            row=1, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._username = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Letters, numbers, _ or - (3-30)"
        )
        self._username.grid(row=1, column=1, padx=(0, 36), pady=8)

        # Role
        customtkinter.CTkLabel(card, text="Role", anchor="e").grid(
            row=2, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._role_var = customtkinter.StringVar(value="Student Librarian")
        customtkinter.CTkOptionMenu(
            card,
            values=["Student Librarian", "Chief Librarian"],
            variable=self._role_var,
            width=220,
        ).grid(row=2, column=1, padx=(0, 36), pady=8)

        # Preferred Language
        customtkinter.CTkLabel(card, text="Preferred Language", anchor="e").grid(
            row=3, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        lang_options = [f"{code} - {name}" for code, name in SUPPORTED_LANGUAGES.items()]
        self._lang_var = customtkinter.StringVar(value=lang_options[0])
        customtkinter.CTkOptionMenu(
            card,
            values=lang_options,
            variable=self._lang_var,
            width=220,
        ).grid(row=3, column=1, padx=(0, 36), pady=8)

        # Password
        customtkinter.CTkLabel(card, text="Password", anchor="e").grid(
            row=4, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._pwd = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Min 6 characters", show="•"
        )
        self._pwd.grid(row=4, column=1, padx=(0, 36), pady=8)

        # Confirm
        customtkinter.CTkLabel(card, text="Confirm", anchor="e").grid(
            row=5, column=0, padx=(36, 10), pady=8, sticky="w"
        )
        self._confirm = customtkinter.CTkEntry(
            card, width=220, placeholder_text="Repeat password", show="•"
        )
        self._confirm.grid(row=5, column=1, padx=(0, 36), pady=8)
        self._confirm.bind("<Return>", lambda _e: self._submit())

        # Status
        self._status = customtkinter.CTkLabel(card, text="", text_color="#FF5555")
        self._status.grid(row=6, column=0, columnspan=2, padx=36, pady=(4, 0))

        # Buttons
        btn_row = customtkinter.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=7, column=0, columnspan=2, padx=36, pady=(12, 30))

        customtkinter.CTkButton(
            btn_row, text="Create User", width=150, command=self._submit
        ).grid(row=0, column=0, padx=(0, 8))

        customtkinter.CTkButton(
            btn_row,
            text="Back",
            width=100,
            fg_color="gray30",
            hover_color="gray20",
            command=lambda: self.handler.show("main_menu"),
        ).grid(row=0, column=1, padx=(8, 0))

    # ------------------------------------------------------------------
    def _submit(self) -> None:
        username = self._username.get().strip()
        role = self._role_var.get()
        password = self._pwd.get()
        confirm = self._confirm.get()
        preferred_lang_full = self._lang_var.get()
        preferred_lang_code = preferred_lang_full.split(" - ")[0]

        if not _USERNAME_RE.match(username):
            self._set_status("Username: 3-30 chars, letters/numbers/_ or -", error=True)
            return
        if len(password) < 6:
            self._set_status("Password must be at least 6 characters.", error=True)
            return
        if password != confirm:
            self._set_status("Passwords do not match.", error=True)
            self._confirm.delete(0, "end")
            return
        if self._manifest.user_exists(username):
            self._set_status(f"Username '{username}' is already taken.", error=True)
            return

        self._manifest.create_user(username, password, role, preferred_lang_code)

        self._username.delete(0, "end")
        self._pwd.delete(0, "end")
        self._confirm.delete(0, "end")
        self._role_var.set("Student Librarian")
        self._lang_var.set("en - English UK")
        self._set_status(f"User '{username}' ({role}) created.", error=False)

    def _set_status(self, msg: str, *, error: bool) -> None:
        self._status.configure(
            text=msg,
            text_color="#FF5555" if error else "#4CAF50",
        )
