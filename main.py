"""
MBOX Viewer — Entry Point
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure the project root is on sys.path regardless of cwd
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils.constants import APP_NAME, APP_VERSION, ORG_NAME
from utils.settings import AppSettings


def _setup_logging() -> None:
    """Configure application-level logging."""
    log_level = logging.DEBUG if os.environ.get("MBOX_DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy Qt / PySide6 internal logs
    logging.getLogger("PySide6").setLevel(logging.WARNING)


def _load_theme(app: QApplication, theme: str) -> None:
    """Load and apply the QSS stylesheet for the given theme name."""
    styles_dir = os.path.join(_ROOT, "gui", "styles")
    qss_path = os.path.join(styles_dir, f"{theme}.qss")
    if os.path.isfile(qss_path):
        with open(qss_path, "r", encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())
    else:
        logging.warning("Theme file not found: %s", qss_path)


def main() -> int:
    _setup_logging()
    log = logging.getLogger("main")
    log.info("Starting %s v%s", APP_NAME, APP_VERSION)

    # Enable high-DPI scaling (must be set before QApplication)
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)

    # Load persistent settings & apply theme
    settings = AppSettings()
    theme = settings.get("theme", "dark")
    _load_theme(app, theme)

    # Build and show main window
    window = MainWindow(settings)

    # If an .mbox file was passed as CLI argument, open it immediately
    if len(sys.argv) > 1:
        cli_path = sys.argv[1]
        if cli_path.lower().endswith(".mbox") and os.path.isfile(cli_path):
            log.info("Opening CLI file: %s", cli_path)
            window.open_mbox_file(cli_path)
        else:
            log.warning("CLI argument is not a valid .mbox file: %s", cli_path)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
