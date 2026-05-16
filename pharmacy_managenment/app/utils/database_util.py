from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def check_database_connection(db: Session) -> bool:
    """Check if database is reachable"""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def get_table_count(db: Session, table_name: str) -> int:
    """Get row count of a table"""
    try:
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
    except Exception as e:
        logger.error(f"Failed to get count for {table_name}: {e}")
        return 0

def vacuum_analyze(db: Session):
    """Run VACUUM ANALYZE (PostgreSQL)"""
    try:
        db.execute(text("VACUUM ANALYZE"))
        db.commit()
        logger.info("VACUUM ANALYZE completed")
    except Exception as e:
        logger.error(f"VACUUM ANALYZE failed: {e}")

def get_database_size(db: Session) -> dict:
    """Get database size information (PostgreSQL)"""
    try:
        result = db.execute(text("""
            SELECT
                pg_database_size(current_database()) as db_size,
                pg_size_pretty(pg_database_size(current_database())) as db_size_pretty
        """)).first()
        return {"bytes": result.db_size, "human": result.db_size_pretty}
    except Exception as e:
        logger.error(f"Failed to get database size: {e}")
        return {"bytes": 0, "human": "Unknown"}

def get_active_connections(db: Session) -> int:
    """Get number of active connections (PostgreSQL)"""
    try:
        result = db.execute(text("""
            SELECT count(*) FROM pg_stat_activity
            WHERE datname = current_database() AND state = 'active'
        """))
        return result.scalar()
    except Exception as e:
        logger.error(f"Failed to get active connections: {e}")
        return 0