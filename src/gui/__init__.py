# Screens are CTkFrame subclasses registered with GuiHandler.
# Call handler.show(name) to switch between them.
from .guihandler import GuiHandler

__all__ = ["GuiHandler"]
