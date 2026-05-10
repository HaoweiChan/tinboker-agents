import json
from typing import Any

try:
    from toon import dumps, loads
except ImportError:
    dumps = None
    loads = None


def json_to_toon(data: dict[str, Any] | list[Any]) -> str:
    if dumps is None:
        raise ImportError("python-toon package is required. Install with: pip install python-toon")
    return dumps(data)


def toon_to_json(toon_str: str) -> dict[str, Any] | list[Any]:
    if loads is None:
        raise ImportError("python-toon package is required. Install with: pip install python-toon")
    return loads(toon_str)


def model_to_toon(data: dict[str, Any]) -> str:
    json_str = json.dumps(data, default=str)
    json_data = json.loads(json_str)
    return json_to_toon(json_data)


def toon_to_model(toon_str: str) -> dict[str, Any]:
    return toon_to_json(toon_str)

