import attr
import pytest
from parking.shared.location import Location
from parking.shared.rest_models import (ParkingLot, ParkingLotCreationResponse,
                                        SpaceAvailableMessage, SpacePriceMessage)

loc = Location(0.0, 1.0)


def test_correct_parkinglot_cons():
    assert isinstance(ParkingLot(100, 'test_name', 0.0, loc), ParkingLot)


def test_missing_parkinglot_arg():
    with pytest.raises(TypeError):
        ParkingLot(100, 'test_name', 0)


def test_incorrect_parkinglot_arg_type():
    with pytest.raises(TypeError):
        ParkingLot(100, 0, 0.0, loc)


def test_incorrect_parkinglot_arg():
    with pytest.raises(ValueError):
        ParkingLot(-100, 'test_name', 0.0, loc)


def test_zero_capacity_parkinglot():
    with pytest.raises(ValueError):
        ParkingLot(0, 'test_name', 0.0, loc)


def test_parkinglot_deser_ser():
    data = {'name': 'test_name', 'capacity': 100, 'price': 0.0,
            'location': {'latitude': 0.0, 'longitude': 1.0}, 'id': 2}
    p = ParkingLot(**data)
    assert attr.asdict(p) == data


def test_parkinglot_creation_resp_id():
    pcr = ParkingLotCreationResponse(5)
    assert isinstance(pcr, ParkingLotCreationResponse)
    assert not pcr.errors
    assert pcr.id == 5


def test_parkinglot_creation_resp_error():
    pcr = ParkingLotCreationResponse(errors=['test'])
    assert isinstance(pcr, ParkingLotCreationResponse)
    assert not pcr.id
    assert pcr.errors == ['test']


def test_parkinglot_creation_resp_neg_id():
    with pytest.raises(ValueError):
        ParkingLotCreationResponse(-5)


def test_space_available_neg():
    with pytest.raises(ValueError):
        SpaceAvailableMessage(-100)


def test_price_available_neg():
    with pytest.raises(ValueError):
        SpacePriceMessage(-100.0)
