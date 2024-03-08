import enum
import logging
from shutter_galxe_credential_server import db

logger = logging.getLogger(__name__)


class Credential(enum.StrEnum):
    SHOP_ENCRYPTED_TX_SENT = "shop_encrypted_tx_sent"


def process_encrypted_transaction_submitted_event(conn, event):
    sender = event.args.sender
    logger.info(
        f"rewarding SHOP_ENCRYPTED_TX_SENT credential to sender {sender} "
        f"for tx {event.transactionHash.hex()} "
        f"in block {event.blockNumber}"
    )
    db.award_credential(conn, sender, Credential.SHOP_ENCRYPTED_TX_SENT)
