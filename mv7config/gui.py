from enum import Enum, auto
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import Gtk, Handy
from gi.repository.GObject import BindingFlags
from .microphone import Microphone, Mode, CompressorState, DistanceState, ToneState
from .dual_scale import DualScale


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


class MicrophoneInitializationPage(Gtk.Box):
    def __init__(self):
        super().__init__(
            valign=Gtk.Align.CENTER,
            orientation=Gtk.Orientation.VERTICAL,
            spacing=26,
        )

        spinner = Gtk.Spinner(expand=False)
        spinner.set_size_request(80, 80)
        spinner.start()
        self.add(spinner)

        text = Gtk.Label()
        text.set_markup("<big>Initializing…</big>")
        self.add(text)


class BindRadio:
    def __init__(self, target, prop, mapping):
        self._target = target
        self._prop = prop
        self._mapping = mapping
        self._reverse_mapping = {
            value: key
            for key, value in mapping.items()
        }

        for button in mapping:
            if button is not None:
                button.connect("toggled", self._on_toggled)

        self._on_changed()
        target.connect("notify::" + prop, lambda x, y: self._on_changed())

    def _on_changed(self):
        button = self._reverse_mapping[self._target.get_property(self._prop)]

        if button is not None:
            button.set_active(True)

    def _on_toggled(self, action):
        if action.props.active:
            next_value = self._mapping[action]

            if self._target.get_property(self._prop) != next_value:
                self._target.set_property(self._prop, next_value)


