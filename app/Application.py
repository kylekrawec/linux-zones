import sys
from enum import Enum
from pynput import keyboard, mouse
import gi

from config import Config
from zones import ZoneWindow, InteractiveZoneDisplay
from settings import ZoneEditor

gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
from gi.repository import Gtk, GLib, Wnck, Gdk


class State(Enum):
    READY = 0
    CTRL_READY = 1
    SET_WINDOW = 2
    SET_ZONE = 3


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.linuxzones", **kwargs)
        self.screen = None
        self.state = State.READY
        self.mouse_pressed = False
        self.geometry_mask = (Wnck.WindowMoveResizeMask.X | Wnck.WindowMoveResizeMask.Y | Wnck.WindowMoveResizeMask.WIDTH | Wnck.WindowMoveResizeMask.HEIGHT)
        self.current_zone = None
        self.zones = None
        self.settings = None
        self.presets = None
        self.styles = None

    # Helpers
    def get_zone_label(self, x, y):
        for label, bounds in self.zones.display.zones.items():
            if bounds.x <= x < bounds.x + bounds.width and bounds.y <= y < bounds.y + bounds.height:
                return label

    def set_window(self):
        cur_x, cur_y = mouse.Controller().position
        self.current_zone = self.get_zone_label(cur_x, cur_y)

        # get positions from preset and current zone
        x = self.zones.display.zones[self.current_zone].x
        y = self.zones.display.zones[self.current_zone].y
        width = self.zones.display.zones[self.current_zone].width
        height = self.zones.display.zones[self.current_zone].height

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

    def on_activate_shortcut(self):
        GLib.idle_add(self.__on_activate_shortcut)

    def __key_press_callback(self, key):
        match self.state:
            case State.READY:
                if key == keyboard.Key.cmd_l:
                    if self.mouse_pressed:
                        self.zones.show_all()
                        self.state = self.state.SET_WINDOW
                    else:
                        self.state = State.CTRL_READY
            case State.SET_ZONE:
                for i, name in self.settings.zonemap.items():
                    if keyboard.KeyCode.from_char(i) == key:
                        self.zones.display.set_zones(self.presets.get(name))
                        self.zones.show()

    def __key_release_callback(self, key):
        match self.state:
            case State.SET_ZONE:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.cmd_l or key == keyboard.Key.alt_l:
                    self.state = State.READY
                else:
                    self.zones.hide()
            case _:
                if key == keyboard.Key.cmd_l:
                    self.zones.hide()
                    self.state = State.READY

    def __mouse_click_callback(self, x, y, button, pressed):
        if button == mouse.Button.left:
            self.mouse_pressed = pressed
            match self.state:
                case State.CTRL_READY:
                    self.zones.show_all()
                    if pressed:
                        self.state = State.SET_WINDOW
                case State.SET_WINDOW:
                    if not pressed:
                        self.set_window()
                        self.zones.hide()
                        self.state = State.CTRL_READY

    def __mouse_move_callback(self, x, y):
        match self.state:
            case State.SET_WINDOW:
                new_zone = self.get_zone_label(x, y)
                if new_zone != self.current_zone:
                    self.zones.display.set_active(new_zone)
                    self.current_zone = new_zone

    def __on_activate_shortcut(self):
        self.state = State.SET_ZONE

    # Gtk Method Overrides
    def do_startup(self):
        Gtk.Application.do_startup(self)

        # get work area dimentions
        display = Gdk.Display.get_default()
        # Fetch the primary monitor number
        primary_monitor = display.get_primary_monitor()
        workarea = primary_monitor.get_workarea()

        # get screen interaction
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        # load configuration
        self.settings = Config('settings.json').load()
        self.presets = Config('presets.json').load()
        self.styles = Config('styles.json').load()

        # create zone display and window container
        default_preset = self.presets[list(self.presets.keys())[0]]
        display = InteractiveZoneDisplay(default_preset, self.styles.active_zone)
        self.zones = ZoneWindow(display)

        # set window position, size and trigger allocation process
        self.zones.move(workarea.x, workarea.y)
        self.zones.set_size_request(workarea.width, workarea.height)
        self.zones.show_all() # this is not ideal but it works
        self.zones.hide()

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

        # add application windows
        self.add_window(self.zones)


if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)
