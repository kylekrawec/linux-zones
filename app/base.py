import gi
from enum import Enum

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class State(Enum):
    READY = 0
    CTRL_READY = 1
    SET_WINDOW = 2
    SET_ZONE = 3


class TransparentApplicationWindow(Gtk.ApplicationWindow):
    def __init__(self):
        super().__init__()

        # Set the window type hint to make it undecorated and generally ignored by the window manager
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)

        # Set the window's visual so it supports transparency.
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Enable transparency
        self.set_app_paintable(True)


class ScaledBounds(Gdk.Rectangle):
    def __init__(self, bounds: dict, allocation: Gdk.Rectangle):
        super().__init__()
        self.x = allocation.x + allocation.width * bounds.get('x')
        self.y = allocation.y + allocation.height * bounds.get('y')
        self.width = allocation.width * bounds.get('width')
        self.height = allocation.height * bounds.get('height')

    def __init__(self, bounds: Gdk.Rectangle, allocation: Gdk.Rectangle):
        super().__init__()
        self.x = allocation.x + allocation.width * bounds.x
        self.y = allocation.y + allocation.height * bounds.y
        self.width = allocation.width * bounds.width
        self.height = allocation.height * bounds.height


class GtkStyleable:
    def add_style_class(self, *class_names: str):
        for class_name in class_names:
            self.get_style_context().add_class(class_name)
        return self

    def remove_style_class(self, *class_names: str):
        for class_name in class_names:
            self.get_style_context().remove_class(class_name)
        return self