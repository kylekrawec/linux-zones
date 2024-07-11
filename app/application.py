import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, GLib, Wnck

import sys
from pynput import keyboard, mouse

from base import State
from zones import ZoneDisplayWindow
from display import get_workarea
from config import Config
from settings import SettingsWindow


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.linuxzones", **kwargs)
        self.screen = None
        self.workarea = None
        self.state = State.READY
        self.mouse_pressed = False
        self.current_zone = None

        # Declare Configs
        self.settings_manager = Config('settings.json')
        self.presets_manager = Config('presets.json')
        self.templates_manager = Config('templates.json')

        # Load settings
        self.settings = self.settings_manager.load()

        # Extract schemas
        self.presets = self.presets_manager.load()
        self.templates = self.templates_manager.load()

        # Default settings
        self.default_preset = self.presets.get(self.settings.get('default_preset'))

        # Create application windows
        self.zone_display_window = ZoneDisplayWindow(self.default_preset)
        self.settings_window = SettingsWindow()
        self.settings_window.add_schemas('Custom', self.presets)
        self.settings_window.add_schemas('Templates', self.templates)

    def set_window(self):
        # get zone the cursor is located within
        cur_x, cur_y = mouse.Controller().position
        self.current_zone = self.zone_display_window.get_zone(cur_x, cur_y)
        allocation = self.current_zone.get_allocation()

        # Translate window allocation to workarea
        workarea = get_workarea()
        allocation.x += workarea.x
        allocation.y += workarea.y

        # get active window and set geometry (size & position)
        active_window = self.screen.get_active_window()
        geometry_mask = (Wnck.WindowMoveResizeMask.X | Wnck.WindowMoveResizeMask.Y | Wnck.WindowMoveResizeMask.WIDTH | Wnck.WindowMoveResizeMask.HEIGHT)
        active_window.set_geometry(Wnck.WindowGravity(0), geometry_mask, allocation.x, allocation.y, allocation.width, allocation.height)

    # Controller
    def key_press(self, key):
        """
        A thread-safe wrapper function for __key_press_callback().
        :param key: a pynput.keyboard.Key object
        :return: none
        """
        GLib.idle_add(self.__key_press_callback, key)

    def key_release(self, key):
        """
        A thread-safe wrapper function for __key_release_callback().
        :param key: a pynput.keyboard.Key object
        :return: none
        """
        GLib.idle_add(self.__key_release_callback, key)

    def mouse_click(self, x, y, button, pressed):
        GLib.idle_add(self.__mouse_click_callback, x, y, button, pressed)

    def mouse_move(self, x, y):
        GLib.idle_add(self.__mouse_move_callback, x, y)

    def on_activate_shortcut(self):
        GLib.idle_add(self.__on_activate_shortcut)

    def __key_press_callback(self, key):
        match self.state:
            case State.READY:
                if key == keyboard.Key.cmd_l:
                    if self.mouse_pressed:
                        self.zone_display_window.show_all()
                        self.state = self.state.SET_WINDOW
                    else:
                        self.state = State.CTRL_READY
            case State.SET_ZONE:
                for i, name in self.settings['zonemap'].items():
                    if keyboard.KeyCode.from_char(i) == key:
                        self.zone_display_window.set_preset(self.presets.get(name, self.default_preset))
                        self.zone_display_window.show_all()

    def __key_release_callback(self, key):
        match self.state:
            case State.SET_ZONE:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.cmd_l or key == keyboard.Key.alt_l:
                    self.state = State.READY
                else:
                    self.zone_display_window.hide()
            case _:
                if key == keyboard.Key.cmd_l:
                    self.zone_display_window.hide()
                    self.state = State.READY

    def __mouse_click_callback(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.mouse_pressed = pressed
            match self.state:
                case State.CTRL_READY:
                    self.zone_display_window.show_all()
                    if pressed:
                        self.state = State.SET_WINDOW
                case State.SET_WINDOW:
                    if not pressed:
                        self.set_window()
                        self.zone_display_window.hide()
                        self.state = State.CTRL_READY

    def __mouse_move_callback(self, x, y):
        match self.state:
            case State.SET_WINDOW:
                new_zone = self.zone_display_window.get_zone(x, y)
                if new_zone != self.current_zone:
                    self.zone_display_window.set_active(new_zone)
                    self.current_zone = new_zone

    def __on_activate_shortcut(self):
        self.state = State.SET_ZONE

    # Gtk Method Overrides
    def do_startup(self):
        Gtk.Application.do_startup(self)

        # get screen interaction object
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        # load css styles
        Config('style.css').load()

    def do_activate(self):
        # Start the keyboard listener in its own thread
        keyboard_listener = keyboard.Listener(on_press=self.key_press, on_release=self.key_release)
        keyboard_listener.start()

        # Start the mouse listener in its own thread
        mouse_listener = mouse.Listener(on_click=self.mouse_click, on_move=self.mouse_move)
        mouse_listener.start()

        # Start the hotkey listener in its own thread
        hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<cmd>+<alt>': self.on_activate_shortcut
        })
        hotkey_listener.start()

        Gtk.ApplicationWindow(application=self)


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
