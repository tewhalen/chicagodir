"""Settings module for test app."""

from environs import Env

env = Env()
env.read_env()

ENV = "development"
TESTING = True
POSTGRES_PORT = env.int("POSTGRES_PORT", default=5432)
SQLALCHEMY_DATABASE_URI = (
    env.str("DATABASE_URL", default="sqlite:////tmp/dev.db")
    .replace("postgres://", "postgresql://")
    .replace("${POSTGRES_PORT}", str(POSTGRES_PORT))
)

SECRET_KEY = "not-so-secret-in-tests"
BCRYPT_LOG_ROUNDS = (
    4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
)
DEBUG_TB_ENABLED = False
CACHE_TYPE = "simple"  # Can be "memcached", "redis", etc.
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = False  # Allows form testing
