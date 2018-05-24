import pytest
from parking.shared.util import serialize_model
from parking.shared.rest_models import ParkingLotAvailableMessage


def test_serialize_model():
    json_str = '{"available": 10}'
    sam = ParkingLotAvailableMessage(10)
    assert serialize_model(sam) == json_str


def test_serialize_model_raises_error():
    with pytest.raises(ValueError):
        serialize_model(None)
