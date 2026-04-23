import json
from pathlib import Path


class JSONStore:
    def __init__(self, path: Path):
        self.path = path
        self.data = None

        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                self.data = {}
        else:
            self.data = None    # already set to None, explicitly redone here for readability.

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=4)

    # Basic operations
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def delete(self, key):
        if key in self.data:
            del self.data[key]

    def exists(self, key):
        return key in self.data

    def clear(self):
        self.data.clear()


class UserJSON(JSONStore):
    
    def __init__(self, filename: str):

        if filename is None:
            raise RuntimeError("Filename is None")
        
        base = Path("data") / "userdata"
        base.mkdir(parents=True, exist_ok=True)

        path = base / f"{filename}.json"

        super().__init__(path)

        if self.Data is None:
            self.SetDefault()
    
    def SetDefault(self):
        self.Data = {}
        self

        pass

