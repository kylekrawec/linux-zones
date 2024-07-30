import gi
import math
import networkx as nx
from itertools import groupby, chain

import shapely
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, unary_union
from typing import Optional, Tuple, Dict, List, Set

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

from config import config
from widgets import Line
from display import get_workarea
from base import Axis, Side, AbstractRectangleSide, Schema, TransparentApplicationWindow
from base import GtkStyleableMixin, SchemableMixin


class Zone(Gtk.Box, SchemableMixin, GtkStyleableMixin):
    """
    A custom Gtk.Box that represents a basic zone area.

    This class combines functionalities of Gtk.Box, SchemableMixin, and GtkStyleableMixin
    to represent a zone area with an associated schema and styling capabilities.

    Attributes:
        schema (Schema): The schema object containing the bounds and ID of the zone.
        label (Gtk.Label): A label widget for displaying text within the zone.
    """

    def __init__(self, schema: Schema):
        """
        Initializes the Zone with a given schema.

        :param schema: The Schema object containing the bounds and ID for the zone.
        """
        Gtk.Box.__init__(self)
        SchemableMixin.__init__(self, schema)
        self.label = Gtk.Label()
        self.set_center_widget(self.label)

    def resize(self, allocation: Gdk.Rectangle) -> None:
        """
        Resizes the zone based on a new allocation.

        Updates the schema attributes (x, y, width, height) based on the new allocation
        and then calls the size_allocate method to apply the changes to the Gtk.Box.

        :param allocation: The Gdk.Rectangle object containing the new size and position.
        """
        self.schema.x = allocation.x
        self.schema.y = allocation.y
        self.schema.width = allocation.width
        self.schema.height = allocation.height
        self.size_allocate(allocation)


class ZoneEdge(AbstractRectangleSide):
    """
    Represents a side of a Zone object, allowing manipulation of its dimensions.

    Attributes:
        zone (Zone): The Zone object associated with this edge.
        side (Side): The specific side (TOP, BOTTOM, LEFT, RIGHT) of the Zone.
        axis (Axis): The axis (x or y) corresponding to the side.
    """
    def __init__(self, zone: Zone, side: Side):
        """
        Initializes the ZoneEdge with a Zone and a specified side.

        :param zone: The Zone object associated with this side.
        :param side: The specific side (TOP, BOTTOM, LEFT, RIGHT) of the Zone.
        """
        super().__init__(zone.schema, side)
        self.zone = zone  # The Zone object associated with this side
        self.axis = Axis.x if side in {Side.TOP, Side.BOTTOM} else Axis.y  # Determine the axis based on the side

    @property
    def rectangle(self) -> Gdk.Rectangle:
        return self.zone.schema.rectangle


