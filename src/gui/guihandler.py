
class GuiHandler:
    def __init__(self, app):
        self.app = app
        self._screens: dict = {}
        self._current_name: str | None = None

    def register(self, name: str, frame) -> None:
        self._screens[name] = frame

    def show(self, name: str) -> None:
        if name not in self._screens:
            raise KeyError(f"Screen '{name}' not registered")
        frame = self._screens[name]
        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()
        self._current_name = name

    def get_current(self):
        return self._screens.get(self._current_name)

    def get_screen(self, name: str):
        return self._screens.get(name)

    def get_current_name(self) -> str | None:
        return self._current_name

    def reset(self) -> None:
        self.show("login")
