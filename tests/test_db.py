from asyncio import AbstractEventLoop
from typing import List
from uuid import uuid4

import pytest
import testing.postgresql
from asyncpg import Record

from parking.backend.db.dbaccess import DbAccess
from parking.shared.location import Location
from parking.shared.rest_models import ParkingLot

Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True)


def teardown_module(module):
    Postgresql.clear_cache()


@pytest.mark.asyncio
async def test_empty_tables(event_loop: AbstractEventLoop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        async with db.pool.acquire() as conn:
                p_lst = await conn.fetch('SELECT * from ParkingLots;')
                assert len(p_lst) == 0
                a_lst = await conn.fetch('SELECT * from Allocations;')
                assert len(a_lst) == 0


@pytest.mark.asyncio
async def test_insert_parking_lot(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)

        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        park_id = await db.insert_parking_lot(parking_lot)
        assert park_id == 1

        async with db.pool.acquire() as conn:
            lst: List[Record] = await conn.fetch('SELECT * from ParkingLots;')
            assert len(lst) == 1


@pytest.mark.asyncio
async def test_delete_parking_lot(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        await db.insert_parking_lot(parking_lot)
        async with db.pool.acquire() as conn:
            lst: List[Record] = await conn.fetch('SELECT * from ParkingLots;')
            assert len(lst) == 1
            park_id = await db.delete_parking_lot(1)
            assert park_id == 1
            lst: List[Record] = await conn.fetch('SELECT * from ParkingLots;')
            assert len(lst) == 0


@pytest.mark.asyncio
async def test_delete_parking_lot_unsuccessful(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        await db.insert_parking_lot(parking_lot)
        async with db.pool.acquire() as conn:
            lst: List[Record] = await conn.fetch('SELECT * from ParkingLots;')
            assert len(lst) == 1
            park_id = await db.delete_parking_lot(2)
            assert park_id is None
            lst: List[Record] = await conn.fetch('SELECT * from ParkingLots;')
            assert len(lst) == 1


@pytest.mark.asyncio
async def test_update_parking_lot_price_and_availability(event_loop):
    new_availability = 10
    new_price = 5

    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)

        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        park_id = await db.insert_parking_lot(parking_lot)
        park_id = await db.update_parking_lot_availability(park_id, new_availability)
        assert park_id == 1
        park_id = await db.update_parking_lot_price(park_id, new_price)
        assert park_id == 1

        async with db.pool.acquire() as conn:
            p_record: Record = await conn.fetchrow('SELECT * from ParkingLots;')

        assert p_record['num_available'] == new_availability
        assert p_record['price'] == new_price


@pytest.mark.asyncio
async def test_update_parking_lot_price_and_availability_unsuccessful(event_loop):
    new_availability = 10
    new_price = 5

    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)

        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        await db.insert_parking_lot(parking_lot)
        park_id = await db.update_parking_lot_availability(2, new_availability)
        assert park_id is None
        park_id = await db.update_parking_lot_price(2, new_price)
        assert park_id is None


@pytest.mark.asyncio
async def test_allocate_parking_lot_to_user(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)

        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0))
        await db.insert_parking_lot(parking_lot)
        assert await db.allocate_parking_lot("test_user", 1) is True


@pytest.mark.asyncio
async def test_allocate_parking_lot_to_user_fail(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        assert await db.allocate_parking_lot("test_user", 1) is False


@pytest.mark.asyncio
async def test_allocate_parking_lot_to_user_already_allocated_fail(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)

        parking_lot1 = ParkingLot(100, 'test_name1', 0.0, Location(0.0, 1.0))
        parking_lot2 = ParkingLot(100, 'test_name2', 0.0, Location(0.0, 1.0))
        await db.insert_parking_lot(parking_lot1)
        await db.insert_parking_lot(parking_lot2)

        assert await db.allocate_parking_lot("test_user", 1) is True
        assert await db.allocate_parking_lot("test_user", 2) is False


@pytest.mark.asyncio
async def test_get_available_parking_lots(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        parking_lot1 = ParkingLot(100, 'test_name1', 0.0, Location(0.0, 1.0089))
        parking_lot2 = ParkingLot(100, 'test_name2', 0.0, Location(0.0, 1.01))
        parking_lot3 = ParkingLot(100, 'test_name2', 0.0, Location(0.0, 1.0))

        await db.insert_parking_lot(parking_lot1)
        await db.update_parking_lot_availability(1, 50)
        await db.insert_parking_lot(parking_lot2)
        await db.update_parking_lot_availability(2, 50)
        await db.insert_parking_lot(parking_lot3)
        await db.update_parking_lot_availability(3, 50)

        records = await db.get_available_parking_lots(lat=0, long=1, dist_meters=1000, exclusions=[])

        assert len(records) == 2
        assert records[0]['id'] == 3
        assert records[0]['distance'] == 0
        assert records[1]['id'] == 1
        assert round(records[1]['distance']) == 991

        records2 = await db.get_available_parking_lots(lat=0, long=1, dist_meters=1000, exclusions=[3])

        assert len(records2) == 1
        assert records2[0]['id'] == 1
        assert round(records2[0]['distance']) == 991


@pytest.mark.asyncio
async def test_add_allocation(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0089))
        user_id = str(uuid4())

        park_id = await db.insert_parking_lot(parking_lot)
        result = await db.allocate_parking_lot(user_id, park_id)
        assert result

        allocations = await db.get_parking_lot_allocations(park_id)
        assert allocations[0]['park_id'] == park_id
        assert allocations[0]['user_id'] == user_id


@pytest.mark.asyncio
async def test_get_parking_lot(event_loop):
    with Postgresql() as postgresql:
        db = await DbAccess.create(postgresql.url(), event_loop, reset_tables=True)
        parking_lot = ParkingLot(100, 'test_name', 0.0, Location(0.0, 1.0089))

        park_id = await db.insert_parking_lot(parking_lot)

        lot = await db.get_parking_lot(park_id)
        assert lot['name'] == parking_lot.name
