"""
SQLite database — MySQL o'rniga, hech qanday server kerak emas.
Fayl: latipov_game.db (backend papkasida avtomatik yaratiladi)
"""
import sqlite3, os, threading

DB_PATH = os.path.join(os.path.dirname(__file__), 'latipov_game.db')
_local = threading.local()


def get_connection():
    if not hasattr(_local, 'conn') or _local.conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
        _init_tables(conn)
    return _local.conn


def _init_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT    NOT NULL UNIQUE,
        email        TEXT    NOT NULL UNIQUE,
        password_hash TEXT   NOT NULL,
        avatar_color TEXT    DEFAULT '#4fc3f7',
        equipped_frame TEXT  DEFAULT 'starter',
        coins        INTEGER DEFAULT 0,
        last_login   TEXT,
        created_at   TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS scores (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id           INTEGER NOT NULL REFERENCES users(id),
        score             INTEGER NOT NULL DEFAULT 0,
        difficulty        TEXT    NOT NULL DEFAULT 'easy',
        questions_correct INTEGER DEFAULT 0,
        questions_total   INTEGER DEFAULT 0,
        time_played_sec   INTEGER DEFAULT 0,
        won               INTEGER DEFAULT 0,
        played_at         TEXT    DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS leaderboard_cache (
        user_id     INTEGER PRIMARY KEY REFERENCES users(id),
        best_score  INTEGER DEFAULT 0,
        total_wins  INTEGER DEFAULT 0,
        total_games INTEGER DEFAULT 0,
        win_rate    REAL    DEFAULT 0,
        updated_at  TEXT    DEFAULT (datetime('now'))
    );
    """)
    conn.commit()

    try:
        conn.execute("ALTER TABLE users ADD COLUMN equipped_frame TEXT DEFAULT 'starter';")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0;")
        conn.commit()
    except sqlite3.OperationalError:
        pass


class DBCursor:
    """Context manager: (conn, cursor)  — auto commit / rollback."""

    def __init__(self, dictionary=True):
        self.dictionary = dictionary
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn   = get_connection()
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        # SQLite cursors don't need explicit close on same connection
        return False
