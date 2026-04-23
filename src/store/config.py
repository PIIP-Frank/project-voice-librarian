import configparser
from pathlib import Path

class Config:
    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.loaded = False
        self.path = None

    def load(self, username: str):
        """
        Loads the user's configuration as well as a default if not available.
        """
        if self.loaded:
            raise RuntimeError("Config already loaded")

        base = Path("data")
        config_store = base / "configs"

        default_path = Path("default.ini")

        (config_store / "stored").mkdir(parents=True, exist_ok=True) 
        
        user_path = config_store / "stored" / f"{username}-config.ini"

        if user_path.exists():
            self.parser.read([default_path, user_path])
            self.path = user_path
        else:
            self.parser.read(default_path)
            self.path = user_path  # will be created on save

        self.loaded = True
        return self.parser

    def save(self):
        """
        Saves the user's configuration.
        """
        if not self.loaded or self.path is None:
            raise RuntimeError("No config loaded")

        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "w") as f:
            self.parser.write(f)