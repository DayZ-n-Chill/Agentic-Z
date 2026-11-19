import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vehicle_proxy_contract import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
