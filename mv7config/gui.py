from enum import Enum, auto
import os
import time
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import GLib, Gtk, Handy
from gi.repository.GObject import BindingFlags
from .microphone import Microphone, Mode, CompressorState, DistanceState, ToneState
from .dual_scale import DualScale


dirname = os.path.dirname(__file__)


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


def bind_toggles(source, source_prop, targets):
    values = {target: value for value, target in targets.items()}

    def on_source_changed():
        key = source.get_property(source_prop)

        if key in targets:
            for target in targets.values():
                if not target.props.sensitive:
                    target.set_sensitive(True)

            if not targets[key].props.active:
                targets[key].set_active(True)
        else:
            for target in targets.values():
                if target.props.sensitive:
                    target.set_sensitive(False)

    def on_target_changed(action):
        if action.props.active and action in values:
            next_value = values[action]

            if source.get_property(source_prop) != next_value:
                source.set_property(source_prop, next_value)

    for target in targets.values():
        target.connect("toggled", on_target_changed)

    on_source_changed()
    source.connect("notify::" + source_prop, lambda x, y: on_source_changed())


def bind_throttled(source, source_prop, target, target_prop, timeout=1):
    last_target_change = 0
    active_timeout = None

    def on_source_changed():
        nonlocal active_timeout
        since_last_change = time.time() - last_target_change

        if active_timeout is not None:
            GLib.source_remove(active_timeout)
            active_timeout = None

        if since_last_change < timeout:
            active_timeout = GLib.timeout_add(
                round((timeout - since_last_change) * 1000),
                on_source_changed,
            )
        else:
            next_value = source.get_property(source_prop)

            if target.get_property(target_prop) != next_value:
                target.set_property(target_prop, next_value)

    def on_target_changed():
        nonlocal last_target_change
        next_value = target.get_property(target_prop)

        if source.get_property(source_prop) != next_value:
            last_target_change = time.time()
            source.set_property(source_prop, next_value)

    target.set_property(
        target_prop,
        source.get_property(source_prop),
    )

    source.connect(
        "notify::" + source_prop,
        lambda x, y: on_source_changed()
    )

    target.connect(
        "notify::" + target_prop,
        lambda x, y: on_target_changed()
    )


@Gtk.Template(filename=os.path.join(dirname, "microphone_control_page.ui"))
class MicrophoneControlPage(Handy.PreferencesPage):
    __gtype_name__ = "MicrophoneControlPage"

    monitor_volume = Gtk.Template.Child()
    monitor_volume_adjustment = Gtk.Template.Child()
    monitor_mute = Gtk.Template.Child()
    monitor_mix = Gtk.Template.Child()

    mode_manual = Gtk.Template.Child()
    mode_auto = Gtk.Template.Child()

    mode_stack_parent = Gtk.Template.Child()
    mode_loading_box = Gtk.Template.Child()
    mode_manual_box = Gtk.Template.Child()
    mode_auto_box = Gtk.Template.Child()

    input_volume = Gtk.Template.Child()
    input_volume_adjustment = Gtk.Template.Child()
    input_mute = Gtk.Template.Child()
    input_mute_auto = Gtk.Template.Child()

    compressor_off = Gtk.Template.Child()
    compressor_light = Gtk.Template.Child()
    compressor_medium = Gtk.Template.Child()
    compressor_heavy = Gtk.Template.Child()

    limiter = Gtk.Template.Child()
    high_pass_filter = Gtk.Template.Child()
    presence_filter = Gtk.Template.Child()

    distance_close = Gtk.Template.Child()
    distance_far = Gtk.Template.Child()

    tone_neutral = Gtk.Template.Child()
    tone_dark = Gtk.Template.Child()
    tone_bright = Gtk.Template.Child()

    def __init__(self, microphone):
        super().__init__()
        self._microphone = microphone

        bind_throttled(
            self._microphone, "monitor-volume",
            self.monitor_volume_adjustment, "value",
        )

        self._microphone.bind_property(
            "monitor-mute", self.monitor_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self.monitor_mute.bind_property(
            "active", self.monitor_volume, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )

        bind_throttled(
            self._microphone, "monitor-mix-mic",
            self.monitor_mix, "first-value",
        )

        bind_throttled(
            self._microphone, "monitor-mix-pc",
            self.monitor_mix, "second-value",
        )

        bind_toggles(
            self._microphone, "mode",
            {
                Mode.Manual: self.mode_manual,
                Mode.Auto: self.mode_auto,
            }
        )

        self._microphone.bind_property(
            "mode", self.mode_stack_parent, "visible-child",
            BindingFlags.SYNC_CREATE,
            lambda _, value: getattr(self, f"mode_{value.name.lower()}_box"),
        )

        bind_throttled(
            self._microphone, "input-volume",
            self.input_volume_adjustment, "value",
        )

        self._microphone.bind_property(
            "input-mute", self.input_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self._microphone.bind_property(
            "input-mute", self.input_mute_auto, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self.input_mute.bind_property(
            "active", self.input_volume, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )

        bind_toggles(
            self._microphone, "compressor",
            {
                CompressorState.Off: self.compressor_off,
                CompressorState.Light: self.compressor_light,
                CompressorState.Medium: self.compressor_medium,
                CompressorState.Heavy: self.compressor_heavy,
            }
        )

        self._microphone.bind_property(
            "limiter", self.limiter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self._microphone.bind_property(
            "high-pass-filter", self.high_pass_filter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self._microphone.bind_property(
            "presence-filter", self.presence_filter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        bind_toggles(
            self._microphone, "auto-distance",
            {
                DistanceState.Close: self.distance_close,
                DistanceState.Far: self.distance_far,
            }
        )

        bind_toggles(
            self._microphone, "auto-tone",
            {
                ToneState.Neutral: self.tone_neutral,
                ToneState.Dark: self.tone_dark,
                ToneState.Bright: self.tone_bright,
            }
        )


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
