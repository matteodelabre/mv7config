import sys
import readline
import threading
from mv7config.text_hid import TextHID
from mv7config.microphone import Microphone


prompt = "> "


class ReaderThread(threading.Thread):
    def __init__(self, device):
        super().__init__()
        self._device = device
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            message = self._device.read_message(timeout_ms=200)

            if message:
                print(
                    "\r", message,
                    prompt, readline.get_line_buffer(),
                    sep="", end="", flush=True
                )

    def stop(self):
        self._stop_event.set()
        self.join()


def main():
    available_devices = Microphone.enumerate()

    if not available_devices:
        print("No MV7 microphone found")
        sys.exit(1)

    with TextHID(next(iter(available_devices))) as device:
        thread = ReaderThread(device)
        thread.start()

        while True:
            print(prompt, end="", flush=True)

            try:
                command = input()
            except (KeyboardInterrupt, EOFError):
                break

            if command:
                device.send_command(command)

            print()

        thread.stop()


if __name__ == "__main__":
    main()
