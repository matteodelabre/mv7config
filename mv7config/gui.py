from enum import Enum, auto
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import GObject, Gtk, Handy
from gi.repository.GObject import BindingFlags
from .microphone import Microphone, CompressorState


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

        for action in mapping:
            action.connect("toggled", self.on_toggled)

        self.on_changed()
        target.connect("notify::" + prop, lambda x, y: self.on_changed())

    def on_changed(self):
        button = self._reverse_mapping[self._target.get_property(self._prop)]
        button.set_active(True)

    def on_toggled(self, action):
        if action.props.active:
            next_value = self._mapping[action]

            if self._target.get_property(self._prop) != next_value:
                self._target.set_property(self._prop, next_value)


class DualScale(Gtk.Box):
    def __init__(
        self,
        first_range, second_range,
        labels, increments,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs, spacing=6)

        self._first_range = first_range
        self._first_value = first_range[1]
        self._second_range = second_range
        self._second_value = second_range[1]

        self._max_gap = max(
            first_range[1] - first_range[0],
            second_range[1] - second_range[0],
        )

        self._unlinked_scales = Gtk.Box(hexpand=True, spacing=0)

        self._first_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self._first_adj = self._first_scale.get_adjustment()
        self._first_scale.set_range(*first_range)
        self._first_scale.set_increments(*increments)
        self._first_scale.add_mark(
            first_range[0],
            Gtk.PositionType.BOTTOM,
            labels[0],
        )
        self._unlinked_scales.add(self._first_scale)

        self._second_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
            inverted=True,
        )
        self._second_adj = self._second_scale.get_adjustment()
        self._second_scale.set_range(*second_range)
        self._second_scale.set_increments(*increments)
        self._second_scale.add_mark(
            second_range[0],
            Gtk.PositionType.BOTTOM,
            labels[1],
        )
        self._unlinked_scales.add(self._second_scale)
        self.pack_start(
            self._unlinked_scales,
            expand=True,
            fill=True,
            padding=0
        )
        self._unlinked_scales.set_no_show_all(True)

        self._linked_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
            has_origin=False,
        )
        self._linked_adj = self._linked_scale.get_adjustment()
        self._linked_scale.set_range(0, self._max_gap * 2)
        self._linked_scale.set_increments(*increments)
        self._linked_scale.add_mark(
            0,
            Gtk.PositionType.BOTTOM,
            labels[0],
        )
        self._linked_scale.add_mark(
            self._max_gap,
            Gtk.PositionType.BOTTOM,
            "",
        )
        self._linked_scale.add_mark(
            self._max_gap * 2,
            Gtk.PositionType.BOTTOM,
            labels[1],
        )
        self.pack_start(
            self._linked_scale,
            expand=True,
            fill=True,
            padding=0
        )
        self._linked_scale.set_no_show_all(True)

        self._link = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="insert-link-symbolic"),
            valign="center",
            relief="none",
            active=True,
        )
        self.pack_end(self._link, expand=False, fill=False, padding=0)

        self._link.connect("toggled", self._on_link_toggled)
        self._on_link_toggled(self._link)

        self._first_adj.connect("notify::value", self._on_scale_changed)
        self._second_adj.connect("notify::value", self._on_scale_changed)
        self._linked_adj.connect("notify::value", self._on_scale_changed)

    def _on_scale_changed(self, target, _=None):
        if self._link.props.active:
            linked_value = int(self._linked_adj.props.value)

            if linked_value == self._max_gap:
                next_first_value = self._first_range[1]
                next_second_value = self._second_range[1]
            elif linked_value < self._max_gap:
                next_first_value = self._first_range[0] + round(
                    (self._first_range[1] - self._first_range[0])
                    * (linked_value / self._max_gap)
                )
                next_second_value = self._second_range[1]
            else:
                next_first_value = self._first_range[1]
                next_second_value = self._second_range[0] + round(
                    (self._second_range[1] - self._second_range[0])
                    * ((self._max_gap * 2 - linked_value) / self._max_gap)
                )
        else:
            if target == self._first_adj:
                next_first_value = int(target.props.value)
                next_second_value = self._second_value
            elif target == self._second_adj:
                next_first_value = self._first_value
                next_second_value = int(target.props.value)
            else:
                return

        if next_first_value != self._first_value:
            self._first_value = next_first_value
            self.notify("first_value")

        if next_second_value != self._second_value:
            self._second_value = next_second_value
            self.notify("second_value")

    def _update_scales(self):
        if self._link.props.active:
            if self._first_value == self._first_range[1]:
                linked_value = round(self._max_gap * (1 +
                    (self._second_range[1] - self._second_value)
                    / (self._second_range[1] - self._second_range[0])
                ))
            else:
                linked_value = round(self._max_gap * (
                    self._first_value
                    / (self._first_range[1] - self._first_range[0])
                ))

            if int(self._linked_adj.props.value) != linked_value:
                self._linked_adj.props.value = linked_value
        else:
            if int(self._first_adj.props.value) != self._first_value:
                self._first_adj.props.value = self._first_value

            if int(self._second_adj.props.value) != self._second_value:
                self._second_adj.props.value = self._second_value

    def _on_link_toggled(self, toggle):
        if toggle.props.active:
            self._linked_scale.show()
            self._unlinked_scales.hide()
        else:
            self._unlinked_scales.show()
            self._first_scale.show()
            self._second_scale.show()
            self._linked_scale.hide()

        self._update_scales()

    @GObject.Property(type=int, default=0)
    def first_value(self):
        return self._first_value

    @first_value.setter
    def first_value(self, value):
        self._first_value = value
        self._update_scales()

    @GObject.Property(type=int, default=0)
    def second_value(self):
        return self._second_value

    @second_value.setter
    def second_value(self, value):
        self._second_value = value
        self._update_scales()


