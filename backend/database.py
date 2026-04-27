from datetime import datetime
from pathlib import Path
import logging

from sqlalchemy import inspect, literal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


SCHEMA_VERSION = 4
UNIQUE_COLLECTION_TABLES = (
    "insect_records",
    "spore_records",
    "runoff_records",
    "rainfall_records",
    "water_quality_records",
    "water_level_records",
)

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.SQLALCHEMY_ECHO)
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


def _get_current_schema_version(sync_conn) -> int:
    _ensure_schema_migrations_table(sync_conn)
    result = sync_conn.exec_driver_sql("SELECT MAX(version) FROM schema_migrations")
    return result.scalar_one() or 0


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


def _deduplicate_collection_tables(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())

    for table_name in UNIQUE_COLLECTION_TABLES:
        if table_name not in existing_tables:
            continue

        result = sync_conn.exec_driver_sql(
            f"""
            DELETE FROM {table_name}
            WHERE EXISTS (
                SELECT 1
                FROM {table_name} AS duplicate_row
                WHERE duplicate_row.device_code = {table_name}.device_code
                  AND duplicate_row.collection_time = {table_name}.collection_time
                  AND duplicate_row.id < {table_name}.id
            )
            """
        )
        if result.rowcount and result.rowcount > 0:
            logger.warning("Removed %s duplicate rows from %s", result.rowcount, table_name)


def _shrink_water_quality_table(sync_conn) -> None:
    inspector = inspect(sync_conn)
    if "water_quality_records" not in set(inspector.get_table_names()):
        return

    expected_columns = {
        "id",
        "device_code",
        "collection_time",
        "ammonia_nitrogen",
        "total_phosphorus",
        "total_nitrogen",
        "permanganate_index",
        "raw_data",
        "created_at",
    }
    existing_columns = {column["name"] for column in inspector.get_columns("water_quality_records")}
    if existing_columns == expected_columns:
        return

    ammonia_source = "ammonia_nitrogen" if "ammonia_nitrogen" in existing_columns else "NULL"
    phosphorus_source = "total_phosphorus" if "total_phosphorus" in existing_columns else "NULL"
    nitrogen_source = "total_nitrogen" if "total_nitrogen" in existing_columns else "NULL"
    permanganate_source = "permanganate_index" if "permanganate_index" in existing_columns else "NULL"
    logger.warning("Rebuilding water_quality_records to keep only current real metrics")
    sync_conn.exec_driver_sql("DROP TABLE IF EXISTS water_quality_records__new")
    sync_conn.exec_driver_sql(
        """
        CREATE TABLE water_quality_records__new (
            id INTEGER NOT NULL PRIMARY KEY,
            device_code VARCHAR(64) NOT NULL,
            collection_time DATETIME NOT NULL,
            ammonia_nitrogen FLOAT,
            total_phosphorus FLOAT,
            total_nitrogen FLOAT,
            permanganate_index FLOAT,
            raw_data JSON NOT NULL,
            created_at DATETIME NOT NULL
        )
        """
    )
    sync_conn.exec_driver_sql(
        f"""
        INSERT INTO water_quality_records__new (
            id,
            device_code,
            collection_time,
            ammonia_nitrogen,
            total_phosphorus,
            total_nitrogen,
            permanganate_index,
            raw_data,
            created_at
        )
        SELECT
            id,
            device_code,
            collection_time,
            {ammonia_source},
            {phosphorus_source},
            {nitrogen_source},
            {permanganate_source},
            raw_data,
            created_at
        FROM water_quality_records
        """
    )
    sync_conn.exec_driver_sql("DROP TABLE water_quality_records")
    sync_conn.exec_driver_sql("ALTER TABLE water_quality_records__new RENAME TO water_quality_records")
    sync_conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_water_quality_records_device_code "
        "ON water_quality_records (device_code)"
    )
    sync_conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_water_quality_records_collection_time "
        "ON water_quality_records (collection_time)"
    )
    sync_conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_water_quality_records_created_at "
        "ON water_quality_records (created_at)"
    )
    sync_conn.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_water_quality_records_device_code_collection_time "
        "ON water_quality_records (device_code, collection_time)"
    )


def sync_schema(sync_conn) -> None:
    Base.metadata.create_all(sync_conn)
    current_version = _get_current_schema_version(sync_conn)
    if current_version < SCHEMA_VERSION:
        _deduplicate_collection_tables(sync_conn)
    if current_version < 4:
        _shrink_water_quality_table(sync_conn)
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
