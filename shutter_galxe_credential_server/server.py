import logging
from flask import Blueprint, jsonify, g
from shutter_galxe_credential_server import db
from shutter_galxe_credential_server.credentials import Credential
import eth_utils


logger = logging.getLogger(__name__)


def get_db_conn():
    if "db_conn" not in g:
        g.db_conn = db.connect()
    return g.db_conn


def close_db_conn(e=None):
    db_conn = g.pop("db_conn", None)
    if db_conn is not None:
        db_conn.close()


server = Blueprint("server", __name__)
server.teardown_request(close_db_conn)


@server.route("/credentials/<credential>/<address>", methods=["GET"])
def get_credential(credential, address):
    credential = credential.lower()
    if credential not in Credential:
        logger.warning(f"received request for unknown credential {credential}")
        return jsonify({"error": "unknown credential"}), 404

    if not eth_utils.is_hex_address(address):
        logger.warning(f"received request for invalid address {address}")
        return jsonify({"error": "invalid address"}), 400
    normalized_address = eth_utils.to_checksum_address(address)

    logger.debug(
        f"handling request for credential {credential} for address {normalized_address}",
    )

    awarded = db.has_credential(get_db_conn(), normalized_address, credential)
    return jsonify(
        {"address": normalized_address, "credential": credential, "awarded": awarded}
    )
