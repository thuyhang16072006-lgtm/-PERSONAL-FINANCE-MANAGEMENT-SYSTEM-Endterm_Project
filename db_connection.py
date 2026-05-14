"""
db_connection.py v3.0
FIX: Connection pooling — không mở connection mới cho mỗi query.
"""
import mysql.connector
from mysql.connector import Error as MySQLError, pooling
from db_config import DB_CONFIG


class DatabaseError(Exception):
    pass


_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="moneymate_pool",
                pool_size=5,
                pool_reset_session=True,
                **DB_CONFIG,
            )
        except MySQLError as e:
            raise DatabaseError(
                f"Cannot create pool for '{DB_CONFIG['database']}' "
                f"at {DB_CONFIG['host']}:{DB_CONFIG['port']}. ({e})"
            )
    return _pool


def get_connection():
    try:
        return _get_pool().get_connection()
    except MySQLError as e:
        raise DatabaseError(f"Cannot get connection from pool: {e}")


def execute_query(sql: str, params: tuple = (), fetchall: bool = True):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall() if fetchall else cursor.fetchone()
    except MySQLError as e:
        raise DatabaseError(f"Query failed: {e}\nSQL: {sql}")
    finally:
        cursor.close()
        conn.close()  # trả lại pool


def execute_update(sql: str, params: tuple = ()):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except MySQLError as e:
        conn.rollback()
        raise DatabaseError(f"Update failed: {e}\nSQL: {sql}")
    finally:
        cursor.close()
        conn.close()