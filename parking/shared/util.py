from typing import Union


def ensure(t):
    '''Returns a function that ensures a result of type t
    e.g. ensure(Location)(Location(1,2)) == ensure(Location)({'latitude': 1, 'longitude': 2})

    Useful for nested attrs that you want to load from JSON.
    '''
    def check(t2):
        if isinstance(t2, t):
            return t2
        elif isinstance(t2, dict):
            return t(**t2)
        else:
            raise TypeError('Expected mapping or {}'.format(t))
    return check


def validate_pos(cls, attribute, value: Union[int, float]) -> None:
    if value < 1:
        raise ValueError('{} must be positive'.format(attribute.name))


def validate_non_neg(cls, attribute, value: Union[int, float]) -> None:
    if value < 0:
        raise ValueError('{} must be non-negative'.format(attribute.name))
