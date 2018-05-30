import asyncio

import parking.shared.clients as clients
from parking.shared.location import Location
import parking.shared.ws_models as wsm

import pytest

import tornado.web
import tornado.websocket


class EchoServer(tornado.websocket.WebSocketHandler):

    def open(self):
        print(' [T] Websocket connection open')

    def on_message(self, message):
        print(' [T] Websocket message received: %s' % message)
        self.write_message(message)

    def on_close(self):
        print(' [T] Websocket connection closed')


@pytest.fixture
def app():
    application = tornado.web.Application([(r'/', EchoServer)])
    return application


@pytest.fixture
def io_loop():
    return tornado.ioloop.IOLoop.current()


@pytest.fixture
def ws_url(base_url):
    return base_url.replace('http', 'ws')


@pytest.mark.gen_test(run_sync=False)
async def test_location_message_future(http_client, ws_url):
    car_ws = await clients.CarWebsocket.create(ws_url)
    location = Location(0.0, 1.0)
    await car_ws.send_location(location)
    response = await car_ws.receive(wsm.LocationUpdateMessage)
    assert response.location == location


@pytest.mark.gen_test(run_sync=False)
async def test_location_message_callback(http_client, ws_url):
    f = asyncio.Future()
    car_ws = await clients.CarWebsocket.create(ws_url, {
        wsm.LocationUpdateMessage: f.set_result,
    })
    location = Location(0.0, 1.0)
    await car_ws.send_location(location)
    response = await f
    assert response.location == location
