import threading
from typing import Any, Dict, Callable
from dataclasses import dataclass
from enum import Enum
import time
from gi.repository import GObject, GLib
import hid
from .text_hid import TextHID


# USB vendor ID for Shure products
shure_vendor_id = 0x14ED

# USB product ID for the MV7
mv7_product_id = 0x1012

# USB interface for the data HID communications
mv7_data_interface = 3


class Mode(Enum):
    """Modes for the Shure MV7 DSP."""
    # Currently switching between the two modes
    Loading = 0

    # Filters are tuned by the user
    Manual = 1

    # Filters are chosen based on a limited set of presets
    Auto = 2


class CompressorState(Enum):
    """Settings for the compressor."""
    Off = 0
    Light = 1
    Medium = 2
    Heavy = 3


class DistanceState(Enum):
    """User distance to microphone in auto mode."""
    Off = -1
    Close = 1
    Far = 4

    def parse(x):
        """Extract the distance component from the combined auto setting."""
        value = int(x, 16)

        if value >= DistanceState.Far.value:
            return DistanceState.Far
        elif value >= DistanceState.Close.value:
            return DistanceState.Close
        else:
            return DistanceState.Off


class ToneState(Enum):
    """Tone in auto mode."""
    Off = -1
    Neutral = 0
    Dark = 1
    Bright = 2

    def parse(x):
        """Extract the tone component from the combined auto setting."""
        value = int(x, 16)

        if value >= DistanceState.Far.value:
            return ToneState(value - DistanceState.Far.value)
        elif value >= DistanceState.Close.value:
            return ToneState(value - DistanceState.Close.value)
        else:
            return ToneState.Off


@dataclass
class MicrophoneProperty:
    """Represents a property that can be read from the HID interface."""
    # Name used in the Microphone class’s _state dict
    local_name: str

    # HID command used to query the current value of the property
    fetch_command: str

    # HID prefix signaling the answer to the property query
    receive_command: str

    # Filter for parsing the answer to the appropriate Python type
    parse_remote: Callable[str, Any]


microphone_properties = {
    prop.local_name: prop
    for prop in [
        MicrophoneProperty(
            local_name="package_version",
            fetch_command="pkgVersion",
            receive_command="pkgVersion",
            parse_remote=lambda x: x,
        ),
        MicrophoneProperty(
            local_name="firmware_version",
            fetch_command="fwVersion",
            receive_command="fwVersion",
            parse_remote=lambda x: x,
        ),
        MicrophoneProperty(
            local_name="dsp_version",
            fetch_command="dspVersion",
            receive_command="dspVersion",
            parse_remote=lambda x: x,
        ),
        MicrophoneProperty(
            local_name="serial_number",
            fetch_command="serialNum",
            receive_command="serialNum",
            parse_remote=lambda x: x,
        ),
        MicrophoneProperty(
            local_name="lock",
            fetch_command="lock",
            receive_command="lock",
            parse_remote=lambda x: x == "on",
        ),
        MicrophoneProperty(
            local_name="monitor_mute",
            fetch_command="audioMute",
            receive_command="audioMute",
            parse_remote=lambda x: x == "on",
        ),
        MicrophoneProperty(
            local_name="monitor_volume",
            fetch_command="volume",
            receive_command="volume",
            parse_remote=lambda x: int(float(x[:-2]) * 100),
        ),
        MicrophoneProperty(
            local_name="mode",
            fetch_command="dspMode",
            receive_command="dspMode",
            parse_remote=lambda x: Mode.Manual if x == "1" else Mode.Auto,
        ),
        MicrophoneProperty(
            local_name="input_mute",
            fetch_command="micMute",
            receive_command="micMute",
            parse_remote=lambda x: x == "on",
        ),
        MicrophoneProperty(
            local_name="input_volume",
            fetch_command="inputGain",
            receive_command="inputGain",
            parse_remote=lambda x: int(float(x[:-2]) * 100),
        ),
        MicrophoneProperty(
            local_name="monitor_mix_pc",
            fetch_command="getBlock 22",
            receive_command="22",
            parse_remote=lambda x: int(x[:8], 16),
        ),
        MicrophoneProperty(
            local_name="monitor_mix_mic",
            fetch_command="getBlock 22",
            receive_command="22",
            parse_remote=lambda x: int(x[8:], 16),
        ),
        MicrophoneProperty(
            local_name="compressor",
            fetch_command="getBlock 19",
            receive_command="19",
            parse_remote=lambda x: CompressorState(int(x, 16)),
        ),
        MicrophoneProperty(
            local_name="limiter",
            fetch_command="getBlock 1F",
            receive_command="1F",
            parse_remote=lambda x: x == "00000001",
        ),
        MicrophoneProperty(
            local_name="high_pass_filter",
            fetch_command="getBlock 31",
            receive_command="31",
            parse_remote=lambda x: int(x, 16) & 1 != 0,
        ),
        MicrophoneProperty(
            local_name="presence_filter",
            fetch_command="getBlock 31",
            receive_command="31",
            parse_remote=lambda x: int(x, 16) & 2 != 0,
        ),
        MicrophoneProperty(
            local_name="auto_distance",
            fetch_command="getBlock 34",
            receive_command="34",
            parse_remote=lambda x: DistanceState.parse(x),
        ),
        MicrophoneProperty(
            local_name="auto_tone",
            fetch_command="getBlock 34",
            receive_command="34",
            parse_remote=lambda x: ToneState.parse(x),
        ),
    ]
}

