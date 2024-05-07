import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

import display
from zones import ZoneDisplay
from config import Config


class ZoneEditor(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Zone Editor")
        self.workarea = display.get_workarea()

        # set window size to 16:9 aspect ratio based on half the monitor height
        self.height = int(self.workarea.height * 0.5)
        self.width = int(self.height * 16/9)
        self.set_size_request(int(self.width/2), int(self.height/2))
        self.set_default_size(self.width, self.height)

        # center window to work space
        self.move((self.workarea.width - self.width)/2, (self.workarea.height - self.height)/2)

        # load templates, presets, and other configurations
        self.templates = Config('templates.json').load()
        self.presets = Config('presets.json').load()
        self.style = Config('styles.json').load()

        # create vertical layout box to hold all window contents
        self.layout_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # form the box to hold all templates
        templates = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        templates.add(Gtk.Label(label='Templates'))
        templates.add(self.display_presets(self.templates))

        # form the box to hold all custom presets
        custom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        custom.add(Gtk.Label(label='Custom'))
        custom.add(self.display_presets(self.presets))

        # add all boxs to main box
        self.layout_box.add(templates)
        self.layout_box.add(custom)

        self.add(self.layout_box)
        self.layout_box.show_all()

    def zone_display_box(self, preset_name: str, preset: dict) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label = Gtk.Label(label=preset_name)
        zone_display = ZoneDisplay(preset, self.style.template_zone)
        # assign size to ZoneDisplay beacuse its a Gtk.DrawingArea
        size = int(min(self.width, self.height) * 0.25)
        zone_display.set_size_request(size, size)

        box.add(label)
        box.add(zone_display)

        return box

    def display_presets(self, presets) -> Gtk.FlowBox:
        flowbox = Gtk.FlowBox(valign=Gtk.Align.START, max_children_per_line=6, homogeneous=True)
        # add each zones display variant to flowbox
        for preset_name, preset in presets.items():
            flowbox.add(self.zone_display_box(preset_name, preset))

        return flowbox
