import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import base
import display
import zones
from config import Config


class PresetDisplay(base.GtkStyleable, Gtk.Box):
    def __init__(self, preset_name: str, preset: dict):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label=preset_name)
        button = Gtk.Button(label="edit")
        zone_display = zones.ZoneContainer(preset).add_zone_style_class('preset-display-pane')
        zone_display.set_size_request(200, 175)

        header.pack_start(title, expand=False, fill=False, padding=0)
        header.pack_end(button, expand=False, fill=False, padding=0)

        self.add(header)
        self.add(zone_display)

        # add css styles
        header.get_style_context().add_class('preset-display-box-header')
        self.add_style_class('preset-display-box')


class PresetDisplayLayout(Gtk.Box):
    def __init__(self, presets: dict):
        super().__init__()
        self.set_orientation(Gtk.Orientation.HORIZONTAL)

        # add each zones display variant to box
        for preset_name, preset in presets.items():
            # format preset names
            words = preset_name.replace('-', ' ').split(' ')
            preset_name = ' '.join([word.capitalize() for word in words])

            self.add(PresetDisplay(preset_name, preset))


class Settings(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Settings")
        self.workarea = display.get_workarea()

        # set window size to 16:9 aspect ratio based on half the monitor height
        self.height = int(self.workarea.height * 0.5)
        self.width = int(self.height * 16 / 9)
        self.set_size_request(int(self.width / 2), int(self.height / 2))
        self.set_default_size(self.width, self.height)

        # center window to work space
        self.move((self.workarea.width - self.width) / 2, (self.workarea.height - self.height) / 2)

        # load templates, presets, and other configurations
        template_presets = Config('templates.json').load()
        custom_presets = Config('presets.json').load()

        # create vertical layout box to hold all window contents
        self.layout_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # form the box to hold all templates
        templates = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        templates.add(Gtk.Label(label='Templates'))
        templates.add(PresetDisplayLayout(template_presets))

        # form the box to hold all custom presets
        custom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        custom.add(Gtk.Label(label='Custom'))
        custom.add(PresetDisplayLayout(custom_presets))

        self.layout_box.add(templates)
        self.layout_box.add(custom)

        self.add(self.layout_box)

        # add css styles
        self.layout_box.get_style_context().add_class('zone-editor')