# List of properties that are changed when the DSP mode is switched
# between auto and manual
mode_reset = [
    "input_volume",
    "compressor",
    "limiter",
    "high_pass_filter",
    "presence_filter",
    "auto_distance",
    "auto_tone",
]


class Microphone(GObject.Object):
    """Interface with a Shure MV7 microphone via the USB HID interface."""
    __gsignals__ = {
        # Emitted when an instance has finished fetching its initial state
        "initialized": (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, path):
        """
        Open a microphone device.

        :param path: path to the device (keys of
            :meth:`Microphone.enumerate`’s return value)
        """
        super().__init__()
        self._device = TextHID(path)
        self._state = {}
        self._switching_modes_sending = threading.Event()
        self._switching_modes_fetching = threading.Event()
        self._stop_event = threading.Event()
        self._reader_thread = threading.Thread(target=self._reader_thread_run)

    def enumerate() -> Dict[bytes, Dict]:
        """List available compatible microphones."""
        return {
            match["path"]: match
            for match in hid.enumerate(shure_vendor_id, mv7_product_id)
            if match["interface_number"] == mv7_data_interface
        }

    def initialize(self):
        """Initiate communication with the device and fetch properties."""
        self._reader_thread.start()

    def _reader_thread_run(self):
        """Background loop for reading messages from the device."""
        # Set user to admin, otherwise some commands are not usable
        self._device.send_command("su adm")
        while self._device.read_message() != "su=adm\n":
            pass

        # Wait until the DSP has booted
        self._device.send_command("bootDSP C")
        while self._device.read_message() != "dspBooted\n":
            pass

        # Initial property fetching
        while self._fetch_fields():
            pass

        GLib.idle_add(lambda: self.emit("initialized"))

        while not self._stop_event.is_set():
            # Fetch missing fields (if the DSP mode was changed)
            message = self._device.read_message(timeout_ms=200)

            if message:
                self._parse_message(message)

            if self._switching_modes_fetching.is_set():
                while self._fetch_fields():
                    pass

                self._switching_modes_fetching.clear()
                self._notify_on_main_thread("mode")

    def _fetch_fields(self):
        """Fetch all missing fields in the _state dict."""
        commands = set()

        if "mode" not in self._state:
            commands.add(microphone_properties["mode"].fetch_command)
        else:
            for local_name, prop in microphone_properties.items():
                if local_name not in self._state:
                    commands.add(prop.fetch_command)

        if commands:
            # Send requests for missing state
            for command in commands:
                self._device.send_command(command)

            # Give time to the device to respond
            time.sleep(.5)

            while (message := self._device.read_message(timeout_ms=200)):
                self._parse_message(message)

            return True
        else:
            return False

    def _parse_message(self, message):
        """Read a message from the device and set property if appropriate."""
        if "=" in message:
            key, value = message.strip().split("=", maxsplit=1)
        elif message.startswith("block ") and "Not valid" not in message:
            key, value = message[6:].strip().split(" ", maxsplit=1)
        else:
            return

        for local_name, prop in microphone_properties.items():
            if key == prop.receive_command:
                next_value = prop.parse_remote(value)

                if local_name == "mode":
                    for reset_key in mode_reset:
                        self._switching_modes_sending.clear()
                        self._switching_modes_fetching.set()
                        self._state.pop(reset_key, None)

                if (
                    prop.local_name not in self._state
                    or next_value != self._state[prop.local_name]
                ):
                    self._state[prop.local_name] = next_value
                    self._notify_on_main_thread(prop.local_name)

    def _notify_on_main_thread(self, prop_name):
        GLib.idle_add(lambda: self.notify(prop_name))

    def identify(self):
        """Ask the device to blink its LEDs."""
        self._device.send_command("identify")

    def close(self):
        """Close connection to the device and background thread."""
        self._stop_event.set()
        self._reader_thread.join()
        self._device.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @GObject.Property(type=str)
    def package_version(self):
        return self._state.get("package_version", None)

    @GObject.Property(type=str)
    def firmware_version(self):
        return self._state.get("firmware_version", None)

    @GObject.Property(type=str)
    def dsp_version(self):
        return self._state.get("dsp_version", None)

    @GObject.Property(type=str)
    def serial_number(self):
        return self._state.get("serial_number", None)

    @GObject.Property(type=bool, default=False)
    def lock(self):
        return self._state.get("lock", None)

    @lock.setter
    def lock(self, value):
        if value != self._state["lock"]:
            self._state["lock"] = value
            self._device.send_command("lock on" if value else "lock off")

    @GObject.Property(type=bool, default=False)
    def monitor_mute(self):
        return self._state.get("monitor_mute", None)

    @monitor_mute.setter
    def monitor_mute(self, value):
        if value != self._state["monitor_mute"]:
            self._state["monitor_mute"] = value
            self._device.send_command("audioMute on" if value else "audioMute off")

    @GObject.Property(type=int, default=0, minimum=-2400, maximum=0)
    def monitor_volume(self):
        return self._state.get("monitor_volume", None)

    @monitor_volume.setter
    def monitor_volume(self, value):
        if value != self._state["monitor_volume"]:
            self._state["monitor_volume"] = send_value = max(min(value, 0), -2400)
            self._device.send_command(f"volume {send_value / 100:.2f}")

    @GObject.Property(type=int, default=0x20C5, minimum=0x20C5, maximum=0x4026E7)
    def monitor_mix_mic(self):
        return self._state.get("monitor_mix_mic", None)

    @monitor_mix_mic.setter
    def monitor_mix_mic(self, value):
        if value != self._state["monitor_mix_mic"]:
            self._state["monitor_mix_mic"] = max(min(value, 0x4026E7), 0x20C5)
            self._send_monitor_mix()

    @GObject.Property(type=int, default=0x20C5, minimum=0x20C5, maximum=0x2026F3)
    def monitor_mix_pc(self):
        return self._state.get("monitor_mix_pc", None)

    @monitor_mix_pc.setter
    def monitor_mix_pc(self, value):
        if value != self._state["monitor_mix_pc"]:
            self._state["monitor_mix_pc"] = max(min(value, 0x2026F3), 0x20C5)
            self._send_monitor_mix()

    def _send_monitor_mix(self):
        msb = hex(self._state["monitor_mix_pc"])[2:].zfill(8).upper()
        lsb = hex(self._state["monitor_mix_mic"])[2:].zfill(8).upper()
        self._device.send_command(f"setBlock 22 {msb}{lsb}")

    @GObject.Property
    def mode(self):
        if (
            self._switching_modes_sending.is_set()
            or self._switching_modes_fetching.is_set()
        ):
            return Mode.Loading
        else:
            return self._state.get("mode", None)

    @mode.setter
    def mode(self, value):
        if value != self._state["mode"]:
            self._state["mode"] = value
            self._switching_modes_sending.set()
            self._device.send_command(f"dspMode {value.value}")

    @GObject.Property(type=bool, default=False)
    def input_mute(self):
        return self._state.get("input_mute", None)

    @input_mute.setter
    def input_mute(self, value):
        if value != self._state["input_mute"]:
            self._state["input_mute"] = value
            self._device.send_command("micMute on" if value else "micMute off")

    @GObject.Property(type=int, default=0, minimum=0, maximum=3600)
    def input_volume(self):
        return self._state.get("input_volume", None)

    @input_volume.setter
    def input_volume(self, value):
        if value != self._state["input_volume"]:
            send_value = max(min(value, 3600), 0)
            half_distance = send_value % 50

            if 0 < half_distance < 25:
                send_value -= half_distance
            elif half_distance >= 25:
                send_value += (50 - half_distance)

            self._state["input_volume"] = send_value
            self._device.send_command(f"inputGain {send_value / 100:.2f}")

    @GObject.Property
    def compressor(self):
        return self._state.get("compressor", None)

    @compressor.setter
    def compressor(self, value):
        if value != self._state["compressor"]:
            self._state["compressor"] = value
            send_value = str(value.value).zfill(8)
            self._device.send_command(f"setBlock 19 {send_value}")

    @GObject.Property(type=bool, default=False)
    def limiter(self):
        return self._state.get("limiter", None)

    @limiter.setter
    def limiter(self, value):
        if value != self._state["limiter"]:
            self._state["limiter"] = value
            send_value = "00000001" if value else "00000000"
            self._device.send_command(f"setBlock 1F {send_value}")

    @GObject.Property(type=bool, default=False)
    def high_pass_filter(self):
        return self._state.get("high_pass_filter", None)

    @high_pass_filter.setter
    def high_pass_filter(self, value):
        if value != self._state["high_pass_filter"]:
            self._state["high_pass_filter"] = value
            self._send_equalizer()

    @GObject.Property(type=bool, default=False)
    def presence_filter(self):
        return self._state.get("presence_filter", None)

    @presence_filter.setter
    def presence_filter(self, value):
        if value != self._state["presence_filter"]:
            self._state["presence_filter"] = value
            self._send_equalizer()

    def _send_equalizer(self):
        send_value = 0

        if self._state["high_pass_filter"]:
            send_value |= 1

        if self._state["presence_filter"]:
            send_value |= 2

        send_value = str(send_value).zfill(8)
        self._device.send_command(f"setBlock 31 {send_value}")

    @GObject.Property
    def auto_distance(self):
        return self._state.get("auto_distance", None)

    @auto_distance.setter
    def auto_distance(self, value):
        if value != self._state["auto_distance"]:
            self._state["auto_distance"] = value
            self._send_auto_level()

    @GObject.Property
    def auto_tone(self):
        return self._state.get("auto_tone", None)

    @auto_tone.setter
    def auto_tone(self, value):
        if value != self._state["auto_tone"]:
            self._state["auto_tone"] = value
            self._send_auto_level()

    def _send_auto_level(self):
        if (
            self._state["auto_distance"] == DistanceState.Off
            or self._state["auto_tone"] == ToneState.Off
        ):
            send_value = 0
        else:
            send_value = (
                self._state["auto_distance"].value
                + self._state["auto_tone"].value
            )

        send_value = str(send_value).zfill(8)
        self._device.send_command(f"setBlock 34 {send_value}")
