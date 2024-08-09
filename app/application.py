import os

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, GLib, Gio, Wnck, AppIndicator3
from pynput import keyboard, mouse

from .base import State
from .zones import ZoneDisplayWindow
from .display import get_workarea
from .config import config
from .settings import SettingsWindow


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.example.linuxzones", **kwargs)
        self.screen = None
        self.workarea = None
        self.state = State.READY
        self.mouse_pressed = False
        self.current_zone = None

        # Default settings
        self.default_preset = config.presets.get(config.settings.get('default_preset'))

        self.zone_display_window = None
        self.settings_window = None
        self.indicator = None

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

    def create_indicator(self):
        # Create the AppIndicator
        self.indicator = AppIndicator3.Indicator.new(
            "linuxzones-indicator",
            "linuxzones",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        # Create the menu for the indicator
        menu = Gtk.Menu()

        # Add menu items
        item_settings = Gtk.MenuItem(label="Settings")
        item_settings.connect("activate", self.on_settings_clicked)
        menu.append(item_settings)

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self.on_quit_clicked)
        menu.append(item_quit)

        menu.show_all()

        # Set the menu
        self.indicator.set_menu(menu)

    def on_settings_clicked(self, widget):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        self.settings_window.show_all()

    def on_quit_clicked(self, widget):
        self.quit()

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
                for i, name in config.settings['zonemap'].items():
                    if keyboard.KeyCode.from_char(i) == key:
                        self.zone_display_window.set_preset(config.presets.get(name, self.default_preset))
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

        # Load and register app resources
        resource_path = os.path.abspath('resources/app.gresource')
        resource = Gio.Resource.load(resource_path)
        Gio.resources_register(resource)

        # get screen interaction object
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()

        # Create the AppIndicator
        self.create_indicator()

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

        # Create application windows if they don't exist
        if not self.zone_display_window:
            self.zone_display_window = ZoneDisplayWindow(self.default_preset)
            self.zone_display_window.set_application(self)

        if not self.settings_window:
            self.settings_window = SettingsWindow()
