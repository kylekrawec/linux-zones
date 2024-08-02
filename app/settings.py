import gi
from typing import Optional, Dict, List

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk

import display
from base import GtkStyleableMixin
from zones import ZoneContainer
from editor import ZoneEditorWindow
from widgets import IconButton
from config import config


class SchemaDisplay(GtkStyleableMixin, Gtk.Box):
    """
    A custom GTK widget that displays a schema layout with an edit button.

    This class creates a vertical box containing a header with the schema name
    and an edit button, followed by a ZoneContainer that visually represents
    the schema layout.

    Attributes:
        name (str): The name of the schema.
        schema (List[Dict]): The schema data structure.
        header (Gtk.Box): The header container for the title and edit button.
        _container (ZoneContainer): The container displaying the schema layout.
    """

    def __init__(self, name: str, schema: List[Dict]):
        """
        Initialize the SchemaDisplay widget.

        :param name: The name of the schema.
        :param schema: The schema data structure.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.name = name
        self.schema = schema
        self._build_ui()

    def _build_ui(self):
        """Build the user interface components."""
        self._create_header()
        self._create_container()
        self._apply_styles()
        self.show_all()

    def _create_header(self):
        """Create and add the header with title and edit button."""
        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label=self.name)
        edit_button = Gtk.Button(label="edit")

        self.header.pack_start(title, expand=False, fill=False, padding=0)
        self.header.pack_end(edit_button, expand=False, fill=False, padding=0)

        edit_button.connect('clicked', self._on_edit_button_click)

        self.add(self.header)

    def _create_container(self):
        """Create and add the ZoneContainer."""
        size = int(display.get_workarea().height * 0.1)
        self._container = ZoneContainer(self.schema).add_zone_style_class('preset-display-pane')
        self._container.set_size_request(size, size)
        self.add(self._container)

    def _apply_styles(self):
        """Apply CSS styles to the widget components."""
        self.header.get_style_context().add_class('preset-display-box-header')
        self.add_style_class('preset-display-box')

    def _on_edit_button_click(self, button):
        """
        Handle edit button click event.

        :param button: The button that was clicked.
        """
        editor = ZoneEditorWindow(self.schema, self.name)
        editor.connect('preset-save', self._on_preset_save)
        editor.show_all()

    def _on_preset_save(self, editor: ZoneEditorWindow, schemas: List[Dict]):
        """
        Handle preset save event from the editor.

        :param editor: The ZoneEditorWindow that emitted the event.
        :param schemas: The updated schemas.
        """
        new_schema = schemas.get(self.name)
        if new_schema:
            self.schema = new_schema
            self.remove(self._container)
            self._create_container()
            self.show_all()


class SchemaDisplayLayout(Gtk.FlowBox):
    """
     A layout widget for displaying multiple schema presets and a button to create new presets.

    This class creates a horizontal flow box that contains SchemaDisplay widgets
    for each schema preset and a button to add new presets.

    Attributes:
        schemas (Dict[str, List[Dict]]): A dictionary of schema presets.
    """

    def __init__(self, schemas: Dict[str, List[Dict]]):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True
        )
        self.schemas = schemas
        self._build_ui()

    def _build_ui(self):
        """Build the user interface components."""
        self._add_schema_displays()
        self._add_new_preset_button()
        self.show_all()

    def _add_schema_displays(self):
        """Add SchemaDisplay widgets for each schema."""
        for name, schema in self.schemas.items():
            self.add(SchemaDisplay(name, schema))

    def _add_new_preset_button(self):
        """Add a button for creating new presets."""
        new_preset_btn = IconButton('plus-sign.svg')
        new_preset_btn.set_size_request(50, 50)
        new_preset_btn.connect('clicked', self._on_new_preset_click)
        self.add(new_preset_btn)
        self._new_preset_btn = new_preset_btn  # Store reference to button

    def _on_new_preset_click(self, button):
        """Handle new preset button click."""
        empty_schema = [{'x': 0, 'y': 0, 'width': 1, 'height': 1}]  # Single zone covering entire workarea
        if name := self._get_preset_name():
            editor = ZoneEditorWindow(empty_schema, name)
            editor.connect('preset-save', self._on_preset_save)
            editor.show_all()

    def _get_preset_name(self) -> Optional[str]:
        """
        Display a dialog to get the new preset name from the user.

        :return: The entered preset name, or None if cancelled.
        """
        name = None
        # Create a dialog window with Cancel and OK buttons
        dialog = Gtk.Dialog(title='Enter Preset Name')
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )

        # Create and add an entry field to the dialog
        entry = Gtk.Entry()
        dialog.get_content_area().add(entry)
        dialog.set_size_request(300, 0)
        dialog.show_all()

        # Run the dialog and wait for user response
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # If user clicked OK, get the entered text
            name = entry.get_text()
        # Clean up
        dialog.destroy()
        return name

    def _on_preset_save(self, editor: ZoneEditorWindow, new_schemas: Dict[str, List[Dict]]):
        """
        Handle preset save event from the editor and updates displayed schemas.

        :param editor: The ZoneEditorWindow that emitted the event.
        :param new_schemas: The updated schemas.
        """
        self.schemas = new_schemas
        self._clear()
        self._build_ui()

    def _clear(self):
        """Remove all child widgets."""
        for child in self.get_children():
            self.remove(child)


class SettingsWindow(Gtk.ApplicationWindow):
    """
    A window for displaying and managing schema settings.

    This class creates a window that displays sections for custom presets
    and templates, each containing a SchemaDisplayLayout.

    Attributes:
        layout (Gtk.Box): The main vertical layout container for the window.
    """

    def __init__(self):
        """Initialize the SettingsWindow."""
        super().__init__(title="Settings")
        self._configure_window()
        self._build_ui()

    def _configure_window(self):
        """Configure window size and position."""
        workarea = display.get_workarea()
        height = int(workarea.height * 0.5)
        width = int(height * 16 / 9)  # 16:9 aspect ratio

        # Set minimum and default window size
        self.set_size_request(width // 2, height // 2)
        self.set_default_size(width, height)

        # Center the window on the screen
        x = (workarea.width - width) // 2
        y = (workarea.height - height) // 2
        self.move(x, y)

    def _build_ui(self):
        """Build the user interface components."""
        self.layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.layout.get_style_context().add_class('settings-window')

        # Create scrollable container
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.layout)

        self.add(scrolled_window)

        # Add sections for custom presets and templates
        self._add_schema_section('Custom', config.presets)
        self._add_schema_section('Templates', config.templates)

    def _add_schema_section(self, label: str, schemas: Dict[str, List[Dict]]):
        """
        Add a section of schemas with a header.

        :param label: The label for the section header.
        :param schemas: The schemas to display in this section.
        """
        header = Gtk.Label(label=label)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(header, expand=False, fill=False, padding=12)

        self.layout.pack_start(header_box, expand=False, fill=False, padding=0)
        self.layout.pack_start(SchemaDisplayLayout(schemas), expand=True, fill=True, padding=0)
