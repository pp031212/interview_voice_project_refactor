from __future__ import annotations

import sys
from pathlib import Path

REFACTOR_ROOT = Path(__file__).resolve().parents[3]
if str(REFACTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(REFACTOR_ROOT))

from app.tasks import run_loop


def main() -> None:
    run_loop()


if __name__ == "__main__":
    main()
