from typing import Dict, List

import attr

from parking.backend.user_server.wsserver import UserWSHandler
from parking.shared.location import Location


@attr.s
class User(object):
    """Object to represent a connected user."""
    user_id: str = attr.ib()
    session: UserWSHandler = attr.ib()
    location: Location = attr.ib(default=None)
    rejections: List[int] = attr.ib(default=attr.Factory(list), init=False)


class UserSessions(object):
    """Class to hold references to open ws connections"""
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}

    def add_user(self, user_id: str, session: UserWSHandler) -> None:
        self.users[user_id] = User(user_id, session)

    def remove_user(self, user_id: str) -> User:
        return self.users.pop(user_id)

    def get_user(self, user_id: str) -> User:
        return self.users[user_id]

    def update_user_location(self, user_id: str, location: Location) -> None:
        self.get_user(user_id).location = location

    def add_user_rejection(self, user_id: str, parking_id: int) -> None:
        self.get_user(user_id).rejections.append(parking_id)

    def deallocate(self, user_id: str) -> None:
        self.get_user(user_id).session.handle_deallocation()
