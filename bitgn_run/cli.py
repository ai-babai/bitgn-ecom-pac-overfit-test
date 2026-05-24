from __future__ import annotations

from .config import config_from_args
from .runner import print_summary, run


def main() -> int:
    config = config_from_args()
    results = run(config)
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