class ZoneBoundary:
    """
    Represents a boundary formed by multiple ZoneEdge objects, allowing manipulation of their positions.

    This class manages a set of ZoneEdge objects that together form a single boundary in the zone layout.
    It provides methods for initializing, accessing, and manipulating the boundary's geometry and position.

    Attributes:
        _edges (set): A set of ZoneEdge objects forming the boundary.
        _axis (Axis): The axis (x or y) along which the boundary is aligned.
        _position (LineString): The line representing the boundary's position.
        _center (Point): The center point of the boundary.
        _buffer (Geometry): A buffer area surrounding the boundary's position.
    """

    def __init__(self, edges: List[ZoneEdge]):
        """
        Initializes the ZoneBoundary with a list of ZoneEdge objects.

        :param edges: A list of ZoneEdge objects forming the boundary.
        """
        self._edges = set(edges)
        self._axis = self._get_axis(self._edges)
        self._set_geometry_attributes()

    def _set_geometry_attributes(self):
        """
        Calculates and sets the geometric attributes of the boundary.

        This method should be called whenever the boundary's position changes.
        """
        self._position = self._get_position()
        self._center = self._get_center()
        self._buffer = self._get_buffer(config.settings.get('boundary-buffer-size'))

    def _get_axis(self, edges: Set[ZoneEdge]) -> Axis:
        """
        Determines the axis of the ZoneBoundary based on the provided edges.

        :param edges: A set of ZoneEdge objects.
        :return: The axis (x or y) of the boundary.
        :raises AssertionError: If edges are not all on the same axis.
        """
        axes = {edge.axis for edge in edges}
        assert len(axes) == 1, 'A ZoneBoundary must only contain ZoneEdges of the same axis. Either (LEFT, RIGHT) for X or (TOP, BOTTOM) for Y.'
        return axes.pop()

    def _get_position(self) -> LineString:
        """
        Calculates the position of the ZoneBoundary as a LineString.

        :return: A LineString representing the boundary's position.
        """
        lines = [edge.position for edge in self._edges]
        bounds = linemerge(lines).bounds
        return LineString([(bounds[0], bounds[1]), (bounds[2], bounds[3])])

    def _get_center(self) -> Point:
        """
        Calculates the center point of the ZoneBoundary.

        :return: A Point representing the center of the boundary.
        """
        minx, miny, maxx, maxy = self._position.bounds
        x = (minx + maxx) / 2
        y = (miny + maxy) / 2
        return Point(x, y)

    def _get_buffer(self, distance: int) -> shapely.buffer:
        """
        Creates a buffer around the boundary's position that extends to the sides but not the ends.

        :param distance: The buffer distance.
        :return: A Shapely geometry representing the buffer area.
        """
        # Create normal buffer
        buffer = self._position.buffer(distance, cap_style=3)  # cap_style=3 for flat ends

        # Create buffers at start and end points
        start_point = Point(self._position.coords[0])
        end_point = Point(self._position.coords[-1])
        start_buffer = start_point.buffer(distance)
        end_buffer = end_point.buffer(distance)

        # Subtract end buffers from full buffer
        return buffer.difference(unary_union([start_buffer, end_buffer]))

    @property
    def axis(self) -> Axis:
        """The axis along which the boundary is aligned."""
        return self._axis

    @property
    def position(self) -> LineString:
        """The LineString representing the boundary's position."""
        return self._position

    @property
    def center(self) -> Point:
        """The center point of the boundary."""
        return self._center

    @property
    def buffer(self) -> shapely.buffer:
        """The buffer area surrounding the boundary's position."""
        return self._buffer

    def is_aligned(self, point: Point) -> bool:
        """
        Checks if a given point is aligned with the boundary's longest edge within the buffer distance.

        :param point: The Point to check for alignment.
        :return: True if the point is aligned, False otherwise.
        """
        spread = abs(point.y - self.center.y) if self.axis is Axis.x else abs(point.x - self.center.x)
        return spread <= config.settings.get('boundary-buffer-size')

    def get_edges(self) -> List[ZoneEdge]:
        """
        Returns a list of all ZoneEdge objects that form this boundary.

        :return: A list of ZoneEdge objects.
        """
        return list(self._edges)

    def move_horizontal(self, position: int) -> None:
        """
        Moves the boundary horizontally to a new position.

        This method adjusts the width of adjacent zones when moving a vertical boundary.

        :param position: New x-coordinate for the boundary.
        """
        if self.axis is Axis.y:
            for edge in self._edges:
                allocation = edge.rectangle
                if edge.side is Side.LEFT:
                    # Adjust the width and x-position when moving the left edge
                    allocation.width = (allocation.x + allocation.width) - position
                    allocation.x = position
                else:
                    # Adjust the width when moving the right edge
                    allocation.width = position - allocation.x
                edge.zone.resize(allocation)
            self._set_geometry_attributes()

    def move_vertical(self, position: int) -> None:
        """
        Moves the boundary vertically to a new position.

        This method adjusts the height of adjacent zones when moving a horizontal boundary.

        :param position: New y-coordinate for the boundary.
        """
        if self.axis is Axis.x:
            for edge in self._edges:
                allocation = edge.rectangle
                if edge.side is Side.TOP:
                    # Adjust the height and y-position when moving the top edge
                    allocation.height = (allocation.y + allocation.height) - position
                    allocation.y = position
                else:
                    # Adjust the height when moving the bottom edge
                    allocation.height = position - allocation.y
                edge.zone.resize(allocation)
            self._set_geometry_attributes()


