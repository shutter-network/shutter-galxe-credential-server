import json
import importlib.resources

with importlib.resources.open_text(
    "shutter_galxe_credential_server.abis", "Inbox.json"
) as file:
    data = json.load(file)
    inbox = data["abi"]
