"""Tests for deploy.py: idempotent copy, ownership gate, bundle checks, .bisign detection."""
from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_deploy_pbo_under_test", HERE / "deploy.py")
deploy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy)
h = deploy.h


# --- copy_if_changed -----------------------------------------------------------

def test_copy_if_changed_copies_new_file(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out" / "Addons"
    assert deploy.copy_if_changed(src, dst_dir) is True
    assert (dst_dir / "a.pbo").read_bytes() == b"payload"


def test_copy_if_changed_skips_identical_second_run(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    assert deploy.copy_if_changed(src, dst_dir) is False


def test_copy_if_changed_recopies_when_size_differs(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    src.write_bytes(b"bigger payload")
    assert deploy.copy_if_changed(src, dst_dir) is True
    assert (dst_dir / "a.pbo").read_bytes() == b"bigger payload"


def test_copy_if_changed_recopies_when_mtime_differs(tmp_path):
    src = tmp_path / "a.pbo"
    src.write_bytes(b"payload")
    dst_dir = tmp_path / "out"
    deploy.copy_if_changed(src, dst_dir)
    later = time.time() + 60
    os.utime(src, (later, later))
    assert deploy.copy_if_changed(src, dst_dir) is True


# --- unsigned_pbos -------------------------------------------------------------

def test_unsigned_pbos_flags_only_missing_signatures():
    pbos = [Path("a.pbo"), Path("b.pbo"), Path("ab.pbo")]
    bisigns = [Path("a.pbo.mykey.bisign")]
    assert deploy.unsigned_pbos(pbos, bisigns) == [Path("b.pbo"), Path("ab.pbo")]


def test_unsigned_pbos_empty_when_all_signed():
    assert deploy.unsigned_pbos([Path("a.pbo")], [Path("a.pbo.key.bisign")]) == []


# --- verify_bundle -------------------------------------------------------------

def test_verify_bundle_requires_pbo(tmp_path):
    (tmp_path / "workspace" / "Bundle" / "Addons").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        deploy.verify_bundle("Bundle", tmp_path)
    assert "No .pbo" in str(exc.value.code)


def test_verify_bundle_requires_addons(tmp_path):
    (tmp_path / "workspace" / "Bundle").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        deploy.verify_bundle("Bundle", tmp_path)
    assert "Addons" in str(exc.value.code)


def test_verify_bundle_accepts_payload_without_config(tmp_path):
    addons = tmp_path / "workspace" / "Bundle" / "Addons"
    addons.mkdir(parents=True)
    (addons / "x.pbo").write_bytes(b"")
    assert deploy.verify_bundle("Bundle", tmp_path) == tmp_path / "workspace" / "Bundle"


# --- gate_on_marker (shared with build and clean) ------------------------------

def test_gate_on_marker_refuses_unowned_dir(tmp_path):
    root = tmp_path / "@Bundle"
    root.mkdir()
    (root / h.SCAFFOLD_MARKER).write_text("SomeoneElse\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        h.gate_on_marker("Bundle", root)


def test_gate_on_marker_accepts_owned_dir(tmp_path):
    root = tmp_path / "@Bundle"
    root.mkdir()
    h.write_marker(root, "Bundle")
    h.gate_on_marker("Bundle", root)
