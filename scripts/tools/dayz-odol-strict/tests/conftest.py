from pathlib import Path
import sys


TOOL_ROOT = Path(__file__).parents[1]
value = str(TOOL_ROOT)
if value not in sys.path:
    sys.path.insert(0, value)
