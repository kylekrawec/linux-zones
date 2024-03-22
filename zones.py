import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class ZonePane(object):
    def __init__(self, label, bounds):
        self.x = bounds['x']
        self.y = bounds['y']
        self.width = bounds['width']
        self.height = bounds['height']
        self.label = label
        self.rgba = (.9, .9, .9, 0.6)


class ZoneDisplay(Gtk.DrawingArea):
    def __init__(self, preset):
        super().__init__()
        self.zones = None
        self.preset = preset

        # set zones when widget layout has been performed
        self.connect("size-allocate", self.on_size_allocate)

        # Initialize the drawing area
        self.connect('draw', self.on_draw)

    def on_draw(self, widget, cr: cairo.Context) -> None:
        # Draw each zone
        for label, z in self.zones.items():
            cr.rectangle(z.x, z.y, z.width, z.height)  # x, y, width, height
            cr.set_source_rgba(z.rgba[0], z.rgba[1], z.rgba[2], z.rgba[3])
            cr.fill_preserve()
            cr.set_source_rgb(0.4, 0.4, 0.4)
            cr.stroke()
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            cr.set_font_size(50)  # Font size in points
            cr.set_source_rgb(0.25, 0.25, 0.25)
            x, y = z.x + (z.width/2), z.y + (z.height/2)
            cr.move_to(x, y)
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
        return ZonePane(label, bounds)

    def set_zones(self, preset: dict) -> None:
        self.zones = {}
        self.preset = self.scale_preset(preset)
        for label, bounds in self.preset.items():
            self.zones[label] = self.create_zone_pane(label, bounds)
        self.queue_draw()


class ActiveZonePane(ZonePane):
    def __init__(self, label, bounds):
        super().__init__(label, bounds)

    def set_active(self):
        self.rgba = (0.2, 0.5, 1, 0.5)

    def set_default(self):
        self.rgba = (.9, .9, .9, 0.6)


class InteractiveZoneDisplay(ZoneDisplay):
    def __init__(self, preset: dict):
        super().__init__(preset)
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
        return ActiveZonePane(label, bounds)


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
