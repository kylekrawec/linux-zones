import os
import json
from typing import Any, Dict

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class _Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(_Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._settings = {}
        self._presets = {}
        self._templates = {}
        self._styles = None
        self.load_all()

    def load_all(self):
        self._settings = self._load_json('settings.json')
        self._presets = self._load_json('presets.json')
        self._templates = self._load_json('templates.json')
        self._styles = self._load_css('style.css')

    def _load_json(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.abspath(os.path.join('settings', filename))
        with open(filepath, 'r') as file:
            return json.load(file)

    def _load_css(self, filename: str) -> Gtk.CssProvider:
        filepath = os.path.abspath(os.path.join('settings', filename))
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(filepath)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        return css_provider

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @property
    def presets(self) -> Dict[str, Any]:
        return self._presets

    @property
    def templates(self) -> Dict[str, Any]:
        return self._templates

    @property
    def styles(self) -> Gtk.CssProvider:
        return self._styles

    def save(self, data: Dict[str, Any], filename: str):
        filepath = os.path.abspath(os.path.join('settings', filename))
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)


# Create a single instance of Config
config = _Config()
