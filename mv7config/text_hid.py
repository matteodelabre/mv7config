import hid
import logging


logger = logging.getLogger(__name__)

## -- set this flag to True if your hid implementation supports hid.Device (capital D in Device)
g__SUPPORT__hid_Device = True


class TextHID:
    def __init__(self, path):
        self._path = path
        if (g__SUPPORT__hid_Device == True):
          vid = 0x14ED
          pid = 0x1012
          self._hid = hid.Device(vid, pid)
        else:
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
        if (g__SUPPORT__hid_Device == True):
          cmd2_str = data + ' ' * (63 - len(data))    ## 64: DATA FULL error
          cmd2_bytes = bytes(cmd2_str, "utf-8")  #"latin-1"
          self._hid.write( cmd2_bytes )          
        else:
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
