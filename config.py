import os


class Config:
    # Secret key for session management (You should change this to a more secure value)
    SECRET_KEY = os.urandom(24)

    # Session lifetime settings (optional)
    PERMANENT_SESSION_LIFETIME = 3600  # In seconds (1 hour)

    # MySQL Configuration
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'  # Change this to your MySQL username
    MYSQL_PASSWORD = 'Student1'  # Change this to your MySQL password
    MYSQL_DB = 'parkinson_db'  # Change this to your MySQL database name

    # For MySQLdb (This would be needed if you're using MySQLdb for connection)
    MYSQL_CURSORCLASS = 'DictCursor'  # Use DictCursor if you want your queries to return dictionaries

    # Debugging
    DEBUG = True
    TESTING = False

    # Additional config options could go here (e.g., email server, logging, etc.)


# You can have different classes for different environments (e.g., Development, Testing, Production)
class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    ENV = 'testing'


class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'
