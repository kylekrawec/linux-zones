import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import base
from display import get_workarea


class ZonePane(base.GtkStyleable, Gtk.Box):
    def __init__(self, preset: base.ScaledPreset):
        Gtk.Box.__init__(self)
        self.__set_preset(preset)
        if preset.label:
            self.set_center_widget(Gtk.Label(label=preset.label))

    def __set_preset(self, preset: base.ScaledPreset):
        self.preset = preset
        self.x = preset.x
        self.y = preset.y
        self.width = preset.width
        self.height = preset.height

    def resize(self, allocation, new_bounds: base.ScaledPreset = None):
        if new_bounds:
            self.__set_preset(new_bounds)
        self.size_allocate(base.ScaledPreset(self.preset, allocation))


class ZoneContainer(Gtk.Fixed):
    def __init__(self, presets: [base.ScaledPreset]):
        super().__init__()
        for preset in presets:
            self.add(ZonePane(preset))
        self.connect('size-allocate', self.__on_size_allocate)

    def __on_size_allocate(self, widget, allocation):
        for child in self.get_children():
            child.resize(allocation)

    def add_zone_style_class(self, *style_classes):
        for child in self.get_children():
            child.add_style_class(*style_classes)
        return self


class ZoneDisplayWindow(base.TransparentApplicationWindow):
    def __init__(self, presets: [base.ScaledPreset]):
        super().__init__()
        self.__container = ZoneContainer(presets).add_zone_style_class('zone-pane', 'passive-zone')
        self.__active_zone = None
        self.add(self.__container)
        self.set_window_bounds(get_workarea())

    def get_zones(self) -> [ZonePane]:
        return self.__container.get_children()

    def get_zone(self, x, y) -> ZonePane:
        assert self.get_allocated_width() != 0 and self.get_allocated_height() != 0, 'Allocated width and height must not be zero.'
        # convert from pixel to scaled coordinates
        x = x / self.get_allocated_width()
        y = y / self.get_allocated_height()

        for child in self.__container.get_children():
            if child.x <= x < child.x + child.width and child.y <= y < child.y + child.height:
                return child

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
