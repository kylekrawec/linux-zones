import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib


class ZoneEditor(Gtk.ApplicationWindow):
    def __init__(self, width, height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(width, height)
        self.set_title("Zone Editor")
