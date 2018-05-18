import attr
from parking.shared.location import Location
from parking.shared.util import ensure, validate_non_neg, validate_pos


@attr.s
class ParkingLot:
    capacity: int = attr.ib(validator=[attr.validators.instance_of(int), validate_pos])
    name: str = attr.ib(validator=attr.validators.instance_of(str))
    price: float = attr.ib(validator=[attr.validators.instance_of(float), validate_non_neg])
    location: Location = attr.ib(converter=ensure(Location), validator=attr.validators.instance_of(Location))
    id: int = attr.ib(validator=attr.validators.instance_of(int), default=0)


@attr.s
class ParkingLotCreationResponse:
    id: int = attr.ib(validator=[attr.validators.instance_of(int), validate_non_neg], default=0)
    errors: list = attr.ib(validator=attr.validators.instance_of(list), factory=list)


@attr.s
class SpaceAvailableMessage:
    available: int = attr.ib(validator=[attr.validators.instance_of(int), validate_non_neg])


@attr.s
class SpacePriceMessage:
    price: float = attr.ib(validator=[attr.validators.instance_of(float), validate_non_neg])
