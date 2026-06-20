import logging
import sys

logger = logging.getLogger("storytime")
logger.setLevel(logging.DEBUG)

_handler = logging.StreamHandler(sys.stdout)
_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
_handler.setFormatter(_formatter)
logger.addHandler(_handler)
