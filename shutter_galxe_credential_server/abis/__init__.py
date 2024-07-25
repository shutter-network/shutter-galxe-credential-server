import json
import importlib.resources

with importlib.resources.open_text(
    "shutter_galxe_credential_server.abis", "Sequencer.json"
) as file:
    data = json.load(file)
    sequencer = data["abi"]
