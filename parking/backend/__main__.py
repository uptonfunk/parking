import tornado

from parking.backend.user_server.wsserver import UserWSHandler, SessionsHandler


def main() -> None:
    app = tornado.web.Application([(r"/ws/(.*)", UserWSHandler, {'sessions_handler': SessionsHandler()})])
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
