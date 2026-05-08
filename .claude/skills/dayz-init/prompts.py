"""Input prompt utilities for /dayz-init.

Three primitives the wizard uses: free-text, yes/no, select-from-list.
All print to stdout, read via builtins.input, and respect a default value.
"""
from __future__ import annotations

from typing import Sequence


def ask_text(question: str, default: str | None = None) -> str:
    """Prompt for free-text input. Empty input returns default if provided."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"{question}{suffix} ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("(value required)")


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for yes/no. Default shown via [Y/n] or [y/N]."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {hint} ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("(answer y or n)")


def ask_select(
    question: str,
    options: Sequence[str],
    default: str | None = None,
) -> str:
    """Prompt for one-of-many. User types the 1-indexed number or accepts default."""
    if not options:
        raise ValueError("ask_select requires at least one option")
    print(question)
    for i, option in enumerate(options, start=1):
        marker = " (default)" if option == default else ""
        print(f"  {i}. {option}{marker}")
    while True:
        answer = input("> ").strip()
        if not answer and default is not None:
            return default
        if answer.isdigit():
            idx = int(answer)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print(f"(enter 1-{len(options)})")
