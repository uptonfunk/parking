import logging
from typing import Dict, List

import attr
from tornado import websocket

import parking.shared.ws_models as models
from parking.shared.location import Location

logger = logging.getLogger('backend')


class UserWSHandler(websocket.WebSocketHandler):
    """The WebSocket handler. Handles user ws connections."""
    def check_origin(self, origin) -> bool:
        return True

    def initialize(self, user_sessions: 'UserSessions') -> None:
        self.usessions = user_sessions

    def open(self, user_id: str) -> None:
        self.user_id = user_id
        logger.info("WebSocket opened for user_id = '{}'".format(self.user_id))
        self.usessions.add_user(user_id, self)

    def on_message(self, message: str) -> None:
        logger.debug("Received message from user_id = '{}' : '{}'".format(self.user_id, message))
        msg = models.deserialize_ws_message(message)

        if isinstance(msg, models.LocationUpdateMessage):
            logger.debug("Received location update from user_id = '{}'".format(self.user_id))
            self.usessions.update_user_location(self.user_id, msg.location)
        elif isinstance(msg, models.ParkingRequestMessage):
            logger.debug("Received parking request from user_id = '{}'".format(self.user_id))
        elif isinstance(msg, models.ParkingAcceptanceMessage):
            logger.debug("Received parking acceptance from user_id = '{}'".format(self.user_id))
        elif isinstance(msg, models.ParkingRejectionMessage):
            logger.debug("Received parking rejection from user_id = '{}'".format(self.user_id))
            self.usessions.add_user_rejection(self.user_id, msg.id)
        elif isinstance(msg, models.ParkingCancellationMessage):
            logger.info("Parking cancelled for user_id = '{}'".format(self.user_id))
            self.close()

    def on_close(self) -> None:
        self.usessions.remove_user(self.user_id)
        logger.info("WebSocket closed for user_id = {}".format(self.user_id))


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
