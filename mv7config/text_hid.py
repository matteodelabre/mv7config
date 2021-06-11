import hid
import logging


logger = logging.getLogger(__name__)


class TextHID:
    def __init__(self, path):
        self._path = path
        self._hid = hid.device()
        self._hid.open_path(path)

    def close(self):
        self._hid.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_command(self, data):
        logger.debug(f"(OUT {self._path.decode()}) {data.strip()}")
        command = [ord(char) for char in data[:64]]
        self._hid.write(command + [0] * (64 - len(command)))

    def read_message(self, timeout_ms=0):
        data = self._hid.read(max_length=64, timeout_ms=timeout_ms)

        if not data:
            return None

        try:
            end = data.index(0)
        except ValueError:
            end = len(data)

        message = "".join(chr(code) for code in data[:end])
        logger.debug(f"( IN {self._path.decode()}) {message.strip()}")
        return message
