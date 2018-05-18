import json
import pytest
from parking.shared.location import Location
from parking.shared.ws_models import deserialize_ws_message, LocationUpdateMessage, WebSocketMessageType


def test_deserialize_valid_ws_msg():
    data = json.dumps({'_type': 1, 'location': {'latitude': 0.0, 'longitude': 1.0}})
    msg = deserialize_ws_message(data)
    assert isinstance(msg, LocationUpdateMessage)


def test_deserialize_invalid_type_ws_msg():
    data = json.dumps({'_type': 9999, 'location': {'latitude': 0.0, 'longitude': 1.0}})
    with pytest.raises(ValueError):
        deserialize_ws_message(data)


def test_message_type():
    msg = LocationUpdateMessage(Location(0.0, 1.0))
    assert msg._type == WebSocketMessageType.LOCATION_UPDATE
