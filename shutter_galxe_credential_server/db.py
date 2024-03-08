import os
import logging
import sqlite3

PATH = os.getenv("DB_PATH")

logger = logging.getLogger(__name__)


def connect():
    if PATH is None:
        raise ValueError("DB_PATH environment variable is not set")
    conn = sqlite3.connect(PATH, autocommit=False)
    conn.row_factory = sqlite3.Row
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
        conn.commit()
    finally:
        conn.close()


def has_credential(conn, address, credential):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM credentials WHERE credential = :credential AND address = :address",
        {"credential": credential, "address": address},
    )
    row = cursor.fetchone()
    return row is not None


def award_credential(conn, address, credential):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO credentials (credential, address) VALUES (:credential, :address)
        ON CONFLICT(credential, address) DO NOTHING
        """,
        {"credential": credential, "address": address},
    )
    conn.commit()


def get_sync_status(conn):
    cursor = conn.cursor()
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
        VALUES (:address, :event, :genesis_hash, :block_number)
        ON CONFLICT(address, event) DO UPDATE SET
        genesis_hash = :genesis_hash, block_number = :block_number
    """,
        {
            "address": address,
            "event": event,
            "genesis_hash": genesis_hash,
            "block_number": block_number,
        },
    )
