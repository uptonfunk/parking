from asyncio import AbstractEventLoop
import json
import pytest
import tornado.web
import testing.postgresql
from parking.backend.sensor_server.rest_server import (IndividualLotDeleteHandler, IndividualLotAvailableHandler,
                                                       IndividualLotPriceHandler, ParkingLotsCreationHandler)
from parking.backend.db.dbaccess import DbAccess
from parking.shared.rest_models import ParkingLot, ParkingLotCreationResponse, ParkingLotPriceMessage
from parking.shared.util import serialize_model
from parking.shared.location import Location


HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}


@pytest.fixture(scope="module")
def postgresql():
    postgresql_con = testing.postgresql.Postgresql()
    yield postgresql_con
    postgresql_con.stop()


@pytest.fixture
def app(postgresql):
    loop: AbstractEventLoop = tornado.ioloop.IOLoop.current().asyncio_loop
    dba: DbAccess = tornado.ioloop.IOLoop.current().run_sync(
        lambda: DbAccess.create(postgresql.url(), loop=loop, init_tables=True, reset_tables=True))
    application = tornado.web.Application([(r'/spaces', ParkingLotsCreationHandler, {'dba': dba}),
                                           (r'/spaces/([0-9])+', IndividualLotDeleteHandler, {'dba': dba}),
                                           (r'/spaces/([0-9])+/available', IndividualLotAvailableHandler, {'dba': dba}),
                                           (r'/spaces/([0-9])+/price', IndividualLotPriceHandler, {'dba': dba})])
    return application


@pytest.fixture
def io_loop():
    return tornado.ioloop.IOLoop.current()


@pytest.mark.gen_test(run_sync=False)
async def test_create_parking_lot(http_client, base_url):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    response = await http_client.fetch(base_url + '/spaces', method='POST', headers=HEADERS, body=serialize_model(lot))
    assert ParkingLotCreationResponse(**json.loads(response.body)).id == 1


@pytest.mark.gen_test(run_sync=False)
async def test_delete_parking_lot(http_client, base_url):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    response = await http_client.fetch(base_url + '/spaces', method='POST', headers=HEADERS, body=serialize_model(lot))
    assert ParkingLotCreationResponse(**json.loads(response.body)).id == 1

    # TODO: Check that the ParkingLot has actually been deleted using a GET # request.
    response = await http_client.fetch(base_url + '/spaces/1', method='DELETE')
    assert response.code == 200


@pytest.mark.gen_test(run_sync=False)
async def test_invalid_content_type(http_client, base_url):
    response = await http_client.fetch(base_url + '/spaces', method='POST', body='not json', raise_error=False)
    assert response.code == 400


@pytest.mark.gen_test(run_sync=False)
async def test_update_parking_lot_price(http_client, base_url):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    response = await http_client.fetch(base_url + '/spaces', method='POST', headers=HEADERS, body=serialize_model(lot))
    assert ParkingLotCreationResponse(**json.loads(response.body)).id == 1

    # TODO: Check that the ParkingLot price has actually been updated using a GET # request.
    body = serialize_model(ParkingLotPriceMessage(2.0))
    response = await http_client.fetch(base_url + '/spaces/1/price', method='POST', headers=HEADERS, body=body)
    assert response.code == 200


@pytest.mark.gen_test(run_sync=False)
async def test_delete_invalid_parking_lot_id(http_client, base_url):
    response = await http_client.fetch(base_url + '/spaces/1234', method='DELETE', raise_error=False)
    assert response.code == 404
