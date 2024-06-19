import gi
from itertools import groupby
from shapely.geometry import LineString
from shapely.ops import linemerge

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from base import Axis, Side, Preset, PresetableMixin, GtkStyleableMixin, TransparentApplicationWindow
from display import get_workarea


class ZonePane(PresetableMixin, GtkStyleableMixin, Gtk.Box):
    """A custom Gtk.Box that represets a basic zone area."""
    def __init__(self, preset: Preset):
        """
        :param preset: A Preset object containing configuration for the ZonePane.
        """
        Gtk.Box.__init__(self)
        PresetableMixin.__init__(self, preset)
        self.label = Gtk.Label()
        self.set_center_widget(self.label)

        # If the preset has a label assign it
        if self.preset.label:
            self.label.set_text(self.preset.label)


class ZoneSide:
    """
    Represents a side of a ZonePane, allowing manipulation of its dimensions.

    Attributes:
        zone (ZonePane): The ZonePane object associated with this side.
        side (Side): The specific side (TOP, BOTTOM, LEFT, RIGHT) of the ZonePane.
        axis (Axis): The axis (x or y) corresponding to the side.
    """

    def __init__(self, zone: ZonePane, side: Side):
        """
        Initializes the ZoneSide with a ZonePane and a specified side.
        :param zone: The ZonePane object associated with this side.
        :param side: The specific side (TOP, BOTTOM, LEFT, RIGHT) of the ZonePane.
        """
        self.zone = zone  # The ZonePane object associated with this side
        self.side = side  # The specific side of the ZonePane
        self.axis = Axis.x if side in {Side.LEFT, Side.RIGHT} else Axis.y  # Determine the axis based on the side

    def get_position(self) -> LineString:
        """
        Gets the position of a ZonePanes side as a LineString.
        :return: A LineString representing the position of the side.
        """
        return self.zone.preset.get_side_position(self.side)

    def move(self, position: int) -> None:
        """
        Moves the side to a new position, updating the dimensions of the ZonePane.
        :param position: The new position to move the side to.
        """
        match self.side:
            case Side.TOP:
                # Adjust the height and y-position when moving the top side
                self.zone.preset.height = (self.zone.preset.y + self.zone.preset.height) - position
                self.zone.preset.y = position
            case Side.BOTTOM:
                # Adjust the height when moving the bottom side
                self.zone.preset.height = position - self.zone.preset.y
            case Side.LEFT:
                # Adjust the width and x-position when moving the left side
                self.zone.preset.width = (self.zone.preset.x + self.zone.preset.width) - position
                self.zone.preset.x = position
            case Side.RIGHT:
                # Adjust the width when moving the right side
                self.zone.preset.width = position - self.zone.preset.x
        # Allocate the ZonePane using the new bounds
        self.zone.size_allocate(self.zone.preset.get_bounds())


class ZoneEdge:
    """
    Represents an edge formed by multiple ZoneSide objects, allowing manipulation of their positions.

    Attributes:
        __sides (set): A set of ZoneSide objects forming the edge.
        axis (Axis): The axis (x or y) along which the edge is aligned.
    """

    def __init__(self, sides: [ZoneSide]):
        """
        Initializes the ZoneEdge with a list of ZoneSide objects.
        :param sides: A list of ZoneSide objects forming the edge.
        """
        self.__sides = set()  # Initialize an empty set for ZoneSide objects
        self.axis = self.__get_axis(sides)  # Determine the axis of the edge
        self.add_sides(sides)  # Add the sides to the edge

    def __is_edge(self, sides: [ZoneSide]) -> bool:
        """
        Checks if the given sides form a valid contiguous and aligned edge.
        :param sides: A list of ZoneSide objects to check.
        :return: True if the sides form a valid edge, False otherwise.
        """
        lines = [side.get_position() for side in sides]  # Get positions of the sides
        lines.sort(key=lambda line: line.bounds[0])  # Sort lines by their starting position on the axis
        axis_position = lines[0].coords[0][self.axis.value]  # Get the position on the axis

        # Verify that all LineString are contiguous and aligned
        for line1, line2 in zip(lines, lines[1:]):
            aligned = any(coord[self.axis.value] == axis_position for coord in line2.coords)
            connected = line1.touches(line2) or line1.intersects(line2)
            if not connected or not aligned:
                return False
        return True

    def __get_axis(self, sides: [ZoneSide]) -> Axis:
        """
        Determines the axis of the edge based on the provided sides.
        :param sides: A list of ZoneSide objects.
        :return: The axis (x or y) of the edge.
        """
        axes = {side.axis for side in sides}  # Get the set of axes from the sides
        assert len(axes) == 1, 'A ZoneEdge must only contain ZoneSides of the same axis. Either (LEFT, RIGHT) for X or (TOP, BOTTOM) for Y.'
        return axes.pop()  # Return the single axis

    def add_sides(self, sides: [ZoneSide]) -> 'ZoneEdge':
        """
        Adds more sides to the edge, ensuring they form a valid contiguous and aligned edge.
        :param sides: A list of ZoneSide objects to add.
        :return: The ZoneEdge object itself for chaining calls.
        """
        assert self.axis is self.__get_axis(sides), f'A ZoneEdge must only contain ZoneSides of the same axis. Current axis is {self.axis.name}.'

        # Copy the current set of sides and add the new sides
        new_sides = self.__sides.copy()
        new_sides.update(sides)

        # Check if the new set of sides forms a valid edge
        if self.__is_edge(new_sides):
            self.__sides.update(sides)  # Update the set of sides with the new valid sides
        return self

    def get_center(self) -> tuple[float, float]:
        """
        Calculates and returns the center point of the line segment.
        :return: A tuple (center_x, center_y) representing the center point of the line.
        """
        minx, miny, maxx, maxy = self.get_position().bounds  # Get the bounds of the edge
        center_x = (minx + maxx) / 2  # Calculate the center x-coordinate
        center_y = (miny + maxy) / 2  # Calculate the center y-coordinate
        return center_x, center_y

    def get_position(self) -> LineString:
        """
        Gets the position of the edge as a LineString.
        :return: A LineString representing the position of the edge.
        """
        lines = [side.get_position() for side in self.__sides]  # Get positions of the sides
        bounds = linemerge(lines).bounds  # Merge the lines and get the bounds
        return LineString([(bounds[0], bounds[1]), (bounds[2], bounds[3])])  # Create a LineString from the bounds

    def move_horizontal(self, position: int) -> None:
        """
        Moves the edge horizontally to a new position.
        :param position: The new horizontal position to move the edge to.
        """
        if self.axis is Axis.x:
            for side in self.__sides:
                side.move(position)  # Move each side to the new position

    def move_vertical(self, position: int) -> None:
        """
        Moves the edge vertically to a new position.
        :param position: The new vertical position to move the edge to.
        """
        if self.axis is Axis.y:
            for side in self.__sides:
                side.move(position)  # Move each side to the new position


