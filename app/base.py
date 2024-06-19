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

        self.__scaled = False  # flag to track if preset has previously been scaled

    def get_bounds(self) -> Gdk.Rectangle:
        """
        Gets the bounds of the preset as a Gdk.Rectangle object.
        :return: A Gdk.Rectangle object representing the bounds of the preset.
        """
        bounds = Gdk.Rectangle()
        bounds.x = self.x
        bounds.y = self.y
        bounds.width = self.width
        bounds.height = self.height
        return bounds

    def is_scaled(self) -> bool:
        """Determines if preset has been previously scaled."""
        return self.__scaled

    def scale(self, bounds: Gdk.Rectangle) -> None:
        """
        Scales the preset dimensions based on the provided bounds.
        :param bounds: A Gdk.Rectangle providing the scaling reference.
        """
        self.x = bounds.x + bounds.width * self.x
        self.y = bounds.y + bounds.height * self.y
        self.width = bounds.width * self.width
        self.height = bounds.height * self.height
        self.__scaled = True

    def get_side_position(self, side: Side) -> LineString:
        """
        Returns the position of the specified side of the preset.
        :param side: A Side enum value indicating which side's position to get.
        :return: A LineString object representing the coordinates of the side.
        """
        match side:
            case Side.TOP:
                return LineString([(self.x, self.y), (self.x + self.width, self.y)])
            case Side.BOTTOM:
                return LineString([(self.x, self.y + self.height), (self.x + self.width, self.y + self.height)])
            case Side.LEFT:
                return LineString([(self.x, self.y), (self.x, self.y + self.height)])
            case Side.RIGHT:
                return LineString([(self.x + self.width, self.y), (self.x + self.width, self.y + self.height)])


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
