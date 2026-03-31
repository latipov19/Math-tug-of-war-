-- Latipov Game Database Schema
CREATE DATABASE IF NOT EXISTS latipov_game CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE latipov_game;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar_color VARCHAR(7) DEFAULT '#4fc3f7',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login  TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS scores (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NOT NULL,
    score             INT NOT NULL DEFAULT 0,
    difficulty        ENUM('easy', 'medium', 'hard') NOT NULL,
    questions_correct INT NOT NULL DEFAULT 0,
    questions_total   INT NOT NULL DEFAULT 0,
    time_played_sec   INT NOT NULL DEFAULT 0,
    won               TINYINT(1) NOT NULL DEFAULT 0,
    played_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS leaderboard_cache (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL UNIQUE,
    best_score  INT NOT NULL DEFAULT 0,
    total_wins  INT NOT NULL DEFAULT 0,
    total_games INT NOT NULL DEFAULT 0,
    win_rate    DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN total_games > 0 THEN (total_wins / total_games) * 100 ELSE 0 END
    ) STORED,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_scores_user     ON scores(user_id);
CREATE INDEX idx_scores_score    ON scores(score DESC);
CREATE INDEX idx_scores_diff     ON scores(difficulty);
CREATE INDEX idx_lb_best_score   ON leaderboard_cache(best_score DESC);

-- Trigger to update leaderboard_cache on new score insert
DELIMITER $$
CREATE TRIGGER after_score_insert
AFTER INSERT ON scores
FOR EACH ROW
BEGIN
    INSERT INTO leaderboard_cache (user_id, best_score, total_wins, total_games)
    VALUES (NEW.user_id, NEW.score, NEW.won, 1)
    ON DUPLICATE KEY UPDATE
        best_score  = GREATEST(best_score, NEW.score),
        total_wins  = total_wins + NEW.won,
        total_games = total_games + 1;
END$$
DELIMITER ;
