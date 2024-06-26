import gi
from itertools import groupby

from shapely.geometry import LineString
from shapely.ops import linemerge

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from base import Axis, Side, Preset, PresetableMixin, GtkStyleableMixin, TransparentApplicationWindow


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


class ZoneEdge:
    """
    Represents a side of a ZonePane, allowing manipulation of its dimensions.

    Attributes:
        zone (ZonePane): The ZonePane object associated with this edge.
        side (Side): The specific side (TOP, BOTTOM, LEFT, RIGHT) of the ZonePane.
        axis (Axis): The axis (x or y) corresponding to the side.
    """

    def __init__(self, zone: ZonePane, side: Side):
        """
        Initializes the ZoneEdge with a ZonePane and a specified side.
        :param zone: The ZonePane object associated with this side.
        :param side: The specific side (TOP, BOTTOM, LEFT, RIGHT) of the ZonePane.
        """
        self.zone = zone  # The ZonePane object associated with this side
        self.side = side  # The specific side of the ZonePane
        self.axis = Axis.x if side in {Side.LEFT, Side.RIGHT} else Axis.y  # Determine the axis based on the side

    def get_position(self, normalized=False) -> LineString:
        """
        Gets the position of a ZonePanes side as a LineString.
        :param normalized: Returns normalized position if True.
        :return: A LineString representing the position of the side.
        """
        bounds = self.zone.preset if normalized else self.zone.get_allocation()
        match self.side:
            case Side.TOP:
                return LineString([(bounds.x, bounds.y), (bounds.x + bounds.width, bounds.y)])
            case Side.BOTTOM:
                return LineString([(bounds.x, bounds.y + bounds.height), (bounds.x + bounds.width, bounds.y + bounds.height)])
            case Side.LEFT:
                return LineString([(bounds.x, bounds.y), (bounds.x, bounds.y + bounds.height)])
            case Side.RIGHT:
                return LineString([(bounds.x + bounds.width, bounds.y), (bounds.x + bounds.width, bounds.y + bounds.height)])