class RectangleSideGraph:
    """
    A graph of rectangle edge relations.

    This class represents a graph where nodes correspond to edges of rectangles defined by a Schema objects. It allows
    for reading and saving graph structures, generating connections based on rectangle edge positions, and retrieving
    connected components.

    Attributes:
        _graph (nx.Graph): The underlying networkx Graph object storing rectangle edge relations.
    """

    def __init__(self, zones: List[Zone]):
        """
        Initializes the RectangleSideGraph with a list of Schema objects generating a graph of rectangle edge relations
        based on their properties.

        :param zones: A list containing Zone objects representing rectangles.
        """
        super().__init__()
        self._graph = nx.Graph()
        self._generate(zones)

    def read_file(self, filename: str) -> None:
        """
        Reads a graph structure from a file and initializes the internal __graph.

        :param filename: The name of the file containing the graph structure.
        """
        self._graph = nx.read_adjlist(filename)

    def save(self, filename: str) -> None:
        """
        Saves the current graph structure to a file.

        :param filename: The name of the file to save the graph structure.
        """
        nx.write_adjlist(self._graph, filename)

    def get_connected_components(self):
        """
        Retrieves a list of connected components in the graph.

        :return: A list of sets, where each set contains nodes belonging to the same connected component.
        """
        return list(nx.connected_components(self._graph))

    def _generate(self, zones: [Zone]):
        """
        Generates the graph by adding edges between adjacent rectangle sides based on their positions.

        :param zones: A list of Zone objects representing rectangles.
        """
        # Add all possible edges
        y_nodes, x_nodes = [], []
        for zone in zones:
            left, right = ZoneEdge(zone, Side.LEFT), ZoneEdge(zone, Side.RIGHT)
            top, bottom = ZoneEdge(zone, Side.TOP), ZoneEdge(zone, Side.BOTTOM)
            y_nodes.extend((left, right))
            x_nodes.extend((top, bottom))
            self._graph.add_nodes_from((left, right, top, bottom))

        y_nodes = self._sort_and_group(y_nodes, Axis.x)
        x_nodes = self._sort_and_group(x_nodes, Axis.y)

        # Connect nodes to form graph based on side positions. Forms connected components which represents boundaries.
        self._add_edges(y_nodes)
        self._add_edges(x_nodes)

        # Find and remove isolated nodes(edges)
        isolated_nodes = list(nx.isolates(self._graph))
        self._graph.remove_nodes_from(isolated_nodes)

    def _sort_and_group(self, nodes: List[Tuple[Schema, Side]], axis: Axis) -> List[Tuple[Schema, Side]]:
        """
        Sorts a list of nodes along the specified axis and groups them into unconnected components.

        This method sorts the given nodes by their positions along the specified
        axis and the opposite axis. It then groups the nodes by their positions
        along their axis to remove components that border the container.

        :param nodes: A list of tuples containing Schema objects and their corresponding sides.
        :param axis: The axis (Axis.x or Axis.y) along which to sort the nodes.
        :return: A list of grouped nodes sorted by their positions.
        """
        # Determine the opposite axis for sorting
        op_axis = Axis.y if axis is Axis.x else Axis.x
        # Sort edges by their positions along the opposite axis and the given axis
        nodes.sort(key=lambda node: (node.position.bounds[axis.value], node.position.bounds[op_axis.value]))
        # Group the sorted sides by their position along the opposite axis
        groups = [list(g) for k, g in groupby(nodes, key=lambda node: node.position.bounds[axis.value])]

        return list(chain.from_iterable(groups[1:-1]))

    def _add_edges(self, nodes: List[Tuple[Schema, Side]]) -> None:
        """
        Adds edges between nodes representing adjacent rectangle sides if they touch or intersect.

        This method iterates through pairs of adjacent nodes and adds edges
        between them if their positions touch or intersect.

        :param nodes: A list of tuples containing Schema objects and their corresponding sides.
        """
        for u, v in zip(nodes, nodes[1:]):
            if u.position.intersects(v.position) or u.position.touches(v.position):
                self._graph.add_edge(u, v)


