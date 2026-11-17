"""build-api-index.py and dayz-api.py: build a script API index from a small scripts tree, then query it.

Both scripts are plain Python, so this runs on Windows too. The Linux shell helpers in this
folder have their own tests, which skip on Windows.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("lzma")

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build-api-index.py"
QUERY = HERE / "dayz-api.py"

ENTITY_AI = """class EntityAI
{
	//! Called when the entity is saved
	void OnStoreSave(ParamsWriteContext ctx) {}
	proto native void SetHealth(float health);
}
"""

ITEM_BASE = """class ItemBase extends EntityAI
{
	protected int m_Quantity;

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
	}

	bool SetQuantity(float value)
	{
		return true;
	}
}

enum EMyState
{
	IDLE,
	RUNNING = 5,
	STOPPED
}
"""


def _run(script: Path, *args: str, api_dir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, DAYZ_API_DIR=str(api_dir), PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, str(script), *args], env=env, capture_output=True, text=True, encoding="utf-8", check=False
    )


@pytest.fixture()
def api_dir(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts"
    (scripts / "3_Game" / "Entities").mkdir(parents=True)
    (scripts / "4_World" / "Entities").mkdir(parents=True)
    (scripts / "3_Game" / "Entities" / "EntityAI.c").write_text(ENTITY_AI, encoding="utf-8")
    (scripts / "4_World" / "Entities" / "ItemBase.c").write_text(ITEM_BASE, encoding="utf-8")
    out = tmp_path / "api"
    done = _run(BUILD, str(scripts), str(out), "--build", "test build", api_dir=out)
    assert done.returncode == 0, done.stderr
    assert (out / "dayz-api.txt.xz").is_file()
    return out


def test_chain_walks_the_base_classes(api_dir):
    done = _run(QUERY, "chain", "ItemBase", api_dir=api_dir)
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ItemBase > EntityAI"


def test_class_lists_members_and_inherited_ones(api_dir):
    own = _run(QUERY, "class", "ItemBase", api_dir=api_dir).stdout
    assert "SetQuantity(float value)" in own
    assert "override: OnStoreSave" in own
    assert "SetHealth" not in own
    inherited = _run(QUERY, "class", "ItemBase", "--inherited", api_dir=api_dir).stdout
    assert "native void SetHealth(float health)" in inherited
    assert "#Called when the entity is saved" in inherited


def test_find_and_enum_and_src(api_dir):
    found = _run(QUERY, "find", "sethealth", api_dir=api_dir).stdout
    assert found.startswith("EntityAI: ")
    values = _run(QUERY, "enum", "EMyState", api_dir=api_dir).stdout
    assert "IDLE=0 RUNNING=5 STOPPED=6" in values
    src = _run(QUERY, "src", "ItemBase", api_dir=api_dir).stdout
    assert "4_World\\Entities\\ItemBase.c" in src


def test_query_without_an_index_names_the_builder(tmp_path):
    done = _run(QUERY, "class", "ItemBase", api_dir=tmp_path / "empty")
    assert done.returncode != 0
    assert "build-api-index.py" in done.stderr


@pytest.mark.parametrize("name", ["..", "", "bad/name"])
def test_mod_name_is_checked_before_anything_is_written(tmp_path, name):
    out = tmp_path / "api"
    done = _run(BUILD, str(tmp_path), str(out), "--mod", name, api_dir=out)
    assert done.returncode != 0
    assert "--mod must match" in done.stderr
    assert not out.exists()
