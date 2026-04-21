import configparser
from pathlib import Path

LoadedCFG = None
parser = configparser.ConfigParser()

# TODO:// path loading in prod vs. testing

class Config():

    @staticmethod
    def SaveConfig() -> bool:
        """
        Save' the user's configuration.
        """
        try:
            with open("config.ini", "w") as file:
                parser.write(file)
            return True
        except Exception as e:
            return False

    @staticmethod
    def LoadConfig(username: str) -> list[str]:
        """
        Loads the user's configuration as well as a default if not available.
        """
        if LoadedCFG is not None:
            raise RuntimeWarning("A config was already loaded.")

        # Reads the default first, then overrides duplicate information from config.ini.
        # In this way, when a user updates their configuration, it should migrate missing information.
        # However, migrations are a problem if needed... in that case, a wipe is recommended.
        if Path(username + ".ini").exists():
            LOADEDCFG = parser.read(["default.ini", username + "config.ini"])
        else:
            LOADEDCFG = parser.read("default.ini")