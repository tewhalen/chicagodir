# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
POSTGRES_PORT = env.int("POSTGRES_PORT", default=5432)
DEBUG = ENV == "development"
SQLALCHEMY_DATABASE_URI = (
    env.str("DATABASE_URL", default="sqlite:////tmp/dev.db")
    .replace("postgres://", "postgresql://")
    .replace("${POSTGRES_PORT}", POSTGRES_PORT)
)
SECRET_KEY = env.str("SECRET_KEY", default="not-so-secret")
SEND_FILE_MAX_AGE_DEFAULT = env.int("SEND_FILE_MAX_AGE_DEFAULT", default=0)
BCRYPT_LOG_ROUNDS = env.int("BCRYPT_LOG_ROUNDS", default=13)
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
CACHE_TYPE = "simple"  # Can be "memcached", "redis", etc.
SQLALCHEMY_TRACK_MODIFICATIONS = False

# redis stuff
REDIS_URL = env.str("REDIS_URL", default="redis://redis:6379/0")
QUEUES = ["default"]
