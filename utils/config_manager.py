import os
from datetime import timedelta

class ConfigManager:
    def __init__(self):
        self._config = {
            'SECRET_KEY': os.environ.get('SECRET_KEY', 'your-secret-key-here'),
            'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///dms.db'),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'UPLOAD_FOLDER': 'static/uploads',
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file size
            'PERMANENT_SESSION_LIFETIME': timedelta(days=1),
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax'
        }

    def get_config(self):
        return self._config

# Create a singleton instance
config_manager = ConfigManager() 