"""Intent prompts for /dayz-init.

Asks the user every "decision" needed by the wizard. Returns an Intent
dataclass that plan.py turns into a concrete sequence of actions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from prompts import ask_text, ask_yes_no, ask_select
from detect import (
    cwd,
    is_mod_dir,
    mod_name_from_config_cpp,
    mod_name_from_cwd,
)


KNOWN_MAPS = ["chernarus", "livonia", "sakhal", "namalsk"]


@dataclass
class Intent:
    is_new: bool             # True = new mod, False = import existing
    mod_name: str
    project_path: Path
    add_server: bool
    server_map: str | None   # None when add_server is False
    build_pbo: bool
    launch_diag: bool
    rag_choice: str          # "skip" | "paste" | "pull"


def gather_intent() -> Intent:
    """Run the intent prompt phase from start to finish."""
    print("\n── Intent ──")

    intent_choice = ask_select(
        "What are you doing?",
        ["starting a new mod", "importing an existing repo"],
        default="starting a new mod",
    )
    is_new = intent_choice == "starting a new mod"

    starting_dir = cwd()
    if is_new:
        default_name = mod_name_from_cwd(starting_dir)
    else:
        default_name = (
            mod_name_from_config_cpp(starting_dir)
            or mod_name_from_cwd(starting_dir)
        )

    mod_name = ask_text("Mod name?", default=default_name)
    project_path = Path(
        ask_text("Project path?", default=str(starting_dir))
    ).resolve()

    add_server = ask_yes_no("Set up a test server?", default=True)
    server_map: str | None = None
    if add_server:
        server_map = ask_select(
            "Map?",
            KNOWN_MAPS,
            default="chernarus",
        )

    build_pbo = ask_yes_no("Build PBO now?", default=False)
    launch_diag = ask_yes_no("Launch DayZ now?", default=False)
    if launch_diag and not build_pbo:
        # Launch implies build; auto-include
        print("(launch implies build, including PBO build in plan)")
        build_pbo = True

    rag_choice = "skip"
    if not os.environ.get("VOYAGE_API_KEY"):
        rag_choice = ask_select(
            "RAG setup?",
            ["skip", "paste Voyage key", "pull prebuilt index"],
            default="skip",
        )
        # Normalize to short codes for plan.py
        rag_choice = {
            "skip": "skip",
            "paste Voyage key": "paste",
            "pull prebuilt index": "pull",
        }[rag_choice]

    return Intent(
        is_new=is_new,
        mod_name=mod_name,
        project_path=project_path,
        add_server=add_server,
        server_map=server_map,
        build_pbo=build_pbo,
        launch_diag=launch_diag,
        rag_choice=rag_choice,
    )
