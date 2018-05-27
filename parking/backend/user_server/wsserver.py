import logging
from typing import Optional

from tornado import websocket, ioloop

import parking.shared.ws_models as models
from parking.backend.engine.alloc_engine import AllocationEngine
from parking.shared.util import serialize_model
from parking.shared.ws_models import ParkingLotAllocation, WebSocketErrorType, ErrorMessage

logger = logging.getLogger('backend')


class UserWSHandler(websocket.WebSocketHandler):
    """The WebSocket handler. Handles user ws connections."""
    def check_origin(self, origin) -> bool:
        return True

    def initialize(self, usessions: 'UserSessions', engine: AllocationEngine) -> None:
        self.usessions = usessions
        self.engine = engine

    def open(self, user_id: str) -> None:
        self.user_id = user_id
        logger.info("WebSocket opened for user_id = '{}'".format(self.user_id))
        self.usessions.add_user(user_id, self)

    async def on_message(self, message: str) -> None:
        logger.debug("Received message from user_id = '{}' : '{}'".format(self.user_id, message))

        try:
            msg = models.deserialize_ws_message(message)
        except (ValueError, TypeError) as e:
            self.write_as_json(ErrorMessage(WebSocketErrorType.INVALID_MESSAGE.value))
            logger.error(e)
        else:
            if isinstance(msg, models.LocationUpdateMessage):
                self.handle_location_update(msg)
            elif isinstance(msg, models.ParkingRequestMessage):
                await self.handle_parking_request(msg)
            elif isinstance(msg, models.ParkingAcceptanceMessage):
                await self.handle_parking_acceptance(msg)
            elif isinstance(msg, models.ParkingRejectionMessage):
                self.handle_parking_rejection(msg)
            elif isinstance(msg, models.ParkingCancellationMessage):
                self.handle_parking_cancellation(msg)
            else:
                logger.warning("Unimplemented message received from user_id = '{}'".format(self.user_id))
                self.write_as_json(ErrorMessage(WebSocketErrorType.NOT_IMPLEMENTED.value))

    def handle_location_update(self, message: models.LocationUpdateMessage) -> None:
        logger.debug("Received location update from user_id = '{}'".format(self.user_id))
        try:
            self.usessions.update_user_location(self.user_id, message.location)
        except KeyError:
            logger.error("user_id = '{}' not in the sessions dictionary.")
            self.write_as_json(ErrorMessage(WebSocketErrorType.CORRUPTED_SESSION.value))
            self.close(code=400, reason=WebSocketErrorType.CORRUPTED_SESSION.value.msg)

    async def handle_parking_request(self, message: models.ParkingRequestMessage) -> None:
        logger.debug("Received parking request from user_id = '{}'".format(self.user_id))
        parking_lot: Optional[ParkingLotAllocation] = await self.engine.handle_allocation_request(self.user_id, message)
        if parking_lot:
            response = models.ParkingAllocationMessage(lot=parking_lot)
        else:
            response = ErrorMessage(WebSocketErrorType.NO_AVAILABLE_PARKING_LOT.value)
        self.write_as_json(response)

    async def handle_parking_acceptance(self, message: models.ParkingAcceptanceMessage) -> None:
        logger.debug("Received parking acceptance from user_id = '{}'".format(self.user_id))
        success = await self.engine.commit_allocation(self.user_id, message.id)
        if success:
            response = models.ConfirmationMessage()
        else:
            response = ErrorMessage(WebSocketErrorType.ALLOCATION_COMMIT_FAIL.value)
        self.write_as_json(response)

    def handle_parking_rejection(self, message: models.ParkingRejectionMessage) -> None:
        logger.debug("Received parking rejection from user_id = '{}'".format(self.user_id))
        try:
            self.usessions.add_user_rejection(self.user_id, message.id)
        except KeyError:
            logger.error("user_id = '{}' not in the sessions dictionary.")
            self.write_as_json(ErrorMessage(WebSocketErrorType.CORRUPTED_SESSION.value))
            self.close(code=400, reason=WebSocketErrorType.CORRUPTED_SESSION.value.msg)
        else:
            self.write_as_json(models.ConfirmationMessage())

    def handle_parking_cancellation(self, message: models.ParkingCancellationMessage) -> None:
        logger.debug("Parking cancelled for user_id = '{}'. Reason = '{}'".format(self.user_id, message.reason))
        self.close()

    def handle_deallocation(self):
        logger.debug("Deallocation requested for user_id = '{}'".format(self.user_id))
        self.write_as_json(models.ParkingDeallocationMessage())

    def on_close(self) -> None:
        ioloop.IOLoop.current().spawn_callback(self.engine.delete_allocation, self.user_id)
        self.usessions.remove_user(self.user_id)
        logger.info("WebSocket closed for user_id = {}".format(self.user_id))

    def write_as_json(self, model: object) -> None:
        self.write_message(serialize_model(model))
