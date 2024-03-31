import cairo
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class ZonePane(object):
    def __init__(self, label, bounds, style):
        self.x = bounds['x']
        self.y = bounds['y']
        self.width = bounds['width']
        self.height = bounds['height']
        self.label = label
        self.color = style.color.default


class ZoneDisplay(Gtk.DrawingArea):
    def __init__(self, preset: dict, style):
        super().__init__()
        self.zones = None
        self.preset = preset
        self.style = style

        # Set zones when widget layout has been performed
        self.connect("size-allocate", self.on_size_allocate)

        # Initialize the drawing area
        self.connect('draw', self.on_draw)

    def on_draw(self, widget, cr: cairo.Context) -> None:
        # Draw each zone
        for label, z in self.zones.items():
            # Draw zone background
            cr.rectangle(z.x, z.y, z.width, z.height)
            cr.set_source_rgba(z.color.r, z.color.g, z.color.b, z.color.a)
            cr.fill_preserve()
            # Draw zone border
            cr.set_source_rgb(self.style.border.color.r, self.style.border.color.g, self.style.border.color.b)
            cr.set_line_width(self.style.border.weight)
            cr.stroke()
            # Assign zone label
            cr.select_font_face(self.style.font.face)
            cr.set_font_size(self.style.font.size)
            cr.set_source_rgb(self.style.font.color.r, self.style.font.color.g, self.style.font.color.b)
            # Position zone
            x_pos, y_pos = z.x + (z.width/2), z.y + (z.height/2)
            cr.move_to(x_pos, y_pos)
            cr.show_text(label)

    def on_size_allocate(self, widget, allocation):
        self.set_zones(self.preset)

    def scale_preset(self, preset: dict) -> dict:
        scaled_preset = {}
        for label, bounds in preset.items():
            scaled_preset[label] = {
                'x': round(self.get_allocated_width() * bounds['x']),
                'y': round(self.get_allocated_height() * bounds['y']),
                'width': round(self.get_allocated_width() * bounds['width']),
                'height': round(self.get_allocated_height() * bounds['height'])
            }
        return scaled_preset

    def create_zone_pane(self, label: str, bounds: dict) -> ZonePane:
        return ZonePane(label, bounds, self.style)

    def set_zones(self, preset: dict) -> None:
        self.zones = {}
        self.preset = self.scale_preset(preset)
        for label, bounds in self.preset.items():
            self.zones[label] = self.create_zone_pane(label, bounds)
        self.queue_draw()


class ActiveZonePane(ZonePane):
    def __init__(self, label, bounds, style):
        super().__init__(label, bounds, style)
        self.style = style

    def set_active(self):
        self.color = self.style.color.active

    def set_default(self):
        self.color = self.style.color.default


class InteractiveZoneDisplay(ZoneDisplay):
    def __init__(self, preset: dict, style):
        super().__init__(preset, style)
        self.__active_zone = None

    def set_active(self, zone_label: str):
        if zone_label in self.zones.keys():
            if self.__active_zone is not None:
                self.zones[self.__active_zone].set_default()
            self.zones[zone_label].set_active()
            self.__active_zone = zone_label
            self.queue_draw()
        else:
            assert "Zone does not exist"

    def create_zone_pane(self, label: str, bounds: dict) -> ActiveZonePane:
        return ActiveZonePane(label, bounds, self.style)


class ZoneWindow(Gtk.Window):
    def __init__(self, width: int, height: int, display: ZoneDisplay):
        super().__init__()
        self.set_default_size(width, height)

        # create container for display
        container = Gtk.Box()
        self.add(container)

        # add display to container
        self.display = display
        container.pack_start(self.display, expand=True, fill=True, padding=0)

        # Set the window type hint to make it undecorated and generally ignored by the window manager
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)

        # Set the window's visual so it supports transparency.
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Enable transparency
        self.set_app_paintable(True)
