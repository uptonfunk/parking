from tornado import ioloop, web
from parking.shared.rest_models import ParkingLotCreationResponse
from parking.shared.util import serialize_model


class MyHandler(web.RequestHandler):
    def post(self):
        print(self.request.body.rstrip())
        self.write(serialize_model(ParkingLotCreationResponse(1)))


app = web.Application([
    web.URLSpec('/spaces', MyHandler),
    web.URLSpec('/spaces/:1/price', MyHandler)
])

app.listen(port=5000)
ioloop.IOLoop.current().start()
