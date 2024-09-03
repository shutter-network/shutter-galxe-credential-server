import logging
from flask import Flask
from flask_cors import CORS

from shutter_galxe_credential_server.server import server
from shutter_galxe_credential_server import db, sync
import threading

ACCESS_CONTROL_ALLOW_ORIGINS = ["https://galxe.com", "https://dashboard.galxe.com"]

logger = logging.getLogger(__name__)


def create_app():
    logger.info("starting credential server")
    db.create()

    sync_thread = threading.Thread(target=sync.sync_events, daemon=True)
    sync_thread.start()

    erpc_thread = threading.Thread(target=sync.sync_erpc, daemon=True)
    erpc_thread.start()
    
    app = Flask(__name__)
    app.register_blueprint(server)
    CORS(app, origins=ACCESS_CONTROL_ALLOW_ORIGINS)

    return app


def main():
    app = create_app()
    app.run(debug=False)
