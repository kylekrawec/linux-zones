import gi
from shapely.geometry import LineString
from enum import Enum

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


# Immutable Types
# ======================================================================================================================

class State(Enum):
    """Represents the various states in which an application or system can be."""
    READY = 0
    CTRL_READY = 1
    SET_WINDOW = 2
    SET_ZONE = 3


class Axis(Enum):
    """Represents the two primary axes in a 2D space."""
    x = 0
    y = 1


class Side(Enum):
    """Represents the four sides of a rectangle or similar object."""
    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3


class Preset:
    """
    Represents a configuration preset with position and size attributes.

    Attributes:
        label (str): The label of the preset.
        x (float|int): The x-coordinate of the preset.
        y (float|int): The y-coordinate of the preset.
        width (float|int): The width of the preset.
        height (float|int): The height of the preset.
    """
    def __init__(self, preset: dict):
        """
        Initializes the Preset instance with values from the provided dictionary.
        :param preset: A dictionary containing the preset configuration.
        Expected keys are 'label', 'x', 'y', 'width', and 'height'.
        """
        self.label = preset.get('label')
        self.x = preset.get('x')
        self.y = preset.get('y')
        self.width = preset.get('width')
        self.height = preset.get('height')

    def scale(self, bounds: Gdk.Rectangle) -> Gdk.Rectangle:
        """
        Scales the preset dimensions based on the provided bounds.
        :param bounds: A Gdk.Rectangle providing the scaling reference.
        :return: A Gdk.Rectangle object representing the scaled bounds of the preset.
        """
        new_bounds = Gdk.Rectangle()
        new_bounds.x = bounds.x + bounds.width * self.x
        new_bounds.y = bounds.y + bounds.height * self.y
        new_bounds.width = bounds.width * self.width
        new_bounds.height = bounds.height * self.height
        return new_bounds


class TransparentApplicationWindow(Gtk.ApplicationWindow):
    """A GTK application window that supports transparency and is generally ignored by the window manager."""
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
        """
        Sets the position and size of the window based on the provided bounds.
        :param bounds: A Gdk.Rectangle object representing the new position and size of the window.
        """
        self.move(bounds.x, bounds.y)
        self.resize(bounds.width, bounds.height)


# Mixin Classes
# ======================================================================================================================

class PresetableMixin:
    """Applies Preset requirements to its subclass."""
    def __init__(self, preset: Preset):
        self.preset = preset
        if not issubclass(type(self), Gtk.Widget):
            raise TypeError(f"{self.__class__} requires inheritance from Gtk.Widget")


class GtkStyleableMixin:
    """Applies functionality to add or remove multiple CSS classes to any ancestor of Gtk.Widget."""
    def add_style_class(self, *class_names: str):
        """
        Adds one or more style classes to the object's style context.
        :param class_names: One or more style class names to add.
        :return: The object itself for chaining calls.
        """
        # Ensure that the mixin is used with a Gtk.Widget or its subclass
        assert issubclass(self.__class__, Gtk.Widget), (
            f'{self.__class__.__name__} must be inherited by a class which is a subclass of {Gtk.Widget.__name__}'
        )
        for class_name in class_names:
            self.get_style_context().add_class(class_name)
        return self

    def remove_style_class(self, *class_names: str):
        """
        Removes one or more style classes from the object's style context.
        :param class_names: One or more style class names to remove.
        :return: The object itself for chaining calls.
        """
        for class_name in class_names:
            self.get_style_context().remove_class(class_name)
        return self
