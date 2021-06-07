import hid

class Device:
    vendor_id = 0x14ED
    product_id = 0x1012

    def __init__(self):
        device = hid.device()
        device.open(Device.vendor_id, Device.product_id)
        self.device = device

    def string_to_command(string):
        long_command = [ord(char) for char in string]
        command = long_command[:64]
        return command + [0] * (64 - len(command))


    def reply_to_string(reply):
        try:
            end = reply.index(0)
        except ValueError:
            end = len(reply)

        return "".join(chr(code) for code in reply[:end])

    def send_command(self, command):
        self.device.write(Device.string_to_command(command))
        reply = Device.reply_to_string(self.device.read(max_length=64))

        while True:
            next_reply = self.device.read(max_length=64, timeout_ms=100)

            if not next_reply:
                break

            reply += Device.reply_to_string(next_reply)

        return reply
