import time
import threading
from typing import Any, Callable
from dataclasses import dataclass
from enum import Enum
from gi.repository import GObject
import hid
from .text_hid import TextHID


shure_vendor_id = 0x14ED
mv7_product_id = 0x1012
mv7_data_interface = 3


class CompressorState(Enum):
    Off = 0
    Low = 1
    Medium = 2
    High = 3


class AutoDistanceState(Enum):
    Off = -1
    Close = 1
    Far = 4

    def parse(x):
        value = int(x, 16)

        if value >= AutoDistanceState.Far.value:
            return AutoDistanceState.Far
        elif value >= AutoDistanceState.Close.value:
            return AutoDistanceState.Close
        else:
            return AutoDistanceState.Off


class AutoToneState(Enum):
    Off = -1
    Neutral = 0
    Dark = 1
    Bright = 2

    def parse(x):
        value = int(x, 16)

        if value >= AutoDistanceState.Far.value:
            return AutoToneState(value - AutoDistanceState.Far.value)
        elif value >= AutoDistanceState.Close.value:
            return AutoToneState(value - AutoDistanceState.Close.value)
        else:
            return AutoToneState.Off


@dataclass
class MicrophoneProperty:
    local_name: str
    fetch_command: str
    receive_command: str
    parse_remote: Callable[str, Any]


microphone_properties = [
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
        parse_remote=lambda x: int(x, 16) & 1 == 1,
    ),
    MicrophoneProperty(
        local_name="presence_filter",
        fetch_command="getBlock 31",
        receive_command="31",
        parse_remote=lambda x: int(x, 16) & 2 == 1,
    ),
    MicrophoneProperty(
        local_name="auto_distance",
        fetch_command="getBlock 34",
        receive_command="34",
        parse_remote=lambda x: AutoDistanceState.parse(x),
    ),
    MicrophoneProperty(
        local_name="auto_tone",
        fetch_command="getBlock 34",
        receive_command="34",
        parse_remote=lambda x: AutoToneState.parse(x),
    ),
]


