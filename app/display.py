from gi.repository import Gdk


def get_workarea() -> Gdk.Rectangle:
    """
    Retrieves the work area dimensions of the primary monitor.
    :return: Gdk.Rectangle representing the work area dimensions.
    """
    display = Gdk.Display.get_default()
    primary_monitor = display.get_primary_monitor()
    return primary_monitor.get_workarea()


def get_pointer_position() -> tuple:
    """
    Retrieves the current position of the pointer relative to the primary monitor's work area.
    :return: A tuple (x, y) representing the pointer position relative to the work area.
    """
    display = Gdk.Display.get_default()
    primary_monitor = display.get_primary_monitor()
    workarea = primary_monitor.get_workarea()

    seat = display.get_default_seat()
    pointer = seat.get_pointer()
    screen, x, y = pointer.get_position()

    # Translate the pointer position relative to the work area
    return x - workarea.x, y - workarea.y
