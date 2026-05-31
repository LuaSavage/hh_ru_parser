import logging

LOGGER_ROOT = "hhparser"


def configure_logging(level: int = logging.INFO) -> None:
    """Opt-in logging setup for scripts and quick experiments.

    Configures the root logger with a single handler so hhparser loggers
    do not duplicate output via propagation.
    """
    logging.getLogger(LOGGER_ROOT).setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
