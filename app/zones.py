import gi
import base

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class ZonePane(base.GtkStyleable, Gtk.Box):
    def __init__(self, bounds: Gdk.Rectangle, label: str = None):
        Gtk.Box.__init__(self)
        self.bounds = bounds
        self.x = bounds.x
        self.y = bounds.y
        self.width = bounds.width
        self.height = bounds.height
        if label:
            self.set_center_widget(Gtk.Label(label=label))


class ZoneContainer(Gtk.Fixed):
    def __init__(self, preset: dict):
        super().__init__()
        for label, bounds in preset.items():
            self.add(ZonePane(bounds, label))
        self.connect('size-allocate', self.__on_size_allocate)

    def __on_size_allocate(self, widget, allocation):
        for child in self.get_children():
            child.size_allocate(base.ScaledBounds(child.bounds, allocation))

    def add_zone_style_class(self, *style_classes):
        for child in self.get_children():
            child.add_style_class(*style_classes)
        return self


class ZoneDisplayWindow(base.TransparentApplicationWindow):
    def __init__(self, preset: dict):
        super().__init__()
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.__active_zone = None
        self.add(self.__container)

    def get_zones(self) -> [ZonePane]:
        return self.__container.get_children()

    def set_active(self, zone: ZonePane) -> None:
        assert zone in self.__container.get_children(), "Zone must be a child of " + self.__container.__class__.__name__
        if self.__active_zone:
            self.__active_zone.remove_style_class('active-zone').add_style_class('passive-zone')
        zone.remove_style_class('passive-zone').add_style_class('active-zone')
        self.__active_zone = zone

    def set_preset(self, preset: dict) -> None:
        self.remove(self.__container)
        self.__container = ZoneContainer(preset).add_zone_style_class('zone-pane', 'passive-zone')
        self.add(self.__container)

    def set_window_bounds(self, bounds: Gdk.Rectangle) -> None:
        self.move(bounds.x, bounds.y)
        self.resize(bounds.width, bounds.height)
