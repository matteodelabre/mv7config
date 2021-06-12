import time
from gi.repository import GLib


def bind_toggles(source, source_prop, targets):
    """
    Make a two-way binding between a set of toggles and an enumeration.

    :param source: source object holding the enumeration value
    :param source_prop: name of the property in :param:`source` that
        holds the enumeration value
    :param targets: mapping from enumeration values to the set of toggles
    """
    values = {target: value for value, target in targets.items()}

    def on_source_changed():
        key = source.get_property(source_prop)

        if key in targets:
            for target in targets.values():
                if not target.props.sensitive:
                    target.set_sensitive(True)

            if not targets[key].props.active:
                targets[key].set_active(True)
        else:
            for target in targets.values():
                if target.props.sensitive:
                    target.set_sensitive(False)

    def on_target_changed(action):
        if action.props.active and action in values:
            next_value = values[action]

            if source.get_property(source_prop) != next_value:
                source.set_property(source_prop, next_value)

    for target in targets.values():
        target.connect("toggled", on_target_changed)

    on_source_changed()
    source.connect("notify::" + source_prop, lambda x, y: on_source_changed())


def bind_throttled(source, source_prop, target, target_prop, timeout=1):
    """
    Make a two-way binding between two properties such that updates from
    the source are ignored while the target is being modified.

    :param source: source object to bind
    :param source_prop: name of the property of the source object to bind
    :param target: target object to bind
    :param target_prop: name of the property of the target object to bind
    :param timeout: number of seconds to wait after each change to the
        target property before accepting changes from the source property
    """
    last_target_change = 0
    active_timeout = None

    def on_source_changed():
        nonlocal active_timeout
        since_last_change = time.time() - last_target_change

        if active_timeout is not None:
            GLib.source_remove(active_timeout)
            active_timeout = None

        if since_last_change < timeout:
            active_timeout = GLib.timeout_add(
                round((timeout - since_last_change) * 1000),
                on_source_changed,
            )
        else:
            next_value = source.get_property(source_prop)

            if target.get_property(target_prop) != next_value:
                target.set_property(target_prop, next_value)

    def on_target_changed():
        nonlocal last_target_change
        next_value = target.get_property(target_prop)

        if source.get_property(source_prop) != next_value:
            last_target_change = time.time()
            source.set_property(source_prop, next_value)

    target.set_property(
        target_prop,
        source.get_property(source_prop),
    )

    source.connect(
        "notify::" + source_prop,
        lambda x, y: on_source_changed()
    )

    target.connect(
        "notify::" + target_prop,
        lambda x, y: on_target_changed()
    )
