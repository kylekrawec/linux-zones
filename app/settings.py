import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk

import display
from base import GtkStyleableMixin, Preset
from zones import ZoneContainer
from editor import ZoneEditorWindow


class PresetDisplay(GtkStyleableMixin, Gtk.Box):
    def __init__(self, name: str, preset: [Preset]):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.preset = preset
        size = display.get_workarea().height * 0.1

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label=name)
        button = Gtk.Button(label="edit")
        zone_container = ZoneContainer(preset).add_zone_style_class('preset-display-pane')
        zone_container.set_size_request(size, size)

        header.pack_start(title, expand=False, fill=False, padding=0)
        header.pack_end(button, expand=False, fill=False, padding=0)

        self.add(header)
        self.add(zone_container)

        # Add css styles
        header.get_style_context().add_class('preset-display-box-header')
        self.add_style_class('preset-display-box')

        # Connect Gtk signals to handlers
        button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        button.connect('button-press-event', self.__on_edit_button_click)

    def __on_edit_button_click(self, widget, event):
        ZoneEditorWindow(self.preset).show_all()


class PresetDisplayLayout(Gtk.FlowBox):
    def __init__(self, presets: dict[str, [Preset]]):
        super().__init__()
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_homogeneous(True)

        # add each zones display variant to box
        for name, preset in presets.items():
            self.add(PresetDisplay(name, preset))


class SettingsWindow(Gtk.ApplicationWindow, Gtk.ScrolledWindow):
    def __init__(self):
        super().__init__()
        self.set_title("Settings")
        workarea = display.get_workarea()

        # set window size to 16:9 aspect ratio based on half the monitor height
        height = int(workarea.height * 0.5)
        width = int(height * 16 / 9)
        self.set_size_request(int(width / 2), int(height / 2))
        self.set_default_size(width, height)

        # center window to work space
        self.move((workarea.width - width) / 2, (workarea.height - height) / 2)

        # create vertical layout box to hold all window contents
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.layout.get_style_context().add_class('settings-window')

        # add scollable functionality
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # nest contents in scrollable window
        scrolled_window.add(self.layout)
        self.add(scrolled_window)

    def add_presets(self, label: str, presets: dict[str, [Preset]]):
        # stack widgets for template preset display
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.pack_start(Gtk.Label(label=label), expand=False, fill=False, padding=12)
        self.layout.add(header)
        self.layout.add(PresetDisplayLayout(presets))
