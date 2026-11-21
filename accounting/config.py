import os
import re
from pathlib import Path

ACCOUNTING_DIR = Path(__file__).resolve().parent
UTILS_DIR = ACCOUNTING_DIR / "utils"

# Base folder for raw/, processed/, and active cashew.db
CASHEW_DIR = Path(os.environ.get("CASHEW_DIR", "/app/data/accounting"))

# SQLite 3 file header bytes
SQLITE_MAGIC = b"SQLite format 3\x00"

# Tables required in the uploaded Cashew DB
REQUIRED_TABLES = {"transactions", "wallets", "categories", "objectives"}

# Expected filename (e.g. cashew-2026-11-20-12-23-15-438739.sql)
FILENAME_PATTERN = re.compile(r"^cashew-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}(-\d+)?\.sql$")

# SQL and HTML asset paths
SCHEMA_PATH = UTILS_DIR / "schema.sql"
EXPENSES_PATH = UTILS_DIR / "expenses.sql"
HTML_PATH = UTILS_DIR / "upload.html"
api