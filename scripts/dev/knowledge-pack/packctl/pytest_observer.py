"""pytest plugin the publish gate loads into every test-folder run.

``packctl gate`` and ``packctl test-folders`` run each skills/<skill>/tests and
tools/<tool>/tests folder as ``pytest -p packctl.pytest_observer
--packctl-observer=<file> <folder>``. Through pytest's own hooks this plugin
writes what the gate judges the run by, in a form that no output option,
colour setting or printing plugin changes: every test item collected, the
items left to run, those that ran to the end, how many were deselected, the
failed reports, and the test modules that yielded items or skipped themselves
at import. pytest is imported here only; the rest of packctl stays stdlib-only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--packctl-observer",
        dest="packctl_observer",
        default=None,
        help="File the packctl gate reads this run's outcome from.",
    )


def pytest_configure(config: pytest.Config) -> None:
    output = config.getoption("packctl_observer")
    if output:
        config.pluginmanager.register(
            _Observer(Path(output), config.rootpath),
            "packctl-observer",
        )


class _Observer:
    def __init__(self, output: Path, rootpath: Path) -> None:
        self.output = output
        self.rootpath = rootpath
        self.collected: set[str] = set()
        self.modules: set[str] = set()
        self.skipped_modules: set[str] = set()
        self.deselected = 0
        self.items: list[str] | None = None
        self.finished: set[str] = set()
        self.failed = 0

    def pytest_itemcollected(self, item: pytest.Item) -> None:
        self.collected.add(item.nodeid)
        self.modules.add(str(item.path))

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.skipped:
            self.skipped_modules.add(
                str(self.rootpath / report.nodeid.split("::")[0])
            )
        elif report.failed:
            self.failed += 1

    def pytest_deselected(self, items: list[pytest.Item]) -> None:
        self.deselected += len(items)

    # tryfirst: the items are recorded before any other hook can end the
    # session here (pytest.exit in a conftest), which leaves them unrun.
    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.items = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.failed:
            self.failed += 1

    def pytest_runtest_logfinish(self, nodeid: str) -> None:
        self.finished.add(nodeid)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        record = {
            "exitstatus": int(session.exitstatus),
            "collected": sorted(self.collected),
            "items": self.items,
            "finished": sorted(self.finished),
            "deselected": self.deselected,
            "failed": self.failed,
            "modules": sorted(self.modules),
            "skipped_modules": sorted(self.skipped_modules),
        }
        self.output.write_text(
            json.dumps(record, indent=2) + "\n",
            encoding="utf-8",
        )
