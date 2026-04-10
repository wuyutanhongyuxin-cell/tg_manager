from src.bot_interface.command_router import CommandRouter


def test_matches_plain_command() -> None:
    assert CommandRouter.matches_command("/start", "start", "ThisBot")
    assert CommandRouter.matches_command("/start now", "start", "ThisBot")


def test_matches_command_for_current_bot_only() -> None:
    assert CommandRouter.matches_command("/start@ThisBot", "start", "ThisBot")
    assert CommandRouter.matches_command("/start@thisbot", "start", "ThisBot")
    assert not CommandRouter.matches_command("/start@OtherBot", "start", "ThisBot")


def test_rejects_similar_but_different_command_names() -> None:
    assert not CommandRouter.matches_command("/start123", "start", "ThisBot")
    assert not CommandRouter.matches_command("/starter", "start", "ThisBot")
