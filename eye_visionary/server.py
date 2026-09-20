"""Windows-compatible API launcher."""

from __future__ import annotations

import asyncio
import uvicorn


def selector_loop_factory():
    """Use the loop required by async Psycopg on Windows."""

    return asyncio.SelectorEventLoop()


def main() -> None:
    uvicorn.run(
        "eye_visionary.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        loop="eye_visionary.server:selector_loop_factory",
    )


if __name__ == "__main__":
    main()
