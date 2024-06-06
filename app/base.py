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

    def set_window_bounds(self, bounds: Gdk.Rectangle) -> None:
        self.move(bounds.x, bounds.y)
        self.resize(bounds.width, bounds.height)


class ScaledPreset(Gdk.Rectangle):
    def __init__(self, preset: dict, allocation: Gdk.Rectangle):
        super().__init__()
        self.label = preset.get('label')
        self.x = allocation.x + allocation.width * preset.get('x')
        self.y = allocation.y + allocation.height * preset.get('y')
        self.width = allocation.width * preset.get('width')
        self.height = allocation.height * preset.get('height')

    def __init__(self, preset: 'ScaledPreset', allocation: Gdk.Rectangle):
        super().__init__()
        self.label = preset.label
        self.x = allocation.x + allocation.width * preset.x
        self.y = allocation.y + allocation.height * preset.y
        self.width = allocation.width * preset.width
        self.height = allocation.height * preset.height


class GtkStyleable:
    def add_style_class(self, *class_names: str):
        for class_name in class_names:
            self.get_style_context().add_class(class_name)
        return self

    def remove_style_class(self, *class_names: str):
        for class_name in class_names:
            self.get_style_context().remove_class(class_name)
        return self
