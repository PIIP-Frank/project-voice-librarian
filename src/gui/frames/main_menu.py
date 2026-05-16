import customtkinter

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
]

class MainMenuFrame(customtkinter.CTkFrame):
    def __init__(self, parent, handler, on_logout, toggle_menu_callback=None):
        super().__init__(parent, fg_color="#F0F4F8")
        self.handler = handler
        self.on_logout = on_logout
        self.toggle_menu = toggle_menu_callback
        self._role = ""
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(2, weight=0)

        # Header with menu button
        header_frame = customtkinter.CTkFrame(self, fg_color="transparent", height=50)
        header_frame.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        if self.toggle_menu:
            self.menu_btn = customtkinter.CTkButton(
                header_frame, text="☰", width=40, height=40, font=customtkinter.CTkFont(size=20),
                fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
                command=self.toggle_menu
            )
            self.menu_btn.grid(row=0, column=0, padx=(0, 10), sticky="w")
        else:
            placeholder = customtkinter.CTkFrame(header_frame, width=40, fg_color="transparent")
            placeholder.grid(row=0, column=0, padx=(0, 10), sticky="w")

        customtkinter.CTkLabel(
            header_frame, text="Project Voice", font=customtkinter.CTkFont(size=20, weight="bold"),
            text_color="#1A1A1A"
        ).grid(row=0, column=1, sticky="w")

        # User info frame (right side)
        self.user_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        self.user_frame.grid(row=0, column=2, sticky="e")

        self.welcome_lbl = customtkinter.CTkLabel(
            self.user_frame, text="Welcome", font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color="#2A6BAA"
        )
        self.welcome_lbl.pack(side="left", padx=5)

        self.role_lbl = customtkinter.CTkLabel(
            self.user_frame, text="", font=customtkinter.CTkFont(size=13), text_color="gray"
        )
        self.role_lbl.pack(side="left", padx=5)

        self.lang_lbl = customtkinter.CTkLabel(
            self.user_frame, text="", font=customtkinter.CTkFont(size=13), text_color="gray"
        )
        self.lang_lbl.pack(side="left", padx=5)

        # Content area
        self.content_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self._btn_area = customtkinter.CTkFrame(self.content_frame, fg_color="transparent")
        self._btn_area.pack(fill="both", expand=True, padx=20, pady=10)
        self._btn_area.grid_columnconfigure(0, weight=1)

        # Bottom navigation
        self.bottom_nav = customtkinter.CTkFrame(
            self, height=50, fg_color="#FFFFFF", corner_radius=0,
            border_width=1, border_color="#D0D5DC"
        )
        self.bottom_nav.grid(row=2, column=0, sticky="ew")
        self.bottom_nav.grid_propagate(False)
        for i in range(2):
            self.bottom_nav.grid_columnconfigure(i, weight=1)

        customtkinter.CTkButton(
            self.bottom_nav, text="🏠 Home", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=lambda: self.handler.show("main_menu")
        ).grid(row=0, column=0, padx=5, pady=8, sticky="ew")

        customtkinter.CTkButton(
            self.bottom_nav, text="← Logout", font=customtkinter.CTkFont(size=12),
            fg_color="transparent", text_color="#1A1A1A", hover_color="#E0E5EA",
            command=self.on_logout
        ).grid(row=0, column=1, padx=5, pady=8, sticky="ew")

    def set_user(self, username: str, role: str, lang_code: str = "en") -> None:
        self._role = role
        self.welcome_lbl.configure(text=f"👤 {username}")
        self.role_lbl.configure(text=f"({role})")

        lang_display = {
            "en": "En UK", "ig": "Ig NG", "yo": "Yr NG",
            "ha": "Hs NG", "tw": "Tw GH", "pg": "Pg NG"
        }.get(lang_code, lang_code.upper())
        self.lang_lbl.configure(text=f"🌐 {lang_display}")
        self._rebuild_buttons()

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
                self._btn_area, text=label, width=280, height=50,
                font=customtkinter.CTkFont(size=14, weight="bold"),
                fg_color="#2A6BAA", hover_color="#3A7BBA", text_color="white",
                corner_radius=10, command=cmd
            ).grid(row=i, column=0, pady=8, sticky="ew")

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