class ZonePanePositionGraph:
    """
    Represents a graph of ZonePane positions, grouping sides by axis and forming ZoneEdges.
    """
    def __init__(self, zones: [ZonePane]):
        """
        Initializes the ZonePanePositionGraph with a list of ZonePane objects.

        This constructor processes the given zones to create a list of ZoneEdges by:
        1. Filtering all x-axis and y-axis sides into separate lists.
        2. Sorting and grouping the sides by their respective axes.
        3. Removing sides that border the screen edges.
        4. Creating ZoneEdges from the grouped sides.

        :param zones: List of ZonePane objects to be processed.
        """
        super().__init__()
        self.edges = []  # Initialize the list to store ZoneEdge objects

        # Filter all x-axis and y-axis sides into separate lists
        x_sides, y_sides = [], []
        for zone in zones:
            x_sides.append(ZoneSide(zone, Side.LEFT))
            x_sides.append(ZoneSide(zone, Side.RIGHT))
            y_sides.append(ZoneSide(zone, Side.TOP))
            y_sides.append(ZoneSide(zone, Side.BOTTOM))

        # Order sides by axis and group matching values of the opposite axis after sorting
        x_sides = self.__sort_and_group(x_sides, Axis.x)
        y_sides = self.__sort_and_group(y_sides, Axis.y)

        # Remove all sides that border the container edges
        if len(x_sides) >= 2:
            x_sides = x_sides[1:-1]  # Remove the left and right container edges from x_sides
        if len(y_sides) >= 2:
            y_sides = y_sides[1:-1]  # Remove the top and bottom container edges from y_sides

        # Create ZoneEdges from the grouped sides
        for group in x_sides:
            zone_edges = self.__get_zone_edges(group)
            self.edges.extend(zone_edges)

        for group in y_sides:
            zone_edges = self.__get_zone_edges(group)
            self.edges.extend(zone_edges)

    def __sort_and_group(self, sides: list[ZoneSide], axis: Axis) -> list[list[ZoneSide]]:
        """
        Sorts a list of ZoneSide objects based on their positions along a given axis and then groups them.

        The method first sorts the sides based on the specified axis. If the axis is x, it sorts by the x-coordinate;
        if the axis is y, it sorts by the y-coordinate. After sorting, it groups the sides by their position on the
        opposite axis.

        :param sides: List of ZoneSide objects to be sorted and grouped.
        :param axis: The axis (x or y) to use for sorting and grouping.
        :return: A list of lists, where each sublist contains ZoneSide objects grouped by their position
                 on the opposite axis.
        """
        # Determine the opposite axis for sorting
        op_axis = Axis.x.value if axis is Axis.x else Axis.y.value

        # Sort sides by their positions along the opposite axis and the given axis
        sides.sort(key=lambda side: (side.get_position().bounds[op_axis], side.get_position().bounds[axis.value]))

        # Group the sorted sides by their position along the opposite axis
        grouped_sides = [list(g) for k, g in groupby(sides, key=lambda side: side.get_position().bounds[op_axis])]

        return grouped_sides

    def __get_zone_edges(self, sides: list[ZoneSide]) -> list[ZoneEdge]:
        """
        Processes a list of ZoneSide objects to group contiguous sides into ZoneEdge objects.

        This method iterates through the list of sides, identifying groups of contiguous sides based on their positions.
        It then creates ZoneEdge objects for each group of contiguous sides and returns a list of these ZoneEdge objects.

        :param sides: List of ZoneSide objects to be processed into ZoneEdge objects.
        :return: A list of ZoneEdge objects, each representing a group of aligned contiguous ZoneSides.
        """
        edges = []  # Initialize the list to store ZoneEdge objects
        contigous_group = [sides[0]]  # Start with the first side in the contiguous group

        # Iterate through pairs of consecutive sides
        for side1, side2 in zip(sides, sides[1:]):
            line1, line2 = side1.get_position(), side2.get_position()
            # Check if the current side is contiguous with the next side
            if line1.touches(line2) or line1.intersects(line2):
                contigous_group.append(side2)  # Add to the current contiguous group
            else:
                # Split the group and start a new one since they aren't contiguous but do align
                edges.append(ZoneEdge(contigous_group))  # Create a ZoneEdge for the current group
                contigous_group = [side2]  # Start a new group with the next side

        # Add the remaining sides as a ZoneEdge if there are any left
        if len(contigous_group) != 0:
            edges.append(ZoneEdge(contigous_group))

        return edges  # Return the list of ZoneEdge objects


