from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .audit import AuditInputError, AuditResult, PreviewCloud
from .reporting import (
    require_matching_reports,
    verify_report_snapshots,
    write_report_tree,
)


_SAMPLE_LIMIT = 5000
_SAMPLE_SEED = 1701


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._")
    return normalized or "node"


def _sample(points: tuple[tuple[float, float, float], ...], seed: int) -> np.ndarray:
    cloud = np.asarray(points, dtype=float)
    if len(cloud) <= _SAMPLE_LIMIT:
        return cloud
    rng = np.random.default_rng(seed)
    indexes = np.sort(rng.choice(len(cloud), size=_SAMPLE_LIMIT, replace=False))
    return cloud[indexes]


def _plot_cloud(
    axis,
    cloud: np.ndarray,
    first: int,
    second: int,
    label: str,
    color: str,
) -> None:
    if len(cloud):
        axis.scatter(
            cloud[:, first],
            cloud[:, second],
            s=2.0,
            alpha=0.55,
            label=label,
            color=color,
            rasterized=True,
        )


def _write_preview(path: Path, title: str, cloud: PreviewCloud, ordinal: int) -> None:
    source = _sample(cloud.source, _SAMPLE_SEED + ordinal * 3)
    raw = _sample(cloud.raw, _SAMPLE_SEED + ordinal * 3 + 1)
    resolved = _sample(cloud.resolved, _SAMPLE_SEED + ordinal * 3 + 2)
    figure, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    views = ((0, 1, "top (X/Y)"), (0, 2, "front (X/Z)"), (2, 1, "side (Z/Y)"))
    for axis, (first, second, view_title) in zip(axes, views):
        _plot_cloud(axis, source, first, second, "source", "#1b9e77")
        _plot_cloud(axis, raw, first, second, "raw", "#d95f02")
        _plot_cloud(axis, resolved, first, second, "resolved", "#7570b3")
        if not len(source):
            axis.text(
                0.5,
                0.5,
                "source unavailable",
                transform=axis.transAxes,
                ha="center",
                va="center",
                color="#b2182b",
            )
        axis.set_title(view_title)
        axis.set_aspect("equal", adjustable="datalim")
        axis.grid(True, linewidth=0.25, alpha=0.4)
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        figure.legend(handles, labels, loc="lower center", ncol=3)
    figure.suptitle(title)
    try:
        figure.savefig(path, dpi=140, format="png")
    finally:
        plt.close(figure)


def _render_previews(result: AuditResult, root: Path) -> tuple[str, ...]:
    names = []
    ordinal = 0
    for node in result.nodes:
        for cloud in node.previews:
            name = (
                f"{ordinal:04d}-{_slug(node.node.piece)}-"
                f"host-{node.node.host_lod:g}-internal-{cloud.internal_lod:g}.png"
            )
            _write_preview(
                root / name,
                (
                    f"{node.node.piece} | host LOD {node.node.host_lod:g} | "
                    f"internal LOD {cloud.internal_lod:g} | "
                    f"alignment {result.alignment_status}"
                ),
                cloud,
                ordinal,
            )
            names.append(name)
            ordinal += 1
    if not names:
        raise AuditInputError("audit produced no previewable visual LODs")
    return tuple(names)


def _directory_identity(path: Path) -> tuple[int, int]:
    stat_result = os.stat(path, follow_symlinks=False)
    return stat_result.st_dev, stat_result.st_ino


def _cleanup_owned_directory(path: Path, owned_identity: tuple[int, int]) -> None:
    if not os.path.lexists(path):
        return
    quarantine = path.with_name(
        f".{path.name}.vehicle-proxy-cleanup-{uuid.uuid4().hex}"
    )
    try:
        os.rename(path, quarantine)
    except OSError:
        return
    try:
        quarantined_identity = _directory_identity(quarantine)
    except OSError:
        quarantined_identity = None
    if quarantined_identity == owned_identity:
        try:
            shutil.rmtree(quarantine)
        except OSError:
            pass
        return
    if not os.path.lexists(path):
        try:
            os.rename(quarantine, path)
        except OSError:
            pass


def _publish_preview_only(result: AuditResult, out: Path) -> tuple[Path, ...]:
    report_snapshots = require_matching_reports(result, out)
    destination = out / "preview"
    if os.path.lexists(destination):
        raise AuditInputError(f"preview directory already exists: {destination}")
    try:
        transaction = Path(
            tempfile.mkdtemp(prefix=".preview.vehicle-proxy-", dir=out)
        )
    except OSError as error:
        raise AuditInputError(f"cannot create preview transaction: {error}") from error
    transaction_identity = _directory_identity(transaction)
    committed = False
    try:
        names = _render_previews(result, transaction)
        verify_report_snapshots(report_snapshots)
        if os.path.lexists(destination):
            raise AuditInputError(f"preview directory already exists: {destination}")
        try:
            os.rename(transaction, destination)
        except FileExistsError as error:
            raise AuditInputError(f"preview directory already exists: {destination}") from error
        except OSError as error:
            raise AuditInputError(f"cannot publish preview directory {destination}: {error}") from error
        try:
            verify_report_snapshots(report_snapshots)
        except AuditInputError:
            _cleanup_owned_directory(destination, transaction_identity)
            raise
        committed = True
        return tuple(destination / name for name in names)
    finally:
        if not committed:
            _cleanup_owned_directory(transaction, transaction_identity)


def write_previews(result: AuditResult, out: Path) -> tuple[Path, ...]:
    out = Path(out)
    if os.path.lexists(out):
        return _publish_preview_only(result, out)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        transaction = Path(
            tempfile.mkdtemp(
                prefix=f".{out.name}.vehicle-proxy-preview-bundle-",
                dir=out.parent,
            )
        )
    except OSError as error:
        raise AuditInputError(f"cannot create preview bundle: {error}") from error
    committed = False
    try:
        write_report_tree(result, transaction)
        preview_root = transaction / "preview"
        preview_root.mkdir()
        names = _render_previews(result, preview_root)
        if os.path.lexists(out):
            raise AuditInputError(f"preview output already exists: {out}")
        try:
            os.rename(transaction, out)
        except FileExistsError as error:
            raise AuditInputError(f"preview output already exists: {out}") from error
        except OSError as error:
            raise AuditInputError(
                f"cannot publish complete preview bundle {out}: {error}"
            ) from error
        committed = True
        return tuple(out / "preview" / name for name in names)
    finally:
        if not committed:
            try:
                shutil.rmtree(transaction)
            except OSError:
                pass
