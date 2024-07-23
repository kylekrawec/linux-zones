import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from shapely.geometry import Point

from config import config
from display import get_pointer_position, get_workarea
from base import Axis, Side, TransparentApplicationWindow
from zones import Zone, ZoneBoundary, ZoneContainer, RectangleSideGraph
from widgets import Line


class BoundPoint(Gtk.Button):
    """
    A button that represents a draggable point bound to a ZoneBoundary.

    This class extends Gtk.Button to create a draggable point that is constrained
    by a ZoneBoundary. It handles its own drag source setup and boundary range calculation.

    :ivar boundary: The ZoneBoundary to which the point is bound.
    :ivar _lower: The lower bound of the point's movement range.
    :ivar _upper: The upper bound of the point's movement range.
    """

    def __init__(self, boundary: ZoneBoundary):
        """
        Initializes the BoundPoint with a ZoneBoundary.

        :param boundary: The ZoneBoundary to which the point is bound.
        :param buffer: A bounding box surrounding a boundary forbidding interaction within.
        """
        super().__init__()
        self.boundary = boundary
        self._lower, self._upper = 0, 0

        # Set object to be a draggable source.
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()

        # Set up event handling for button press
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('button-press-event', self._on_button_press)

    def _on_button_press(self, widget, event) -> None:
        """
        Handler for button press events.

        This method calculates and sets the boundary range when the button is pressed,
        preparing for a potential drag operation.

        :param widget: The widget that received the event.
        :param event: The event data.
        """
        self._lower, self._upper = self.get_boundary_range()

    def get_boundary_range(self) -> tuple[int, int]:
        """
        Calculates the valid range for this boundary point.

        This method determines the minimum and maximum positions that this point
        can occupy based on its associated boundary and the zones it separates.

        :return: A tuple containing the lower and upper bounds of the valid range.
        """
        is_vertical = self.boundary.axis is Axis.y

        # Determine which attributes to use based on the boundary axis
        edge_attr = 'x' if is_vertical else 'y'
        size_attr = 'width' if is_vertical else 'height'
        lower_side = Side.RIGHT if is_vertical else Side.BOTTOM

        # Calculate the lower bound
        lower = max(
            getattr(edge.zone.schema, edge_attr)
            for edge in self.boundary.get_edges()
            if edge.side is lower_side
        ) + config.settings.get('boundary-buffer-size')

        # Calculate the upper bound
        upper = min(
            getattr(edge.zone.schema, edge_attr) + getattr(edge.zone.schema, size_attr)
            for edge in self.boundary.get_edges()
            if edge.side is not lower_side
        ) - config.settings.get('boundary-buffer-size')

        return lower, upper

    def is_valid_position(self, x: int, y: int) -> bool:
        """
        Checks if a given position is valid for this boundary point.

        :param x: The x-coordinate of the position to check.
        :param y: The y-coordinate of the position to check.
        :return: True if the position is within the valid range, False otherwise.
        """
        position = x if self.boundary.axis is Axis.y else y
        return self._lower <= position <= self._upper


class Editor(Gtk.Fixed):
    """
    A custom widget that serves as an editor for manipulating BoundPoint widgets.

    This class extends Gtk.Fixed to create a drag destination for BoundPoint widgets,
    allowing them to be moved within the editor.
    """

    def __init__(self):
        """
        Initializes the Editor widget and sets it up as a drag destination.
        """
        super().__init__()

        # Make the editor a drag destination
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()

        # Connect the drag-motion signal to the handler
        self.connect('drag-motion', self._on_boundary_drag)

    def _on_boundary_drag(self, widget: Gtk.Widget, context: Gdk.DragContext, x: int, y: int, time: int) -> bool:
        """
        Handles the drag-motion signal to move the BoundPoint widget.

        :param widget: The editor widget handling BoundPoints.
        :param context: The drag context.
        :param x: The x-coordinate of the current drag position.
        :param y: The y-coordinate of the current drag position.
        :param time: The timestamp of the event.
        :return: True to indicate the drag motion was handled.
        """
        point = Gtk.drag_get_source_widget(context)
        if point.is_valid_position(x, y):
            self.move(point, x, y)
        return True

    @staticmethod
    def get_boundaries(zones: list[Zone]) -> dict[Axis, list[ZoneBoundary]]:
        """
        Generates boundaries from a list of zones.

        This method creates a RectangleSideGraph from the given zones and uses
        connected components to form boundaries, organizing them by axis.

        :param zones: A list of Zone objects to generate boundaries from.
        :return: A dictionary mapping Axis to lists of ZoneBoundary objects.
        """
        boundaries = {Axis.x: [], Axis.y: []}
        graph = RectangleSideGraph(zones)
        # Use connected components to form each boundary and organize boundaries by axis.
        for component in graph.get_connected_components():
            boundary = ZoneBoundary(component)
            boundaries[boundary.axis].append(boundary)

        return boundaries

    def move(self, widget: BoundPoint, x: int, y: int):
        """
        Moves a BoundPoint widget to a new position.

        This method updates the position of the boundary associated with the widget
        and then moves the widget itself within the editor.

        :param widget: The BoundPoint widget to move.
        :param x: The new x-coordinate for the widget.
        :param y: The new y-coordinate for the widget.
        """
        # Update the boundary position based on its axis
        if widget.boundary.axis is Axis.y:
            widget.boundary.move_horizontal(x)
        else:
            widget.boundary.move_vertical(y)

        # Adjust the widget position to center it on the cursor
        x -= widget.get_allocated_width() / 2
        y -= widget.get_allocated_height() / 2

        # Move the widget using the parent class method
        super().move(widget, x, y)


