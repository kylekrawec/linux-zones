import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from display import get_pointer_position, get_workarea
from base import Axis, TransparentApplicationWindow
from zones import ZoneBoundary, ZoneContainer, ZoneEdge, RectangleSideGraph
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
        __threshold (int): Threshold for detecting proximity to boundaries.
        __focus_point (BoundPoint or None): The currently focused BoundPoint, ensuring only one point is active.
        __edge_axis (Axis): The current axis (Axis.x or Axis.y) for edge movement.
        __edge_divider (Line): A line widget to visualize new edge positions before dividing.
        __overlay (Gtk.Overlay): The overlay widget for combining multiple widgets on top of one another.
        __editor (Gtk.Fixed): A fixed container holding BoundPoints.
        __container (zones.ZoneContainer): A container holding Zone objects.
    """

    def __init__(self, schemas: [dict]):
        """
        Initializes the ZoneEditorWindow with a list of dicts representing schema data.
        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        self.maximize()
        workarea = get_workarea()

        # Initialize attributes
        self.__threshold = 50
        self.__focus_point = None
        self.__edge_axis = Axis.y
        self.__edge_divider = Line(0, 0, 0, 0)
        self.__overlay = Gtk.Overlay()
        self.__editor = Gtk.Fixed()
        self.__container = ZoneContainer(schemas)

        # Set child size requests
        self.__container.set_size_request(workarea.width, workarea.height)

        # Add CSS classes
        self.__container.add_zone_style_class('zone-pane', 'passive-zone')

        # Add Line to represent edge division
        self.__overlay.add_overlay(self.__edge_divider)

        # Add primary widgets to the window
        self.__overlay.add_overlay(self.__container)
        self.__overlay.add_overlay(self.__editor)
        self.add(self.__overlay)

        # Connect Gtk signals to handlers
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.KEY_RELEASE_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK
        )

        # Connect signals to handlers
        self.__container.connect('size-allocate', self.__on_container_allocation)
        self.connect('motion-notify-event', self.__on_motion_move_bound_point)
        self.connect('motion-notify-event', self.__on_motion_move_edge)
        self.connect('key-press-event', self.__on_key_press)
        self.connect('key-release-event', self.__on_key_release)
        self.connect('button-press-event', self.__on_button_press)

    def __on_container_allocation(self, container: ZoneContainer, allocation: Gdk.Rectangle) -> None:
        """
        Handles the container's size-allocate signal to adjust the BoundPoints.

        This method recalculates the threshold and point sizes based on the new allocation,
        removes existing BoundPoints, and adds new ones based on the updated container layout.

        :param container: The container that received the size-allocate signal.
        :param allocation: The new allocation containing the updated size information.
        """
        # Update threshold and point size based on new allocation
        self.__threshold = round(min(allocation.width, allocation.height) * 0.04)
        self.__point_size = round(min(allocation.width, allocation.height) * 0.03)
        self.__point_offset = self.__point_size / 2

        # Remove existing BoundPoints
        for child in self.__editor.get_children():
            if isinstance(child, BoundPoint):
                self.__editor.remove(child)

        # Create new graph and add boundary points
        schemas = [zone.schema for zone in container.get_children()]
        graph = RectangleSideGraph(schemas)
        self.__add_boundary_points(graph)

    def __add_boundary_points(self, graph: RectangleSideGraph) -> None:
        """
        Layouts boundary points based on zone boundary relations and positions.

        This method creates BoundPoint widgets for each connected component in the graph,
        representing the boundaries between zones.

        :param graph: A RectangleSideGraph representing the zones and their boundaries.
        """
        zones = {zone.schema.id: zone for zone in self.__container.get_children()}

        for component in graph.get_connected_components():
            # Create ZoneEdges for each node in the component
            edges = [ZoneEdge(zones[node.rectangle.id], node.side) for node in component]
            boundary = ZoneBoundary(edges)

            # Create and configure a new BoundPoint
            point = BoundPoint(boundary)
            point.set_size_request(self.__point_size, self.__point_size)
            point.connect("motion-notify-event", self.__on_bound_point_motion)

            # Reset focus point and add the new BoundPoint to the editor
            self.__focus_point = None
            self.__editor.add(point)

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
        Handle motion-notify-event to show and move BoundPoint widgets along boundary based on pointer proximity.

        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        for point in self.__editor.get_children():
            x, y = point.boundary.center
            x1, y1, x2, y2 = point.boundary.position.bounds

            is_within_threshold = {
                Axis.x: lambda: abs(event.x - x) < self.__threshold and y1 <= event.y <= y2,
                Axis.y: lambda: abs(event.y - y) < self.__threshold and x1 <= event.x <= x2
            }

            if is_within_threshold[point.boundary.axis]():
                if not point.is_visible() and self.__focus_point is None:
                    point.show()
                    self.__focus_point = point

                new_position = {
                    Axis.x: (x - self.__point_offset, event.y - self.__point_offset),
                    Axis.y: (event.x - self.__point_offset, y - self.__point_offset)
                }[point.boundary.axis]

                self.__editor.move(point, *new_position)
            elif point.is_visible():
                self.__focus_point = None
                point.hide()

    def __set_edge_divider(self, x, y):
        """
        Sets the position and visibility of the edge divider based on the current pointer position.
        :param x: The x-coordinate of the pointer position.
        :param y: The y-coordinate of the pointer position.
        """
        if self.__focus_point is None:
            allocation = self.__container.get_zone(x, y).get_allocation()  # Get the allocation of zone under the pointer
            if self.__edge_axis is Axis.y:
                # Set the position of the edge divider vertically
                self.__edge_divider.set_position(x, allocation.y, x, allocation.y + allocation.height)
            else:
                # Set the position of the edge divider horizontally
                self.__edge_divider.set_position(allocation.x, y, allocation.x + allocation.width, y)
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

    def __on_button_press(self, widget, event):
        """
        Handles the button-press event to initiate zone division.

        When the primary mouse button is pressed, this method identifies the
        ZonePane at the event coordinates and divides it using the edge divider.

        :param widget: The widget that received the button press event.
        :param event: The Gdk.Event containing the event details, such as button and coordinates.
        :return: True to stop further handling of the event.
        """
        if event.button == Gdk.BUTTON_PRIMARY:
            zone = self.__container.get_zone(event.x, event.y)
            self.__container.divide(zone, self.__edge_divider)
        return True

    def show_all(self):
        """
        Shows all widgets within the window and presents the window.
        """
        super().show_all()
        self.present()
