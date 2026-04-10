"""Bot interface package exports."""

from __future__ import annotations

__all__ = ["CommandRouter", "CallbackRouter", "MenuBuilder"]


def __getattr__(name: str):
    if name == "CommandRouter":
        from .command_router import CommandRouter

        return CommandRouter
    if name == "CallbackRouter":
        from .callback_router import CallbackRouter

        return CallbackRouter
    if name == "MenuBuilder":
        from .menu_builder import MenuBuilder

        return MenuBuilder
    raise AttributeError(name)
