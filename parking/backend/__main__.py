import argparse
from asyncio import AbstractEventLoop

import testing.postgresql
import tornado

from parking.backend.db.dbaccess import DbAccess
from parking.backend.user_server.wsserver import UserWSHandler, UserSessions
from parking.backend.sensor_server.rest_server import (IndividualLotDeleteHandler, IndividualLotAvailableHandler,
                                                       IndividualLotPriceHandler, ParkingLotsCreationHandler)


def main(temp_db: bool, db_url: str, reset_tables: bool):
    def _main(url: str, _init_tables: bool = False, _reset_tables: bool = False):
        loop: AbstractEventLoop = tornado.ioloop.IOLoop.current().asyncio_loop
        dba: DbAccess = tornado.ioloop.IOLoop.current().run_sync(
            lambda: DbAccess.create(url, loop=loop, init_tables=_init_tables, reset_tables=_reset_tables))
        app = tornado.web.Application([(r"/ws/(.*)", UserWSHandler, {'user_sessions': UserSessions(), 'dba': dba}),
                                       (r'/spaces', ParkingLotsCreationHandler, {'dba': dba}),
                                       (r'/spaces/([0-9])+', IndividualLotDeleteHandler, {'dba': dba}),
                                       (r'/spaces/([0-9])+/available', IndividualLotAvailableHandler, {'dba': dba}),
                                       (r'/spaces/([0-9])+/price', IndividualLotPriceHandler, {'dba': dba})])

        app.listen(8888)
        tornado.ioloop.IOLoop.current().start()

    if temp_db:
        with testing.postgresql.Postgresql() as postgresql:
            _main(postgresql.url(), _init_tables=True)
    else:
        _main(db_url, _reset_tables=reset_tables)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parking backend.')
    parser.add_argument("--db", default="postgresql://localhost/postgres", help="Database full url")
    parser.add_argument("--temp-db", action='store_true', help="Create and initialise a temporary database")
    parser.add_argument("--reset-tables", action='store_true', help="Drop and recreate database tables")
    args: argparse.Namespace = parser.parse_args()

    main(args.temp_db, args.db, args.reset_tables)
