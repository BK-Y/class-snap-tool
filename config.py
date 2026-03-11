import os
from pathlib import Path


class BaseConfig:
    """Base configuration with sensible defaults.

    Production and development configurations can extend this class.  All
    settings may be overridden via environment variables.
    """

    # secret key for session cookies and CSRF.  *must* be set in production.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    # debug flag (Flask will also respect FLASK_DEBUG) but we expose it here
    DEBUG = os.getenv("DEBUG", "0") in {"1", "true", "True"}


    # database path (sqlite by default). can be an absolute path or relative to
    # the project root. if not provided we fall back to `.data/school.db`.
    DATABASE_PATH = os.getenv("DATABASE_PATH") or str(
        Path(__file__).parent.resolve() / ".data" / "school.db"
    )
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_PATH
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # when true (and DEBUG), the initialization helper will drop all tables
    # on startup.  This is useful for resetting a development database but
    # should normally be off so that data is preserved.
    RESET_DB = os.getenv("RESET_DB", "0") in {"1", "true", "True"}

    # host/port defaults (run.py already reads from env variables directly but
    # keeping them here for consistency)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    # explicit disable debug to be safe
    DEBUG = False


def get_config():
    """Return the configuration object for the current environment.

    The caller can use ``app.config.from_object(get_config())``.
    The environment is determined by :envvar:`FLASK_ENV` which mirrors the
    default behaviour of Flask itself.  Supported values are ``production``
    and ``development``; anything else falls back to development.
    """

    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
