"""
TabPal, a TUI for adding and editing custom colour palettes for use in Tableau.
"""

import os
from platform import system
from re import fullmatch
import xml.etree.ElementTree as ET

from textual import on
from textual.app import App
from textual.containers import Vertical, Center
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Input,
    Label,
    Markdown,
    OptionList,
    Select,
)
from textual.validation import Validator
from textual.widgets.option_list import Option, Separator

PALETTE_TYPES = {
    "regular": "Categorical",
    "ordered-sequential": "Sequential",
    "ordered-diverging": "Diverging",
}

HEX_VALIDATION_REGEX = "^(#)?(?:[0-9a-fA-F]{6}){1}$"


# Validators.
class FilePath(Validator):
    """Verify the file path is valid."""

    def validate(self, value):
        """Check the file path exists."""
        if os.path.exists(value) and value.endswith("Preferences.tps"):
            return self.success()
        return self.failure()


class HexCode(Validator):
    """Validate the hex code is valid."""

    def validate(self, hex_code):
        """Validate hex code entered."""
        if fullmatch(HEX_VALIDATION_REGEX, hex_code):
            return self.success()
        return self.failure()


# Screens.
class Configuration(Screen):
    """Configuration page."""

    def compose(self):
        """Create child widgets for the app."""
        yield Markdown(
            """**TabPal** couldn't find your *Preferences* file. 
        
Enter the file path to your *Preferences* file or create an environmental \
    variable named `TAB_PAL_FILE`.
        """
        )

        yield Input(
            placeholder="File path of Preferences file.",
            validate_on=["submitted"],
            validators=FilePath(),
            id="file_path_input",
        )

        yield Label(id="status_message")

    @on(Input.Submitted)
    def show_status_message(self, event):
        """Update the label to show if the validation succeeded or not."""
        if not event.validation_result.is_valid:
            self.query_one("#status_message").update(
                "File not found. Please try again."
            )
        else:
            user_input = self.query_one(Input)
            preferences_file = user_input.value
            self.dismiss(preferences_file)


class AddPalette(Screen):
    """Add a new colour palette page."""

    def compose(self):
        """Create child widgets for the add palette screen."""
        with Center():
            yield Label("Palette name:", classes="add_palette")
            yield Input(id="palette_name", validate_on=["blur"])
        with Center():
            yield Label("Palette type:", classes="add_palette")
            yield Select(
                ((line, line) for line in PALETTE_TYPES.values()),
                allow_blank=False,
                classes="add_palette",
                id="palette_types",
            )
            yield Button("Add palette", classes="add_palette", id="add_palette_button")

    @on(Button.Pressed, "#add_palette_button")
    def add_new_palette(self):
        """Add a new (blank) colour palette."""

        palette_name = self.query_one("#palette_name").value
        existing_palettes_names = [
            palette.get("name") for palette in self.app.existing_palettes
        ]

        palette_type = self.query_one("#palette_types").value
        if palette_type == "Categorical":
            palette_type = "regular"
        elif palette_type == "Sequential":
            palette_type = "ordered-sequential"
        elif palette_type == "Diverging":
            palette_type = "ordered-diverging"

        if palette_name not in existing_palettes_names and palette_name != "":
            with open(self.app.preferences_file, "r", encoding="UTF-8") as f:
                tree = ET.parse(f)
                parent_tag = tree.find("preferences")
                element = ET.Element(
                    "color-palette", {"name": palette_name, "type": palette_type}
                )
                parent_tag.append(element)

            tree.write(
                self.app.preferences_file, encoding="utf-8", xml_declaration=True
            )
            self.dismiss(self.app.preferences_file)


