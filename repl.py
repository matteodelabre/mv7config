import sys
import readline
import threading
import time
from mv7config.text_hid import TextHID
from mv7config.microphone import Microphone


prompt = "> "


class ReaderThread(threading.Thread):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.device.hid.set_nonblocking(1)
        self.stop = False

    def run(self):
        while not self.stop:
            message = self.device.read_message()

            if message:
                print(
                    "\r", message,
                    prompt, readline.get_line_buffer(),
                    sep="", end="", flush=True
                )

            time.sleep(0.05)


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

        thread.stop = True
        thread.join()


if __name__ == "__main__":
    main()
