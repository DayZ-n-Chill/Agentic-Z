#!/usr/bin/env python3

from setuptools import setup

# Kept only for legacy `python setup.py` invocations. pyproject.toml is the
# single source of truth for packaging metadata; the values below MUST stay
# in sync with it (two authorities for the same metadata is how a release
# ends up mislabelled).
setup(
    name = "py3d-dayz",
    packages = ["py3d"],
    version = "1.10.1",
    install_requires = [],
    author = "Guillermo",
    author_email = "willy92wins@gmail.com",
    description = "DayZ/Arma MLOD .p3d reader and writer - a maintained fork of KoffeinFlummi/py3d with anti-corruption guards and a DayZ model validator.",
    license = "MIT",
    keywords = "arma dayz 3d p3d mlod",
    url = "https://github.com/willy92wins/py3d-dayz",
    classifiers = []
)
