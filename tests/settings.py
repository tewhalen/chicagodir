"""Settings module for test app."""
import os

POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]

ENV = "development"
TESTING = True
SQLALCHEMY_DATABASE_URI = f"postgresql://hello_flask:hello_flask@{POSTGRES_HOST}:{POSTGRES_PORT}/chicagodir_dev"
SECRET_KEY = "not-so-secret-in-tests"
BCRYPT_LOG_ROUNDS = (
    4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
)
DEBUG_TB_ENABLED = False
CACHE_TYPE = "simple"  # Can be "memcached", "redis", etc.
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = False  # Allows form testing
