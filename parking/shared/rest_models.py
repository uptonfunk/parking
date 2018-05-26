import attr
from parking.shared.location import Location
from parking.shared.util import ensure, validate_non_neg, validate_pos, enforce_type


@attr.s
class ParkingLot:
    capacity: int = attr.ib(validator=[enforce_type, validate_pos])
    name: str = attr.ib(validator=enforce_type)
    price: float = attr.ib(converter=float, validator=validate_non_neg)
    location: Location = attr.ib(converter=ensure(Location), validator=attr.validators.instance_of(Location))
    id: int = attr.ib(validator=enforce_type, default=0)


@attr.s
class ParkingLotCreationResponse:
    id: int = attr.ib(validator=[enforce_type, validate_non_neg], default=0)


@attr.s
class ParkingLotAvailableMessage:
    available: int = attr.ib(validator=[enforce_type, validate_non_neg])


@attr.s
class ParkingLotPriceMessage:
    price: float = attr.ib(validator=[enforce_type, validate_non_neg])
