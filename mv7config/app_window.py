import os
import gi
from gi.repository import Gtk
from gi.repository.GObject import BindingFlags
from .microphone import Microphone
from .microphone_control_page import MicrophoneControlPage


dirname = os.path.dirname(__file__)


@Gtk.Template(filename=os.path.join(dirname, "app_window.ui"))
class AppWindow(Gtk.ApplicationWindow):
    """
    Application entry point.

    Provides feedback while the connection to the microphone is being
    established, or if there is no microphone available.
    """
    __gtype_name__ = "AppWindow"

    header_stack = Gtk.Template.Child()
    header_basic = Gtk.Template.Child()
    header_mic_control = Gtk.Template.Child()

    page_stack = Gtk.Template.Child()
    page_no_mic = Gtk.Template.Child()
    page_mic_init = Gtk.Template.Child()
    page_mic_control = Gtk.Template.Child()

    lock_toggle = Gtk.Template.Child()
    identify_button = Gtk.Template.Child()
    retry_button = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(600, 400)
        self.connect("destroy", lambda _: self.close_microphone())

        self.identify_button.connect("clicked", lambda _: self.microphone.identify())
        self.retry_button.connect("clicked", lambda _: self.discover_mics())

        self.microphone = None
        self.show_all()
        self.discover_mics()

    def discover_mics(self):
        """Scan available mics and open the first one available."""
        mics = Microphone.enumerate()

        if not mics:
            self.show_no_mic()
        else:
            self.open_microphone(next(iter(mics)))

    def show_no_mic(self):
        """Show a status page indicating that no mic were found."""
        self.header_stack.set_visible_child(self.header_basic)
        self.page_stack.set_visible_child(self.page_no_mic)

    def open_microphone(self, microphone_path):
        """Establish a connection to a mic and show a waiting screen."""
        if self.microphone is not None:
            self.microphone.close()

        self.header_stack.set_visible_child(self.header_basic)
        self.page_stack.set_visible_child(self.page_mic_init)

        self.microphone = Microphone(microphone_path)
        self.microphone.connect("initialized", lambda _: self.show_control_page())
        self.microphone.initialize()

    def close_microphone(self):
        """Close the open microphone if applicable."""
        if self.microphone is not None:
            self.microphone.close()
            self.microphone = None

    def show_control_page(self):
        """Show the mic controls once the connection has been established."""
        self.page_mic_control.props.microphone = self.microphone
        self.header_mic_control.set_title(self.microphone.props.serial_number)

        self.microphone.bind_property(
            "lock", self.lock_toggle, "active",
            BindingFlags.BIDIRECTIONAL | BindingFlags.SYNC_CREATE,
        )

        for group in self.page_mic_control.get_children():
            self.microphone.bind_property(
                "lock", group, "sensitive",
                BindingFlags.INVERT_BOOLEAN | BindingFlags.SYNC_CREATE,
            )

        self.header_stack.set_visible_child(self.header_mic_control)
        self.page_stack.set_visible_child(self.page_mic_control)
