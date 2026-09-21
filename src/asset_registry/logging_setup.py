from __future__ import annotations

import logging
from pathlib import Path

from asset_registry.config import get_settings

_configured = False


def configure_logging() -> logging.Logger:
    """Configure application, request and ingest loggers that append to files."""
    global _configured
    settings = get_settings()
    log_dir = settings.resolved_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if not _configured:
        root = logging.getLogger("asset_registry")
        root.setLevel(logging.INFO)
        if not root.handlers:
            stream = logging.StreamHandler()
            stream.setFormatter(formatter)
            root.addHandler(stream)
            app_file = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
            app_file.setFormatter(formatter)
            root.addHandler(app_file)
        _configured = True

    _ensure_file_logger("asset_registry.requests", log_dir / "requests.log", formatter)
    _ensure_file_logger("asset_registry.ingest", log_dir / "ingest.log", formatter)
    return logging.getLogger("asset_registry")


def _ensure_file_logger(name: str, path: Path, formatter: logging.Formatter) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    target = str(path.resolve())
    already = any(
        isinstance(handler, logging.FileHandler)
        and Path(handler.baseFilename).resolve() == Path(target)
        for handler in logger.handlers
    )
    if already:
        return
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
