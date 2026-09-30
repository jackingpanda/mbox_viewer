"""
utils/constants.py
Application-wide constants and developer metadata.
"""

APP_NAME = "MBOX Viewer"
APP_VERSION = "1.3.0"
ORG_NAME = "MboxViewer"
APP_ID = "dimasaldrian.mboxviewer.app.1.3"

# Developer attribution
APP_AUTHOR = "Dimas Aldrian"
APP_EMAIL = "mbox@kulam.my.id"

# Default Google Takeout archive path
DEFAULT_TAKEOUT_PATH = r"D:\secret\M\gmail\Takeout\Mail\All mail Including Spam and Trash.mbox"

# Email list table columns
EMAIL_COLUMNS = ["#", "From", "Subject", "Date", "Labels", "📎"]
EMAIL_COL_INDEX = 0
EMAIL_COL_FROM = 1
EMAIL_COL_SUBJECT = 2
EMAIL_COL_DATE = 3
EMAIL_COL_LABELS = 4
EMAIL_COL_ATT = 5

# Default window geometry
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 800

# Loading batch size (emails per signal emission)
PARSE_BATCH_SIZE = 300

# Max snippet length
SNIPPET_MAX_LEN = 200
