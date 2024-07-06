import gi
from typing import Union
from enum import Enum
from shapely.geometry import LineString
from abc import ABC

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


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


class Schema:
    """
    Represents a schema object with ID and bounds attributes.

    Attributes:
        id (str): Identifier for the schema object.
        x (float): X-coordinate of the schema bounds.
        y (float): Y-coordinate of the schema bounds.
        width (float): Width of the schema bounds.
        height (float): Height of the schema bounds.
    """

    def __init__(self, obj_id: str, bounds: Union[tuple, dict, Gdk.Rectangle, 'Schema', 'Preset']):
        """
        Initializes a Schema rectangle object with the given ID and bounds.

        :param obj_id: Identifier for the schema object.
        :param bounds: Bounds information for the schema object. Can be provided as a tuple, dictionary,
            Gdk.Rectangle, or another Schema object.
            - If tuple: Expects (x, y, width, height) where all elements are integers or floats.
            - If dict: Expects {'x': x, 'y': y, 'width': width, 'height': height} with all values as integers or floats.
            - If Gdk.Rectangle: Directly takes x, y, width, and height attributes.
            - If Schema: Copies x, y, width, and height from another Schema object.

        :raises TypeError: If bounds object is not a tuple, dict, Gdk.Rectangle, or Schema.
        """
        self.id = obj_id
        self.x, self.y, self.width, self.height = self._parse_bounds(bounds)

    def _parse_bounds(self, bounds: Union[tuple, dict, Gdk.Rectangle, 'Schema', 'Preset']):
        """
        Parses and validates the bounds input to extract x, y, width, and height.

        :param bounds: Bounds information to parse and validate.
        :return: Extracted x, y, width, and height as floats.
        :raises TypeError: If bounds object is not a tuple, dict, Gdk.Rectangle, or Schema.
        """
        if isinstance(bounds, tuple):
            return self.__parse_tuple(bounds)
        elif isinstance(bounds, dict):
            return self.__parse_dict(bounds)
        elif isinstance(bounds, Gdk.Rectangle) or isinstance(bounds, Schema) or isinstance(bounds, Preset):
            return bounds.x, bounds.y, bounds.width, bounds.height
        else:
            raise TypeError("Bounds object must be a tuple, dict, Gdk.Rectangle, or Schema")

    def __parse_tuple(self, bounds):
        """
        Parses a tuple bounds input.

        :param bounds: Tuple containing (x, y, width, height).
        :return: Parsed x, y, width, and height as floats.
        :raises AssertionError: If tuple length is not 4 or elements are not integers or floats.
        """
        assert len(bounds) == 4 and all(isinstance(item, (int, float)) for item in bounds), (
            'Tuple of bounds must contain integers and/or floats where (bounds[0], bounds[1], bounds[2], bounds[3]) '
            'represent (x, y, width, height) respectively.')
        return bounds

    def __parse_dict(self, bounds):
        """
        Parses a dictionary bounds input.

        :param bounds: Dictionary containing {'x': x, 'y': y, 'width': width, 'height': height}.
        :return: Parsed x, y, width, and height as floats.
        :raises AssertionError: If dictionary keys are missing or values are not integers or floats.
        """
        assert all(key in bounds and isinstance(bounds[key], (int, float)) for key in ['x', 'y', 'width', 'height']), \
            'Dict of bounds must contain the required keys (x, y, width, height) where each value is an integer or float.'
        return bounds['x'], bounds['y'], bounds['width'], bounds['height']


class Preset(Schema):
    """
    Represents a zone schema with normalized bounds between 0 and 1 inclusive.

    Attributes:
        id (str): The identifier of the preset.
        x (float): The normalized x-coordinate of the preset within [0, 1].
        y (float): The normalized y-coordinate of the preset within [0, 1].
        width (float): The normalized width of the preset within [0, 1].
        height (float): The normalized height of the preset within [0, 1].
    """

    def __init__(self, preset: dict):
        """
        Initializes the Preset instance with values from the provided dictionary.

        :param preset: A dictionary containing the preset configuration in normalized bounds.
                       Expected keys are 'id', 'x', 'y', 'width', and 'height'.
        :raises AssertionError: If any of the normalized bounds (x, y, width, height) are outside the range [0, 1].
        """
        Schema.__init__(self, preset.get('id'), preset)
        self.__verify_bounds((self.x, self.y, self.width, self.height))
        self.__truncate_preset(10)

    def __verify_bounds(self, bounds: tuple):
        assert all(0 <= i <= 1 for i in bounds), \
            f'{self.__class__.__name__} requires normalized bounds between 0 and 1 (inclusive), instead got {bounds}.'

    def __truncate_preset(self, digits):
        multiplier = 10 ** digits
        self.x = int(self.x * multiplier) / multiplier
        self.y = int(self.y * multiplier) / multiplier
        self.width = int(self.width * multiplier) / multiplier
        self.height = int(self.height * multiplier) / multiplier

    def set_bounds(self, bounds: Union[tuple, dict, Schema, 'Preset']):
        bounds = self._parse_bounds(bounds)
        self.__verify_bounds(bounds)
        self.__truncate_preset(10)
        self.x, self.y, self.width, self.height = bounds

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
        self.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)

        # Set the window's visual so it supports transparency.
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Enable transparency
        self.set_app_paintable(True)


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


class AbstractRectangleSide(ABC):
    """
    Abstract base class representing a side of a rectangle.
    """
    def __init__(self, rectangle, side: Side):
        """
        Initializes the AbstractRectangleSide instance.

        :param rectangle: The rectangle object with attributes 'x', 'y', 'width', and 'height'.
        :param side: The side of the rectangle represented as a Side enum.
        :raises TypeError: If the rectangle does not have 'x', 'y', 'width', and 'height' attributes.
        """
        # enforce rectangle structure
        self.__rectangle = rectangle
        self.side = side

        if not all(hasattr(rectangle, attr) for attr in ['x', 'y', 'width', 'height']):
            raise TypeError('Rectangle must have x, y, width, and height attributes.')

    @property
    def rectangle(self):
        """
        Getter for the rectangle attribute.

        :return: The rectangle object.
        """
        return self.__rectangle

    @property
    def position(self) -> LineString:
        """
        Gets the position of the rectangle's side as a LineString.

        :return: A LineString representing the position of the side.
        """
        r = self.rectangle
        match self.side:
            case Side.TOP:
                return LineString([(r.x, r.y), (r.x + r.width, r.y)])
            case Side.BOTTOM:
                return LineString([(r.x, r.y + r.height), (r.x + r.width, r.y + r.height)])
            case Side.LEFT:
                return LineString([(r.x, r.y), (r.x, r.y + r.height)])
            case Side.RIGHT:
                return LineString([(r.x + r.width, r.y), (r.x + r.width, r.y + r.height)])

