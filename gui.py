#!/usr/bin/env python3
import signal
import sys
import logging
from mv7config.application import Application
from gi.repository import GLib

logging.basicConfig(
    format="[%(levelname)8s] %(name)s: %(message)s",
    level=logging.DEBUG,
)

app = Application()
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.quit)
app.run(sys.argv)
