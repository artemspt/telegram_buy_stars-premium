import os
import sys
import threading

# Allow imports like "from src..." to resolve to project root /src
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import settings


def main() -> None:
    import uvicorn

    # Uvicorn reload uses signals and must run in the main thread.
    reload = settings.server.reload
    if threading.current_thread() is not threading.main_thread():
        reload = False

    uvicorn.run(
        "src.app:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
