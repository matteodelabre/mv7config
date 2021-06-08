import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.header_bar = Gtk.HeaderBar()
        self.control_grid = Gtk.Grid(
            column_spacing=16,
            margin_start=16,
            margin_end=16,
            margin_top=16,
            margin_bottom=16,
        )
        self.controls = {}

        # Panel lock
        self.controls["lock"] = Gtk.ToggleButton(label="Lock")
        self.header_bar.pack_start(self.controls["lock"])

        # Input volume
        self.input_volume_label = Gtk.Label(
            label="Input volume",
            halign=Gtk.Align.START,
        )
        self.input_volume_controls = Gtk.Box()

        self.controls["input_volume_scale"] = scale = Gtk.Scale(hexpand=True)
        scale.set_range(0, 36)
        scale.set_increments(1, 1)
        scale.set_round_digits(0)
        scale.set_digits(0)
        self.input_volume_controls.append(scale)

        self.controls["input_volume_mute"] = button = Gtk.ToggleButton(label="Mute")
        self.input_volume_controls.append(button)

        self.control_grid.attach(self.input_volume_label, 0, 0, 1, 1)
        self.control_grid.attach(self.input_volume_controls, 1, 0, 1, 1)

        # Output volume
        self.output_volume_label = Gtk.Label(
            label="Output volume",
            halign=Gtk.Align.START,
        )
        self.output_volume_controls = Gtk.Box()

        self.controls["output_volume_scale"] = scale = Gtk.Scale(hexpand=True)
        scale.set_range(-24, 0)
        scale.set_increments(1, 1)
        scale.set_round_digits(0)
        scale.set_digits(0)
        self.output_volume_controls.append(scale)

        self.controls["output_volume_mute"] = button = Gtk.ToggleButton(label="Mute")
        self.output_volume_controls.append(button)

        self.control_grid.attach(self.output_volume_label, 0, 1, 1, 1)
        self.control_grid.attach(self.output_volume_controls, 1, 1, 1, 1)

        # Compressor
        self.compressor_label = Gtk.Label(
            label="Compressor",
            halign=Gtk.Align.START,
        )

        self.controls["compressor_scale"] = scale = Gtk.Scale(hexpand=True)
        scale.set_range(0, 3)
        scale.set_increments(1, 1)
        scale.set_round_digits(0)
        scale.set_digits(0)
        scale.add_mark(0, Gtk.PositionType.TOP, "Off")
        scale.add_mark(1, Gtk.PositionType.TOP, "Light")
        scale.add_mark(2, Gtk.PositionType.TOP, "Medium")
        scale.add_mark(3, Gtk.PositionType.TOP, "Heavy")

        self.control_grid.attach(self.compressor_label, 0, 2, 1, 1)
        self.control_grid.attach(scale, 1, 2, 1, 1)

        self.set_titlebar(self.header_bar)
        self.set_child(self.control_grid)


class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="re.delab.mv7config",
            **kwargs,
        )
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(application=self, title="mv7config")

        self.window.present()