class TabPal(App):
    """A TUI app for adding and editing colour palettes to Tableau."""

    CSS_PATH = "tabpal.tcss"
    SCREENS = {"configuration": Configuration, "add_palette": AddPalette}
    BINDINGS = [
        ("a", "add_palette", "Add palette"),
        ("d", "delete", "Delete palette or colour"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.preferences_file = self.find_preferences_file()
        self.existing_palettes = self.get_existing_palettes()
        self.dark = False

    # App functions.
    def compose(self):
        """Construct a user interface with widgets."""

        try:
            existing_palettes_names = [
                Option(palette.get("name"), id="test")
                for palette in self.existing_palettes
            ]
            existing_palettes_types = [
                Option(PALETTE_TYPES.get(palette.get("type")), disabled=True, id="test")
                for palette in self.existing_palettes
            ]
            seperators = [Separator() for item in existing_palettes_names]
            existing_palettes = [
                item
                for container in zip(
                    existing_palettes_names, existing_palettes_types, seperators
                )
                for item in container
            ]
            yield OptionList(*existing_palettes, id="existing_palettes")

        except TypeError:  # No custom colour palettes exist in the Preferences file.
            yield OptionList(id="existing_palettes")

        yield Vertical(
            OptionList(id="existing_colours"),
            Input(
                placeholder="Enter new code",
                id="add_code",
                validate_on=["submitted"],
                validators=HexCode(),
            ),
        )
        yield Vertical(id="colour_palettes_viz")
        yield Footer()

    def on_mount(self):
        """Push configuration screen if Preferences file not found."""

        if self.preferences_file is None:
            self.push_screen(Configuration(), self.refresh_palettes)

    # File manipulation.
    def find_preferences_file(self):
        """Look in the usual spots for the Preferences file."""

        WINDOWS_USUAL_PATH = (
            rf"C:\Users\{os.getlogin()}\Documents\My Tableau Repository\Preferences.tps"
        )
        MAC_USUAL_PATH = (
            rf"/Users/{os.getlogin()}/Documents/My Tableau Repository/Preferences.tps"
        )

        try:
            if not (VARIABLE_FILE_PATH := os.environ["TAB_PAL_FILE"]).endswith(
                "Preferences.tps"
            ):
                return None
            return VARIABLE_FILE_PATH
        except KeyError:
            if system() == "Darwin":
                if os.path.exists(MAC_USUAL_PATH):
                    return MAC_USUAL_PATH
            if system() == "Windows":
                if os.path.exists(WINDOWS_USUAL_PATH):
                    return WINDOWS_USUAL_PATH
            return None

    def get_existing_palettes(self):
        """Get the existing custom colour palettes from the user's
        Preferences file."""

        # Open Preferences file.
        try:
            with open(self.preferences_file, "r", encoding="UTF-8") as f:
                tree = ET.parse(f)
        # Preferences file can't be found. Note that in order for on_mount()
        # to execute a value needs to be returned to the app's
        # existing_palettes attribute, hence None being returned.
        except TypeError:
            return None

        # Parse Preferences file.
        palettes = []
        for palette in tree.findall(".//color-palette"):
            palette_name = palette.attrib.get("name")
            palette_type = palette.attrib.get("type")
            colours = [colour.text for colour in palette.findall("./color")]
            palettes.append(
                {"name": palette_name, "type": palette_type, "colours": colours}
            )
        return palettes

    def add_new_colour(self, palette_name, hex_code):
        """Add a new colour to the selected palette in the Preferences file."""

        with open(self.preferences_file, "r", encoding="UTF-8") as f:
            tree = ET.parse(f)
            parent_tag = tree.find(f'.//color-palette[@name="{palette_name}"]')
            element = ET.Element("color")
            element.text = hex_code
            parent_tag.append(element)

        tree.write(self.preferences_file, encoding="utf-8", xml_declaration=True)

    def refresh_palette_colours(self):
        """Refresh the palette's list of colours pane."""
        selected_option = (
            self.query_one("#existing_palettes")
            .get_option_at_index(self.query_one("#existing_palettes").highlighted)
            .prompt
        )
        existing_colours = [
            palette.get("colours")
            for palette in self.existing_palettes
            if palette.get("name") == selected_option
        ][0]
        options = [Option(colour) for colour in existing_colours]
        self.query_one("#existing_colours").clear_options()
        self.query_one("#existing_colours").add_options(options)

    def refresh_palettes(self, preferences_file):
        """Refreshes the existing colour palettes list in the app's
        pane."""

        self.preferences_file = preferences_file
        self.existing_palettes = self.get_existing_palettes()

        options_list = self.query_one("#existing_palettes")
        options_list.clear_options()
        existing_palettes_names = [
            Option(palette.get("name")) for palette in self.existing_palettes
        ]
        existing_palettes_types = [
            Option(PALETTE_TYPES.get(palette.get("type")), disabled=True)
            for palette in self.existing_palettes
        ]
        seperators = [Separator() for item in existing_palettes_names]
        existing_palettes = [
            item
            for container in zip(
                existing_palettes_names, existing_palettes_types, seperators
            )
            for item in container
        ]
        options_list.add_options(existing_palettes)

    def refresh_visualisation(self):
        """Refresh the visualisation pane with the current selected palette's
        colours."""
        viz = self.query_one("#colour_palettes_viz")
        viz.remove_children()

        try:
            highlighted_palette = (
                self.query_one("#existing_palettes")
                .get_option_at_index(self.query_one("#existing_palettes").highlighted)
                .prompt
            )
            highlighted_palette_colours = [
                colour
                for colour in self.existing_palettes
                if colour.get("name") == highlighted_palette
            ][0]["colours"]

            labels = []
            for colour in highlighted_palette_colours:
                label = Label(colour, classes="viz_labels")
                label.styles.background = colour
                labels.append(label)

            viz.mount(*labels)
        # No palette highlighted (when a palette is deleted or no custom colour
        # palettes exist.
        except TypeError:
            pass

    # Keys.
    def action_delete(self):
        """Delete the selected palette or palette colour."""

        with open(self.preferences_file, "r", encoding="UTF-8") as f:
            tree = ET.parse(f)
        root = tree.getroot()
        preferences = root.find("preferences")

        highlighted_colour_palette = (
            self.query_one("#existing_palettes")
            .get_option_at_index(self.query_one("#existing_palettes").highlighted)
            .prompt
        )
        colour_palette = preferences.find(
            f""".//color-palette[@name="{highlighted_colour_palette}"]"""
        )

        try:
            highlighted_colour = (
                self.query_one("#existing_colours")
                .get_option_at_index(self.query_one("#existing_colours").highlighted)
                .prompt
            )
            colour = [
                colour for colour in colour_palette if colour.text == highlighted_colour
            ][0]
            colour_palette.remove(colour)
            tree.write(self.preferences_file, encoding="utf-8", xml_declaration=True)
            self.query_one("#existing_colours").clear_options()
            self.existing_palettes = self.get_existing_palettes()
            self.refresh_palette_colours()
            self.refresh_visualisation()
            return None

        except TypeError:  # No colour highlighted.
            preferences.remove(colour_palette)
            tree.write(self.preferences_file, encoding="utf-8", xml_declaration=True)
            self.refresh_palettes(self.preferences_file)
            self.query_one("#existing_colours").clear_options()
            self.refresh_visualisation()
            return None

    def action_add_palette(self):
        """Add a new colour palette."""
        self.push_screen(AddPalette(self), self.refresh_palettes)

    # Widget interaction.
    @on(OptionList.OptionSelected, "#existing_palettes")
    def option_selected(self):
        """Refresh colours palette list and visualisation pane
        when a new colour palette is selected."""
        self.refresh_palette_colours()
        self.refresh_visualisation()

    @on(OptionList.OptionHighlighted, "#existing_palettes")
    def option_highlighted(self):
        """Refresh colours palette list and visualisation pane when a new
        colour palette is highlighted.

        This is necessary to populate the colours palettes list on launch of
        the app (as an option is highlighted, but not selected, when the widget
        is added to the app on launch.)
        """
        self.refresh_palette_colours()
        self.refresh_visualisation()

    @on(Input.Submitted, "#add_code")
    def process_input(self):
        """Add hex code to highlighted colour palette."""
        try:
            selected_option_index = self.query_one("#existing_palettes").highlighted
            highlighted_colour_palette = (
                self.query_one("#existing_palettes")
                .get_option_at_index(selected_option_index)
                .prompt
            )

            palette_colours = [
                palette.get("colours")
                for palette in self.existing_palettes
                if palette.get("name") == highlighted_colour_palette
            ][0]

            hex_code_input = self.query_one("#add_code")
            hex_code = hex_code_input.value
            if len(hex_code) < 7:
                hex_code = "#" + hex_code
            if (
                fullmatch(HEX_VALIDATION_REGEX, hex_code)
                and hex_code not in palette_colours
            ):
                self.add_new_colour(highlighted_colour_palette, hex_code)
                self.existing_palettes = self.get_existing_palettes()
                hex_code_input.clear()

                self.refresh_palette_colours()
                self.refresh_visualisation()
        except TypeError:  # No colour palette list exists.
            pass


# Entry point script.
def main():
    app = TabPal()
    app.run()


if __name__ == "__main__":
    main()
