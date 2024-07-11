import gi
import networkx as nx
from itertools import groupby, chain
from shapely.geometry import LineString
from shapely.ops import linemerge

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

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
        self.axis = Axis.x if side in {Side.LEFT, Side.RIGHT} else Axis.y  # Determine the axis based on the side

    @property
    def rectangle(self) -> Gdk.Rectangle:
        """
        Retrieves the allocation rectangle of the Zone associated with this edge.

        :return: A Gdk.Rectangle representing the allocation of the associated Zone.
        """
        return self.zone.get_allocation()


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
        lines = [edge.position for edge in edges]  # Get positions of the edges
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
        lines = [edge.position for edge in self.__edges]  # Get positions of the edges
        bounds = linemerge(lines).bounds  # Merge the lines and get the bounds
        return LineString([(bounds[0], bounds[1]), (bounds[2], bounds[3])])  # Create a LineString from the bounds

    def move_horizontal(self, position: int) -> None:
        """
        Moves the edge horizontally to a new position.
        :param position: Pixel value of a new position to move the edge.
        """
        if self.axis is Axis.x:
            for edge in self.__edges:
                allocation = edge.rectangle
                if edge.side is Side.LEFT:
                    # Adjust the width and x-position when moving the left edge
                    allocation.width = (allocation.x + allocation.width) - position
                    allocation.x = position
                else:
                    # Adjust the width when moving the right edge
                    allocation.width = position - allocation.x
                edge.zone.resize(allocation)

    def move_vertical(self, position: int) -> None:
        """
        Moves the edge vertically to a new position.
        :param position: Pixel value of a new position to move the edge.
        """
        if self.axis is Axis.y:
            for edge in self.__edges:
                allocation = edge.rectangle
                if edge.side is Side.TOP:
                    # Adjust the height and y-position when moving the top edge
                    allocation.height = (allocation.y + allocation.height) - position
                    allocation.y = position
                else:
                    # Adjust the height when moving the bottom edge
                    allocation.height = position - allocation.y
                edge.zone.resize(allocation)


class RectangleSideGraph:
    """
    A graph of rectangle edge relations.

    This class represents a graph where nodes correspond to edges of rectangles defined by a Schema objects. It allows
    for reading and saving graph structures, generating connections based on rectangle edge positions, and retrieving
    connected components.

    Attributes:
        __graph (nx.Graph): The underlying networkx Graph object storing rectangle edge relations.
    """

    def __init__(self, schemas: list[Schema]):
        """
        Initializes the RectangleSideGraph with a list of Schema objects generating a graph of rectangle edge relations
        based on their properties.

        :param schemas: A list containing Schema objects representing rectangle definitions.
        :raises TypeError: If schemas is not a list or does not contain objects of types Schema.
        """
        super().__init__()
        self.__graph = nx.Graph()
        assert len(schemas) > 0 and isinstance(schemas, list), 'Schema data must be a list containing one or more items.'
        assert all(isinstance(item, Schema) for item in schemas), f'Schema data must be a list of {Schema}.'
        self.__generate(schemas)

    def read_file(self, filename: str) -> None:
        """
        Reads a graph structure from a file and initializes the internal __graph.

        :param filename: The name of the file containing the graph structure.
        """
        self.__graph = nx.read_adjlist(filename)

    def save(self, filename: str) -> None:
        """
        Saves the current graph structure to a file.

        :param filename: The name of the file to save the graph structure.
        """
        nx.write_adjlist(self.__graph, filename)

    def get_connected_components(self):
        """
        Retrieves a list of connected components in the graph.

        :return: A list of sets, where each set contains nodes belonging to the same connected component.
        """
        return list(nx.connected_components(self.__graph))

    def __generate(self, schemas: [Schema]):
        """
        Generates the graph by adding edges between adjacent rectangle sides based on their positions.

        :param schemas: A list of Schema objects representing rectangles.
        """
        # Add all possible edges
        x_nodes, y_nodes = [], []
        for schema in schemas:
            left, right = AbstractRectangleSide(schema, Side.LEFT), AbstractRectangleSide(schema, Side.RIGHT)
            top, bottom = AbstractRectangleSide(schema, Side.TOP), AbstractRectangleSide(schema, Side.BOTTOM)
            x_nodes.extend((left, right))
            y_nodes.extend((top, bottom))
            self.__graph.add_nodes_from((left, right, top, bottom))

        # Sort nodes to simplify edge discovery
        x_nodes.sort(key=lambda n: n.position.bounds[Axis.x.value])
        y_nodes.sort(key=lambda n: n.position.bounds[Axis.y.value])

        if len(x_nodes) > 2:
            # Remove the nodes that border the left and right most positions
            groups = [list(g) for k, g in groupby(x_nodes, key=lambda n: n.position.bounds[Axis.x.value])]
            x_nodes = list(chain.from_iterable(groups[1:-1]))
        if len(y_nodes) > 2:
            # Remove the nodes that border the top and bottom most positions
            groups = [list(g) for k, g in groupby(y_nodes, key=lambda n: n.position.bounds[Axis.y.value])]
            y_nodes = list(chain.from_iterable(groups[1:-1]))

        # Connect nodes to form graph based on side positions. Also forms connected components which represents boundaries.
        self.__add_edges(x_nodes)
        self.__add_edges(y_nodes)

        # Find and remove isolated nodes(edges)
        isolated_nodes = list(nx.isolates(self.__graph))
        self.__graph.remove_nodes_from(isolated_nodes)

    def __add_edges(self, nodes: [tuple[Schema, Side]]) -> None:
        """
        Adds edges between nodes representing adjacent rectangle sides if they touch or intersect.

        :param nodes: A list of tuples containing Schema objects and their corresponding sides.
        """
        for u, v in zip(nodes, nodes[1:]):
            if u.position.touches(v.position) or u.position.intersects(v.position):
                self.__graph.add_edge(u, v)


