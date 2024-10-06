import gi
import hashlib
import random
from typing import Optional, Union
from enum import Enum
from shapely.geometry import LineString
from abc import ABC

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio

from .config import config
from .exceptions import NormalizationFailureException, ScalingFailureException


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


def create_icon(resource_filename: str, size: Optional[Gtk.IconSize] = Gtk.IconSize.BUTTON) -> Gtk.Image:
    """
    Create a Gtk.Image from a resource file.

    This function loads an icon from a resource file and creates a Gtk.Image
    object with the specified size. The resource file should be located in
    the directory specified by the 'resource-prefix' setting in the config.

    :param resource_filename: The name of the icon resource file
    :param size: The size of the icon, defaults to Gtk.IconSize.BUTTON
    :return: A Gtk.Image object containing the loaded icon
    :raises Gio.Error: If the resource file cannot be found or loaded
    """
    # Construct the resource URI
    uri = f"resource://{config.settings.get('resource-prefix')}/{resource_filename}"
    # Create an icon
    file = Gio.File.new_for_uri(uri)
    icon = Gio.FileIcon.new(file)
    # Create and return a Gtk.Image from the icon
    return Gtk.Image.new_from_gicon(icon, size)


class Schema:
    """
    Represents a rectangular schema with normalized or pixel-based coordinates.

    This class can be initialized with either a dictionary or a Gdk.Rectangle object.
    It supports operations for scaling between normalized (0-1) and pixel-based coordinates.

    :ivar x: X-coordinate of the top-left corner
    :ivar y: Y-coordinate of the top-left corner
    :ivar width: Width of the rectangle
    :ivar height: Height of the rectangle
    :ivar id: Unique identifier for the schema
    :ivar is_normal: Indicates if the coordinates are normalized (0-1)
    """

    def __init__(self, data: Union[dict, Gdk.Rectangle]):
        """
        Initialize a Schema object.

        :param data: Input data for schema initialization.
        :raises TypeError: If data is neither a dict nor a Gdk.Rectangle.
        """
        if isinstance(data, Gdk.Rectangle):
            # Initialize from Gdk.Rectangle
            self.x = data.x
            self.y = data.y
            self.width = data.width
            self.height = data.height
            self.id = self.generate_id()
        elif isinstance(data, dict):
            # Initialize from dictionary
            self.x = data['x']
            self.y = data['y']
            self.width = data['width']
            self.height = data['height']
            self.id = data.get('id', self.generate_id())
        else:
            raise TypeError("data must be either a dict or Gdk.Rectangle")

        # Check if coordinates are normalized
        self.is_normal = all(0 <= i <= 1 for i in [self.x, self.y, self.width, self.height])

    @property
    def rectangle(self) -> Gdk.Rectangle:
        """
        Convert the schema to a Gdk.Rectangle.

        :return: A Gdk.Rectangle representation of the schema.
        """
        r = Gdk.Rectangle()
        r.x = self.x
        r.y = self.y
        r.width = self.width
        r.height = self.height
        return r

    def get_scaled(self, width: int, height: int) -> 'Schema':
        """
        Get a scaled Schema from normalized coordinates to pixel coordinates.

        :param width: The width to scale to.
        :param height: The height to scale to.
        :return: A new Schema with scaled coordinates.
        :raises AssertionError: If the schema is not in normalized coordinates.
        :raises ScalingFailureException: If scaling results in values less than or equal to 1.
        """
        assert self.is_normal, 'Cannot scale non-normalized bounds.'

        new_schema = Schema({
            'x': round(self.x * width),
            'y': round(self.y * height),
            'width': round(self.width * width),
            'height': round(self.height * height),
            'id': self.id
        })

        if any(getattr(new_schema, attr) < 1 for attr in ['width', 'height']):
            raise ScalingFailureException(
                f'{self.__class__} failed to be scaled. Ensure width and height values are greater than one.')

        new_schema.is_normal = False
        return new_schema

    def get_normalized(self, width: int, height: int) -> 'Schema':
        """
        Get a normalized Schema from pixel coordinates to 0-1 range.

        :param width: The width to normalize against.
        :param height: The height to normalize against.
        :return: A new Schema with normalized coordinates.
        :raises AssertionError: If the schema is already normalized or if width/height are invalid.
        :raises NormalizationFailureException: If normalization results in out-of-range values.
        """
        assert not self.is_normal, 'Cannot normalize already normalized bounds.'
        assert width > 0 and height > 0, 'Width and height must be greater than zero.'

        new_schema = Schema({
            'x': self.x / width,
            'y': self.y / height,
            'width': self.width / width,
            'height': self.height / height,
            'id': self.id
        })

        if not new_schema.is_normal:
            raise NormalizationFailureException(
                f'{self.__class__} failed to be normalized. Ensure width and height values are greater than schema width and height.')

        return new_schema

    def copy(self) -> 'Schema':
        """
        Create and return a new Schema object with the same attributes as this one.

        :return: A new Schema instance that is a copy of the current one.
        """
        return Schema(self.__dict__())

    @staticmethod
    def generate_id() -> str:
        """
        Generate a unique ID using MD5 hash.

        :return: A unique string identifier.
        """
        return hashlib.md5(random.randbytes(20)).hexdigest()

    def __str__(self) -> str:
        """
        Return a string representation of the Schema.

        :return: A string describing the Schema object.
        """
        return f"Schema(id={self.id}, x={self.x}, y={self.y}, width={self.width}, height={self.height})"

    def __dict__(self) -> dict:
        """
        Return a dictionary representation of the Schema.

        :return: A dictionary containing the Schema's attributes.
        """
        return {'id': self.id, 'x': self.x, 'y': self.y, 'width': self.width, 'height': self.height}


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


class SchemableMixin:
    """Applies Schema requirements to its subclass."""
    def __init__(self, schema: Schema):
        self.__schema = schema
        if not issubclass(type(self), Gtk.Widget):
            raise TypeError(f"{self.__class__} requires inheritance from Gtk.Widget")

    @property
    def schema(self) -> Schema:
        return self.__schema

    def update_schema(self, schema: Schema):
        """
        Update the schema of the object while preserving its ID.

        This method replaces the current schema with a new one, but keeps the original
        schema's ID. This allows for updating the schema's content without changing its
        identifier.

        :param schema: The new schema to be applied to the object.
        """
        _id = self.__schema.id
        self.__schema = schema
        self.__schema.id = _id


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

