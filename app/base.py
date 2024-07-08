import gi
import hashlib
import random
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

    def __init__(self, schema: Union[tuple, dict, Gdk.Rectangle, 'Schema', 'Preset']):
        """
        Initializes a Schema rectangle object with the optional ID and mandatory schema data.

        :param schema: Bound and optional ID information for the Schema object using any of the following formats:

            Formats with Auto-generated ID
            ------------------------------------------------------------------------------------------------------------
            - If Gdk.Rectangle: Directly takes x, y, width, and height attributes.
            - If tuple: Expects (x, y, width, height) where all items are integers or floats.
            - If dict: Expects {'x': x, 'y': y, 'width': width, 'height': height} where all values are integers or floats.

            Formats with Given ID
            ------------------------------------------------------------------------------------------------------------
            - If tuple: Expects (id, x, y, width, height) where id is a string and all other items are integers or floats.
            - If dict: Expects {'id': id, 'x': x, 'y': y, 'width': width, 'height': height} where 'id' is a string and
              all other values are integers or floats.
            - If Schema: Copies id, x, y, width, and height from Schema object.
            - If Preset: Copies id, x, y, width, and height from Preset object.

        :raises TypeError: If schema object is not a tuple, dict, Gdk.Rectangle, Schema, or Preset.
        """
        self.id, self.x, self.y, self.width, self.height = self._parse_schema(schema)

        assert isinstance(self.id, str) and all(isinstance(item, (int, float)) for item in (self.x, self.y, self.width, self.height)), (
            'Object data must represent (x, y, width, height) or (id, x, y, width, height) where id is a string and '
            '(x, y, width, height) are integers and/or floats.')

    def _parse_schema(self, schema: Union[tuple, dict, Gdk.Rectangle, 'Schema', 'Preset']) -> tuple:
        """
        Parses and validates the schema input to extract x, y, width, and height.

        :param schema: Bounds and optional ID information to parse and validate.
        :return: Generated or extracted id and extracted x, y, width, and height as integers and/or floats.
        :raises TypeError: If schema object is not a tuple, dict, Gdk.Rectangle, Schema, or Preset.
        """
        if isinstance(schema, tuple):
            if len(schema) == 4:
                schema = (Schema.generate_id(), *schema)
            return schema
        elif isinstance(schema, dict):
            if 'id' not in schema:
                schema['id'] = Schema.generate_id()
            return schema['id'], schema['x'], schema['y'], schema['width'], schema['height']
        elif isinstance(schema, Gdk.Rectangle):
            return Schema.generate_id(), schema.x, schema.y, schema.width, schema.height
        elif isinstance(schema, (Schema, Preset)):
            return schema.id, schema.x, schema.y, schema.width, schema.height
        else:
            raise TypeError("Object must be a tuple, dict, Gdk.Rectangle, Schema, or Preset object.")

    @staticmethod
    def generate_id() -> str:
        """
        Generates a unique ID using MD5 hash.

        :return: A unique string identifier.
        """
        return hashlib.md5(random.randbytes(20)).hexdigest()


class Preset(Schema):
    """
    Represents a zone schema with normalized bounds between 0 and 1 inclusive.

    Attributes:
        id (str): An optional identifier of the preset that auto-generates if omitted.
        x (float): The normalized x-coordinate of the preset within [0, 1].
        y (float): The normalized y-coordinate of the preset within [0, 1].
        width (float): The normalized width of the preset within [0, 1].
        height (float): The normalized height of the preset within [0, 1].
    """

    def __init__(self, preset: Union[tuple, dict, 'Schema', 'Preset']):
        """
        Initializes the Preset instance with values from the provided object.

        :param preset: An object containing the preset configuration in normalized bounds.
                       Expected values are 'id', 'x', 'y', 'width', and 'height'.
        :raises AssertionError: If any of the bounds (x, y, width, height) lie outside a normal range [0, 1].
        """
        Schema.__init__(self, preset)
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
        # Parse bounds and omit generated or existing id.
        bounds = self._parse_schema(bounds)[1:]
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

