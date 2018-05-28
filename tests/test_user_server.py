import pytest
import tornado
import tornado.web
import tornado.websocket
from tornado.websocket import WebSocketClientConnection

from parking.backend.user_server.wsserver import UserWSHandler
from parking.backend.db.dbaccess import DbAccess
from parking.backend.engine.alloc_engine import AllocationEngine
from parking.backend.user_server.session import UserSessions
from parking.shared.ws_models import deserialize_ws_message, WebSocketErrorType


@pytest.fixture
def dbaccess():
    return DbAccess()


@pytest.fixture
def app():
    usessions: UserSessions = UserSessions()
    engine: AllocationEngine = AllocationEngine(dbaccess(), usessions)
    application = tornado.web.Application([(r"/ws/(.*)", UserWSHandler, {'usessions': usessions, 'engine': engine})])
    return application


@pytest.mark.gen_test(run_sync=False)
async def test_invalid_message(http_port, http_server, app):
    user_id = "donald"
    ws_url = "ws://localhost:{}/ws/{}".format(http_port, user_id)

    conn: WebSocketClientConnection = await tornado.websocket.websocket_connect(ws_url)
    await conn.write_message("test")
    msg = deserialize_ws_message(await conn.read_message())
    assert WebSocketErrorType(msg.error) == WebSocketErrorType.INVALID_MESSAGE

    conn.close()
