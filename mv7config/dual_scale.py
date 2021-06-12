import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GObject, Gtk


class DualScale(Gtk.Box):
    """
    A scale widget used to set two related values.

    This widget has two states:

    * In the linked state, only one scale is shown. In the first half of the
      scale, the first value varies from its minimum to its maximum while the
      second value stays fixed at its maximum. In the second half, the first
      value is fixed at its maximum while the second varies from its maximum to
      its minimum.

    * In the unlinked state, two scales are shown, allowing to set each value
      independently.

    A toggle button allows the user to switch between the two states.
    """
    __gtype_name__ = "DualScale"

    def __init__(
        self,
        first_range, second_range,
        labels, increments,
        *args, **kwargs
    ):
        """
        Create a new dual scale widget.

        :param first_range: Minimum and maximum of the first value.
        :param second_range: Minimum and maximum of the second value.
        :param labels: Labels to show at each end of the scales.
        :param increments: Discrete increments value.
        """
        super().__init__(*args, **kwargs, spacing=6)

        self._first_range = first_range
        self._first_value = first_range[1]
        self._second_range = second_range
        self._second_value = second_range[1]

        self._max_gap = max(
            first_range[1] - first_range[0],
            second_range[1] - second_range[0],
        )

        self._unlinked_scales = Gtk.Box(hexpand=True, spacing=0)

        self._first_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
        )
        self._first_adj = self._first_scale.get_adjustment()
        self._first_scale.set_range(*first_range)
        self._first_scale.set_increments(*increments)
        self._first_scale.add_mark(
            first_range[0],
            Gtk.PositionType.BOTTOM,
            labels[0],
        )
        self._unlinked_scales.add(self._first_scale)

        self._second_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
            inverted=True,
        )
        self._second_adj = self._second_scale.get_adjustment()
        self._second_scale.set_range(*second_range)
        self._second_scale.set_increments(*increments)
        self._second_scale.add_mark(
            second_range[0],
            Gtk.PositionType.BOTTOM,
            labels[1],
        )
        self._unlinked_scales.add(self._second_scale)
        self.pack_start(
            self._unlinked_scales,
            expand=True,
            fill=True,
            padding=0
        )
        self._unlinked_scales.set_no_show_all(True)

        self._linked_scale = Gtk.Scale(
            hexpand=True,
            draw_value=False,
            round_digits=0,
            digits=0,
            has_origin=False,
        )
        self._linked_adj = self._linked_scale.get_adjustment()
        self._linked_scale.set_range(0, self._max_gap * 2)
        self._linked_scale.set_increments(*increments)
        self._linked_scale.add_mark(
            0,
            Gtk.PositionType.BOTTOM,
            labels[0],
        )
        self._linked_scale.add_mark(
            self._max_gap,
            Gtk.PositionType.BOTTOM,
            "",
        )
        self._linked_scale.add_mark(
            self._max_gap * 2,
            Gtk.PositionType.BOTTOM,
            labels[1],
        )
        self.pack_start(
            self._linked_scale,
            expand=True,
            fill=True,
            padding=0
        )
        self._linked_scale.set_no_show_all(True)

        self._link = Gtk.ToggleButton(
            image=Gtk.Image(icon_name="insert-link-symbolic"),
            valign="center",
            relief="none",
            active=True,
        )
        self.pack_end(self._link, expand=False, fill=False, padding=0)

        self._link.connect("toggled", self._on_link_toggled)
        self._on_link_toggled(self._link)

        self._first_adj.connect("notify::value", self._on_scale_changed)
        self._second_adj.connect("notify::value", self._on_scale_changed)
        self._linked_adj.connect("notify::value", self._on_scale_changed)

    def _on_scale_changed(self, target, _=None):
        """
        When one of the scale widgets is changed by the user, update
        the internal values accordingly.
        """
        if self._link.props.active:
            linked_value = int(self._linked_adj.props.value)

            if linked_value == self._max_gap:
                next_first_value = self._first_range[1]
                next_second_value = self._second_range[1]
            elif linked_value < self._max_gap:
                next_first_value = self._first_range[0] + round(
                    (self._first_range[1] - self._first_range[0])
                    * (linked_value / self._max_gap)
                )
                next_second_value = self._second_range[1]
            else:
                next_first_value = self._first_range[1]
                next_second_value = self._second_range[0] + round(
                    (self._second_range[1] - self._second_range[0])
                    * ((self._max_gap * 2 - linked_value) / self._max_gap)
                )
        else:
            if target == self._first_adj:
                next_first_value = int(target.props.value)
                next_second_value = self._second_value
            elif target == self._second_adj:
                next_first_value = self._first_value
                next_second_value = int(target.props.value)
            else:
                return

        if next_first_value != self._first_value:
            self._first_value = next_first_value
            self.notify("first_value")

        if next_second_value != self._second_value:
            self._second_value = next_second_value
            self.notify("second_value")

    def _update_scales(self):
        """
        When one of the values is changed, move the scales accordingly.
        """
        if self._link.props.active:
            if self._first_value == self._first_range[1]:
                linked_value = round(self._max_gap * (1 +
                    (self._second_range[1] - self._second_value)
                    / (self._second_range[1] - self._second_range[0])
                ))
            else:
                linked_value = round(self._max_gap * (
                    self._first_value
                    / (self._first_range[1] - self._first_range[0])
                ))

            if int(self._linked_adj.props.value) != linked_value:
                self._linked_adj.props.value = linked_value
        else:
            if int(self._first_adj.props.value) != self._first_value:
                self._first_adj.props.value = self._first_value

            if int(self._second_adj.props.value) != self._second_value:
                self._second_adj.props.value = self._second_value

    def _on_link_toggled(self, toggle):
        """Switch between the linked and unlinked state."""
        if toggle.props.active:
            self._linked_scale.show()
            self._unlinked_scales.hide()
        else:
            self._unlinked_scales.show()
            self._first_scale.show()
            self._second_scale.show()
            self._linked_scale.hide()

        self._update_scales()

    @GObject.Property(type=int, default=0)
    def first_value(self):
        return self._first_value

    @first_value.setter
    def first_value(self, value):
        self._first_value = value
        self._update_scales()

    @GObject.Property(type=int, default=0)
    def second_value(self):
        return self._second_value

    @second_value.setter
    def second_value(self, value):
        self._second_value = value
        self._update_scales()
