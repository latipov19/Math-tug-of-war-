import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'latipov-game-super-secret-2024-change-in-prod')
    DEBUG      = os.environ.get('DEBUG', 'False').lower() == 'true'

    # MySQL
    MYSQL_HOST     = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT     = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER     = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB       = os.environ.get('MYSQL_DB', 'latipov_game')

    # JWT
    JWT_SECRET        = os.environ.get('JWT_SECRET', SECRET_KEY)
    JWT_EXPIRY_HOURS  = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

    # CORS origins (comma-separated)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:5500').split(',')
