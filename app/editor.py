import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import base
from base import Axis
from zones import ZoneBoundary, ZoneContainer
from display import get_workarea


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


class ZoneEditorWindow(base.TransparentApplicationWindow):
    """
    A window for editing and configuring zones using BoundPoint widgets.

    Attributes:
        __overlay (Gtk.Overlay): The overlay widget for combining multiple widgets on top of one another.
        __container (zones.ZoneContainer): A container holding ZonePane objects.
        __editor (Gtk.Fixed): A fixed container holding BoundsPoints.
        size_allocate_id (int): The ID for the size-allocate signal handler.
    """

    def __init__(self, preset: [base.Preset]):
        """
        Initializes the ZoneEditorWindow with a list of Preset objects.
        :param preset: A list of Preset objects to initialize ZonePane objects.
        """
        super().__init__()
        self.set_window_bounds(get_workarea())  # Set the window bounds to the work area

        self.__threshold = 50  # Defines a threshold for boundary proximity detection
        self.__focus_point = None  # Tracks the currently focused point to limit only one point shown at a time
        self.__overlay = Gtk.Overlay()
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.__editor = Gtk.Fixed()

        # Add primary widgets to the window
        self.__overlay.add_overlay(self.__container)
        self.__overlay.add_overlay(self.__editor)
        self.add(self.__overlay)

        # Layout boundary points based on zone boundary relations and position
        for boundary in self.__container.get_position_graph().boundaries:
            point = BoundPoint(boundary)  # Create a BoundPoint widget for each boundary
            point.connect("motion-notify-event", self.__on_button_motion)  # Connect motion-notify-event to local handler
            self.__editor.add(point)

        # Connect Gtk signals to handlers
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)  # Add mask to capture pointer motion events
        self.connect("motion-notify-event", self.__on_motion_notify)
        self.point_allocation_handler_id = self.connect('size-allocate', self.__point_size_allocate)

    def __point_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to adjust the size of BoundPoint widgets.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        self.threshold = min(allocation.width, allocation.height) * 0.05  # Adjust threshold based on allocation
        size = min(allocation.width, allocation.height) * 0.025  # Calculate the size based on the allocation
        for point in self.__editor.get_children():
            point.set_size_request(size, size)  # Set the size request for each point
            point.hide()
        self.disconnect(self.point_allocation_handler_id)  # Disconnect the signal handler to prevent interference with points

    def __on_button_motion(self, widget, event) -> None:
        """
        Handles the motion-notify-event to move the BoundPoint widget horizontally or vertically.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        x, y = widget.translate_coordinates(self, event.x, event.y)  # Translate coordinates relative to the window
        offset_size = widget.get_allocated_width() / 2
        x -= offset_size  # Adjust x-coordinate to get widget center using offset
        y -= offset_size  # Adjust y-coordinate to get widget center using offset
        if widget.boundary.axis is Axis.x and x >= 0:
            self.__editor.move(widget, x, y)  # Move the widget horizontally if axis is x
        elif y >= 0:
            self.__editor.move(widget, x, y)  # Move the widget vertically if axis is y

    def __on_motion_notify(self, widget, event) -> None:
        """
        Handles the motion-notify-event to show and move the BoundPoint widgets based on proximity to the pointer and
        alligns with boundary axis.
        :param widget: The widget that received the event.
        :param event: The event object containing information about the motion event.
        """
        for point in self.__editor.get_children():
            point_offset = point.get_allocated_width() / 2  # Calculate the offset for the point
            x, y = point.boundary.get_center()  # Get the center coordinates of the boundary
            if point.boundary.axis is Axis.x and -self.__threshold < (event.x - x) < self.__threshold:
                if point.is_visible() or self.__focus_point is None:
                    point.show()
                    self.__focus_point = point
                self.__editor.move(point, x - point_offset, event.y - point_offset)  # Move the point horizontally
            elif point.boundary.axis is Axis.y and -self.__threshold < (event.y - y) < self.__threshold:
                if point.is_visible() or self.__focus_point is None:
                    point.show()
                    self.__focus_point = point
                self.__editor.move(point, event.x - point_offset, y - point_offset)  # Move the point vertically
            else:
                if point.is_visible():
                    self.__focus_point = None
                point.hide()  # Hide the point if not within the __threshold

