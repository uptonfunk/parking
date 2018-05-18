from tornado import ioloop, web


class MyHandler(web.RequestHandler):
    def post(self):
        print(self.request.body.rstrip())


app = web.Application([
    web.URLSpec('/spaces', MyHandler),
    web.URLSpec('/spaces/:1/price', MyHandler)
])

app.listen(port=5000)
ioloop.IOLoop.current().start()
