import base64
import pickle
from typing import Any


def serialize(obj: Any) -> str:
    return base64.b64encode(pickle.dumps(obj)).decode('utf-8')


def deserialize(text: str) -> Any:
    return pickle.loads(base64.b64decode(text.encode('utf-8')))
