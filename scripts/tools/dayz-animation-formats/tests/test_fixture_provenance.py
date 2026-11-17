import hashlib
import json
from pathlib import Path


FIXTURES = Path(__file__).with_name("fixtures")


def test_first_party_animation_fixture_hashes_are_frozen():
    """Breaks if any oracle fixture changes without a new adjudication."""
    expected = {
        "seanim-v1-full.seanim": (
            288,
            "75af1c6ab01ae715e6cea01e6897b804586687ccf7a234c21be6bef871288b29",
        ),
        "rtm-0101-mdat.rtm": (
            258,
            "37aa63f705d874c79b94721027d376a7cab347fc94691ad419e1172c5597c3f8",
        ),
    }
    for name, (size, digest) in expected.items():
        data = (FIXTURES / name).read_bytes()
        assert len(data) == size
        assert hashlib.sha256(data).hexdigest() == digest


def test_semantic_expectations_are_valid_json_objects():
    """Breaks if a golden stops being a comparable JSON document."""
    for name in ("seanim-v1-full.json", "rtm-0101-mdat.json"):
        value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        assert value["format"] in {"seanim", "rtm"}
