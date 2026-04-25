import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SRC)
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import customtkinter

from store import Config, UserManifest
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

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._cfg: Config | None = None
        self._manifest = UserManifest()
        first_run = self._manifest.ensure_defaults()

        self._handler = GuiHandler(self)

        login = LoginFrame(self, self._handler, self._on_login, self._manifest, first_run=first_run)
        menu = MainMenuFrame(self, self._handler, self._on_logout)
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

        self._handler.show("login")

    def _on_login(self, username: str) -> None:
        self._cfg = Config()
        self._cfg.load(username)


        # TODO: singleton the state?
        role = self._manifest.get_role(username)
        menu: MainMenuFrame = self._handler.get_screen("main_menu")
        menu.set_user(username, role)
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