class ZoneContainer(Gtk.Fixed):
    """
    A container that holds multiple Zone objects and manages their positions and styles.

    Attributes:
        graph (RectangleSideGraph): Graph representing positions of zone sides within the container.
    """

    def __init__(self, schemas: list[dict]):
        """
        Initializes the ZoneContainer with a list of dicts representing schema data.
        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        for i, schema in enumerate(schemas):
            zone = Zone(Schema(schema))
            zone.label.set_label(str(i+1))
            self.add(zone)  # Add Zone objects to the container

        self.graph = RectangleSideGraph([child.schema for child in self.get_children()])
        self.initial_allocation_handler_id = self.connect('size-allocate', self.__on_initial_allocation)

    def __on_initial_allocation(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to scale and allocate sizes for child Zone objects. Disconnects after the
        first allocation.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        for zone in self.get_children():
            if zone.schema.is_normal:
                zone.schema.scale(allocation.width, allocation.height)

            # Translate zone position relative to container position
            zone.schema.x += allocation.x
            zone.schema.y += allocation.y

            zone.size_allocate(zone.schema.rectangle)

        self.connect('size-allocate', self.__on_size_allocate)
        self.disconnect(self.initial_allocation_handler_id)

    def __on_size_allocate(self, widget, allocation) -> None:
        """
        Handles the size-allocate signal to scale and allocate sizes for child Zone objects.
        :param widget: The widget that received the signal.
        :param allocation: The allocation (Gtk.Allocation) containing the new size.
        """
        for zone in self.get_children():
            zone.size_allocate(zone.schema.rectangle)

    def add_zone_style_class(self, *style_classes):
        """
        Adds style classes to all children in the container.
        :param style_classes: One or more style class names to add.
        :return: The ZoneContainer object itself for chaining calls.
        """
        for child in self.get_children():
            child.add_style_class(*style_classes)  # Add style classes to each child
        return self


class ZoneDisplayWindow(TransparentApplicationWindow):
    """
    A window that displays and manages multiple Zone objects within a ZoneContainer.

    Attributes:
        __container (ZoneContainer): The container holding Zone objects.
        __active_zone (Zone): The currently active Zone object.
    """

    def __init__(self, schemas: list[dict]):
        """
        Initializes the ZoneDisplayWindow with a list of dicts representing schema data.
        :param schemas: A list of dicts representing schema data to initialize Zone objects.
        """
        super().__init__()
        self.maximize()
        workarea = get_workarea()

        # Create the ZoneContainer and add style classes
        self.__container = ZoneContainer(schemas).add_zone_style_class('zone-pane', 'passive-zone')
        self.__container.set_size_request(workarea.width, workarea.height)
        self.__active_zone = None
        self.add(self.__container)  # Add the container to the window

    def get_zones(self) -> [Zone]:
        """
        Retrieves all Zone objects within the container.
        :return: A list of Zone objects.
        """
        return self.__container.get_children()

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

        for zone in self.__container.get_children():
            allocation = zone.get_allocation()
            if allocation.x <= x < allocation.x + allocation.width and allocation.y <= y < allocation.y + allocation.height:
                return zone

    def set_active(self, zone: Zone) -> None:
        """
        Sets the specified Zone as the active zone.
        :param zone: The Zone object to set as active.
        """
        assert zone in self.__container.get_children(), f"Zone must be a child of {self.__container.__class__.__name__}"
        if self.__active_zone:
            # Remove the active style from the previously active zone
            self.__active_zone.remove_style_class('active-zone').add_style_class('passive-zone')
        zone.remove_style_class('passive-zone').add_style_class('active-zone')  # Add the active style to the new active zone
        self.__active_zone = zone  # Update the active zone

    def set_preset(self, schemas: [dict]) -> None:
        """
        Sets a new list of dicts representing schema data for the ZoneDisplayWindow.
        :param schemas: A new list of dict objects.
        """
        self.remove(self.__container)  # Remove the current container
        # Create a new container with the new schema and add style classes
        self.__container = ZoneContainer(schemas).add_zone_style_class('zone-pane', 'passive-zone')
        self.add(self.__container)  # Add the new container to the window
