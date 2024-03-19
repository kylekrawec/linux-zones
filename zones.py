import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import cairo


class ZonePane(object):
    def __init__(self, x, y, width, height, label):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.label = label
        self.rgba = (.9, .9, .9, 0.6)

    def set_active(self):
        self.rgba = (0.2, 0.5, 1, 0.5)

    def set_default(self):
        self.rgba = (.9, .9, .9, 0.6)


class ZoneGraphics(Gtk.DrawingArea):
    def __init__(self, zones: dict[str, ZonePane]):
        super().__init__()
        self.zones = zones
        self.connect('draw', self.on_draw)

    def on_draw(self, widget, cr: cairo.Context):
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


class ZoneWindow(Gtk.Window):
    def __init__(self, width, height, zones):
        super().__init__()
        self.set_default_size(width, height)

        # Set the window type hint to make it undecorated and generally ignored by the window manager
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)

        # Set the window's visual so it supports transparency.
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        # Enable transparency
        self.set_app_paintable(True)

        # TODO Not sure if working or even needed?
        # Make the window click-through
        self.set_accept_focus(False)
        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK)

        # Instantiate zones from configuration
        self.__zones = {}
        for label, v in zones.items():
            self.__zones[label] = ZonePane(v['x'], v['y'], v['width'], v['height'], label)

        self.__active_zone = None
        self.__graphics = ZoneGraphics(self.__zones)

        self.add(self.__graphics)

    def set_active(self, zone_label: str):
        if zone_label in self.__zones.keys():
            if self.__active_zone is not None:
                self.__zones[self.__active_zone].set_default()
            self.__zones[zone_label].set_active()
            self.__active_zone = zone_label
            self.__graphics.queue_draw()
        else:
            assert "Zone does not exist"
