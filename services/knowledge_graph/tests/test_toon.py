import json

import pytest

from utils.toon import json_to_toon, model_to_toon, toon_to_json, toon_to_model


def test_json_to_toon():
    data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
    try:
        toon_str = json_to_toon(data)
        assert isinstance(toon_str, str)
        assert len(toon_str) > 0
    except ImportError:
        pytest.skip("python-toon not installed")


def test_toon_to_json():
    data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
    try:
        toon_str = json_to_toon(data)
        result = toon_to_json(toon_str)
        assert result == data
    except ImportError:
        pytest.skip("python-toon not installed")


def test_model_to_toon():
    data = {"id": "test", "type": "Person", "props": {"name": "John"}}
    try:
        toon_str = model_to_toon(data)
        assert isinstance(toon_str, str)
    except ImportError:
        pytest.skip("python-toon not installed")

