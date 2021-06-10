import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import Gtk, Handy
from .microphone import Microphone


class NoMicrophonePage(Handy.StatusPage):
    def __init__(self):
        super().__init__(
            title="No MV7 found",
            description="Check that your microphone is plugged in and try again.",
            icon_name="audio-input-microphone-symbolic",
        )

        self.retry_button = Gtk.Button(label="Retry", halign="center")
        style_context = self.retry_button.get_style_context()
        style_context.add_class("suggested-action")
        self.add(self.retry_button)


class MicrophoneControlPage(Handy.PreferencesPage):
    def __init__(self):
        super().__init__()

        # Group: Volume
        volume_group = Handy.PreferencesGroup(title="Volume")
        volume_list = Gtk.ListBox(selection_mode="none")
        volume_group.add(volume_list)
        self.add(volume_group)

        # Input volume
        input_volume_row = Handy.ActionRow(title="Input volume")
        input_volume_controls = Gtk.Box(spacing=6, hexpand=True)

        self.input_volume_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self.input_volume_scale.set_range(0, 3600)
        self.input_volume_scale.set_increments(1, 1)
        input_volume_controls.add(self.input_volume_scale)

        self.input_volume_mute = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="microphone-sensitivity-muted-symbolic"),
            valign="center",
            relief="none",
        )
        input_volume_controls.add(self.input_volume_mute)

        input_volume_row.add(input_volume_controls)
        input_volume_row.set_activatable_widget(self.input_volume_scale)
        volume_list.add(input_volume_row)

        # Output volume
        output_volume_row = Handy.ActionRow(title="Output volume")
        output_volume_controls = Gtk.Box(spacing=6, hexpand=True)

        self.output_volume_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self.output_volume_scale.set_range(-2400, 0)
        self.output_volume_scale.set_increments(1, 1)
        output_volume_controls.add(self.output_volume_scale)

        self.output_volume_mute = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="audio-volume-muted-symbolic"),
            valign="center",
            relief="none",
        )
        output_volume_controls.add(self.output_volume_mute)

        output_volume_row.add(output_volume_controls)
        output_volume_row.set_activatable_widget(self.output_volume_scale)
        volume_list.add(output_volume_row)

        # Monitor mix
        monitor_mix_row = Handy.ActionRow(title="Monitor mix")

        self.monitor_mix_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self.monitor_mix_scale.set_range(0, 26)
        self.monitor_mix_scale.set_increments(1, 1)
        self.monitor_mix_scale.add_mark(0, Gtk.PositionType.BOTTOM, "PC")
        self.monitor_mix_scale.add_mark(13, Gtk.PositionType.BOTTOM, "Balanced")
        self.monitor_mix_scale.add_mark(26, Gtk.PositionType.BOTTOM, "Mic")

        monitor_mix_row.add(self.monitor_mix_scale)
        monitor_mix_row.set_activatable_widget(self.monitor_mix_scale)
        volume_list.add(monitor_mix_row)

        # Group: Compressor
        compressor_group = Handy.PreferencesGroup(title="Compressor")
        compressor_list = Gtk.ListBox(selection_mode="none")
        compressor_group.add(compressor_list)
        self.add(compressor_group)

        # Compressor
        compressor_row = Handy.ActionRow(title="Compressor")

        self.compressor_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self.compressor_scale.set_range(0, 3)
        self.compressor_scale.set_increments(1, 1)
        self.compressor_scale.add_mark(0, Gtk.PositionType.BOTTOM, "Off")
        self.compressor_scale.add_mark(1, Gtk.PositionType.BOTTOM, "Light")
        self.compressor_scale.add_mark(2, Gtk.PositionType.BOTTOM, "Medium")
        self.compressor_scale.add_mark(3, Gtk.PositionType.BOTTOM, "Heavy")

        compressor_row.add(self.compressor_scale)
        compressor_row.set_activatable_widget(self.compressor_scale)
        compressor_list.add(compressor_row)

        # Limiter
        limiter_row = Handy.ActionRow(title="Limiter")
        self.limiter_switch = Gtk.Switch(valign="center")
        limiter_row.add(self.limiter_switch)
        limiter_row.set_activatable_widget(self.limiter_switch)
        compressor_list.add(limiter_row)

        # Group: Equalizer
        equalizer_group = Handy.PreferencesGroup(title="Equalizer")
        equalizer_list = Gtk.ListBox(selection_mode="none")
        equalizer_group.add(equalizer_list)
        self.add(equalizer_group)

        # High pass filter
        high_pass_row = Handy.ActionRow(title="High pass filter")
        self.high_pass_switch = Gtk.Switch(valign="center")
        high_pass_row.add(self.high_pass_switch)
        high_pass_row.set_activatable_widget(self.high_pass_switch)
        equalizer_list.add(high_pass_row)

        # Presence filter
        presence_row = Handy.ActionRow(title="Presence filter")
        self.presence_switch = Gtk.Switch(valign="center")
        presence_row.add(self.presence_switch)
        presence_row.set_activatable_widget(self.presence_switch)
        equalizer_list.add(presence_row)


class LockButton(Gtk.ToggleButton):
    def __init__(self, label="Lock"):
        super().__init__()
        container = Gtk.Box(spacing=6)
        self.add(container)

        image = Gtk.Image(icon_name="system-lock-screen-symbolic")
        container.add(image)

        label = Gtk.Label(label=label)
        container.add(label)


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_size_request(600, 400)
        self.discover_mics()

    def discover_mics(self, button=None):
        mics = Microphone.enumerate()

        if not mics:
            self.show_no_mic_page()
        else:
            self.show_control_page()

    def show_no_mic_page(self):
        if self.get_child() is not None:
            self.remove(self.get_child())

        no_mic_header_bar = Handy.HeaderBar(
            title=self.props.title,
            show_close_button=True,
        )
        self.set_titlebar(no_mic_header_bar)

        no_mic_page = NoMicrophonePage()
        no_mic_page.retry_button.connect("clicked", self.discover_mics)
        self.add(no_mic_page)
        self.show_all()

    def show_control_page(self):
        if self.get_child() is not None:
            self.remove(self.get_child())

        control_header_bar = Handy.HeaderBar(
            title=self.props.title,
            show_close_button=True,
        )
        control_lock = LockButton()
        # control_lock = Gtk.ToggleButton(
        #     label="Lock",
        #     image=Gtk.Image(icon_name="system-lock-screen-symbolic"),
        #     always_show_image=True,
        # )

        control_header_bar.pack_start(control_lock)
        self.set_titlebar(control_header_bar)

        control_page = MicrophoneControlPage()
        self.add(control_page)
        self.show_all()


class Application(Gtk.Application):
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

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()