class ZoneContainer(Gtk.Fixed):
    """
    A container that holds multiple Zone objects, managing their positions and styles.
    """

    def __init__(self, schemas: List[Dict], _id: Optional[str] = None):
        """
        Initializes the ZoneContainer with a list of dicts representing schema data.
        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        self.id = _id
        self._style_classes = None
        for i, schema in enumerate(schemas):
            zone = Zone(Schema(schema))
            zone.label.set_label(str(i+1))
            self.add(zone)  # Add Zone objects to the container

        self.connect('size-allocate', self._on_size_allocate)

    def _on_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to scale and allocate sizes for child Zone objects.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        # Sort zones by the Euclidean distance of their (x, y) bounds relative to the orign
        sorted_zones = sorted(self.get_children(), key=lambda zone: math.dist((0, 0), (zone.schema.x, zone.schema.y)))
        for i, zone in enumerate(sorted_zones):
            if zone.schema.is_normal:
                zone.schema.scale(allocation.width, allocation.height)

            # Translate zone position relative to container position
            zone.schema.x += allocation.x
            zone.schema.y += allocation.y

            # Label zones based on proximity to the origin from lower(closer) to higher(further)
            zone.label.set_label(str(i+1))
            zone.size_allocate(zone.schema.rectangle)

    def get_zone(self, x, y) -> Zone:
        """
        Retrieves the Zone object at the specified coordinates.
        :param x: The x-coordinate.
        :param y: The y-coordinate.
        :return: The Zone object at the specified coordinates.
        """
        # Verify the window has already been allocated.
        assert self.get_allocated_width() != 0 and self.get_allocated_height() != 0, \
            f'Allocated width and/or height is zero. {self.__class__.__name__} must be size allocated before use.'

        for zone in self.get_children():
            allocation = zone.get_allocation()
            if allocation.x <= x < allocation.x + allocation.width and allocation.y <= y < allocation.y + allocation.height:
                return zone

    def add_zone_style_class(self, *style_classes):
        """
        Adds style classes to all children in the container.
        :param style_classes: One or more style class names to add.
        :return: The ZoneContainer object itself for chaining calls.
        """
        self._style_classes = style_classes
        for child in self.get_children():
            child.add_style_class(*style_classes)  # Add style classes to each child
        return self

    def divide(self, zone: Zone, line: Line) -> None:
        """
        Divides a Zone into two new zones along the specified line.

        This method takes an existing Zone and splits it into two new Zones based on
        the position of the provided Line. The division can be either horizontal or
        vertical, depending on the Line's axis.

        :param zone: The Zone object to be divided.
        :param line: The Line object defining the axis and position for division.
        :raises ValueError: If the given zone is not a child of this container.
        """
        # Validate that the zone is a child of this container
        if zone not in self.get_children():
            raise ValueError(f"Zone must be a child of {self.__class__.__name__} to divide.")

        # Get the current allocation of the zone and create two copies
        allocation = zone.get_allocation()
        alloc_a, alloc_b = allocation.copy(), allocation.copy()

        # Adjust allocations based on the line's axis and position
        if line.axis is Axis.y:
            # Vertical division
            x = round(line.x1)
            alloc_b.x = x
            alloc_b.width = allocation.x + allocation.width - x
            alloc_a.width -= alloc_b.width
        else:
            # Horizontal division
            y = round(line.y1)
            alloc_b.y = y
            alloc_b.height = allocation.y + allocation.height - y
            alloc_a.height -= alloc_b.height

        # Remove the original zone
        self.remove(zone)

        # Create new zones based on the adjusted allocations
        new_zones = [Zone(Schema(alloc)) for alloc in (alloc_a, alloc_b)]

        # Add new zones to the container and apply style classes if any
        for zone in new_zones:
            self.add(zone)
            if self._style_classes:
                zone.add_style_class(*self._style_classes)

        # Update the container's display if it's currently visible
        if self.is_visible():
            self.show_all()


class ZoneDisplayWindow(TransparentApplicationWindow):
    """
    A window that displays and manages multiple Zone objects within a ZoneContainer.

    Attributes:
        __container (ZoneContainer): The container holding Zone objects.
        __active_zone (Zone): The currently active Zone object.
    """

    def __init__(self, schemas: List[Dict]):
        """
        Initializes the ZoneDisplayWindow with a list of dicts representing schema data.
        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        self.maximize()
        workarea = get_workarea()

        # Create the ZoneContainer and add style classes
        self._container = ZoneContainer(schemas).add_zone_style_class('zone-pane', 'passive-zone')
        self._container.set_size_request(workarea.width, workarea.height)
        self._active_zone = None
        self.add(self._container)  # Add the container to the window

    def get_zones(self) -> List[Zone]:
        """
        Retrieves all Zone objects within the container.
        :return: A list of Zone objects.
        """
        return self._container.get_children()

    def get_zone(self, x, y) -> Zone:
        """
        Retrieves the Zone object at the specified coordinates.
        :param x: The x-coordinate.
        :param y: The y-coordinate.
        :return: The Zone object at the specified coordinates.
        """
        return self._container.get_zone(x, y)

    def set_active(self, zone: Zone) -> None:
        """
        Sets the specified Zone as the active zone.
        :param zone: The Zone object to set as active.
        """
        assert zone in self._container.get_children(), f"Zone must be a child of {self._container.__class__.__name__}"
        if self._active_zone:
            # Remove the active style from the previously active zone
            self._active_zone.remove_style_class('active-zone').add_style_class('passive-zone')
        zone.remove_style_class('passive-zone').add_style_class('active-zone')  # Add the active style to the new active zone
        self._active_zone = zone  # Update the active zone

    def set_preset(self, schemas: [dict]) -> None:
        """
        Sets a new list of dicts representing schema data for the ZoneDisplayWindow.
        :param schemas: A new list of dict objects.
        """
        workarea = get_workarea()
        self.remove(self._container)  # Remove the current container
        # Create a new container with the new schema and add style classes
        self._container = ZoneContainer(schemas).add_zone_style_class('zone-pane', 'passive-zone')
        self._container.set_size_request(workarea.width, workarea.height)
        self.add(self._container)  # Add the new container to the window
