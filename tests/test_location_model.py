import pytest
from parking.shared.location import Location


def test_location_cons():
    loc = Location(0.0, 0.0)
    assert isinstance(loc, Location)


def test_location_missing_arg():
    with pytest.raises(TypeError):
        Location(0.0)


def test_location_incorrect_arg_type():
    with pytest.raises(TypeError):
        Location(0.0, 'a')
