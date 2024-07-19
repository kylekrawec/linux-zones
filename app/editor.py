import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

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
        # Set object to be a draggable source.
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.MOVE)
        self.drag_source_add_text_targets()

        self.boundary = boundary


class Editor(Gtk.Fixed):
    def move(self, widget: BoundPoint, x: int, y: int):
        if widget.boundary.axis is Axis.y:
            widget.boundary.move_horizontal(x)
        else:
            widget.boundary.move_vertical(y)

        x -= widget.get_allocated_width() / 2
        y -= widget.get_allocated_height() / 2
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

        # Make the window a drag destination
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.MOVE)
        self.drag_dest_add_text_targets()

        # Initialize attributes
        self._threshold = 50
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
        self.connect('drag-motion', self._on_boundary_drag)

    def _on_container_allocation(self, container: ZoneContainer, allocation: Gdk.Rectangle) -> None:
        """
        Handles the container's size-allocate signal to adjust the BoundPoints.

        This method recalculates the threshold and point sizes based on the new allocation,
        removes existing BoundPoints, and adds new ones based on the updated container layout.

        :param container: The container that received the size-allocate signal.
        :param allocation: The new allocation containing the updated size information.
        """
        # Update threshold and point size based on new allocation
        self._threshold = round(min(allocation.width, allocation.height) * 0.04)
        self._point_size = round(min(allocation.width, allocation.height) * 0.025)

        # Remove existing BoundPoints
        for child in self._editor.get_children():
            if isinstance(child, BoundPoint):
                self._editor.remove(child)

        # Create new graph and add boundary points
        graph = RectangleSideGraph(container.get_children())
        self._boundaries = self._create_boundaries(graph)
        self._add_boundary_points(self._boundaries[Axis.x] + self._boundaries[Axis.y])

    def _create_boundaries(self, graph: RectangleSideGraph) -> dict[Axis, list[ZoneBoundary]]:
        """
        Creates ZoneBoundary objects from a RectangleSideGraph and organizes them by axis.

        This method processes the connected components of the graph, creates ZoneBoundary
        objects for each component, and sorts them into horizontal (x-axis) and vertical
        (y-axis) boundaries.

        :param graph: A RectangleSideGraph representing the layout of zones.
        :return: A dictionary with Axis keys and lists of ZoneBoundary objects as values.
        """
        boundaries = {Axis.x: [], Axis.y: []}
        # Create boundary for each component and organize by axis
        for component in graph.get_connected_components():
            boundary = ZoneBoundary(component)
            boundaries[boundary.axis].append(boundary)
        return boundaries

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

    def _on_boundary_drag(self, editor, context, x, y, time) -> bool:
        """
        Handles the drag-motion signal to move the BoundPoint widget.
        :param editor: The editor class handling BoundPoints.
        """
        point = Gtk.drag_get_source_widget(context)
        self._editor.move(point, x, y)
        return True

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
        if event.button == Gdk.BUTTON_PRIMARY and not self._focus_point:
            zone = self._container.get_zone(event.x, event.y)
            self._container.divide(zone, self._edge_divider)
        return True

    def show_all(self):
        """
        Shows all widgets within the window and presents the window.
        """
        super().show_all()
        self.present()
