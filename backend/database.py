"""Database connection and session management."""
import logging
import os
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

logger = logging.getLogger(__name__)

db_url = os.environ.get("DATABASE_URL") or settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Automatically use Supabase Transaction Mode Pooler (port 6543) if using a pooler URL
# to bypass the 15-connection strict limit on port 5432.
if ".pooler.supabase.com:5432" in db_url:
    db_url = db_url.replace(".pooler.supabase.com:5432", ".pooler.supabase.com:6543")

is_sqlite = db_url.startswith("sqlite")
allow_sqlite_fallback = os.environ.get("ALLOW_SQLITE_FALLBACK", "true").lower() in ("true", "1")

def _create_engine_for_url(url: str):
    if url.startswith("sqlite"):
        return create_engine(
            url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        url,
        echo=settings.debug,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Help recover stale connections
        connect_args={"prepare_threshold": None, "connect_timeout": 3},  # Disable prepared statements for pgBouncer; 3s timeout
    )

def _probe_engine(candidate_engine) -> bool:
    try:
        with candidate_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as ex:
        logger.warning(f"Database probe failed for {candidate_engine.url}: {ex}")
        return False

# Attempt primary engine connection
try:
    engine = _create_engine_for_url(db_url)
    # Quick probe on non-sqlite to verify host is reachable
    if not is_sqlite and not _probe_engine(engine):
        raise ConnectionError(f"Primary database at {db_url} is unreachable or project is paused.")
except Exception as e:
    logger.warning(f"Primary database connection failed for {db_url}: {e}")
    # Attempt local Postgres fallback first (Docker container 'facial_postgres')
    local_pg_urls = [
        "postgresql://postgres:postgrespassword@127.0.0.1:5432/facial_ops",
        "postgresql://postgres:postgrespassword@postgres:5432/facial_ops",
        "postgresql://postgres:postgrespassword@localhost:5432/facial_ops",
    ]
    fallback_engine = None
    for l_url in local_pg_urls:
        try:
            cand = _create_engine_for_url(l_url)
            if _probe_engine(cand):
                logger.info(f"Connected to local PostgreSQL fallback: {l_url}")
                engine = cand
                db_url = l_url
                fallback_engine = cand
                break
        except Exception:
            continue

    if fallback_engine is None:
        if not allow_sqlite_fallback and not is_sqlite:
            logger.critical(f"FATAL: Database connection failed for {db_url}: {e}")
            raise RuntimeError(
                f"Production database connection failed: {e}. "
                "Halting to prevent silent local SQLite fallback and data loss. "
                "Set ALLOW_SQLITE_FALLBACK=1 only for offline local testing."
            ) from e

        logger.warning(f"Local PostgreSQL not reachable. Falling back to local SQLite.")
        db_url = "sqlite:///./facial_recognition.db"
        engine = _create_engine_for_url(db_url)

@event.listens_for(engine, "connect")
def on_db_connect(dbapi_conn, connection_record):
    """Configure PostgreSQL session timezone or SQLite WAL concurrency pragmas."""
    if engine.dialect.name == "postgresql":
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("SET TIMEZONE='Asia/Kolkata'")
        except Exception as ex:
            logger.debug(f"PostgreSQL connection timezone hook warning: {ex}")
        finally:
            cursor.close()
    elif engine.dialect.name == "sqlite":
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=15000")
        except Exception as ex:
            logger.warning(f"SQLite connection hook warning: {ex}")
        finally:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def check_database_health() -> bool:
    """Fast probe to verify database connectivity and readiness."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def ensure_detection_event_id_column():
    """Upgrade legacy tables with columns added after initial release."""
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except Exception as e:
                logger.warning(f"Could not create vector extension (may already exist or lack superuser): {e}")

        inspector = inspect(connection)
        table_columns = {
            "detections": {
                "event_id": "VARCHAR",
                "embedding_vector": "vector(512)" if engine.dialect.name == "postgresql" else "TEXT",
                "unregistered_subject_id": "VARCHAR",
                "device_id": "VARCHAR",
                "sequence_number": "INTEGER",
                "priority": "VARCHAR",
                "config_version": "INTEGER",
                "detection_model_version": "VARCHAR",
                "embedding_model_version": "VARCHAR",
                "gallery_version": "INTEGER",
                "threshold_version": "INTEGER",
                "camera_config_version": "INTEGER",
                "algorithm_version": "VARCHAR",
                "version_bundle_hash": "VARCHAR",
                "source": "VARCHAR DEFAULT 'live'",
                "batch_id": "VARCHAR",
                "quality_score": "FLOAT",
            },
            "unregistered_subjects": {
                "quality_score": "FLOAT",
            },
            "alerts": {
                "source": "VARCHAR DEFAULT 'live'",
                "batch_id": "VARCHAR",
            },
            "embeddings": {
                "model_version": "VARCHAR",
            },
            "event_provenances": {
                "clock_source": "VARCHAR DEFAULT 'edge_pc'",
                "clock_skew_seconds": "FLOAT DEFAULT 0.0",
            },
        }
        for table_name, missing_columns in table_columns.items():
            if not inspector.has_table(table_name):
                continue
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in missing_columns.items():
                if column_name not in columns:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )

            if table_name == "detections" and "event_id" not in columns:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_detections_event_id "
                        "ON detections (event_id)"
                    )
                )
            if table_name == "detections" and "source" not in columns:
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_detections_source_timestamp "
                        "ON detections (source, timestamp)"
                    )
                )
            if table_name == "embeddings" and "model_version" not in columns:
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_embeddings_model_version "
                        "ON embeddings (model_version)"
                    )
                )
            if table_name == "alerts" and "source" not in columns:
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_alerts_source_timestamp "
                        "ON alerts (source, timestamp)"
                    )
                )

        if engine.dialect.name == "postgresql":
            try:
                if inspector.has_table("embeddings"):
                    connection.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_hnsw "
                            "ON embeddings USING hnsw (vector vector_cosine_ops) "
                            "WITH (m = 16, ef_construction = 64)"
                        )
                    )
                if inspector.has_table("detections"):
                    connection.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_detections_embedding_vector_hnsw "
                            "ON detections USING hnsw (embedding_vector vector_cosine_ops) "
                            "WITH (m = 16, ef_construction = 64)"
                        )
                    )
            except Exception as e:
                logger.warning(f"Could not ensure HNSW indexes on PostgreSQL: {e}")


def get_db():
    """Dependency for FastAPI to inject database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

