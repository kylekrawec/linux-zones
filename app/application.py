import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, GLib, Wnck

import sys
from pynput import keyboard, mouse

import base
import display
import zones
from base import State
from config import Config
from settings import Settings


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.linuxzones", **kwargs)
        self.screen = None
        self.workarea = None
        self.state = State.READY
        self.mouse_pressed = False
        self.current_zone = None

        # app windows
        self.zone_display = None
        self.settings_window = None

        # configuration files
        self.settings = None
        self.presets = None

    def set_window(self):
        # get zone the cursor is located within
        cur_x, cur_y = mouse.Controller().position
        self.current_zone = self.zone_display.get_zone(cur_x, cur_y)
        bounds = base.ScaledBounds(self.current_zone.bounds, self.workarea)

        # get active window and set geometry (size & position)
        active_window = self.screen.get_active_window()
        geometry_mask = (Wnck.WindowMoveResizeMask.X | Wnck.WindowMoveResizeMask.Y | Wnck.WindowMoveResizeMask.WIDTH | Wnck.WindowMoveResizeMask.HEIGHT)
        active_window.set_geometry(Wnck.WindowGravity(0), geometry_mask, bounds.x, bounds.y, bounds.width, bounds.height)

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
                    # update workarea and set display dimentions if user modifies the workarea during runtime
                    if display.get_workarea() != self.workarea:
                        self.workarea = display.get_workarea()
                        self.zone_display.set_window_bounds(self.workarea)

                    if self.mouse_pressed:
                        self.zone_display.show_all()
                        self.state = self.state.SET_WINDOW
                    else:
                        self.state = State.CTRL_READY
            case State.SET_ZONE:
                for i, name in self.settings.zonemap.items():
                    if keyboard.KeyCode.from_char(i) == key:
                        self.zone_display.set_preset(self.presets.get(name))
                        self.zone_display.show_all()

    def __key_release_callback(self, key):
        match self.state:
            case State.SET_ZONE:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.cmd_l or key == keyboard.Key.alt_l:
                    self.state = State.READY
                else:
                    self.zone_display.hide()
            case _:
                if key == keyboard.Key.cmd_l:
                    self.zone_display.hide()
                    self.state = State.READY

    def __mouse_click_callback(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.mouse_pressed = pressed
            match self.state:
                case State.CTRL_READY:
                    self.zone_display.show_all()
                    if pressed:
                        self.state = State.SET_WINDOW
                case State.SET_WINDOW:
                    if not pressed:
                        self.set_window()
                        self.zone_display.hide()
                        self.state = State.CTRL_READY

    def __mouse_move_callback(self, x, y):
        match self.state:
            case State.SET_WINDOW:
                new_zone = self.zone_display.get_zone(x, y)
                if new_zone != self.current_zone:
                    self.zone_display.set_active(new_zone)
                    self.current_zone = new_zone

    def __on_activate_shortcut(self):
        self.state = State.SET_ZONE

    # Gtk Method Overrides
    def do_startup(self):
        Gtk.Application.do_startup(self)

        # get workarea
        self.workarea = display.get_workarea()

        # get screen interaction object
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        # load configuration
        self.settings = Config('settings.json').load()
        self.presets = Config('presets.json').load()

        # load css styles
        Config('style.css').load()

    def do_activate(self):
        # start the keyboard listener in its own thread
        keyboard_listener = keyboard.Listener(on_press=self.key_press, on_release=self.key_release)
        keyboard_listener.start()

        # start the mouse listener in its own thread
        mouse_listener = mouse.Listener(on_click=self.mouse_click, on_move=self.mouse_move)
        mouse_listener.start()

        # start the hotkey listener in its own thread
        hotkey_listener = keyboard.GlobalHotKeys({
            '<ctrl>+<cmd>+<alt>': self.on_activate_shortcut
        })
        hotkey_listener.start()

        # create zone display and window container
        default_preset = self.presets[self.settings.get('default_preset')]
        self.zone_display = zones.ZoneDisplayWindow(default_preset)
        self.zone_display.set_window_bounds(self.workarea)

        # create settings windows
        self.settings_window = Settings(application=self)
        self.settings_window.show_all()


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
