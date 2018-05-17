import attr


@attr.s
class Location:
    latitude: float = attr.ib(validator=attr.validators.instance_of(float))
    longitude: float = attr.ib(validator=attr.validators.instance_of(float))
