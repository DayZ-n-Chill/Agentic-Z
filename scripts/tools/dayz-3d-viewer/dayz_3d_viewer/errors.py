"""Typed failures for the DayZ 3D viewer tool."""


class ViewerError(Exception):
    """User-facing conversion or parse failure."""


class MissingDependencyError(ViewerError):
    """A declared optional extra is not installed."""
