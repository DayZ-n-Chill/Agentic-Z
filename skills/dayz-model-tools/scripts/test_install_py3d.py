"""Regression tests for install_py3d.py, the py3d fork wheel installer."""

from importlib import metadata
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


INSTALLER_PATH = Path(__file__).resolve().parent / "install_py3d.py"


def _load_installer():
    spec = importlib.util.spec_from_file_location("model_tools_install_py3d", INSTALLER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_distribution(root, *, is_dayz_fork):
    package = root / "py3d" / "__init__.py"
    package.parent.mkdir(parents=True)
    package.write_text(
        f"IS_DAYZ_FORK = {is_dayz_fork!r}\n__version__ = '9.9.0'\n",
        encoding="utf-8",
    )
    dist_info = root / "py3d-9.9.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: py3d\nVersion: 9.9.0\n",
        encoding="utf-8",
    )
    (dist_info / "RECORD").write_text(
        "py3d/__init__.py,,\n"
        "py3d-9.9.0.dist-info/METADATA,,\n"
        "py3d-9.9.0.dist-info/RECORD,,\n",
        encoding="utf-8",
    )
    dist = next(metadata.distributions(name="py3d", path=[str(root)]))
    return dist, package


def test_foreign_distribution_cannot_borrow_shadow_checkout_flag(tmp_path):
    """Fails if a flag from another checkout authorizes uninstalling py3d."""
    installer = _load_installer()
    foreign_root = tmp_path / "foreign-site"
    dist, foreign_module = _write_distribution(
        foreign_root,
        is_dayz_fork=False,
    )
    shadow_module = tmp_path / "shadow-checkout" / "py3d" / "__init__.py"
    shadow_module.parent.mkdir(parents=True)
    shadow_module.write_text(
        "IS_DAYZ_FORK = True\n__version__ = '1.5.0'\n",
        encoding="utf-8",
    )
    imported = SimpleNamespace(
        __file__=str(shadow_module),
        IS_DAYZ_FORK=True,
    )
    before = {
        path.relative_to(foreign_root): path.read_bytes()
        for path in foreign_root.rglob("*")
        if path.is_file()
    }

    with pytest.raises(installer.InstallerError, match="RECORD"):
        installer.authorize_legacy_uninstall(dist, imported)

    after = {
        path.relative_to(foreign_root): path.read_bytes()
        for path in foreign_root.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert foreign_module.is_file()


def test_owned_foreign_distribution_cannot_use_planted_memory_flag(tmp_path):
    """Fails if a flag planted in memory stands in for the value on disk."""
    installer = _load_installer()
    dist, module_path = _write_distribution(tmp_path, is_dayz_fork=False)
    imported = SimpleNamespace(
        __file__=str(module_path),
        IS_DAYZ_FORK=True,
    )

    with pytest.raises(installer.InstallerError, match="not the DayZ fork"):
        installer.authorize_legacy_uninstall(dist, imported)


def test_owned_dayz_fork_is_the_only_uninstallable_distribution(tmp_path):
    """Fails if the ownership check blocks the legitimate legacy migration."""
    installer = _load_installer()
    dist, module_path = _write_distribution(tmp_path, is_dayz_fork=True)
    imported = SimpleNamespace(
        __file__=str(module_path),
        IS_DAYZ_FORK=True,
    )

    installer.authorize_legacy_uninstall(dist, imported)


def test_pip_commands_are_bound_to_the_gate_interpreter():
    """Fails if install or uninstall go back to a bare pip found on PATH."""
    installer = _load_installer()

    assert installer.pip_command("install", "wheel.whl") == [
        sys.executable,
        "-m",
        "pip",
        "install",
        "wheel.whl",
    ]
    assert installer.pip_command("uninstall", "-y", "py3d")[:3] == [
        sys.executable,
        "-m",
        "pip",
    ]


def test_missing_new_wheel_is_reported_before_legacy_collision():
    """Fails if the message claims a DayZ wheel exists when none was found."""
    installer = _load_installer()

    with pytest.raises(installer.InstallerError) as caught:
        installer.resolve_wheel([], [Path("py3d-1.4.0-py3-none-any.whl")])

    message = str(caught.value)
    assert "no py3d_dayz" in message
    assert "alongside the DayZ wheel" not in message


def test_valid_new_wheel_still_aborts_when_legacy_is_present():
    """Fails if fixing the order lets the legacy collision through."""
    installer = _load_installer()
    new = Path("py3d_dayz-1.5.0-py3-none-any.whl")
    legacy = Path("py3d-1.4.0-py3-none-any.whl")

    with pytest.raises(installer.InstallerError, match="legacy"):
        installer.resolve_wheel([new], [legacy])


def test_fallback_is_the_repo_py3d_dist_folder():
    """Fails if the fallback points anywhere but <repo>/scripts/tools/py3d/dist."""
    installer = _load_installer()
    repo = Path(__file__).resolve().parents[3]

    assert installer.FALLBACK_DIST == repo / "scripts" / "tools" / "py3d" / "dist"


def test_wheel_in_the_fallback_folder_is_selected(tmp_path, monkeypatch):
    """Fails if a wheel in the fallback folder is not found when wheels/ has none."""
    installer = _load_installer()
    wheel = tmp_path / "py3d_dayz-9.9.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    monkeypatch.setattr(installer, "PRIMARY_WHEELS", tmp_path / "no-wheels-here")
    monkeypatch.setattr(installer, "FALLBACK_DIST", tmp_path)

    assert installer._select_wheel() == wheel


def test_wheel_next_to_the_skill_wins_over_the_fallback(tmp_path, monkeypatch):
    """Fails if the fallback folder is read while the skill's wheels/ holds a wheel."""
    installer = _load_installer()
    primary = tmp_path / "wheels"
    fallback = tmp_path / "dist"
    primary.mkdir()
    fallback.mkdir()
    wheel = primary / "py3d_dayz-9.9.0-py3-none-any.whl"
    wheel.write_bytes(b"")
    (fallback / "py3d_dayz-9.8.0-py3-none-any.whl").write_bytes(b"")
    monkeypatch.setattr(installer, "PRIMARY_WHEELS", primary)
    monkeypatch.setattr(installer, "FALLBACK_DIST", fallback)

    assert installer._select_wheel() == wheel


def test_legacy_wheel_in_the_fallback_folder_still_aborts(tmp_path, monkeypatch):
    """Fails if a legacy py3d-*.whl beside the fallback wheel is ignored."""
    installer = _load_installer()
    (tmp_path / "py3d_dayz-9.9.0-py3-none-any.whl").write_bytes(b"")
    (tmp_path / "py3d-1.4.0-py3-none-any.whl").write_bytes(b"")
    monkeypatch.setattr(installer, "PRIMARY_WHEELS", tmp_path / "no-wheels-here")
    monkeypatch.setattr(installer, "FALLBACK_DIST", tmp_path)

    with pytest.raises(installer.InstallerError, match="legacy"):
        installer._select_wheel()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
