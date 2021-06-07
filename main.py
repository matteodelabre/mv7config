from mv7config.device import Device
import readline

while True:
    print("> ", end="")
    command = input()
    dev = Device()
    print(dev.send_command(command))