class ZoneBoundary:
    """
    Represents a boundary formed by multiple ZoneEdge objects, allowing manipulation of their positions.

    Attributes:
        __edges (set): A set of ZoneEdge objects forming the edge.
        axis (Axis): The axis (x or y) along which the edge is aligned.
    """

    def __init__(self, edges: [ZoneEdge]):
        """
        Initializes the ZoneBoundary with a list of ZoneEdge objects.
        :param edges: A list of ZoneEdge objects forming the edge.
        """
        self.__edges = set()  # Initialize an empty set for ZoneEdge objects
        self.axis = self.__get_axis(edges)  # Determine the axis of the edge
        self.add_edges(edges)  # Add the sides to the edge

    def __is_edge(self, edges: [ZoneEdge]) -> bool:
        """
        Checks if the given sides form a valid contiguous and aligned edge.
        :param edges: A list of ZoneEdge objects to check.
        :return: True if the sides form a valid edge, False otherwise.
        """
        lines = [edge.get_position(normalized=True) for edge in edges]  # Get positions of the edges
        lines.sort(key=lambda line: line.bounds[0])  # Sort lines by their starting position on the axis
        axis_position = lines[0].coords[0][self.axis.value]  # Get the position on the axis

        # Verify that all LineString are contiguous and aligned
        for line1, line2 in zip(lines, lines[1:]):
            aligned = any(coord[self.axis.value] == axis_position for coord in line2.coords)
            connected = line1.touches(line2) or line1.intersects(line2)
            if not connected or not aligned:
                return False
        return True

    def __get_axis(self, edges: [ZoneEdge]) -> Axis:
        """
        Determines the axis of the ZoneBoundary based on the provided edges.
        :param edges: A list of ZoneEdge objects.
        :return: The axis (x or y) of the edge.
        """
        axes = {edge.axis for edge in edges}  # Get the set of axes from the sides
        assert len(axes) == 1, 'A ZoneBoundary must only contain ZoneEdges of the same axis. Either (LEFT, RIGHT) for X or (TOP, BOTTOM) for Y.'
        return axes.pop()  # Return the single axis

    def add_edges(self, edges: [ZoneEdge]) -> 'ZoneBoundary':
        """
        Adds more edges to the ZoneBoundary, ensuring they form a valid contiguous and aligned edge.
        :param edges: A list of ZoneEdge objects to add.
        :return: The ZoneBoundary object itself for chaining calls.
        """
        assert self.axis is self.__get_axis(edges), f'A ZoneBoundary must only contain ZoneEdges of the same axis. Current axis is {self.axis.name}.'

        # Copy the current set of edges and add the new edges
        new_edges = self.__edges.copy()
        new_edges.update(edges)

        # Check if the new set of edges forms a valid boundary
        if self.__is_edge(new_edges):
            self.__edges.update(edges)  # Update the set of edges with the new valid edges
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
        Gets the position of the ZoneBoundary as a LineString.
        :return: A LineString representing the position of the boundary.
        """
        lines = [edges.get_position() for edges in self.__edges]  # Get positions of the edges
        bounds = linemerge(lines).bounds  # Merge the lines and get the bounds
        return LineString([(bounds[0], bounds[1]), (bounds[2], bounds[3])])  # Create a LineString from the bounds

    def move_horizontal(self, position: int) -> None:
        """
        Moves the edge horizontally to a new position.
        :param position: Pixel value of a new position to move the edge.
        """
        if self.axis is Axis.x:
            for edge in self.__edges:
                allocation = edge.zone.get_allocation()
                if edge.side is Side.LEFT:
                    # Adjust the width and x-position when moving the left edge
                    allocation.width = (allocation.x + allocation.width) - position
                    allocation.x = position
                else:
                    # Adjust the width when moving the right edge
                    allocation.width = position - allocation.x
                edge.zone.size_allocate(allocation)

    def move_vertical(self, position: int) -> None:
        """
        Moves the edge vertically to a new position.
        :param position: Pixel value of a new position to move the edge.
        """
        if self.axis is Axis.y:
            for edge in self.__edges:
                allocation = edge.zone.get_allocation()
                if edge.side is Side.TOP:
                    # Adjust the height and y-position when moving the top edge
                    allocation.height = (allocation.y + allocation.height) - position
                    allocation.y = position
                else:
                    # Adjust the height when moving the bottom edge
                    allocation.height = position - allocation.y
                edge.zone.size_allocate(allocation)


class ZonePanePositionGraph:
    """
    Represents a graph of ZonePane positions, grouping sides by axis and forming ZoneBoundary's.
    """
    def __init__(self, zones: [ZonePane]):
        """
        Initializes the ZonePanePositionGraph with a list of ZonePane objects.

        This constructor processes the given zones to create a list of ZoneBoundary's by:
        1. Filtering all x-axis and y-axis sides into separate lists.
        2. Sorting and grouping the sides by their respective axes.
        3. Removing sides that border the screen edges.
        4. Creating ZoneBoundary's from the grouped sides.

        :param zones: List of ZonePane objects to be processed.
        """
        super().__init__()
        self.boundaries = []  # Initialize the list to store ZoneBoundary objects

        # Filter all x-axis and y-axis sides into separate lists
        x_sides, y_sides = [], []
        for zone in zones:
            x_sides.append(ZoneEdge(zone, Side.LEFT))
            x_sides.append(ZoneEdge(zone, Side.RIGHT))
            y_sides.append(ZoneEdge(zone, Side.TOP))
            y_sides.append(ZoneEdge(zone, Side.BOTTOM))

        # Order sides by axis and group matching values of the opposite axis after sorting
        x_sides = self.__sort_and_group(x_sides, Axis.x)
        y_sides = self.__sort_and_group(y_sides, Axis.y)

        # Remove all sides that border the container edges
        if len(x_sides) >= 2:
            x_sides = x_sides[1:-1]  # Remove the left and right container edges from x_sides
        if len(y_sides) >= 2:
            y_sides = y_sides[1:-1]  # Remove the top and bottom container edges from y_sides

        # Create ZoneBoundary's from the grouped sides
        for group in x_sides:
            boundaries = self.__get_zone_boundaries(group)
            self.boundaries.extend(boundaries)

        for group in y_sides:
            boundaries = self.__get_zone_boundaries(group)
            self.boundaries.extend(boundaries)

    def __sort_and_group(self, edges: list[ZoneEdge], axis: Axis) -> list[list[ZoneEdge]]:
        """
        Sorts a list of ZoneEdge objects based on their positions along a given axis and then groups them.

        The method first sorts the edges based on the specified axis. If the axis is x, it sorts by the x-coordinate;
        if the axis is y, it sorts by the y-coordinate. After sorting, it groups the edges by their position on the
        opposite axis.

        :param edges: List of ZoneEdge objects to be sorted and grouped.
        :param axis: The axis (x or y) to use for sorting and grouping.
        :return: A list of lists, where each sublist contains ZoneEdge objects grouped by their position
                 on the opposite axis.
        """
        # Determine the opposite axis for sorting
        op_axis = Axis.x.value if axis is Axis.x else Axis.y.value

        # Sort edges by their positions along the opposite axis and the given axis
        edges.sort(key=lambda edge: (
            edge.get_position(normalized=True).bounds[op_axis],
            edge.get_position(normalized=True).bounds[axis.value]
        ))

        # Group the sorted sides by their position along the opposite axis
        grouped_edges = [list(g) for k, g in groupby(edges, key=lambda edge: edge.get_position(normalized=True).bounds[op_axis])]

        return grouped_edges

    def __get_zone_boundaries(self, edges: list[ZoneEdge]) -> list[ZoneBoundary]:
        """
        Processes a list of ZoneEdge objects to group contiguous sides into ZoneBoundary objects.

        This method iterates through the list of sides, identifying groups of contiguous sides based on their positions.
        It then creates ZoneBoundary objects for each group of contiguous sides and returns a list of these ZoneBoundary objects.

        :param edges: List of ZoneEdge objects to be processed into ZoneBoundary objects.
        :return: A list of ZoneBoundary objects, each representing a group of aligned contiguous ZoneEdges.
        """
        boundaries = []  # Initialize the list to store ZoneBoundary objects
        contigous_group = [edges[0]]  # Start with the first side in the contiguous group

        # Iterate through pairs of consecutive sides
        for side1, side2 in zip(edges, edges[1:]):
            line1, line2 = side1.get_position(normalized=True), side2.get_position(normalized=True)
            # Check if the current side is contiguous with the next side
            if line1.touches(line2) or line1.intersects(line2):
                contigous_group.append(side2)  # Add to the current contiguous group
            else:
                # Split the group and start a new one since they aren't contiguous but do align
                boundaries.append(ZoneBoundary(contigous_group))  # Create a ZoneBoundary for the current group
                contigous_group = [side2]  # Start a new group with the next side

        # Add the remaining sides as a ZoneBoundary if there are any left
        if len(contigous_group) != 0:
            boundaries.append(ZoneBoundary(contigous_group))

        return boundaries  # Return the list of ZoneBoundary objects


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

        self.connect('size-allocate', self.__on_size_allocate)

    def __on_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to scale and allocate sizes for child ZonePane objects.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        for child in self.get_children():
            child.size_allocate(child.preset.scale(allocation))

    def get_position_graph(self):
        return ZonePanePositionGraph(self.get_children())

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
        self.maximize()

        # Create the ZoneContainer and add style classes
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.__active_zone = None
        self.add(self.__container)  # Add the container to the window

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
            allocation = zone.get_allocation()
            if allocation.x <= x < allocation.x + allocation.width and allocation.y <= y < allocation.y + allocation.height:
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
