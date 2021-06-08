import hid
import time
import threading
from enum import Enum, Flag


vendor_id = 0x14ED
product_id = 0x1012
interface_number = 3


def list_devices():
    return [
        match["path"]
        for match in hid.enumerate(vendor_id, product_id)
        if match["interface_number"] == interface_number
    ]


class TextHID:
    def __init__(self, path):
        self.hid = hid.device()
        self.hid.open_path(path)

    def close(self):
        self.hid.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_command(self, data):
        command = [ord(char) for char in data[:64]]
        self.hid.write(command + [0] * (64 - len(command)))

    def send_commands(self, *args):
        for data in args:
            self.send_command(data)

    def read_message(self):
        data = self.hid.read(max_length=64)

        if not data:
            return None

        try:
            end = data.index(0)
        except ValueError:
            end = len(data)

        message = "".join(chr(code) for code in data[:end])
        return message


class CompressorState(Enum):
    Off = 0
    Low = 1
    Medium = 2
    High = 3


class EqualizerState(Flag):
    Off = 0
    HighPass = 1
    Presence = 2


class AutoLevelState(Enum):
    Off = 0
    CloseNeutral = 1
    CloseDark = 2
    CloseBright = 3
    FarNeutral = 4
    FarDark = 5
    FarBright = 6


class Microphone:
    def __init__(self, path, reboot=False):
        self._device = TextHID(path)
        self._device.hid.set_nonblocking(False)

        self._reader_thread = threading.Thread(target=self._reader_thread_run)

        self._state = {
            "pkgVersion": None,
            "fwVersion": None,
            "dspVersion": None,
            "serialNum": None,
            "lock": None,
            "audioMute": None,
            "volume": None,
            "micMute": None,
            "inputGain": None,
            "19": None,
            "1F": None,
            "31": None,
            "22": None,
            "34": None,
        }

        # Set user to admin, otherwise some commands are not usable
        self._device.send_command("su adm")
        response = self._device.read_message()
        assert response == "su=adm\n"

        # Wait until the DSP has booted
        self._device.send_command("bootDSP" if reboot else "bootDSP C")

        while self._device.read_message() != "dspBooted\n":
            time.sleep(.5)

        # Fill in metadata and state information
        self._running = True
        self._reader_thread.start()

        while not self.is_initialized():
            for key, value in self._state.items():
                if value is None:
                    if len(key) == 2:
                        self._device.send_command(f"getBlock {key}")
                    else:
                        self._device.send_command(key)

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

            if key in self._state:
                self._state[key] = value
        elif message.startswith("block "):
            key, value = message[6:].strip().split(" ", maxsplit=1)

            if key in self._state:
                self._state[key] = value

    def is_initialized(self):
        return self._state and all(
            value is not None for value in self._state.values()
        )

    def close(self):
        self._running = False
        self._reader_thread.join()
        self._state = {}
        self._device.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def package_version(self):
        return self._state["pkgVersion"]

    @property
    def firmare_version(self):
        return self._state["fwVersion"]

    @property
    def dsp_version(self):
        return self._state["dspVersion"]

    @property
    def serial_number(self):
        return self._state["serialNum"]

    @property
    def lock(self):
        return self._state["lock"] == "on"

    @lock.setter
    def lock(self, value):
        if value == self.lock:
            return

        self._device.send_command("lock on" if value else "lock off")

    @property
    def monitor_mute(self):
        return self._state["audioMute"] == "on"

    @monitor_mute.setter
    def monitor_mute(self, value):
        if value == self.monitor_mute:
            return

        self._device.send_command("audioMute on" if value else "audioMute off")

    @property
    def monitor_volume(self):
        return int(self._state["volume"][:-2])

    @monitor_volume.setter
    def monitor_volume(self, value):
        if self.monitor_volume == value:
            return

        value = max(min(value, 0), -24)
        self._device.send_command(f"volume {value}")

    @property
    def monitor_mix_mic(self):
        return int(self._state["22"][8:], 16)

    @monitor_mix_mic.setter
    def monitor_mix_mic(self, value):
        if self.monitor_mix_mic == value:
            return

        clamped_value = max(min(value, 0x4026E7), 0x20C5)
        send_value = self._state["22"][:8] + hex(clamped_value)[2:].zfill(8)
        self._device.send_command(f"setBlock 22 {send_value}")

    @property
    def monitor_mix_pc(self):
        return int(self._state["22"][:8], 16)

    @monitor_mix_pc.setter
    def monitor_mix_pc(self, value):
        if self.monitor_mix_pc == value:
            return

        clamped_value = max(min(value, 0x2026F3), 0x20C5)
        send_value = hex(clamped_value)[2:].zfill(8) + self._state["22"][8:]
        self._device.send_command(f"setBlock 22 {send_value}")

    @property
    def input_mute(self):
        return self._state["micMute"] == "on"

    @input_mute.setter
    def input_mute(self, value):
        if value == self.input_mute:
            return

        self._device.send_command("micMute on" if value else "micMute off")

    @property
    def input_volume(self):
        return int(self._state["inputGain"][:-2])

    @input_volume.setter
    def input_volume(self, value):
        if self.input_volume == value:
            return

        send_value = max(min(value, 36), 0)
        self._device.send_command(f"inputGain {send_value}")

    @property
    def compressor(self):
        return CompressorState(int(self._state["19"], 16))

    @compressor.setter
    def compressor(self, value):
        if self.compressor == value:
            return

        send_value = str(value.value).zfill(8)
        self._device.send_command(f"setBlock 19 {send_value}")

    @property
    def limiter(self):
        return self._state["1F"] == "00000001"

    @limiter.setter
    def limiter(self, value):
        if self.limiter == value:
            return

        send_value = "00000001" if value else "00000000"
        self._device.send_command(f"setBlock 1F {send_value}")

    @property
    def equalizer(self):
        return EqualizerState(int(self._state["31"], 16))

    @equalizer.setter
    def equalizer(self, value):
        if self.equalizer == value:
            return

        send_value = str(value.value).zfill(8)
        self._device.send_command(f"setBlock 31 {send_value}")

    @property
    def auto_level(self):
        return AutoLevelState(int(self._state["34"], 16))

    @auto_level.setter
    def auto_level(self, value):
        if self.auto_level == value:
            return

        send_value = str(value.value).zfill(8)
        self._device.send_command(f"setBlock 34 {send_value}")
