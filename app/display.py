from gi.repository import Gdk


def get_workarea() -> Gdk.Rectangle:
    # get work area dimentions
    display = Gdk.Display.get_default()
    # Fetch the primary monitor number
    primary_monitor = display.get_primary_monitor()
    return primary_monitor.get_workarea()
