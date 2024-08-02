import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf, Gdk, GLib

from config import config
from base import Axis


class Line(Gtk.DrawingArea):
    """Custom Gtk widget representing a straight line drawn using Cairo."""

    __gtype_name__ = 'Line'

    def __init__(self, x1, y1, x2, y2):
        """
        Initializes a Line widget with specified coordinates.

        axis: The Axis of the line. Axis.x if horizontal, Axis.y if vertical.
        :param x1: X-coordinate of the starting point.
        :param y1: Y-coordinate of the starting point.
        :param x2: X-coordinate of the ending point.
        :param y2: Y-coordinate of the ending point.
        """
        super().__init__()
        assert x1 == x2 or y1 == y2, 'Line is constrained to be a horizontal or vertical straight line.'
        self.axis = Axis.y if x1 == x2 else Axis.x
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.connect("draw", self.__on_draw)

    def __on_draw(self, widget, cr: cairo.Context):
        """
        Handles the draw signal to draw the line using Cairo.

        :param widget: The widget that received the draw signal (Gtk.DrawingArea).
        :param cr: The Cairo context used for drawing.
        """
        cr.set_source_rgb(0.05, 0.05, 0.05)
        cr.set_line_width(1.25)
        cr.move_to(self.x1, self.y1)
        cr.line_to(self.x2, self.y2)
        cr.stroke()

    def set_position(self, x1, y1, x2, y2):
        """
        Sets new coordinates for the line and queues a redraw.

        axis: The Axis of the line. Axis.x if horizontal, Axis.y if vertical.
        :param x1: New X-coordinate of the starting point.
        :param y1: New Y-coordinate of the starting point.
        :param x2: New X-coordinate of the ending point.
        :param y2: New Y-coordinate of the ending point.
        """
        assert x1 == x2 or y1 == y2, 'Line is constrained to be a horizontal or vertical straight line.'
        self.axis = Axis.y if x1 == x2 else Axis.x
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.queue_draw()  # Queue a redraw to update the line


# Register the custom widget type
GObject.type_register(Line)


class IconButton(Gtk.Button):
    """
    A custom Gtk.Button that displays an icon.

    This button loads an icon resource and displays it. The icon
    is automatically scaled when the button is resized.
    """

    def __init__(self, resource: str):
        """
        Initialize the IconButton.

        :param resource: The name of the icon resource file (including the file extension)
        """
        super().__init__()

        self.resource = resource
        self._pixbuf = None

        self._load_resource()

        # Configure button appearance
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_property("can-focus", False)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)

        # Connect the size-allocate signal
        self._size_allocate_handler_id = self.connect('size-allocate', self._on_size_allocate)

    def _load_resource(self):
        """
        Load the icon resource into the pixbuf.
        """
        path = f'{config.settings.get("resource-prefix")}/{self.resource}'
        try:
            self._pixbuf = GdkPixbuf.Pixbuf.new_from_resource(path)
        except GLib.Error as e:
            print(f"Error loading resource: {e}")
            # Set a default "missing image" pixbuf
            self._pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 24, 24)
            self._pixbuf.fill(0xFF0000FF)  # Fill with red color

    def _on_size_allocate(self, widget: Gtk.Widget, allocation: Gdk.Rectangle):
        """
        Handle the size-allocate signal.

        This method is called when the button is allocated a new size. It scales
        the icon to fit the new size and updates the button's image.

        :param widget: The widget that received the signal (self)
        :param allocation: The new allocation for the button
        """
        scaled_buf = self._pixbuf.scale_simple(
            allocation.width,
            allocation.height,
            GdkPixbuf.InterpType.BILINEAR
        )
        image = Gtk.Image.new_from_pixbuf(scaled_buf)
        self.set_image(image)

        # Disconnect handler after initial allocation.
        self.disconnect(self._size_allocate_handler_id)
