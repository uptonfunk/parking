import json
import attr


def ensure(t, allow_none=False):
    '''Returns a function that ensures a result of type t
    e.g. ensure(Location)(Location(1,2)) == ensure(Location)({'latitude': 1, 'longitude': 2})

    Useful for nested attrs that you want to load from JSON.
    '''
    def check(t2):
        if isinstance(t2, t):
            return t2
        elif isinstance(t2, dict):
            return t(**t2)
        elif allow_none and t2 is None:
            return None
        else:
            raise TypeError('Expected mapping or {}'.format(t))
    return check


def serialize_model(model: object) -> str:
    '''Handy function to dump an attr object to a JSON encoded string'''
    return json.dumps(attr.asdict(model))


def validate_pos(cls, attribute, value: float) -> None:
    if value < 1:
        raise ValueError('{} must be positive'.format(attribute.name))


def validate_non_neg(cls, attribute, value: float) -> None:
    if value < 0:
        raise ValueError('{} must be non-negative'.format(attribute.name))


def enforce_type(cls, attribute, value) -> None:
    if not isinstance(value, attribute.type):
        raise TypeError('{} must be of type {}'
                        .format(attribute.name, str(attribute.type)))
