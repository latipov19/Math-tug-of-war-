import bcrypt
from database import DBCursor


def _row(row):
    return dict(row) if row else None


class UserModel:

    @staticmethod
    def create(username, email, password, avatar_color='#4fc3f7'):
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with DBCursor() as (conn, cur):
            cur.execute(
                "INSERT INTO users (username, email, password_hash, avatar_color) VALUES (?, ?, ?, ?)",
                (username, email, hashed, avatar_color)
            )
            user_id = cur.lastrowid
        return UserModel.get_by_id(user_id)

    @staticmethod
    def get_by_id(user_id):
        with DBCursor() as (_, cur):
            cur.execute(
                "SELECT id, username, email, avatar_color, created_at FROM users WHERE id = ?",
                (user_id,)
            )
            return _row(cur.fetchone())

    @staticmethod
    def get_by_username(username):
        with DBCursor() as (_, cur):
            cur.execute("SELECT * FROM users WHERE username = ?", (username,))
            return _row(cur.fetchone())

    @staticmethod
    def get_by_email(email):
        with DBCursor() as (_, cur):
            cur.execute("SELECT * FROM users WHERE email = ?", (email,))
            return _row(cur.fetchone())

    @staticmethod
    def verify_password(user, password):
        return bcrypt.checkpw(password.encode(), user['password_hash'].encode())

    @staticmethod
    def update_last_login(user_id):
        with DBCursor() as (_, cur):
            cur.execute(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?",
                (user_id,)
            )

    @staticmethod
    def exists_username(username):
        with DBCursor() as (_, cur):
            cur.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            return cur.fetchone() is not None

    @staticmethod
    def exists_email(email):
        with DBCursor() as (_, cur):
            cur.execute("SELECT 1 FROM users WHERE email = ?", (email,))
            return cur.fetchone() is not None