class MicrophoneControlPage(Handy.PreferencesPage):
    def __init__(self, microphone):
        super().__init__()
        self._microphone = microphone

        # Group: Volume
        volume_group = Handy.PreferencesGroup(title="Volume")
        volume_list = Gtk.ListBox(selection_mode="none")
        volume_group.add(volume_list)
        self.add(volume_group)

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
        volume_list.add(input_volume_row)

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
        volume_list.add(monitor_volume_row)

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
        volume_list.add(monitor_mix_row)

        # Group: Compressor
        compressor_group = Handy.PreferencesGroup(title="Compressor")
        compressor_list = Gtk.ListBox(selection_mode="none")
        compressor_group.add(compressor_list)
        self.add(compressor_group)

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
        compressor_list.add(compressor_row)

        # Limiter
        limiter_row = Handy.ActionRow(title="Limiter")
        limiter_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "limiter", limiter_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        limiter_row.add(limiter_switch)
        limiter_row.set_activatable_widget(limiter_switch)
        compressor_list.add(limiter_row)

        # Group: Equalizer
        equalizer_group = Handy.PreferencesGroup(title="Equalizer")
        equalizer_list = Gtk.ListBox(selection_mode="none")
        equalizer_group.add(equalizer_list)
        self.add(equalizer_group)

        # High pass filter
        high_pass_row = Handy.ActionRow(title="High pass filter")
        high_pass_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "high_pass_filter", high_pass_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        high_pass_row.add(high_pass_switch)
        high_pass_row.set_activatable_widget(high_pass_switch)
        equalizer_list.add(high_pass_row)

        # Presence filter
        presence_row = Handy.ActionRow(title="Presence filter")
        presence_switch = Gtk.Switch(valign="center")
        self._microphone.bind_property(
            "presence_filter", presence_switch, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )
        presence_row.add(presence_switch)
        presence_row.set_activatable_widget(presence_switch)
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
            title=self.props.title,
            show_close_button=True,
        )
        control_lock = LockButton()

        self._microphone.bind_property(
            "lock", control_lock, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        control_header_bar.pack_start(control_lock)
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
