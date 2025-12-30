import base64
import json

def encode_data(payload: dict) -> str:
    return base64.b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("utf-8")
