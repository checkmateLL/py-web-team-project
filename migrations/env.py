import asyncio
from logging.config import fileConfig
import os

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from urllib.parse import quote_plus

from alembic import context

from app.config import settings as app_settings
from app.database.models import BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = BaseModel.metadata

def get_database_url():
    """
    Retrieve the database URL, giving priority to environment variables.
    """
    # First, check for complete PG_URL environment variable
    pg_url = os.environ.get('PG_URL')
    if pg_url:
        return pg_url

    # If not, construct from individual environment variables
    pg_driver = os.environ.get('PG_DRIVER', 'postgresql+asyncpg')
    pg_user = os.environ.get('PG_USER', app_settings.PG_USER)
    pg_password = quote_plus(os.environ.get('PG_PASSWORD', app_settings.PG_PASSWORD))
    pg_host = os.environ.get('PG_HOST', app_settings.PG_HOST)
    pg_port = os.environ.get('PG_PORT', str(app_settings.PG_PORT))
    pg_db = os.environ.get('PG_DATABASE', app_settings.PG_DATABASE)
    
    return f"{pg_driver}://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

# Set the database URL, giving priority to environment variables
config.set_main_option('sqlalchemy.url', get_database_url())

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations(connection: Connection):
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run async migrations."""
    config_section = config.get_section(config.config_ini_section) or {}
    config_section['sqlalchemy.url'] = get_database_url()

    connectable = async_engine_from_config(
        config_section,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(run_migrations)

    await connectable.dispose()


def run_migrations_online():
    """Run migrations in 'online' mode for sync context."""
    config_section = config.get_section(config.config_ini_section) or {}
    config_section['sqlalchemy.url'] = get_database_url()

    connectable = async_engine_from_config(
        config_section,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    def do_run_migrations(connection):
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

    # This is a synchronous run of an async engine
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()