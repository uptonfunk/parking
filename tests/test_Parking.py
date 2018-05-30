import pytest
from tornado import httpclient

from simulation.simulation import ParkingLot
import json

# TODO add async http client

@pytest.fixture
def client():
    return httpclient.AsyncHTTPClient()

# def test_AddNew():
#     lot = ParkingLot(1.0, 0.5, 500, "my_parking_lot", 1.5, 500, client)
#     assert lot.data_to_send == json.dumps({"data": {"capacity": 500, "location": {"latitude": 1.0,
#                                           "longitude": 0.5},
#                                            "name": "my_parking_lot", "price": 1.5}
#                                            })


def test_AddZeroSpaces():
    with pytest.raises(ValueError):
        ParkingLot(1.0, 0.5, 0, "my_parking_lot", 1.5, 0, client)


def test_AddNegativeSpaces():
    with pytest.raises(ValueError):
        ParkingLot(1.0, 0.5, -10, "my_parking_lot", 1.5, -10, client)


def test_AddDecimalSpaces():
    with pytest.raises(TypeError):
        ParkingLot(1.0, 0.5, 3.5, "my_parking_lot", 1.5, 3.5, client)


def test_AddBigAvailability():
    with pytest.raises(ValueError):
        ParkingLot(1.0, 0.5, 10, "my_parking_lot", 1.5, 20, client)


def test_AddTwoSpaces():
    lot = ParkingLot(1.0, 0.5, 500, "my_parking_lot", 1.5, 500, client)
    print(lot)
    with pytest.raises(RuntimeError):
        ParkingLot(1.0, 0.5, 10, "my_parking_lot", 1.5, 10, client)


def test_ChangingAvailability():
    lot = ParkingLot(1.0, 0.5, 500, "my_parking_lot", 1.5, 500, client)
    lot.change_availability(250)
    assert lot.available == 250
