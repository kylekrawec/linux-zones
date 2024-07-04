import os
import json
from box import Box
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class Config(object):
    def __init__(self, filename, *path):
        relative_path = os.path.join('settings', filename) if path == () else os.path.join(*path, filename)
        self.filepath = os.path.abspath(relative_path)

    def load(self):
        if self.filepath.endswith('.json'):
            with open(self.filepath, 'r') as file:
                content = json.load(file)
            return Box(content)
        elif self.filepath.endswith('.css'):
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(self.filepath)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            return css_provider

    def save(self, data):
        if self.filepath.endswith('.json'):
            # Write dictionary to a JSON file
            assert isinstance(data, dict), f'data must be a dictionary for json files.'
            with open(self.filepath, 'w') as file:
                json.dump(data, file, indent=4)