class ZoneEditorWindow(TransparentApplicationWindow):
    """
    A window for editing and configuring zones using BoundPoint widgets.

    Attributes:
        _threshold (int): Threshold for detecting proximity to boundaries.
        _focus_point (BoundPoint or None): The currently focused BoundPoint, ensuring only one point is active.
        _edge_axis (Axis): The current axis (Axis.x or Axis.y) for edge movement.
        _edge_divider (Line): A line widget to visualize new edge positions before dividing.
        _overlay (Gtk.Overlay): The overlay widget for combining multiple widgets on top of one another.
        _editor (Gtk.Fixed): A fixed container holding BoundPoints.
        _container (zones.ZoneContainer): A container holding Zone objects.
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
        self._threshold = config.settings.get('boundary-buffer-size') / 2
        self._focus_point = None
        self._edge_axis = Axis.y
        self._edge_divider = Line(0, 0, 0, 0)
        self._overlay = Gtk.Overlay()
        self._editor = Editor()
        self._container = ZoneContainer(schemas)

        # Set child size requests
        self._container.set_size_request(workarea.width, workarea.height)

        # Add CSS classes
        self._container.add_zone_style_class('zone-pane', 'passive-zone')

        # Add Line to represent edge division
        self._overlay.add_overlay(self._edge_divider)

        # Add primary widgets to the window
        self._overlay.add_overlay(self._container)
        self._overlay.add_overlay(self._editor)
        self.add(self._overlay)

        # Connect Gtk signals to handlers
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.KEY_RELEASE_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK
        )

        # Connect signals to handlers
        self._container.connect('size-allocate', self._on_container_allocation)
        self.connect('motion-notify-event', self._on_motion_move_bound_point)
        self.connect('motion-notify-event', self._on_motion_move_edge_divider)
        self.connect('key-press-event', self._on_key_press)
        self.connect('key-release-event', self._on_key_release)
        self.connect('button-press-event', self._on_button_press)

    def _on_container_allocation(self, container: ZoneContainer, allocation: Gdk.Rectangle) -> None:
        """
        Handles the container's size-allocate signal to adjust the BoundPoints.

        This method recalculates the threshold and point sizes based on the new allocation,
        removes existing BoundPoints, and adds new ones based on the updated container layout.

        :param container: The container that received the size-allocate signal.
        :param allocation: The new allocation containing the updated size information.
        """
        # Update threshold and point size based on new allocation
        self._point_size = self._threshold / 2

        # Remove existing BoundPoints
        for child in self._editor.get_children():
            if isinstance(child, BoundPoint):
                self._editor.remove(child)

        # Add boundary points
        zones = container.get_children()
        self._boundaries = self._editor.get_boundaries(zones)
        self._add_boundary_points(self._boundaries[Axis.x] + self._boundaries[Axis.y])

    def _add_boundary_points(self, boundaries: list[ZoneBoundary]) -> None:
        """
        Creates and adds BoundPoint widgets for each ZoneBoundary.

        This method takes a list of ZoneBoundary objects and creates a corresponding
        BoundPoint widget for each. These widgets are then added to the editor for
        visual representation and interaction.

        :param boundaries: A list of ZoneBoundary objects to create points for.
        """
        for boundary in boundaries:
            # Create and configure a new BoundPoint
            point = BoundPoint(boundary)
            point.set_size_request(self._point_size, self._point_size)

            # Add the new BoundPoint to the editor
            self._editor.put(point, -self._point_size*2, -self._point_size*2)
            point.show()

        self._focus_point = None

    def _on_motion_move_bound_point(self, widget, event) -> None:
        """
        Handle motion-notify-event to show and move BoundPoint widgets along boundary based on pointer proximity.

        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        for point in self._editor.get_children():
            x, y = point.boundary.center
            x1, y1, x2, y2 = point.boundary.position.bounds

            is_within_threshold = {
                Axis.y: lambda: abs(event.x - x) < self._threshold and y1 <= event.y <= y2,
                Axis.x: lambda: abs(event.y - y) < self._threshold and x1 <= event.x <= x2
            }

            if is_within_threshold[point.boundary.axis]():
                if self._focus_point is None:
                    point.show()
                    self._focus_point = point

                new_position = {
                    Axis.y: (x, event.y),
                    Axis.x: (event.x, y)
                }[point.boundary.axis]

                self._editor.move(point, *new_position)
            elif point.is_visible():
                self._focus_point = None
                point.hide()

    def _get_nearby_boundary(self, x: float, y: float, threshold: int = 50) -> ZoneBoundary | None:
        """
        Snaps the given coordinates to the nearest boundary if within given threshold.

        :param x: The x-coordinate to potentially snap.
        :param y: The y-coordinate to potentially snap.
        :param threshold: The maximum distance (in pixels) within which a boundary is considered "nearby".
        :return: A tuple of the (potentially) adjusted x and y coordinates.
        """
        index, coord = (0, x) if self._edge_axis is Axis.y else (1, y)
        nearest_boundary = next(
            (b for b in self._boundaries[self._edge_axis]
             if abs(coord - b.center[index]) < threshold),
            None
        )
        return nearest_boundary

    def _set_edge_divider(self, x, y):
        """
        Sets the position of the edge divider based on the current pointer position.
        :param x: The x-coordinate of the pointer position.
        :param y: The y-coordinate of the pointer position.
        """
        # Get the allocation of zone under the pointer
        allocation = self._container.get_zone(x, y).get_allocation()

        # Snap divider position if within proximity to an existing boundary
        boundary = self._get_nearby_boundary(x, y, self._threshold)
        x, y = boundary.center if boundary else (x, y)

        # Set the position of the edge divider vertically or horizontally
        x1, y1, x2, y2 = {
            Axis.x: (allocation.x, y, allocation.x + allocation.width, y),
            Axis.y: (x, allocation.y, x, allocation.y + allocation.height)
        }[self._edge_axis]

        self._edge_divider.set_position(x1, y1, x2, y2)

    def _on_motion_move_edge_divider(self, widget, event) -> None:
        """
        Handles the motion-notify-event to update the edge divider line position and visibility.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        if self._focus_point is None:
            self._set_edge_divider(event.x, event.y)
            self._edge_divider.show()
        else:
            self._edge_divider.hide()

    def _on_key_press(self, widget, event):
        """
        Handles key press events to toggle edge axis/divider when Shift key is pressed.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the key press event.
        """
        if event.keyval == Gdk.KEY_Shift_L:
            self._edge_axis = Axis.x
            x, y = get_pointer_position()
            self._set_edge_divider(x, y)

    def _on_key_release(self, widget, event):
        """
        Handles key release events to reset edge axis/divider when Shift key is released.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the key release event.
        """
        if event.keyval == Gdk.KEY_Shift_L:
            self._edge_axis = Axis.y
            x, y = get_pointer_position()
            self._set_edge_divider(x, y)

    def _on_button_press(self, widget, event):
        """
        Handles the button-press event to initiate zone division.

        When the primary mouse button is pressed, this method identifies the
        ZonePane at the event coordinates and divides it using the edge divider.

        :param widget: The widget that received the button press event.
        :param event: The Gdk.Event containing the event details, such as button and coordinates.
        :return: True to stop further handling of the event.
        """
        # Check if cursor position intersects a boundary buffer
        boundary = self._get_nearby_boundary(event.x, event.y, self._threshold * 2)
        valid_position = True if not boundary else not boundary.buffer.intersects(Point(event.x, event.y))
        # Divide zone if cursor is exterior to all boundary buffers
        if event.button == Gdk.BUTTON_PRIMARY and valid_position and self._edge_divider.is_visible():
            zone = self._container.get_zone(event.x, event.y)
            self._container.divide(zone, self._edge_divider)
        return True

    def show_all(self):
        """
        Shows all widgets within the window and presents the window.
        """
        super().show_all()
        self.present()