class MicrophoneControlPage(Handy.PreferencesPage):
    def __init__(self, microphone):
        super().__init__()
        self._microphone = microphone

        # Group: Monitor
        monitor_group = Handy.PreferencesGroup(title="Monitor")
        monitor_list = Gtk.ListBox(selection_mode="none")
        monitor_group.add(monitor_list)
        self.add(monitor_group)

        # Monitor volume
        monitor_volume_row = Handy.ActionRow(title="Monitor volume")
        monitor_volume_controls = Gtk.Box(spacing=6, hexpand=True)

        monitor_volume_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        monitor_volume_scale.set_range(-2400, 0)
        monitor_volume_scale.set_increments(100, 100)
        self._microphone.bind_property(
            "monitor_volume", monitor_volume_scale.get_adjustment(), "value",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        monitor_volume_controls.add(monitor_volume_scale)

        monitor_volume_mute = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="audio-volume-muted-symbolic"),
            valign="center",
            relief="none",
        )
        self._microphone.bind_property(
            "monitor_mute", monitor_volume_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        monitor_volume_mute.bind_property(
            "active", monitor_volume_scale, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )
        monitor_volume_controls.add(monitor_volume_mute)

        monitor_volume_row.add(monitor_volume_controls)
        monitor_volume_row.set_activatable_widget(monitor_volume_mute)
        monitor_list.add(monitor_volume_row)

        # Monitor mix
        monitor_mix_row = Handy.ActionRow(title="Monitor mix")
        monitor_mix_control = DualScale(
            first_range=(0x20C5, 0x4026E7),
            second_range=(0x20C5, 0x2026F3),
            labels=("Mic off", "PC off"),
            increments=(200_000, 200_000),
        )
        self._microphone.bind_property(
            "monitor_mix_mic", monitor_mix_control, "first_value",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        self._microphone.bind_property(
            "monitor_mix_pc", monitor_mix_control, "second_value",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        monitor_mix_row.add(monitor_mix_control)
        monitor_list.add(monitor_mix_row)

        # Group: Signal
        signal_group = Handy.PreferencesGroup(title="Signal")
        self.add(signal_group)

        # Switch between auto and manual modes
        mode_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE,
            vhomogeneous=False,
            interpolate_size=True,
        )
        mode_stack_switcher = Gtk.StackSwitcher(
            stack=mode_stack,
            hexpand=True,
            homogeneous=False,
            halign="end",
            valign="center"
        )

        def mode_transform_forward(_, mode):
            if mode == Mode.Manual:
                return "manual"
            else:
                return "auto"

        def mode_transform_backward(_, name):
            if name == "manual":
                return Mode.Manual
            else:
                return Mode.Auto

        self._microphone.bind_property(
            "mode", mode_stack, "visible-child-name",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
            mode_transform_forward,
            mode_transform_backward,
        )

        mode_stack_switcher_row = Handy.ActionRow(title="Mode")
        mode_stack_switcher_row.add(mode_stack_switcher)
        signal_group.add(mode_stack_switcher_row)
        signal_group.add(mode_stack)

        # Mode: Manual
        manual_list = Gtk.ListBox(selection_mode="none")
        mode_stack.add_titled(manual_list, "manual", "Manual")

        # Input volume
        input_volume_row = Handy.ActionRow(title="Input volume")
        input_volume_controls = Gtk.Box(spacing=6, hexpand=True)

        input_volume_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        input_volume_scale.set_range(0, 3600)
        input_volume_scale.set_increments(100, 100)
        self._microphone.bind_property(
            "input_volume", input_volume_scale.get_adjustment(), "value",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        input_volume_controls.add(input_volume_scale)

        input_volume_mute = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="microphone-sensitivity-muted-symbolic"),
            valign="center",
            relief="none",
        )
        self._microphone.bind_property(
            "input_mute", input_volume_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        input_volume_mute.bind_property(
            "active", input_volume_scale, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )
        input_volume_controls.add(input_volume_mute)

        input_volume_row.add(input_volume_controls)
        input_volume_row.set_activatable_widget(input_volume_mute)
        manual_list.add(input_volume_row)

        # Compressor
        compressor_row = Handy.ActionRow(title="Compressor")
        compressor_controls = Gtk.Box(hexpand=True, valign="center", halign="end")
        compressor_controls.get_style_context().add_class("linked")

        compressor_off_button = Gtk.RadioButton.new_with_label_from_widget(
            None, "Off"
        )
        compressor_off_button.set_mode(False)
        compressor_controls.add(compressor_off_button)

        compressor_light_button = Gtk.RadioButton.new_with_label_from_widget(
            compressor_off_button, "Light"
        )
        compressor_light_button.set_mode(False)
        compressor_controls.add(compressor_light_button)

        compressor_medium_button = Gtk.RadioButton.new_with_label_from_widget(
            compressor_off_button, "Medium"
        )
        compressor_medium_button.set_mode(False)
        compressor_controls.add(compressor_medium_button)

        compressor_heavy_button = Gtk.RadioButton.new_with_label_from_widget(
            compressor_off_button, "Heavy"
        )
        compressor_heavy_button.set_mode(False)
        compressor_controls.add(compressor_heavy_button)

        self.compressor_binding = BindRadio(
            self._microphone, "compressor", {
                compressor_off_button: CompressorState.Off,
                compressor_light_button: CompressorState.Light,
                compressor_medium_button: CompressorState.Medium,
                compressor_heavy_button: CompressorState.Heavy,
            }
        )
        compressor_row.add(compressor_controls)
        manual_list.add(compressor_row)

        # Limiter
        limiter_row = Handy.ActionRow(title="Limiter")
        limiter_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "limiter", limiter_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        limiter_row.add(limiter_switch)
        limiter_row.set_activatable_widget(limiter_switch)
        manual_list.add(limiter_row)

        # High pass filter
        high_pass_row = Handy.ActionRow(title="High pass filter")
        high_pass_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "high_pass_filter", high_pass_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        high_pass_row.add(high_pass_switch)
        high_pass_row.set_activatable_widget(high_pass_switch)
        manual_list.add(high_pass_row)

        # Presence filter
        presence_row = Handy.ActionRow(title="Presence filter")
        presence_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "presence_filter", presence_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        presence_row.add(presence_switch)
        presence_row.set_activatable_widget(presence_switch)
        manual_list.add(presence_row)

        # Group: Auto
        auto_list = Gtk.ListBox(selection_mode="none")
        mode_stack.add_titled(auto_list, "auto", "Automatic")

        # Mute
        input_mute_row = Handy.ActionRow(title="Input mute")
        input_mute_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "input_mute", input_mute_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        input_mute_row.add(input_mute_switch)
        input_mute_row.set_activatable_widget(input_mute_switch)
        auto_list.add(input_mute_row)

        # Distance
        auto_distance_row = Handy.ActionRow(title="Distance")
        auto_distance_controls = Gtk.Box(hexpand=True, valign="center", halign="end")
        auto_distance_controls.get_style_context().add_class("linked")

        auto_distance_close_button = Gtk.RadioButton.new_with_label_from_widget(
            None, "Close"
        )
        auto_distance_close_button.set_mode(False)
        auto_distance_controls.add(auto_distance_close_button)

        auto_distance_far_button = Gtk.RadioButton.new_with_label_from_widget(
            auto_distance_close_button, "Far"
        )
        auto_distance_far_button.set_mode(False)
        auto_distance_controls.add(auto_distance_far_button)

        self.auto_distance_binding = BindRadio(
            self._microphone, "auto-distance", {
                None: DistanceState.Off,
                auto_distance_close_button: DistanceState.Close,
                auto_distance_far_button: DistanceState.Far,
            }
        )
        auto_distance_row.add(auto_distance_controls)
        auto_list.add(auto_distance_row)

        # Tone
        auto_tone_row = Handy.ActionRow(title="Tone")
        auto_tone_controls = Gtk.Box(hexpand=True, valign="center", halign="end")
        auto_tone_controls.get_style_context().add_class("linked")

        auto_tone_neutral_button = Gtk.RadioButton.new_with_label_from_widget(
            None, "Neutral"
        )
        auto_tone_neutral_button.set_mode(False)
        auto_tone_controls.add(auto_tone_neutral_button)

        auto_tone_dark_button = Gtk.RadioButton.new_with_label_from_widget(
            auto_tone_neutral_button, "Dark"
        )
        auto_tone_dark_button.set_mode(False)
        auto_tone_controls.add(auto_tone_dark_button)

        auto_tone_bright_button = Gtk.RadioButton.new_with_label_from_widget(
            auto_tone_neutral_button, "Bright"
        )
        auto_tone_bright_button.set_mode(False)
        auto_tone_controls.add(auto_tone_bright_button)

        self.auto_tone_binding = BindRadio(
            self._microphone, "auto-tone", {
                None: ToneState.Off,
                auto_tone_neutral_button: ToneState.Neutral,
                auto_tone_dark_button: ToneState.Dark,
                auto_tone_bright_button: ToneState.Bright,
            }
        )
        auto_tone_row.add(auto_tone_controls)
        auto_list.add(auto_tone_row)


class AppState(Enum):
    Uninitialized = auto()
    NoMicrophone = auto()
    HasMicrophone = auto()


class AppWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(600, 400)
        self.connect("destroy", lambda _: self.close_microphone())

        self._microphone = None
        self._state = AppState.Uninitialized
        self.discover_mics()

    def discover_mics(self):
        mics = Microphone.enumerate()

        if not mics:
            self.show_no_mic_page()
        else:
            self.open_microphone(next(iter(mics)))

    def show_no_mic_page(self):
        if self._state == AppState.NoMicrophone:
            return

        if self.get_child() is not None:
            self.remove(self.get_child())

        no_mic_header_bar = Handy.HeaderBar(
            title=self.props.title,
            show_close_button=True,
        )
        self.set_titlebar(no_mic_header_bar)

        no_mic_page = NoMicrophonePage()
        no_mic_page.retry_button.connect(
            "clicked", lambda _: self.discover_mics()
        )
        self.add(no_mic_page)
        self.show_all()

    def open_microphone(self, microphone_path):
        if self._state == AppState.HasMicrophone:
            return

        if self._microphone is not None:
            self._microphone.close()

        self._microphone = Microphone(microphone_path)
        self._microphone.connect("initialized", lambda _: self.show_control_page())

        if self.get_child() is not None:
            self.remove(self.get_child())

        initializing_header_bar = Handy.HeaderBar(
            title=self.props.title,
            show_close_button=True,
        )
        self.set_titlebar(initializing_header_bar)

        init_page = MicrophoneInitializationPage()
        self.add(init_page)
        self.show_all()

        self._microphone.initialize()

    def close_microphone(self):
        if self._microphone is not None:
            self._microphone.close()
            self._microphone = None

    def show_control_page(self):
        if self.get_child() is not None:
            self.remove(self.get_child())

        control_header_bar = Handy.HeaderBar(
            title=self._microphone.props.serial_number,
            show_close_button=True,
        )
        lock_toggle = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="system-lock-screen-symbolic"),
        )
        identify_button = Gtk.Button(
            image=Gtk.Image(icon_name="keyboard-brightness-symbolic"),
        )

        self._microphone.bind_property(
            "lock", lock_toggle, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        identify_button.connect(
            "clicked", lambda _: self._microphone.identify()
        )

        control_header_bar.pack_start(lock_toggle)
        control_header_bar.pack_start(identify_button)
        self.set_titlebar(control_header_bar)

        control_page = MicrophoneControlPage(self._microphone)

        for group in control_page.get_children():
            self._microphone.bind_property(
                "lock", group, "sensitive",
                BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
            )

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
