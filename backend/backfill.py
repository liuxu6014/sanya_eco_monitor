"""Compatibility wrapper for the short insect/spore backfill script.

The implementation lives in backend/scripts/backfill.py.
"""

import asyncio

from scripts.backfill import backfill


if __name__ == "__main__":
    asyncio.run(backfill())
