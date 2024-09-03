import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

PATH = os.getenv("DB_PATH")

logger = logging.getLogger(__name__)


def connect():
    if PATH is None:
        raise ValueError("DB_PATH environment variable is not set")
    conn = conn = psycopg2.connect(PATH)
    return conn


def create():
    logger.debug("ensuring database exists")
    conn = connect()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS credentials (
                credential TEXT,
                address TEXT,
                counter BIGINT,
                PRIMARY KEY (credential, address)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_status (
                address TEXT,
                event TEXT,
                genesis_hash TEXT NOT NULL,
                block_number INTEGER NOT NULL,
                PRIMARY KEY (address, event)
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS erpc_sync (
                last_submission_time INTEGER NOT NULL,
                PRIMARY KEY (last_submission_time)
            )
        """
        )
        conn.commit()
    finally:
        conn.close()


def has_credential(conn, address, credential):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM credentials WHERE credential = %s AND address = %s",
        (credential, address),
    )
    row = cursor.fetchone()
    return row is not None


def award_credential(conn, address, credential):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO credentials (credential, address, counter)
        VALUES (%s, %s, 1)
        ON CONFLICT (credential, address)
        DO UPDATE SET counter = credentials.counter + 1;
        """,
        (credential, address),
    )
    conn.commit()

def award_credential_multiple(conn, data):
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO credentials (credential, address, counter)
            VALUES (%s, %s, 1)
            ON CONFLICT (credential, address)
            DO UPDATE SET counter = credentials.counter + 1;
            """,
            data
        )
        conn.commit()


def get_sync_status(conn):
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT address, event, genesis_hash, block_number FROM sync_status")
    rows = cursor.fetchall()
    return {
        (row["address"], row["event"]): (row["genesis_hash"], row["block_number"])
        for row in rows
    }


def set_sync_status(conn, address, event, genesis_hash, block_number):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sync_status (address, event, genesis_hash, block_number)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(address, event) DO UPDATE SET
        genesis_hash = %s, block_number = %s
    """,
        (
            address, event, genesis_hash, block_number, genesis_hash, block_number
        )
    )

def get_erpc_updates(conn, last_sync_timestamp):
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT address, tx_hash FROM transaction_details WHERE inclusion_time > 0 AND is_cancellation = false AND submission_time > %s", (last_sync_timestamp,))
    rows = cursor.fetchall()
    return rows

def get_max_submission_time(conn, tx_hashes):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(submission_time) as last_submission_time FROM transaction_details WHERE tx_hash IN %s", (tuple(tx_hashes),))
    rows = cursor.fetchone()
    return rows[0]

def get_erpc_sync_status(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(last_submission_time) AS max_submission_time FROM erpc_sync")
    rows = cursor.fetchone()
    return rows[0]

def update_erpc_sync_status(conn, last_update):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO erpc_sync (last_submission_time) VALUES (%s) ON CONFLICT(last_submission_time) DO NOTHING", (last_update,))
    conn.commit()