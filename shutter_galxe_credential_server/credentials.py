import enum
import logging
from shutter_galxe_credential_server import db

logger = logging.getLogger(__name__)


class Credential(enum.StrEnum):
    GNOSH_TRANSACTION_SUBMITTED = "gnosh_transaction_submitted"


def process_transaction_submitted_event(conn, event, erpc_address):
    sender = event.args.sender
    logger.info(
        f"rewarding GNOSH_TRANSACTION_SUBMITTED credential to sender {sender} "
        f"for tx {event.transactionHash.hex()} "
        f"in block {event.blockNumber}"
    )
    if sender != erpc_address:
        db.award_credential(conn, sender, Credential.GNOSH_TRANSACTION_SUBMITTED)

def process_new_erpc_updates(conn, updates):
    addresses = [row[0] for row in updates]
    credentials_and_addresses = [(Credential.GNOSH_TRANSACTION_SUBMITTED, address) for address in addresses]
    db.award_credential_multiple(conn, credentials_and_addresses)

