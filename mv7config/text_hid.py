import hid


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
