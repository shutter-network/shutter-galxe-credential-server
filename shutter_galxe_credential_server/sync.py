import logging
import eth_utils
import os
from web3 import Web3
import time
import datetime

from shutter_galxe_credential_server import abis, db, credentials

ERPC_ADDRESS = os.getenv("ERPC_ADDRESS")

MAX_SYNC_BLOCK_RANGE = 1000
BLOCK_POLL_INTERVAL = 1
LAST_ERPC_SYNC = 0

logger = logging.getLogger(__name__)


def get_address(name):
    env_value = os.getenv(name)
    if env_value is None:
        raise ValueError(f"{name} environment variable is not set")
    if not eth_utils.is_hex_address(env_value):
        raise ValueError(
            f"{name} environment variable with value '{env_value}' is not a valid address"
        )
    return eth_utils.to_checksum_address(env_value)


w3 = Web3()  # uses provider from env var WEB3_PROVIDER_URI
sequencer = w3.eth.contract(
    address=get_address("SEQUENCER_ADDRESS"), abi=abis.sequencer
)


event_processors = [
    (
        sequencer.events.TransactionSubmitted,
        credentials.process_transaction_submitted_event,
    )
]


def sync_events():
    logger.debug("starting event sync")
    while True:
        try:
            sync_events_once()
        except Exception:
            logger.exception("error during event sync")
        time.sleep(BLOCK_POLL_INTERVAL)


def sync_events_once():
    current_block = w3.eth.block_number
    genesis_hash = w3.eth.get_block(0).hash.hex()
    with db.connect() as conn:
        sync_status = db.get_sync_status(conn)

    for event, process in event_processors:
        sync_genesis, sync_block = sync_status.get(
            (event.address, event.event_name), (None, -1)
        )
        if sync_genesis is not None and sync_genesis != genesis_hash:
            logger.warning(
                f"restarting {event.event_name} sync from 0 due to chain reset"
            )
        sync_range = get_sync_range(
            genesis_hash, sync_genesis, sync_block, current_block
        )
        for fetch_from_block in range(
            sync_range[0], sync_range[1] + 1, MAX_SYNC_BLOCK_RANGE
        ):
            fetch_to_block = min(
                fetch_from_block + MAX_SYNC_BLOCK_RANGE - 1, current_block
            )
            events = fetch_events(event, fetch_from_block, fetch_to_block)
            with db.connect() as conn:
                for ev in events:
                    process(conn, ev, ERPC_ADDRESS)
                db.set_sync_status(
                    conn, event.address, event.event_name, genesis_hash, fetch_to_block
                )
                conn.commit()


def get_sync_range(genesis_hash, sync_genesis, sync_block, current_block):
    if sync_genesis != genesis_hash:
        return (0, current_block)
    return (sync_block + 1, current_block)


def fetch_events(event, from_block, to_block):
    logger.debug(
        f"fetching {event.event_name} events from block {from_block} to {to_block}"
    )
    if from_block >= to_block:
        return []

    events = event.get_logs(
        fromBlock=from_block,
        toBlock=to_block,
    )
    return events

def sync_erpc():
    logger.debug("starting erpc db sync")
    with db.connect() as conn:
        global LAST_ERPC_SYNC
        LAST_ERPC_SYNC = db.get_erpc_sync_status(conn)
    while True:
        try:
            sync_erpc_db_once()
        except Exception:
            logger.exception("error during ERPC sync")
        time.sleep(BLOCK_POLL_INTERVAL)



def sync_erpc_db_once():
    with db.connect() as conn:
        global LAST_ERPC_SYNC
        if LAST_ERPC_SYNC == None:
            LAST_ERPC_SYNC = 0
            logger.debug(f"fetching erpc updates from start")
        else:
            logger.debug(f"fetching erpc updates after {datetime.datetime.fromtimestamp(LAST_ERPC_SYNC)}")
        newUpdates = db.get_erpc_updates(conn, LAST_ERPC_SYNC)
        if len(newUpdates) > 0:
            logger.debug(f"found {len(newUpdates)} new updates from erpc | updating credentials")
            credentials.process_new_erpc_updates(conn, newUpdates)
            last_submission_time = max(row[1] for row in newUpdates)
            LAST_ERPC_SYNC = last_submission_time
            db.update_erpc_sync_status(conn, last_submission_time)

