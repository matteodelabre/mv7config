import os
import gi
from gi.repository import Gtk, Handy, GObject
from gi.repository.GObject import BindingFlags
from .microphone import Microphone, Mode, CompressorState, DistanceState, ToneState
from .utils import bind_toggles, bind_throttled
from .dual_scale import DualScale


dirname = os.path.dirname(__file__)


@Gtk.Template(filename=os.path.join(dirname, "microphone_control_page.ui"))
class MicrophoneControlPage(Handy.PreferencesPage):
    __gtype_name__ = "MicrophoneControlPage"

    microphone = GObject.Property(type=Microphone)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("notify::microphone", self.on_set_microphone)

    def on_set_microphone(self, x, y):
        microphone = self.props.microphone

        if microphone is None:
            return

        bind_throttled(
            microphone, "monitor-volume",
            self.monitor_volume_adjustment, "value",
        )

        microphone.bind_property(
            "monitor-mute", self.monitor_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self.monitor_mute.bind_property(
            "active", self.monitor_volume, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )

        bind_throttled(
            microphone, "monitor-mix-mic",
            self.monitor_mix, "first-value",
        )

        bind_throttled(
            microphone, "monitor-mix-pc",
            self.monitor_mix, "second-value",
        )

        bind_toggles(
            microphone, "mode",
            {
                Mode.Manual: self.mode_manual,
                Mode.Auto: self.mode_auto,
            }
        )

        microphone.bind_property(
            "mode", self.mode_stack_parent, "visible-child",
            BindingFlags.SYNC_CREATE,
            lambda _, value: getattr(self, f"mode_{value.name.lower()}_box"),
        )

        bind_throttled(
            microphone, "input-volume",
            self.input_volume_adjustment, "value",
        )

        microphone.bind_property(
            "input-mute", self.input_mute, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        microphone.bind_property(
            "input-mute", self.input_mute_auto, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        self.input_mute.bind_property(
            "active", self.input_volume, "sensitive",
            BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
        )

        bind_toggles(
            microphone, "compressor",
            {
                CompressorState.Off: self.compressor_off,
                CompressorState.Light: self.compressor_light,
                CompressorState.Medium: self.compressor_medium,
                CompressorState.Heavy: self.compressor_heavy,
            }
        )

        microphone.bind_property(
            "limiter", self.limiter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        microphone.bind_property(
            "high-pass-filter", self.high_pass_filter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        microphone.bind_property(
            "presence-filter", self.presence_filter, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        bind_toggles(
            microphone, "auto-distance",
            {
                DistanceState.Close: self.distance_close,
                DistanceState.Far: self.distance_far,
            }
        )

        bind_toggles(
            microphone, "auto-tone",
            {
                ToneState.Neutral: self.tone_neutral,
                ToneState.Dark: self.tone_dark,
                ToneState.Bright: self.tone_bright,
            }
        )
