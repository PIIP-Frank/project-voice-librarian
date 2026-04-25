import customtkinter

# (label, screen_name or None for placeholder)
_STUDENT_ACTIONS = [
    ("Word Query", "word_query"),
    ("Add Word", "add_word"),
]

_ADMIN_ACTIONS = [
    ("Word Query", "word_query"),
    ("Add Word", "add_word"),
    ("Create User", "create_user"),
    ("Reset Password", "reset_password"),
    ("Manage Library", "manage_library"),
    ("Admin Settings", None),
    ("Cloud Update", None),
]


class MainMenuFrame(customtkinter.CTkFrame):

    def __init__(self, parent, handler, on_logout):
        super().__init__(parent, fg_color="transparent")
        self.handler = handler
        self.on_logout = on_logout
        self._role = ""
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._card = customtkinter.CTkFrame(self)
        self._card.grid(row=1, column=0, padx=60, pady=40)
        self._card.grid_columnconfigure(0, weight=1)

        self._welcome_lbl = customtkinter.CTkLabel(
            self._card,
            text="Welcome",
            font=customtkinter.CTkFont(size=18, weight="bold"),
        )
        self._welcome_lbl.grid(row=0, column=0, padx=40, pady=(30, 2))

        self._role_lbl = customtkinter.CTkLabel(
            self._card, text="", text_color="gray",
            font=customtkinter.CTkFont(size=12),
        )
        self._role_lbl.grid(row=1, column=0, padx=40, pady=(0, 18))

        self._btn_area = customtkinter.CTkFrame(self._card, fg_color="transparent")
        self._btn_area.grid(row=2, column=0, padx=40, pady=(0, 12))
        self._btn_area.grid_columnconfigure(0, weight=1)

        customtkinter.CTkFrame(self._card, height=1, fg_color="gray30").grid(
            row=3, column=0, sticky="ew", padx=30, pady=(4, 0)
        )

        customtkinter.CTkButton(
            self._card,
            text="Logout",
            width=240,
            fg_color="gray30",
            hover_color="gray20",
            command=self.on_logout,
        ).grid(row=4, column=0, padx=40, pady=(10, 30))

    # ── Public API ───────────────────────────────────────────────────────────

    def set_user(self, username: str, role: str) -> None:
        self._role = role
        self._welcome_lbl.configure(text=f"Welcome, {username}")
        self._role_lbl.configure(text=role)
        self._rebuild_buttons()

    # ── Internal ─────────────────────────────────────────────────────────────

    def _rebuild_buttons(self):
        for w in self._btn_area.winfo_children():
            w.destroy()

        actions = _ADMIN_ACTIONS if self._role == "Chief Librarian" else _STUDENT_ACTIONS

        for i, (label, target) in enumerate(actions):
            if target:
                cmd = lambda t=target: self._navigate(t)
            else:
                cmd = lambda l=label: print(f"[MainMenu] '{l}' — not yet implemented")
            customtkinter.CTkButton(
                self._btn_area, text=label, width=240, command=cmd
            ).grid(row=i, column=0, pady=6)

    def _navigate(self, target: str) -> None:
        if target == "reset_password":
            screen = self.handler.get_screen("reset_password")
            if screen:
                screen.refresh_users()
        elif target == "word_query":
            screen = self.handler.get_screen("word_query")
            if screen:
                screen.refresh()
        elif target == "add_word":
            screen = self.handler.get_screen("add_word")
            if screen:
                screen.refresh()
        elif target == "manage_library":
            screen = self.handler.get_screen("manage_library")
            if screen:
                screen.refresh()
        self.handler.show(target)