class Microphone(GObject.Object):
    def __init__(self, path):
        super().__init__()
        self._device = TextHID(path)
        self._state = {}

    def enumerate():
        return {
            match["path"]: match
            for match in hid.enumerate(shure_vendor_id, mv7_product_id)
            if match["interface_number"] == mv7_data_interface
        }

    def initialize(self):
        self._device.hid.set_nonblocking(False)
        self._reader_thread = threading.Thread(target=self._reader_thread_run)

        self._state = {}

        # Set user to admin, otherwise some commands are not usable
        self._device.send_command("su adm")
        response = self._device.read_message()
        assert response == "su=adm\n"

        # Wait until the DSP has booted
        self._device.send_command("bootDSP C")

        while self._device.read_message() != "dspBooted\n":
            time.sleep(.05)

        # Fill in metadata and state information
        self._running = True
        self._reader_thread.start()

        initialized = False

        while not initialized:
            initialized = True

            for prop in microphone_properties:
                if prop.local_name not in self._state:
                    self._device.send_command(prop.fetch_command)
                    initialized = False

            time.sleep(.5)

    def _reader_thread_run(self):
        self._device.hid.set_nonblocking(True)

        while self._running:
            message = self._device.read_message()

            if message:
                self._parse_message(message)

            time.sleep(0.05)

    def _parse_message(self, message):
        if "=" in message:
            key, value = message.strip().split("=", maxsplit=1)
        elif message.startswith("block "):
            key, value = message[6:].strip().split(" ", maxsplit=1)
        else:
            return

        for prop in microphone_properties:
            if key == prop.receive_command:
                next_value = prop.parse_remote(value)

                if (
                    prop.local_name not in self._state
                    or next_value != self._state[prop.local_name]
                ):
                    self._state[prop.local_name] = next_value
                    self.notify(prop.local_name)

    def close(self):
        self._running = False
        self._reader_thread.join()
        self._state = {}
        self._device.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @GObject.Property
    def package_version(self):
        return self._state["package_version"]

    @GObject.Property
    def firmware_version(self):
        return self._state["firmware_version"]

    @GObject.Property
    def dsp_version(self):
        return self._state["dsp_version"]

    @GObject.Property
    def serial_number(self):
        return self._state["serial_number"]

    @GObject.Property
    def lock(self):
        return self._state["lock"]

    @lock.setter
    def lock(self, value):
        if value != self._state["lock"]:
            self._state["lock"] = value
            self._device.send_command("lock on" if value else "lock off")

    @GObject.Property
    def monitor_mute(self):
        return self._state["monitor_mute"]

    @monitor_mute.setter
    def monitor_mute(self, value):
        if value != self._state["monitor_mute"]:
            self._state["monitor_mute"] = value
            self._device.send_command("audioMute on" if value else "audioMute off")

    @GObject.Property
    def monitor_volume(self):
        return self._state["monitor_volume"]

    @monitor_volume.setter
    def monitor_volume(self, value):
        if value != self._state["monitor_volume"]:
            self._state["monitor_volume"] = max(min(value, 0), -2400)
            send_value = str(self._state["monitor_volume"])
            send_value = send_value[:-2] + "." + send_value[-2:]
            self._device.send_command(f"volume {send_value}")

    @GObject.Property
    def monitor_mix_mic(self):
        return self._state["monitor_mix_mic"]

    @monitor_mix_mic.setter
    def monitor_mix_mic(self, value):
        if value != self._state["monitor_mix_mic"]:
            self._state["monitor_mix_mic"] = max(min(value, 0x4026E7), 0x20C5)
            self._send_monitor_mix()

    @GObject.Property
    def monitor_mix_pc(self):
        return self._state["monitor_mix_pc"]

    @monitor_mix_pc.setter
    def monitor_mix_pc(self, value):
        if value != self._state["monitor_mix_pc"]:
            self._state["monitor_mix_pc"] = max(min(value, 0x2026F3), 0x20C5)
            self._send_monitor_mix()

    def _send_monitor_mix(self):
        msb = hex(self._state["monitor_mix_pc"])[2:].zfill(8)
        lsb = hex(self._state["monitor_mix_mic"])[2:].zfill(8)
        self._device.send_command(f"setBlock 22 {msb}{lsb}")

    @GObject.Property(type=bool, default=True)
    def input_mute(self):
        return self._state["input_mute"]

    @input_mute.setter
    def input_mute(self, value):
        if value != self._state["input_mute"]:
            self._state["input_mute"] = value
            self._device.send_command("micMute on" if value else "micMute off")

    @GObject.Property
    def input_volume(self):
        return self._state["input_volume"]

    @input_volume.setter
    def input_volume(self, value):
        if value != self._state["input_volume"]:
            self._state["input_volume"] = max(min(value, 3600), 0)
            send_value = str(self._state["input_volume"])
            send_value = send_value[:-2] + "." + send_value[-2:]
            self._device.send_command(f"inputGain {send_value}")

    @GObject.Property
    def compressor(self):
        return self._state["compressor"]

    @compressor.setter
    def compressor(self, value):
        if value != self._state["compressor"]:
            self._state["compressor"] = value
            send_value = str(value.value).zfill(8)
            self._device.send_command(f"setBlock 19 {send_value}")

    @GObject.Property
    def limiter(self):
        return self._state["limiter"]

    @limiter.setter
    def limiter(self, value):
        if value != self._state["limiter"]:
            self._state["limiter"] = value
            send_value = "00000001" if value else "00000000"
            self._device.send_command(f"setBlock 1F {send_value}")

    @GObject.Property
    def high_pass_filter(self):
        return self._state["high_pass_filter"]

    @high_pass_filter.setter
    def high_pass_filter(self, value):
        if value != self._state["high_pass_filter"]:
            self._state["high_pass_filter"] = value
            self._send_equalizer()

    @GObject.Property
    def presence_filter(self):
        return self._state["presence_filter"]

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
        return self._state["auto_distance"]

    @auto_distance.setter
    def auto_distance(self, value):
        if value != self._state["auto_distance"]:
            self._state["auto_distance"] = value
            self._send_auto_level()

    @GObject.Property
    def auto_tone(self):
        return self._state["auto_tone"]

    @auto_tone.setter
    def auto_tone(self, value):
        if value != self._state["auto_tone"]:
            self._state["auto_tone"] = value
            self._send_auto_level()

    def _send_auto_level(self):
        if (
            self._state["auto_distance"] == AutoDistanceState.Off
            or self._state["auto_tone"] == AutoToneState.Off
        ):
            send_value = 0
        else:
            send_value = (
                self._state["auto_distance"].value
                + self._state["auto_tone"].value
            )

        send_value = str(send_value).zfill(8)
        self._device.send_command(f"setBlock 34 {send_value}")
