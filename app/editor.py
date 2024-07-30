from typing import Optional, Tuple, Dict, List

from shapely.geometry import Point
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


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

    def _on_button_press(self, widget, event):
        """
        Handler for button press events.

        This method calculates and sets the boundary range when the button is pressed,
        preparing for a potential drag operation.

        :param widget: The widget that received the event.
        :param event: The event data.
        """
        self._lower, self._upper = self.get_boundary_range()

    def get_boundary_range(self) -> Tuple[int, int]:
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


class Editor(Gtk.Layout):
    """
    A custom widget that serves as an editor for manipulating zone boundaries.

    This class extends Gtk.Layout to create a drag destination for BoundPoint widgets,
    allowing them to be moved within the editor. It manages the visibility and movement
    of boundary points, and handles user interactions with the zone layout.

    Attributes:
        threshold (int): Threshold for detecting proximity to boundaries.
        point_size (float): Size of the BoundPoint widgets.
        _boundary_point_map (Dict[Axis, Dict[ZoneBoundary, BoundPoint]]): Maps boundaries to their BoundPoint widgets.
        visible_point (Optional[BoundPoint]): The currently visible BoundPoint, ensuring only one point is shown at a time.
        boundaries (List[ZoneBoundary]): List of all zone boundaries.
    """

    def __init__(self):
        """
        Initializes the Editor widget and sets it up as a drag destination.
        """
        super().__init__()
        self.threshold = config.settings.get('boundary-buffer-size') / 2
        self.point_size = self.threshold / 2
        self._boundary_point_map = {Axis.x: {}, Axis.y: {}}
        self.visible_point: Optional[BoundPoint] = None
        self.boundaries = None

        # Make the editor a drag destination
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()

        # Add Gdk event masks
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)

        # Connect signals to handlers
        self.connect('drag-motion', self._on_boundary_drag)
        self.connect('motion-notify-event', self._on_motion_notify)

    def _clear(self):
        """
        Clears the editor state and removes all BoundPoint widgets.
        """
        self._set_visible_point(None)
        self._boundary_point_map[Axis.x].clear()
        self._boundary_point_map[Axis.y].clear()

        for child in self.get_children():
            if isinstance(child, BoundPoint):
                self.remove(child)

    def _on_motion_notify(self, widget, event):
        """
        Handles mouse motion events to show and move BoundPoint widgets.

        :param widget: The widget that received the event.
        :param event: The motion event object.
        """
        cursor = Point(event.x, event.y)
        boundary = self.get_nearest_boundary(cursor)
        point = self.get_boundpoint(boundary)

        if cursor.intersects(boundary.buffer):
            new_position = {
                Axis.y: (boundary.center.x, cursor.y),
                Axis.x: (cursor.x, boundary.center.y)
            }[boundary.axis]

            self.move(point, *new_position)
            self._set_visible_point(point)
        else:
            self._set_visible_point(None)

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

    def _set_visible_point(self, point: Optional[BoundPoint] = None):
        """
        Sets the visible BoundPoint and hides the previously visible one.

        :param point: The BoundPoint to make visible, or None to hide all points.
        """
        if self.visible_point:
            self.visible_point.hide()
        if point:
            point.show()
        self.visible_point = point

    def move(self, widget: BoundPoint, x: int, y: int):
        """
        Moves a BoundPoint widget to a new position and updates the associated boundary.

        :param widget: The BoundPoint widget to move.
        :param x: The new x-coordinate for the widget.
        :param y: The new y-coordinate for the widget.
        """
        if widget.boundary.axis is Axis.y:
            widget.boundary.move_horizontal(x)
        else:
            widget.boundary.move_vertical(y)

        x -= widget.get_allocated_width() / 2
        y -= widget.get_allocated_height() / 2

        super().move(widget, x, y)

    def get_boundpoint(self, boundary: ZoneBoundary) -> Optional[BoundPoint]:
        """
        Retrieves the BoundPoint associated with a given boundary.

        :param boundary: The ZoneBoundary to find the BoundPoint for.
        :return: The associated BoundPoint, or None if not found.
        """
        return self._boundary_point_map[Axis.x].get(boundary) or self._boundary_point_map[Axis.y].get(boundary)

    def get_nearest_boundary(self, point: Point, axis: Optional[Axis] = None) -> ZoneBoundary:
        """
        Finds the nearest ZoneBoundary to a given point.

        :param point: The Point to find the nearest boundary to.
        :param axis: Optional axis to restrict the search to.
        :return: The nearest ZoneBoundary.
        """
        boundaries = self._boundary_point_map[axis].keys() or self.boundaries if axis else self.boundaries
        return min(boundaries, key=lambda boundary: point.distance(boundary.position))

    @staticmethod
    def create_boundaries(zones: List[Zone]) -> List[ZoneBoundary]:
        """
        Generates boundaries from a list of zones.

        :param zones: A list of Zone objects to generate boundaries from.
        :return: A list of ZoneBoundary objects.
        """
        graph = RectangleSideGraph(zones)
        return [ZoneBoundary(component) for component in graph.get_connected_components()]

    @staticmethod
    def create_boundpoints(boundaries: List[ZoneBoundary]) -> List[BoundPoint]:
        """
        Creates BoundPoint objects for a list of boundaries.

        :param boundaries: A list of ZoneBoundary objects.
        :return: A list of BoundPoint objects.
        """
        return [BoundPoint(boundary) for boundary in boundaries]

    def set_zones(self, zones: List[Zone]):
        """
        Sets up the editor with a new set of zones, creating boundaries and BoundPoints.

        :param zones: A list of Zone objects to set up the editor with.
        """
        self._clear()
        self.boundaries = self.create_boundaries(zones)
        for point in self.create_boundpoints(self.boundaries):
            self._boundary_point_map[point.boundary.axis][point.boundary] = point
            point.set_size_request(self.point_size, self.point_size)
            self.put(point, -self.point_size * 5, -self.point_size * 5)
            point.show()


