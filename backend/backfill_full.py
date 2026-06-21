"""Compatibility wrapper for the full historical backfill script.

The implementation lives in backend/scripts/backfill_full.py.
"""

import asyncio

from scripts.backfill_full import main


if __name__ == "__main__":
    asyncio.run(main())
