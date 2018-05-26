import tornado.testing
import tornado.web
import tornado.websocket
from parking.shared.clients import CarWS as wscli
from parking.shared.util import serialize_model
import tornado.websocket
import parking.shared.ws_models

class SocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        print(' [T] Websocket connection open')

    def on_message(self, message):
        print(' [T] Websocket message received: %s' % message)
        self.write_message(message)

    def on_close(self):
        print(' [T] Websocket connection closed')


class TestWebSockets(tornado.testing.AsyncHTTPTestCase):

    def get_app(self):
        return tornado.web.Application([(r'/', SocketHandler)])

    @tornado.testing.gen_test
    async def test_async_client(self):

        url = "ws://localhost:" + str(self.get_http_port()) + "/"

        async with wscli(url) as cli:
            await cli.send('message')
            response = await cli.receive()

        assert response == 'message'

    @tornado.testing.gen_test
    async def test_async_client(self):
        url = "ws://localhost:" + str(self.get_http_port()) + "/"
        lum = parking.shared.ws_models.LocationUpdateMessage(parking.shared.ws_models.Location(1.0, 1.0))

        async with wscli(url) as cli:
            await cli.send(lum)
            response = await cli.receive()

        assert response == serialize_model(lum)
