import os
import sqlite3

DB_PATH = os.environ.get("YFINANCE_DB_PATH", "/app/data/investments/yfinance.db")


class DBConn:
    def __init__(self):
        """Initialize SQLite database with required tables if they don't exist"""
        self.db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                close REAL, 
                high REAL,
                low REAL,
                volume REAL,
                average REAL,
                UNIQUE(symbol, date)
            )
            """
        )
        self.db_conn.commit()
        self.db_conn.close()

    def __enter__(self):
        self.db_conn = sqlite3.connect(DB_PATH)
        return self.db_conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Multi-treading throws error if a connection was closed by another thread, even with check_same_thread=False above
        if self.db_conn:
            self.db_conn.close()
