import json
from tornado import web
from parking.shared.rest_models import (ParkingLot, ParkingLotCreationResponse, ParkingLotAvailableMessage,
                                        ParkingLotPriceMessage)
from parking.shared.util import serialize_model
from parking.backend.db.dbaccess import DbAccess


class ParkingLotHandlerBase(web.RequestHandler):
    def initialize(self, dba: DbAccess) -> None:
        self.dba = dba

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)
        if status_code == 400 and 'exc_info' in kwargs:
            payload = {'error': str(kwargs['exc_info'][1])}
            self.finish(json.dumps(payload))
        elif status_code == 500:
            self.finish(json.dumps({'error': 'HTTPinternal server error'}))
        else:
            super.write_error(status_code, kwargs)

    def prepare(self):
        if self.request.headers.get('Content-Type', '').startswith('application/json'):
            self.json_args = json.loads(self.request.body)
        else:
            raise web.HTTPError(400, 'Invalid content type')

    @staticmethod
    def load_from_json_data(cls: object, json_data: dict, err_msg: str) -> object:
        try:
            return cls(**json_data)
        # Display validation errors
        except ValueError as err:
            raise web.HTTPError(400, str(err))
        # Fall back to provided error message as TypeErrors are ugly
        except TypeError as err:
            raise web.HTTPError(400, err_msg)


class ParkingLotsCreationHandler(ParkingLotHandlerBase):
    async def post(self):
        lot = self.load_from_json_data(ParkingLot, self.json_args, 'Invalid parking lot data')
        pid = await self.dba.insert_parking_lot(lot)
        self.write(serialize_model(ParkingLotCreationResponse(id=pid)))


class IndividualLotPriceHandler(ParkingLotHandlerBase):
    async def post(self, lot_id: str):
        msg = self.load_from_json_data(ParkingLotPriceMessage, self.json_args, 'Invalid price data')
        park_id = await self.dba.update_parking_lot_price(int(lot_id), msg.price)
        if not park_id:
            raise web.HTTPError(404, 'Unknown lot ID')


class IndividualLotAvailableHandler(ParkingLotHandlerBase):
    async def post(self, lot_id: str):
        msg = self.load_from_json_data(ParkingLotAvailableMessage, self.json_args, 'Invalid availability data')
        park_id = await self.dba.update_parking_lot_availability(int(lot_id), msg.available)
        if not park_id:
            raise web.HTTPError(404, 'Unknown lot ID')


class IndividualLotDeleteHandler(web.RequestHandler):
    def initialize(self, dba: DbAccess) -> None:
        self.dba = dba

    async def delete(self, lot_id: str):
        lot_id = int(lot_id)
        park_id = await self.dba.delete_parking_lot(lot_id)
        if not park_id:
            raise web.HTTPError(404, 'Unknown lot ID')
