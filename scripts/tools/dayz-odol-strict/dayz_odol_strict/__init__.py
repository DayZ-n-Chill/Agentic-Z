"""Strict read-only ODOL adapter."""

__all__ = ["OdolStrictError", "diff_anatomy", "inspect_odol"]


def __getattr__(name):
    if name == "OdolStrictError":
        from .errors import OdolStrictError
        return OdolStrictError
    if name == "diff_anatomy":
        from .diff import diff_anatomy
        return diff_anatomy
    if name == "inspect_odol":
        from .inspect import inspect_odol
        return inspect_odol
    raise AttributeError(name)
