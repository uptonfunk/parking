from asyncio import sleep

import pytest
import tornado
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketClientConnection

from parking.backend.db.dbaccess import DbAccess
from parking.backend.engine.alloc_engine import AllocationEngine
from parking.backend.user_server.session import UserSessions
from parking.backend.user_server.wsserver import UserWSHandler
from parking.shared.location import Location
from parking.shared.util import serialize_model
from parking.shared.ws_models import deserialize_ws_message, WebSocketErrorType, LocationUpdateMessage, \
    ParkingRequestMessage, ParkingAcceptanceMessage, ConfirmationMessage, ParkingRejectionMessage, \
    ParkingCancellationMessage, ParkingLotAllocation, ParkingAllocationMessage


async def return_async_value(val):
    return val


@pytest.fixture
def user_id():
    return "donald"


@pytest.fixture
def dbaccess(mocker):
    dba = DbAccess()
    mocker.patch.object(dba, "delete_allocation")
    return dba


@pytest.fixture
def usessions():
    return UserSessions()


@pytest.fixture
def engine(dbaccess, usessions):
    return AllocationEngine(dbaccess, usessions)


@pytest.fixture
def app(usessions, engine):
    application = tornado.web.Application([(r"/ws/(.*)", UserWSHandler, {'usessions': usessions, 'engine': engine})])
    return application


@pytest.fixture
def ws_url(http_server, http_port):
    return "ws://localhost:{}/ws/".format(http_port)


@pytest.mark.gen_test(run_sync=False)
async def test_open_close_session(ws_url, mocker, dbaccess, usessions, user_id):
    mocker.spy(usessions, 'add_user')
    mocker.spy(usessions, 'remove_user')
    dbaccess.delete_allocation.return_value = return_async_value(None)

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    usessions.add_user.assert_called_once_with(user_id, mocker.ANY)

    conn.close()
    assert await conn.read_message() is None

    usessions.remove_user.assert_called_once_with(user_id)
    dbaccess.delete_allocation.assert_called_once_with(user_id)


@pytest.mark.gen_test(run_sync=False)
async def test_another_connection_open(ws_url):
    await tornado.websocket.websocket_connect(ws_url)
    conn2: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url)
    msg = deserialize_ws_message(await conn2.read_message())
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.ANOTHER_CONNECTION_OPEN

    # confirm that second connection was closed
    assert await conn2.read_message() is None


@pytest.mark.gen_test(run_sync=False)
async def test_db_error(ws_url, user_id, mocker, usessions):
    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    session: UserWSHandler = usessions.get_user(user_id).session

    from asyncpg import PostgresError
    mocker.patch.object(session, '_on_message', side_effect=PostgresError.new({}))
    await conn.write_message("test")

    msg = deserialize_ws_message(await conn.read_message())
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.DATABASE


@pytest.mark.gen_test(run_sync=False)
async def test_internal_error(ws_url, user_id, mocker, usessions):
    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    session: UserWSHandler = usessions.get_user(user_id).session

    mocker.patch.object(session, '_on_message', side_effect=NameError())
    await conn.write_message("test")

    msg = deserialize_ws_message(await conn.read_message())
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.INTERNAL


@pytest.mark.gen_test(run_sync=False)
async def test_invalid_message(ws_url, user_id):
    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    await conn.write_message("test")
    msg = deserialize_ws_message(await conn.read_message())
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.INVALID_MESSAGE


@pytest.mark.gen_test(run_sync=False)
async def test_location_update_message(ws_url, user_id, mocker, usessions):
    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)

    mocker.spy(usessions, 'update_user_location')

    location = Location(0.0, 1.0)
    await conn.write_message(serialize_model(LocationUpdateMessage(location)))
    await sleep(0.01)
    usessions.update_user_location.assert_called_once_with(user_id, location)


@pytest.mark.gen_test(run_sync=False)
async def test_parking_request_message(ws_url, user_id, mocker, engine):
    user_location = Location(0.0, 1.0)
    lot_location = Location(0.001, 1.0)
    lot_allocation = ParkingLotAllocation(100, "test_lot", 0, lot_location, 1, distance=50.0, availability=20)
    parking_request = ParkingRequestMessage(user_location)

    mocker.patch.object(engine, 'handle_allocation_request')
    engine.handle_allocation_request.return_value = return_async_value(lot_allocation)

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    await conn.write_message(serialize_model(parking_request))
    msg = deserialize_ws_message(await conn.read_message())

    engine.handle_allocation_request.assert_called_once_with(user_id, parking_request)
    assert isinstance(msg, ParkingAllocationMessage)
    assert msg.lot == lot_allocation


@pytest.mark.gen_test(run_sync=False)
async def test_parking_request_message_no_parking_lot(ws_url, user_id, mocker, engine):
    user_location = Location(0.0, 1.0)
    parking_request = ParkingRequestMessage(user_location)

    mocker.patch.object(engine, 'handle_allocation_request')
    engine.handle_allocation_request.return_value = return_async_value(None)

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    await conn.write_message(serialize_model(parking_request))
    msg = deserialize_ws_message(await conn.read_message())

    engine.handle_allocation_request.assert_called_once_with(user_id, parking_request)
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.NO_AVAILABLE_PARKING_LOT


@pytest.mark.gen_test(run_sync=False)
async def test_parking_acceptance_message_happy_case(ws_url, user_id, mocker, dbaccess, engine):
    lot_id = 7

    mocker.patch.object(dbaccess, "allocate_parking_lot")
    dbaccess.allocate_parking_lot.return_value = return_async_value(True)
    mocker.spy(engine, "commit_allocation")

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)

    await conn.write_message(serialize_model(ParkingAcceptanceMessage(lot_id)))
    msg = deserialize_ws_message(await conn.read_message())

    engine.commit_allocation.assert_called_once_with(user_id, lot_id)
    assert isinstance(msg, ConfirmationMessage)


@pytest.mark.gen_test(run_sync=False)
async def test_parking_acceptance_message_failed_commit(ws_url, user_id, mocker, dbaccess, engine):
    lot_id = 7

    mocker.patch.object(dbaccess, "allocate_parking_lot")
    dbaccess.allocate_parking_lot.return_value = return_async_value(False)
    mocker.spy(engine, "commit_allocation")

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)

    await conn.write_message(serialize_model(ParkingAcceptanceMessage(lot_id)))
    msg = deserialize_ws_message(await conn.read_message())

    engine.commit_allocation.assert_called_once_with(user_id, lot_id)
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.ALLOCATION_COMMIT_FAIL


@pytest.mark.gen_test(run_sync=False)
async def test_parking_rejection_message(ws_url, user_id, mocker, usessions):
    lot_id = 7
    mocker.spy(usessions, "add_user_rejection")

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)

    await conn.write_message(serialize_model(ParkingRejectionMessage(lot_id)))
    msg = deserialize_ws_message(await conn.read_message())

    usessions.add_user_rejection.assert_called_once_with(user_id, lot_id)
    assert isinstance(msg, ConfirmationMessage)


@pytest.mark.gen_test(run_sync=False)
async def test_parking_cancellation_message(ws_url, user_id, dbaccess):
    lot_id = 7
    dbaccess.delete_allocation.return_value = return_async_value(None)

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url + user_id)
    await conn.write_message(serialize_model(ParkingCancellationMessage(lot_id)))

    assert await conn.read_message() is None  # assert connection was closed by server
    await sleep(0.01)
    dbaccess.delete_allocation.assert_called_once_with(user_id)