class ZoneContainer(Gtk.Fixed):
    """
    A container that holds multiple ZonePane objects and manages their positions and styles.

    Attributes:
        position_graph (ZonePanePositionGraph): Graph representing positions of ZonePane objects.
    """

    def __init__(self, preset: [Preset]):
        """
        Initializes the ZoneContainer with a list of Preset objects.
        :param preset: A list of Preset objects to initialize ZonePane objects.
        """
        super().__init__()
        for preset in preset:
            self.add(ZonePane(preset))  # Add ZonePane objects to the container
        self.position_graph = ZonePanePositionGraph(self.get_children())  # Initialize the position graph
        self.connect('size-allocate', self.__on_size_allocate)

    def __on_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to scale and allocate sizes for child ZonePane objects.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        for child in self.get_children():
            if not child.preset.is_scaled():
                child.preset.scale(allocation)  # Scale the preset according to the new allocation
            child.size_allocate(child.preset.get_bounds())  # Allocate the new size to the child

    def add_zone_style_class(self, *style_classes):
        """
        Adds style classes to all ZonePane children in the container.
        :param style_classes: One or more style class names to add.
        :return: The ZoneContainer object itself for chaining calls.
        """
        for child in self.get_children():
            child.add_style_class(*style_classes)  # Add style classes to each child
        return self


class ZoneDisplayWindow(TransparentApplicationWindow):
    """
    A window that displays and manages multiple ZonePane objects within a ZoneContainer.

    Attributes:
        __container (ZoneContainer): The container holding ZonePane objects.
        __active_zone (ZonePane): The currently active ZonePane object.
    """

    def __init__(self, preset: [Preset]):
        """
        Initializes the ZoneDisplayWindow with a list of Preset objects.
        :param preset: A list of Preset objects to initialize ZonePane objects.
        """
        super().__init__()
        # Create the ZoneContainer and add style classes
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.__active_zone = None
        self.add(self.__container)  # Add the container to the window
        self.set_window_bounds(get_workarea())  # Set the window bounds to the current workarea

    def get_zones(self) -> [ZonePane]:
        """
        Retrieves all ZonePane objects within the container.
        :return: A list of ZonePane objects.
        """
        return self.__container.get_children()

    def get_zone(self, x, y) -> ZonePane:
        """
        Retrieves the ZonePane object at the specified coordinates.
        :param x: The x-coordinate.
        :param y: The y-coordinate.
        :return: The ZonePane object at the specified coordinates.
        """
        # Verify the window has already been allocated.
        assert self.get_allocated_width() != 0 and self.get_allocated_height() != 0, \
            f'Allocated width and/or height is zero. {self.__class__.__name__} must be size allocated before use.'

        for zone in self.__container.get_children():
            if zone.preset.x <= x < zone.preset.x + zone.preset.width and zone.preset.y <= y < zone.preset.y + zone.preset.height:
                return zone

    def set_active(self, zone: ZonePane) -> None:
        """
        Sets the specified ZonePane as the active zone.
        :param zone: The ZonePane object to set as active.
        """
        assert zone in self.__container.get_children(), f"Zone must be a child of {self.__container.__class__.__name__}"
        if self.__active_zone:
            # Remove the active style from the previously active zone
            self.__active_zone.remove_style_class('active-zone').add_style_class('passive-zone')
        zone.remove_style_class('passive-zone').add_style_class('active-zone')  # Add the active style to the new active zone
        self.__active_zone = zone  # Update the active zone

    def set_preset(self, preset: [Preset]) -> None:
        """
        Sets a new list of Preset objects for the ZoneDisplayWindow.
        :param preset: A new list of Preset objects.
        """
        self.remove(self.__container)  # Remove the current container
        # Create a new container with the new preset and add style classes
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.add(self.__container)  # Add the new container to the window
