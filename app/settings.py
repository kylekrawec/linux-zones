import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib

from zones import ZoneDisplay
from config import Config


class ZoneEditor(Gtk.ApplicationWindow):
    def __init__(self, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(width, height)
        self.set_title("Zone Editor")
        self.templates = Config('templates.json').load()
        self.style = Config('styles.json').load()


        self.template_grid = Gtk.Grid(column_spacing=10)

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label='priority-grid')
        template = ZoneDisplay(self.templates.priority_grid, self.style.template_zone)
        container.pack_start(label, expand=False, fill=False, padding=10)
        container.pack_start(template, expand=True, fill=True, padding=10)  # Usually, you want your custom drawing area to expand
        container.set_size_request(250, 250)

        self.template_grid.attach(container, 1, 1, 1, 1)
        self.add(self.template_grid)
