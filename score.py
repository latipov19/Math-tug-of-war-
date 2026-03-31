from database import DBCursor


def _row(row):
    return dict(row) if row else None

def _rows(rows):
    return [dict(r) for r in rows]


class ScoreModel:

    @staticmethod
    def save(user_id, score, difficulty, questions_correct,
             questions_total, time_played_sec, won):
        with DBCursor() as (_, cur):
            cur.execute(
                """INSERT INTO scores
                   (user_id, score, difficulty, questions_correct,
                    questions_total, time_played_sec, won)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, score, difficulty, questions_correct,
                 questions_total, time_played_sec, int(won))
            )
            score_id = cur.lastrowid

        # Update leaderboard cache
        ScoreModel._update_cache(user_id)
        return ScoreModel.get_by_id(score_id)

    @staticmethod
    def get_by_id(score_id):
        with DBCursor() as (_, cur):
            cur.execute("SELECT * FROM scores WHERE id = ?", (score_id,))
            return _row(cur.fetchone())

    @staticmethod
    def get_user_scores(user_id, limit=10):
        with DBCursor() as (_, cur):
            cur.execute(
                "SELECT * FROM scores WHERE user_id = ? ORDER BY played_at DESC LIMIT ?",
                (user_id, limit)
            )
            return _rows(cur.fetchall())

    @staticmethod
    def _update_cache(user_id):
        with DBCursor() as (_, cur):
            cur.execute("""
                SELECT
                    MAX(score)                          AS best_score,
                    SUM(won)                            AS total_wins,
                    COUNT(*)                            AS total_games,
                    ROUND(100.0*SUM(won)/COUNT(*), 1)  AS win_rate
                FROM scores WHERE user_id = ?
            """, (user_id,))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    INSERT INTO leaderboard_cache
                        (user_id, best_score, total_wins, total_games, win_rate, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(user_id) DO UPDATE SET
                        best_score  = excluded.best_score,
                        total_wins  = excluded.total_wins,
                        total_games = excluded.total_games,
                        win_rate    = excluded.win_rate,
                        updated_at  = datetime('now')
                """, (user_id, row['best_score'] or 0,
                      row['total_wins'] or 0,
                      row['total_games'] or 0,
                      row['win_rate'] or 0))

    @staticmethod
    def get_leaderboard(difficulty=None, limit=50):
        with DBCursor() as (_, cur):
            if difficulty:
                cur.execute("""
                    SELECT u.username, u.avatar_color,
                           lc.best_score, lc.total_wins, lc.total_games, lc.win_rate,
                           lc.updated_at
                    FROM leaderboard_cache lc
                    JOIN users u ON u.id = lc.user_id
                    JOIN (
                        SELECT user_id, MAX(score) as best
                        FROM scores WHERE difficulty = ? GROUP BY user_id
                    ) ds ON ds.user_id = lc.user_id
                    ORDER BY ds.best DESC
                    LIMIT ?
                """, (difficulty, limit))
            else:
                cur.execute("""
                    SELECT u.username, u.avatar_color,
                           lc.best_score, lc.total_wins, lc.total_games, lc.win_rate,
                           lc.updated_at
                    FROM leaderboard_cache lc
                    JOIN users u ON u.id = lc.user_id
                    ORDER BY lc.best_score DESC
                    LIMIT ?
                """, (limit,))
            return _rows(cur.fetchall())

    @staticmethod
    def get_user_rank(user_id):
        with DBCursor() as (_, cur):
            cur.execute("""
                SELECT COUNT(*) + 1 AS rank
                FROM leaderboard_cache
                WHERE best_score > (
                    SELECT COALESCE(best_score, 0)
                    FROM leaderboard_cache WHERE user_id = ?
                )
            """, (user_id,))
            row = cur.fetchone()
            return row['rank'] if row else None
