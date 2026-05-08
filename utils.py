"""Logging centralizado compartido por todos los módulos."""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configura el handler raíz una sola vez."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
