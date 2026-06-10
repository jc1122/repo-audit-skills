import sys
from pathlib import Path

_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)
sys.modules.pop("helpers", None)

collect_ignore = ["fixtures"]

collect_ignore = ["fixtures"]

# Prevent pytest from collecting fixture test files as test cases.
collect_ignore = ["fixtures"]
