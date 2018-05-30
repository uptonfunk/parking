from parking.backend.__main__ import make_app

import pytest
import tornado
import tornado.web
import tornado.websocket
import testing.postgresql
from tornado.websocket import WebSocketClientConnection

@pytest.fixture(scope="module")
def postgresql():
    postgresql_con = testing.postgresql.Postgresql()
    yield postgresql_con
    postgresql_con.stop()

@pytest.fixture
def app(postgresql):
    return make_app(postgresql.url(), _init_tables=True, _reset_tables=True)
