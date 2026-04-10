from types import SimpleNamespace

from src.plugins.plugin_base import PluginBase


class DummyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "message.sender"

    @property
    def description(self) -> str:
        return "dummy"

    async def setup(self) -> None:
        return None

    async def teardown(self) -> None:
        return None


def test_plugin_config_merges_namespace_and_exact_keys() -> None:
    config = SimpleNamespace(
        plugin_config={
            "message": {"enabled": True, "timeout": 10},
            "sender": {"timeout": 20, "format": "plain"},
            "message_sender": {"format": "markdown", "batch": 2},
            "message.sender": {"batch": 5},
        }
    )

    plugin = DummyPlugin(
        client=None,
        config=config,
        event_bus=None,
        db=None,
    )

    assert plugin.get_plugin_config() == {
        "enabled": True,
        "timeout": 20,
        "format": "markdown",
        "batch": 5,
    }
