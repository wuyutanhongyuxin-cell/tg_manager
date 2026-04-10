from types import SimpleNamespace

from src.bot_interface.handlers.admin_handler import AdminHandler


def _make_handler() -> AdminHandler:
    config = SimpleNamespace(telegram=SimpleNamespace(admin_user_id="1"))
    return AdminHandler(config=config, event_bus=None)


def test_parse_mute_duration_with_explicit_user_id() -> None:
    handler = _make_handler()

    assert handler._parse_mute_duration("/mute 123 10", replied=False) == 10


def test_parse_mute_duration_when_replying_to_a_message() -> None:
    handler = _make_handler()

    assert handler._parse_mute_duration("/mute 10", replied=True) == 10


def test_parse_mute_duration_falls_back_to_default() -> None:
    handler = _make_handler()

    assert handler._parse_mute_duration("/mute", replied=True) == 60
    assert handler._parse_mute_duration("/mute 123 nope", replied=False) == 60
    assert handler._parse_mute_duration("/mute 0", replied=True) == 1
