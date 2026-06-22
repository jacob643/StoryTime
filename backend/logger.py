import logging
import sys

logger = logging.getLogger("storytime")
logger.setLevel(logging.INFO)

_handler = logging.StreamHandler(sys.stdout)
_handler.setLevel(logging.INFO)
_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
_handler.setFormatter(_formatter)
logger.addHandler(_handler)


def set_verbose() -> None:
    logger.setLevel(logging.DEBUG)
    _handler.setLevel(logging.DEBUG)
