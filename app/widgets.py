import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf, Gdk, GLib, Gio

from config import config
from base import Axis, create_icon


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
    is automatically scaled when the button is resized. The button
    has no relief (flat appearance) and doesn't receive keyboard focus.
    """

    def __init__(self, resource: str, size: Gtk.IconSize):
        """
        Initialize the IconButton.

        :param resource: The name of the icon resource file (including the file extension)
        :param size: The size of the icon, specified as a Gtk.IconSize enum value
        """
        super().__init__()

        # Create and set the icon image
        icon = create_icon(resource, size)
        self.set_image(icon)

        # Configure button appearance
        self.set_relief(Gtk.ReliefStyle.NONE)  # Make the button flat (no visible border)
        self.set_property("can-focus", False)  # Prevent the button from receiving keyboard focus
        self.set_valign(Gtk.Align.CENTER)  # Center the button vertically within its allocated space
        self.set_halign(Gtk.Align.CENTER)  # Center the button horizontally within its allocated space


class DropDownMenu(Gtk.Button):
    """
    A custom Gtk.Button that displays a drop-down menu when clicked.

    This button creates a menu that can be populated with items, each containing
    an icon and a label. The menu appears below the button when it's clicked.
    """

    def __init__(self, resource: str):
        """
        Initialize the DropDownMenu.

        :param resource: The name of the icon resource file for the button
        """
        super().__init__()
        self.menu = Gtk.Menu()

        # Add menu icon
        icon = create_icon(resource)
        self.set_image(icon)

        self.connect_object('button-press-event', self._on_pop_menu, self.menu)

    def _on_pop_menu(self, widget, event):
        """
        Display the menu when the button is clicked.

        :param widget: The widget that triggered the event
        :param event: The event object
        """
        widget.popup(None, None, None, None, event.button, event.time)

    def _create_menu_item_with_icon(self, name: str, resource: str) -> Gtk.MenuItem:
        """
        Create a menu item with an icon and label.

        :param name: The text label for the menu item
        :param resource: The name of the icon resource file for the menu item
        :return: A Gtk.MenuItem with the specified icon and label
        """
        # Create a box to hold the icon and label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Create the icon
        image = create_icon(resource)
        box.pack_start(image, False, False, 10)

        # Create the label
        label_widget = Gtk.Label(label=name)
        box.pack_start(label_widget, False, False, 0)

        # Create the MenuItem and add the box
        menu_item = Gtk.MenuItem()
        menu_item.add(box)

        return menu_item

    def add_item(self, name: str, resource: str, callback):
        """
        Add an item to the drop-down menu.

        :param name: The text label for the menu item
        :param resource: The name of the icon resource file for the menu item
        :param callback: The function to be called when the menu item is activated
        """
        menu_item = self._create_menu_item_with_icon(name, resource)
        self.menu.append(menu_item)
        menu_item.connect('activate', callback)
        menu_item.show_all()
