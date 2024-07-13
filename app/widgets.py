import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

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
