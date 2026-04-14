from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, literal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


SCHEMA_VERSION = 2

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


def get_sqlite_db_path() -> Path | None:
    prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
    for prefix in prefixes:
        if settings.DATABASE_URL.startswith(prefix):
            return Path(settings.DATABASE_URL[len(prefix):]).resolve()
    return None


def _scalar_default_sql(column, dialect) -> str | None:
    if column.server_default is not None and getattr(column.server_default, "arg", None) is not None:
        return str(
            column.server_default.arg.compile(
                dialect=dialect,
                compile_kwargs={"literal_binds": True},
            )
        )

    default = column.default
    if default is None or not default.is_scalar:
        return None

    return str(
        literal(default.arg).compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True},
        )
    )


def _add_column_ddl(column, dialect) -> str:
    type_sql = column.type.compile(dialect=dialect)
    pieces = [dialect.identifier_preparer.quote(column.name), type_sql]
    default_sql = _scalar_default_sql(column, dialect)
    if default_sql is not None:
        pieces.extend(["DEFAULT", default_sql])

    if not column.nullable and not column.primary_key:
        if default_sql is not None:
            pieces.append("NOT NULL")
        else:
            pieces.append("NULL")

    return " ".join(pieces)


def _ensure_schema_migrations_table(sync_conn) -> None:
    sync_conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME NOT NULL,
            note TEXT
        )
        """
    )


def _record_schema_version(sync_conn, version: int, note: str) -> None:
    _ensure_schema_migrations_table(sync_conn)
    sync_conn.exec_driver_sql(
        """
        INSERT OR REPLACE INTO schema_migrations (version, applied_at, note)
        VALUES (?, ?, ?)
        """,
        (version, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note),
    )


def _sync_existing_tables(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            ddl = _add_column_ddl(column, sync_conn.dialect)
            sync_conn.exec_driver_sql(f"ALTER TABLE {table.name} ADD COLUMN {ddl}")

        existing_indexes = {index["name"] for index in inspector.get_indexes(table.name)}
        for index in table.indexes:
            if not index.name or index.name in existing_indexes:
                continue
            index.create(bind=sync_conn, checkfirst=True)


def sync_schema(sync_conn) -> None:
    Base.metadata.create_all(sync_conn)
    _sync_existing_tables(sync_conn)
    _record_schema_version(sync_conn, SCHEMA_VERSION, "metadata sync")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(sync_schema)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
