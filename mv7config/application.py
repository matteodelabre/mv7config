import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Handy", "1")
from gi.repository import Gtk, Handy
from .app_window import AppWindow


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="re.delab.mv7config",
            **kwargs,
        )
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = AppWindow(application=self, title="mv7config")

        self.window.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)
        self.window.destroy()
