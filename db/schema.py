"""Database initialization helpers.

This module consolidates table creation logic so that during development
we can simply call ``init_db()`` to ensure all tables exist. It is intentionally
simple and does *not* rely on Alembic; migrations can be added later once the
project is closer to production.
"""

from flask import current_app
from db.sa_db import db


def init_db():
    """Ensure the database schema exists and is up‑to‑date.

    When the application starts we call this routine so that a fresh install
    will automatically create the necessary tables, and a later run will
    silently add any missing columns or tables without touching existing
    data.  This is handy during development when models are still changing.

    If you really want to blow everything away (for example, after renaming a
    column or resetting tests) set the ``RESET_DB`` configuration flag to a
    true value while running; in debug mode the database will be dropped and
    recreated in that case.

    The function should be invoked from within an application context, e.g.::

        with app.app_context():
            init_db()

    For convenience a quick command is added to ``app.py`` (commented out by
    default) but you can also run::

        RESET_DB=1 python -c "from db.schema import init_db; init_db()"
    """
    # import models to ensure they are registered with SQLAlchemy
    from db import models  # noqa: F401
    # in development it's convenient to reset the schema when you're
    # actively changing models, but wiping the database on every
    # application start is usually surprising (and it was clearing data
    # whenever the debug reloader restarted the process). instead we only
    # drop tables when an explicit configuration flag is set.
    #
    # To force a reset run with ``RESET_DB=1`` in your environment or
    # adjust the flag in ``config.py``.  In production the default is to
    # never drop existing data.
    if current_app.config.get('DEBUG') and current_app.config.get('RESET_DB'):
        db.drop_all()
    db.create_all()  # kept for RESET_DB branch, but not called elsewhere
    # after tables are created (or already existed) ensure any new columns
    # from model changes are added to existing tables without destroying data
    _add_missing_columns()


def _add_missing_columns():
    """Scan existing tables and add any columns that our models define.

    SQLite's ``ALTER TABLE`` is very limited; we only append new nullable
    columns with no default.  Columns marked ``nullable=False`` are skipped
    because SQLite can't add them safely once rows exist.  This function is
    intentionally conservative to avoid data loss.
    """
    from sqlalchemy import inspect

    insp = inspect(db.engine)
    metadata = db.metadata
    for table_name, table in metadata.tables.items():
        if not insp.has_table(table_name):
            # table will be created by create_all() earlier
            continue
        existing_cols = {c['name'] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            if not col.nullable:
                current_app.logger.warning(
                    "skipping not-null column %s on %s", col.name, table_name
                )
                continue
            col_type = col.type.compile(db.engine.dialect)
            sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}"
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text(sql))
                current_app.logger.info(
                    "added missing column %s to %s", col.name, table_name
                )
            except Exception as e:
                current_app.logger.warning(
                    "failed to add column %s to %s: %s", col.name, table_name, e
                )
    db.session.commit()
