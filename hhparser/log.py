import logging

LOGGER_ROOT = "hhparser"


def configure_logging(level: int = logging.INFO) -> None:
    """Opt-in logging setup for scripts and quick experiments.

    When hhparser is used as a library, the host application should configure
    logging itself (see example.py). This helper is not called automatically.
    """
    logger = logging.getLogger(LOGGER_ROOT)
    logger.setLevel(level)
    if logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