class ZoneEditorWindow(TransparentApplicationWindow):
    """
    A window for editing and configuring zones using BoundPoint widgets.

    This class provides a graphical interface for manipulating and dividing zones
    within a workspace. It manages the interaction between the zone container,
    the editor for boundary points, and user inputs for zone manipulation.

    Attributes:
        _overlay (Gtk.Overlay): The overlay widget for combining multiple widgets on top of one another.
        _editor (Editor): An editor widget for managing BoundPoints and zone boundaries.
        _container (ZoneContainer): A container holding Zone objects.
        _zone_divider (Line): A line widget representing the current zone division position.
    """

    def __init__(self, schemas: List[Dict], _id: Optional[str] = None):
        """
        Initializes the ZoneEditorWindow with a list of dicts representing schema data.

        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        self.maximize()
        workarea = get_workarea()

        # Initialize attributes
        self._overlay = Gtk.Overlay()
        self._editor = Editor()
        self._container = ZoneContainer(schemas, _id)
        self._zone_divider = Line(0, 0, 0, 0)

        # Set child size requests
        self._container.set_size_request(workarea.width, workarea.height)
        self._editor.set_size_request(workarea.width, workarea.height)

        # Add CSS classes
        self._container.add_zone_style_class('zone-pane', 'passive-zone')

        # Add Line to represent zone division
        self._overlay.add_overlay(self._zone_divider)

        # Add primary widgets to the window
        self._overlay.add_overlay(self._container)
        self._overlay.add_overlay(self._editor)
        self.add(self._overlay)

        # Add Gdk events
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.KEY_RELEASE_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK
        )

        # Connect signals to handlers
        self._container.connect('size-allocate', self._on_container_allocation)
        self.connect('motion-notify-event', self._on_motion_notify)
        self.connect('key-press-event', self._on_key_press_event)
        self.connect('key-press-event', self._on_key_event)
        self.connect('key-release-event', self._on_key_event)
        self.connect('button-press-event', self._on_button_press)

    def _on_container_allocation(self, container: ZoneContainer, allocation: Gdk.Rectangle):
        """
        Handles the container's size-allocate signal to add allocated zones to the editor.

        This method is called when the container's size is allocated or changed. It updates
        the editor with the current set of zones in the container.

        :param container: The container that received the size-allocate signal.
        :param allocation: The new allocation containing the updated size information.
        """
        zones = container.get_children()
        self._editor.set_zones(zones)

    def _save_preset(self):
        # Normalize zone schemas and collect dictionary representations
        width, height = self._container.get_allocated_width(), self._container.get_allocated_height()
        schemas = [zone.schema.get_normalized(width, height).__dict__() for zone in self._container.get_children()]
        # Save preset
        presets = config.presets
        presets[self._container.id] = schemas
        config.save(presets, 'presets.json')

    def _set_zone_divider(self, x: float, y: float, axis: Optional[Axis] = None):
        """
        Sets the position of the zone divider based on the current pointer position.

        This method updates the position of the zone divider line, taking into account
        the nearest boundary and the current zone under the cursor.

        :param x: The x-coordinate of the pointer position.
        :param y: The y-coordinate of the pointer position.
        :param axis: Optional axis to constrain the divider movement. If None, uses the current axis.
        """
        axis = axis if axis else self._zone_divider.axis
        cursor = Point(x, y)

        # Get the allocation of zone under the pointer
        allocation = self._container.get_zone(x, y).get_allocation()

        # Snap divider position if within proximity to an existing boundary
        boundary = self._editor.get_nearest_boundary(cursor, axis)
        position = boundary.center if boundary.is_aligned(cursor) else cursor

        # Set the position of the zone divider vertically or horizontally
        x1, y1, x2, y2 = {
            Axis.x: (allocation.x, position.y, allocation.x + allocation.width, position.y),
            Axis.y: (position.x, allocation.y, position.x, allocation.y + allocation.height)
        }[axis]

        self._zone_divider.set_position(x1, y1, x2, y2)

    def _on_motion_notify(self, widget, event) -> bool:
        """
        Handles the motion-notify-event to update the zone divider line position and visibility.

        This method shows or hides the zone divider based on whether a boundary point is currently
        visible, and updates its position when visible.

        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        :return: False to allow further processing of the event.
        """
        if self._editor.visible_point is None:
            self._set_zone_divider(event.x, event.y)
            self._zone_divider.show()
        else:
            self._zone_divider.hide()
        return False

    def _on_key_event(self, widget, event):
        """
        Handles key events to toggle the zone divider axis when the Shift key is pressed.

        This method switches the zone divider between vertical and horizontal orientation
        when the Shift key is pressed or released.

        :param widget: The widget that received the event.
        :param event: The event object containing information about the key press/release event.
        """
        if event.keyval == Gdk.KEY_Shift_L:
            x, y = get_pointer_position()
            axis = Axis.x if self._zone_divider.axis is Axis.y else Axis.y
            self._set_zone_divider(x, y, axis)

    def _on_key_press_event(self, widget, event):
        # Check if Control is being held down
        ctrl = (event.state & Gdk.ModifierType.CONTROL_MASK)
        # Check for Ctrl+S hotkey
        if ctrl and event.keyval == Gdk.KEY_s:
            self._save_preset()

    def _on_button_press(self, widget, event) -> bool:
        """
        Handles the button-press event to initiate zone division.

        When the primary mouse button is pressed, this method identifies the
        Zone at the event coordinates and divides it using the zone divider,
        if the cursor is not intersecting any boundary buffer.

        :param widget: The widget that received the button press event.
        :param event: The Gdk.Event containing the event details, such as button and coordinates.
        :return: True to stop further handling of the event.
        """
        cursor = Point(event.x, event.y)
        boundary = self._editor.get_nearest_boundary(cursor, self._zone_divider.axis)
        # Divide zone if cursor does not intersect any boundary buffer.
        if event.button == Gdk.BUTTON_PRIMARY and not cursor.intersects(boundary.buffer):
            zone = self._container.get_zone(event.x, event.y)
            self._container.divide(zone, self._zone_divider)
        return True

    def show_all(self):
        """
        Shows all widgets within the window and presents the window.

        This method makes the window and all its child widgets visible and brings
        the window to the forefront of the user's display.
        """
        super().show_all()
        self.present()