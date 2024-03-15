import sys
import json
from enum import Enum

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, Gio, GLib, Wnck

from pynput import keyboard, mouse
from zones import ZoneWindow


class State(Enum):
    READY = 0
    CTRL_READY = 1
    SET_WINDOW = 2


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.windowsystem", **kwargs)
        self.window = None
        self.screen = None
        self.width = None
        self.height = None
        self.state = State.READY
        self.mouse_pressed = False
        self.geometry_mask = (Wnck.WindowMoveResizeMask.X | Wnck.WindowMoveResizeMask.Y | Wnck.WindowMoveResizeMask.WIDTH | Wnck.WindowMoveResizeMask.HEIGHT)
        self.zone = None
        self.zone_manager = None
        self.preset = None
        self.presets = None

    # Helpers
    def get_zone(self, x, y):
        for label, v in self.preset.items():
            if v['x'] <= x < v['x'] + v['width']:
                return label

    def set_window(self):
        cur_x, cur_y = mouse.Controller().position
        self.zone = self.get_zone(cur_x, cur_y)

        # get positions from preset and current zone
        x = self.preset[self.zone]['x']
        y = self.preset[self.zone]['y']
        width = self.preset[self.zone]['width']
        height = self.preset[self.zone]['height']

        # get active window and set geometry (size & position)
        active_window = self.screen.get_active_window()
        active_window.set_geometry(Wnck.WindowGravity(0), self.geometry_mask, x, y, width, height)

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

    def __key_press_callback(self, key):
        match self.state:
            case State.READY:
                if key == keyboard.Key.cmd_l:
                    if self.mouse_pressed:
                        self.zone_manager.show_all()
                        self.state = self.state.SET_WINDOW
                    else:
                        self.state = State.CTRL_READY

    def __key_release_callback(self, key):
        if key == keyboard.Key.cmd_l:
            self.zone_manager.hide()
            self.state = State.READY

    def __mouse_click_callback(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.mouse_pressed = pressed
            match self.state:
                case State.CTRL_READY:
                    self.zone_manager.show_all()
                    if pressed:
                        self.state = State.SET_WINDOW
                case State.SET_WINDOW:
                    if not pressed:
                        self.set_window()
                        self.zone_manager.hide()
                        self.state = State.CTRL_READY

    def __mouse_move_callback(self, x, y):
        match self.state:
            case State.SET_WINDOW:
                new_zone = self.get_zone(x, y)
                if new_zone != self.zone:
                    self.zone_manager.set_active(new_zone)
                    self.zone = new_zone

    # Gtk Method Overrides
    def do_startup(self):
        Gtk.Application.do_startup(self)

        with open('presets.json') as file:
            self.presets = json.load(file)
        self.preset = self.presets['center-right-bias']

        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.height = self.screen.get_height()
        self.width = self.screen.get_width()

        self.zone_manager = ZoneWindow(self.width, self.height, self.preset)

    def do_activate(self):
        # Start the keyboard listener in its own thread
        keyboard_listener = keyboard.Listener(on_press=self.key_press, on_release=self.key_release)
        keyboard_listener.start()

        # Start the mouse listener in its own thread
        mouse_listener = mouse.Listener(on_click=self.mouse_click, on_move=self.mouse_move)
        mouse_listener.start()

        if not self.window:
            self.window = AppWindow(application=self, title="Main Window")

        # start dummy window for Gtk main thread
        self.window.present()


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
