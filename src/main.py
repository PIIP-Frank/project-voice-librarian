import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SRC)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import customtkinter

from store import Config, UserManifest
from store.word_translations import SUPPORTED_LANGUAGES
from gui.guihandler import GuiHandler
from gui.frames.login import LoginFrame
from gui.frames.main_menu import MainMenuFrame
from gui.frames.create_user import CreateUserFrame
from gui.frames.reset_password import ResetPasswordFrame
from gui.frames.word_query import WordQueryFrame
from gui.frames.add_word import AddWordFrame
from gui.frames.manage_library import ManageLibraryFrame


class App(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.title("Project Voice Librarian")
        self.geometry("520x600")
        self.resizable(True, True)
        self.minsize(460, 480)

        customtkinter.set_appearance_mode("Light")
        customtkinter.set_default_color_theme("blue")

        self._bg_color = "#F0F4F8"
        self.configure(fg_color=self._bg_color)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._cfg: Config | None = None
        self._manifest = UserManifest()
        first_run = self._manifest.ensure_defaults()

        self._handler = GuiHandler(self)

        self._menu_frame = None
        self._menu_visible = False

        login = LoginFrame(self, self._handler, self._on_login, self._manifest, first_run=first_run)
        menu = MainMenuFrame(self, self._handler, self._on_logout, self._toggle_menu)
        create_user = CreateUserFrame(self, self._handler, self._manifest)
        reset_pwd = ResetPasswordFrame(self, self._handler, self._manifest)
        word_query = WordQueryFrame(self, self._handler)
        add_word = AddWordFrame(self, self._handler, lambda: self._cfg)
        manage_library = ManageLibraryFrame(self, self._handler)

        self._handler.register("login", login)
        self._handler.register("main_menu", menu)
        self._handler.register("create_user", create_user)
        self._handler.register("reset_password", reset_pwd)
        self._handler.register("word_query", word_query)
        self._handler.register("add_word", add_word)
        self._handler.register("manage_library", manage_library)

        self._create_slide_menu()
        self._handler.show("login")

    def _create_slide_menu(self):
        self._menu_frame = customtkinter.CTkFrame(
            self, width=200, corner_radius=0, fg_color="#FFFFFF",
            border_width=1, border_color="#D0D5DC"
        )
        self._menu_frame.place(x=-250, y=0, relheight=1)   # fully hidden

        header = customtkinter.CTkFrame(self._menu_frame, fg_color="#2A6BAA", height=60)
        header.pack(fill="x", pady=(0, 20))
        header.pack_propagate(False)
        customtkinter.CTkLabel(header, text="📚 Menu", font=customtkinter.CTkFont(size=20, weight="bold"), text_color="white").pack(pady=15)

        menu_items = [
            ("🏠 Home", "main_menu"),
            ("📖 Word Library", "word_query"),
            ("🎤 Add Word", "add_word"),
            ("📊 Manage Library", "manage_library"),
            ("👤 Create User", "create_user"),
            ("🔑 Reset Password", "reset_password"),
        ]
        for text, screen_name in menu_items:
            btn = customtkinter.CTkButton(
                self._menu_frame, text=text, font=customtkinter.CTkFont(size=14),
                fg_color="transparent", text_color="#1A1A1A", hover_color="#E8EDF2",
                anchor="w", command=lambda s=screen_name: self._menu_navigate(s)
            )
            btn.pack(fill="x", padx=10, pady=5)

        separator1 = customtkinter.CTkFrame(self._menu_frame, height=1, fg_color="#D0D5DC")
        separator1.pack(fill="x", padx=10, pady=10)

        # Change language button
        lang_btn = customtkinter.CTkButton(
            self._menu_frame, text="🌐 Change Language", font=customtkinter.CTkFont(size=14),
            fg_color="#4A6B8A", hover_color="#3A5B7A", text_color="white",
            anchor="center", command=self._show_language_selector
        )
        lang_btn.pack(fill="x", padx=10, pady=5)

        # Logout & Exit
        logout_btn = customtkinter.CTkButton(
            self._menu_frame, text="🚪 Logout", font=customtkinter.CTkFont(size=14, weight="bold"),
            fg_color="#6B7280", hover_color="#4B5563", text_color="white", anchor="center",
            command=self._logout_from_menu
        )
        logout_btn.pack(fill="x", padx=10, pady=5)

        exit_btn = customtkinter.CTkButton(
            self._menu_frame, text="⏻ Exit Application", font=customtkinter.CTkFont(size=14, weight="bold"),
            fg_color="#B33A3A", hover_color="#8C2A2A", text_color="white", anchor="center",
            command=self._exit_app
        )
        exit_btn.pack(fill="x", padx=10, pady=5)

        separator2 = customtkinter.CTkFrame(self._menu_frame, height=1, fg_color="#D0D5DC")
        separator2.pack(fill="x", padx=10, pady=10)

        customtkinter.CTkButton(
            self._menu_frame, text="← Close Menu", font=customtkinter.CTkFont(size=12),
            fg_color="#D0D5DC", text_color="#1A1A1A", hover_color="#B8C0C8",
            command=self._toggle_menu
        ).pack(side="bottom", fill="x", padx=10, pady=20)

    def _toggle_menu(self):
        if self._menu_visible:
            self._menu_frame.place(x=-250, y=0)   # fully off-screen
            self._menu_visible = False
        else:
            self._menu_frame.lift()
            self._menu_frame.place(x=0, y=0)
            self._menu_visible = True

    def _menu_navigate(self, screen_name: str):
        self._toggle_menu()
        if screen_name == "reset_password":
            screen = self._handler.get_screen("reset_password")
            if screen:
                screen.refresh_users()
        elif screen_name == "word_query":
            screen = self._handler.get_screen("word_query")
            if screen:
                screen.refresh()
        elif screen_name == "add_word":
            screen = self._handler.get_screen("add_word")
            if screen:
                screen.refresh()
        elif screen_name == "manage_library":
            screen = self._handler.get_screen("manage_library")
            if screen:
                screen.refresh()
        self._handler.show(screen_name)

    def _logout_from_menu(self):
        self._toggle_menu()
        self._on_logout()

    def _exit_app(self):
        if self._cfg:
            try:
                self._cfg.save()
            except Exception:
                pass
        word_query = self._handler.get_screen("word_query")
        if word_query and hasattr(word_query, '_detail_window'):
            if word_query._detail_window and word_query._detail_window.winfo_exists():
                word_query._detail_window.destroy()
        self.quit()
        self.destroy()
        sys.exit(0)

    # ---------- Language switcher ----------
    def _show_language_selector(self):
        if not self._cfg:
            return
        username = self._cfg.username
        current = self._manifest.get_preferred_language(username)
        popup = customtkinter.CTkToplevel(self)
        popup.title("Change Language")
        popup.geometry("300x150")
        popup.resizable(False, False)
        popup.grab_set()
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        popup.geometry(f"+{x}+{y}")

        customtkinter.CTkLabel(popup, text="Select Preferred Language", font=customtkinter.CTkFont(size=16)).pack(pady=10)
        lang_var = customtkinter.StringVar(value=current)
        lang_options = [f"{code} - {name}" for code, name in SUPPORTED_LANGUAGES.items()]
        menu = customtkinter.CTkOptionMenu(popup, values=lang_options, variable=lang_var, width=200)
        menu.pack(pady=10)

        def apply():
            selected = lang_var.get().split(" - ")[0]
            self._manifest.set_preferred_language(username, selected)
            menu_frame = self._handler.get_screen("main_menu")
            if menu_frame:
                role = self._manifest.get_role(username)
                menu_frame.set_user(username, role, selected)
            popup.destroy()
        customtkinter.CTkButton(popup, text="Apply", command=apply).pack(pady=10)

    # ---------- Login / Logout ----------
    def _on_login(self, username: str) -> None:
        self._cfg = Config()
        self._cfg.load(username)

        role = self._manifest.get_role(username)
        pref_lang = self._manifest.get_preferred_language(username)
        menu: MainMenuFrame = self._handler.get_screen("main_menu")
        menu.set_user(username, role, pref_lang)

        wq: WordQueryFrame = self._handler.get_screen("word_query")
        wq.set_user(username)
        aw: AddWordFrame = self._handler.get_screen("add_word")
        aw.set_user(username)
        self._handler.show("main_menu")

    def _on_logout(self) -> None:
        if self._cfg:
            try:
                self._cfg.save()
            except Exception:
                pass
            self._cfg = None
        self._handler.reset()


if __name__ == "__main__":
    app = App()
    app.mainloop()
