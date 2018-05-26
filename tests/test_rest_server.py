from asyncio import AbstractEventLoop
import pytest
import tornado.web
import testing.postgresql
from parking.backend.sensor_server.rest_server import (IndividualLotDeleteHandler, IndividualLotAvailableHandler,
                                                       IndividualLotPriceHandler, ParkingLotsCreationHandler)
from parking.backend.db.dbaccess import DbAccess
from parking.shared.rest_models import ParkingLot
from parking.shared.location import Location

from parking.shared.clients import ParkingLotRest


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


@pytest.fixture
def plr(base_url, http_client):
    return ParkingLotRest(base_url, http_client)


@pytest.mark.gen_test(run_sync=False)
async def test_create_parking_lot_new(plr):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    lot_id = await plr.create_lot(lot)
    assert lot_id == 1


@pytest.mark.gen_test(run_sync=False)
async def test_delete_parking_lot(plr):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    lot_id = await plr.create_lot(lot)
    assert lot_id == 1

    # TODO: Check that the ParkingLot has actually been deleted using a GET # request.
    await plr.delete_lot(lot_id)


@pytest.mark.gen_test(run_sync=False)
async def test_invalid_content_type(http_client, base_url):
    with pytest.raises(tornado.httpclient.HTTPError) as http_error:
        await http_client.fetch(base_url + '/spaces', method='POST', body='not json')
    assert http_error.value.code == 400


@pytest.mark.gen_test(run_sync=False)
async def test_update_parking_lot_price(plr):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    lot_id = await plr.create_lot(lot)
    assert lot_id == 1

    # TODO: Check that the ParkingLot price has actually been updated using a GET # request.
    await plr.update_price(lot_id, 2.0)


@pytest.mark.gen_test(run_sync=False)
async def test_update_parking_lot_availability(plr):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    lot_id = await plr.create_lot(lot)
    assert lot_id == 1

    # TODO: Check that the ParkingLot availability has actually been updated using a GET # request.
    await plr.update_available(lot_id, 2)


@pytest.mark.gen_test(run_sync=False)
async def test_update_invalid_parking_lot_availability(plr):
    with pytest.raises(tornado.httpclient.HTTPError) as http_error:
        await plr.update_available(1234, 2)
    assert http_error.value.code == 404


@pytest.mark.gen_test(run_sync=False)
async def test_update_invalid_parking_lot_price(plr):
    with pytest.raises(tornado.httpclient.HTTPError) as http_error:
        await plr.update_price(1234, 2.0)
    assert http_error.value.code == 404


@pytest.mark.gen_test(run_sync=False)
async def test_delete_invalid_parking_lot_id(plr):
    with pytest.raises(tornado.httpclient.HTTPError) as http_error:
        await plr.delete_lot(1234)
    assert http_error.value.code == 404
