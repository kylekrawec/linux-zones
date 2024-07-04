import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from display import get_pointer_position
from base import Axis, Preset, TransparentApplicationWindow
from zones import ZoneBoundary, ZoneContainer, ZoneEdge
from widgets import Line


class BoundPoint(Gtk.Button):
    """
    A button that represents a draggable point bound to a ZoneBoundary.

    Attributes:
        boundary (ZoneBoundary): The ZoneBoundary to which the point is bound.
    """

    def __init__(self, boundary: ZoneBoundary):
        """
        Initializes the BoundPoint with a ZoneBoundary.
        :param boundary: The ZoneBoundary to which the point is bound.
        """
        super().__init__()
        self.boundary = boundary
        # Connect Gtk signals to handlers
        self.add_events(Gdk.EventMask.BUTTON_MOTION_MASK)  # Add mask to capture motion events while button is pressed.
        self.connect("motion-notify-event", self.__on_button_motion)  # Connect motion event to local handler

    def __on_button_motion(self, widget, event) -> None:
        """
        Handles the motion-notify-event to move the boundary horizontally or vertically based on the axis.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        parent = widget.get_parent()
        # Translate coordinates relative to the parent widget if it exists
        x, y = event if parent is None else self.translate_coordinates(parent, event.x, event.y)
        if self.boundary.axis is Axis.x and x >= 0:
            self.boundary.move_horizontal(x)  # Move the boundary horizontally if axis is x
        elif y >= 0:
            self.boundary.move_vertical(y)  # Move the boundary vertically if axis is y


class ZoneEditorWindow(TransparentApplicationWindow):
    """
    A window for editing and configuring zones using BoundPoint widgets.

    Attributes:
        __overlay (Gtk.Overlay): The overlay widget for combining multiple widgets on top of one another.
        __container (zones.ZoneContainer): A container holding ZonePane objects.
        __editor (Gtk.Fixed): A fixed container holding BoundPoints.
        __edge_divider (Line): A line widget used for visualizing new edge positions before dividing.
        __point_allocation_handler_id (int): The ID for the size-allocate signal handler.
        __threshold (int): Defines a threshold for boundary proximity detection.
        __focus_point (BoundPoint or None): Tracks the currently focused point to limit only one point shown at a time.
        __edge_axis (Axis): Tracks the current axis (Axis.x or Axis.y) for edge movement.
    """

    def __init__(self, presets: [Preset]):
        """
        Initializes the ZoneEditorWindow with a list of Preset objects.
        :param presets: A list of Preset objects to initialize ZonePane objects.
        """
        super().__init__()
        self.maximize()

        # Initialize attributes
        self.__threshold = 50
        self.__focus_point = None
        self.__edge_axis = Axis.y
        self.__overlay = Gtk.Overlay()
        self.__container = ZoneContainer(presets).add_zone_style_class('zone-pane', 'passive-zone')
        self.__editor = Gtk.Fixed()
        self.__edge_divider = Line(0, 0, 0, 0)

        # Add Line to represent edge division
        self.__overlay.add_overlay(self.__edge_divider)

        # Add primary widgets to the window
        self.__overlay.add_overlay(self.__container)
        self.__overlay.add_overlay(self.__editor)
        self.add(self.__overlay)

        # Connect Gtk signals to handlers
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.KEY_RELEASE_MASK)
        self.__point_allocation_handler_id = self.connect('size-allocate', self.__on_size_allocate)
        self.connect("motion-notify-event", self.__on_motion_move_bound_point)
        self.connect("motion-notify-event", self.__on_motion_move_edge)
        self.connect("key-press-event", self.__on_key_press)
        self.connect("key-release-event", self.__on_key_release)

    def __on_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to create and size BoundPoint widgets.

        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        self.__threshold = min(allocation.width, allocation.height) * 0.05
        size = min(allocation.width, allocation.height) * 0.025
        # Layout boundary points based on zone boundary relations and position
        for boundary in self.__get_boundaries():
            point = BoundPoint(boundary)
            point.connect("motion-notify-event", self.__on_bound_point_motion)
            point.set_size_request(size, size)
            point.hide()
            self.__editor.add(point)
        self.disconnect(self.__point_allocation_handler_id)

    def __get_boundaries(self) -> [ZoneBoundary]:
        """
        Retrieves the boundaries of zones based on their connections in the container graph.

        This method collects the ZoneBoundary objects by examining the connected components in the graph. Each component is
        translated into a list of ZoneEdge objects, which are then used to create ZoneBoundary objects.

        :return: A list of ZoneBoundary objects representing the boundaries of connected zones.
        """
        boundaries = []
        zones = {zone.preset.id: zone for zone in self.__container.get_children()}
        for component in self.__container.graph.get_connected_components():
            edges = [ZoneEdge(zones[node.rectangle.id], node.side) for node in component]
            boundaries.append(ZoneBoundary(edges))
        return boundaries

    def __on_bound_point_motion(self, widget, event) -> None:
        """
        Handles the motion-notify-event to move the BoundPoint widget horizontally or vertically.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        x, y = widget.translate_coordinates(self, event.x, event.y)
        offset_size = widget.get_allocated_width() / 2
        x -= offset_size
        y -= offset_size
        if widget.boundary.axis is Axis.x and x >= 0:
            self.__editor.move(widget, x, y)
        elif y >= 0:
            self.__editor.move(widget, x, y)

    def __on_motion_move_bound_point(self, widget, event) -> None:
        """
        Handles the motion-notify-event to show and move the BoundPoint widgets along its boundary based on proximity to
        the pointer.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        for point in self.__editor.get_children():
            point_offset = point.get_allocated_width() / 2  # Calculate the offset for the point
            x, y = point.boundary.get_center()
            # Check proximity to pointer based on the axis of the boundary
            if point.boundary.axis is Axis.x and -self.__threshold < (event.x - x) < self.__threshold:
                # Handle horizontal movement for BoundPoints controlling horizontal boundaries
                if point.is_visible() or self.__focus_point is None:
                    point.show()
                    self.__focus_point = point
                self.__editor.move(point, x - point_offset, event.y - point_offset)
            elif point.boundary.axis is Axis.y and -self.__threshold < (event.y - y) < self.__threshold:
                # Handle vertical movement for BoundPoints controlling vertical boundaries
                if point.is_visible() or self.__focus_point is None:
                    point.show()
                    self.__focus_point = point
                self.__editor.move(point, event.x - point_offset, y - point_offset)
            else:
                # Hide the BoundPoint if it's not within the threshold distance
                if point.is_visible():
                    self.__focus_point = None
                point.hide()

    def __set_edge_divider(self, x, y):
        """
        Sets the position and visibility of the edge divider based on the current pointer position.
        :param x: The x-coordinate of the pointer position.
        :param y: The y-coordinate of the pointer position.
        """
        if self.__focus_point is None:
            zone_allocation = self.__get_zone_allocation(x, y)  # Get the allocation of the zone under the pointer
            if self.__edge_axis is Axis.y:
                # Set the position of the edge divider vertically
                self.__edge_divider.set_position(x, zone_allocation.y, x, zone_allocation.y + zone_allocation.height)
            else:
                # Set the position of the edge divider horizontally
                self.__edge_divider.set_position(zone_allocation.x, y, zone_allocation.x + zone_allocation.width, y)
            self.__edge_divider.show()
        else:
            self.__edge_divider.hide()  # Hide the edge divider if there is a focused point

    def __on_motion_move_edge(self, widget, event) -> None:
        """
        Handles the motion-notify-event to update the edge line position.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        self.__set_edge_divider(event.x, event.y)

    def __get_zone_allocation(self, x, y) -> Gdk.Rectangle:
        """
        Retrieves the allocation of the zone at the given coordinates.
        :param x: The x-coordinate.
        :param y: The y-coordinate.
        :return: The allocation (Gdk.Rectangle) of the zone.
        """
        assert self.get_allocated_width() != 0 and self.get_allocated_height() != 0, \
            f'Allocated width and/or height is zero. {self.__class__.__name__} must be size allocated before use.'

        for zone in self.__container.get_children():
            allocation = zone.get_allocation()
            if allocation.x <= x < allocation.x + allocation.width and allocation.y <= y < allocation.y + allocation.height:
                return allocation

    def show_all(self):
        """
        Shows all widgets within the window and presents the window.
        """
        super().show_all()
        self.present()

    def __on_key_press(self, widget, event):
        """
        Handles key press events to toggle edge axis/divider when Shift key is pressed.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the key press event.
        """
        if event.keyval == Gdk.KEY_Shift_L:
            self.__edge_axis = Axis.x
            x, y = get_pointer_position()
            self.__set_edge_divider(x, y)

    def __on_key_release(self, widget, event):
        """
        Handles key release events to reset edge axis/divider when Shift key is released.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the key release event.
        """
        if event.keyval == Gdk.KEY_Shift_L:
            self.__edge_axis = Axis.y
            x, y = get_pointer_position()
            self.__set_edge_divider(x, y)

