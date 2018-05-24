import logging
from asyncio import AbstractEventLoop
from typing import Optional, List

import asyncpg
from asyncpg import Record

import parking.backend.db.sql_constants as c
from parking.shared.rest_models import ParkingLot

logger = logging.getLogger('backend')


class DbAccess(object):
    @classmethod
    async def create(cls, destination: str, loop: AbstractEventLoop,
                     init_tables: bool = False, reset_tables: bool = False) -> 'DbAccess':
        self = DbAccess()
        self.pool: asyncpg.pool.Pool = await asyncpg.create_pool(dsn=destination, loop=loop)
        if reset_tables:
            await self._drop_tables()
        if init_tables or reset_tables:
            await self._create_tables()
        return self

    async def _drop_tables(self):
        logger.info("Dropping database tables.")
        async with self.pool.acquire() as conn:
            await conn.execute(c.ALLOCATIONS_DROP_TABLE)
            await conn.execute(c.PARKINGLOTS_DROP_TABLE)
        logger.info("Database tables dropped.")

    async def _create_tables(self):
        logger.info("Creating database tables.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(c.SETUP_EXTENSIONS)
                await conn.execute(c.PARKINGLOTS_CREATE_TABLE)
                await conn.execute(c.ALLOCATIONS_CREATE_TABLE)
        logger.info("Database tables created.")

    async def insert_parking_lot(self, p: ParkingLot) -> Optional[int]:
        async with self.pool.acquire() as conn:
            park_id: int = await conn.fetchval(c.PARKINGLOTS_INSERT,
                                               p.name, p.capacity, p.location.latitude,
                                               p.location.longitude, p.price, p.capacity, 0)
        return park_id

    async def delete_parking_lot(self, park_id: int) -> Optional[int]:
        async with self.pool.acquire() as conn:
            park_id: int = await conn.fetchval(c.PARKINGLOTS_DELETE, park_id)
        return park_id

    async def update_parking_lot_availability(self, park_id: int, availability: int) -> Optional[int]:
        async with self.pool.acquire() as conn:
            park_id: int = await conn.fetchval(c.PARKINGLOTS_UPDATE_AVAILABILITY, park_id, availability)
        return park_id

    async def update_parking_lot_price(self, park_id: int, price: int) -> Optional[int]:
        async with self.pool.acquire() as conn:
            park_id: int = await conn.fetchval(c.PARKINGLOTS_UPDATE_PRICE, park_id, price)
        return park_id

    async def allocate_parking_lot(self, user_id: str, park_id: int) -> bool:
        async with self.pool.acquire() as conn:
            try:
                async with conn.transaction():
                    status: str = await conn.execute(c.PARKINGLOTS_INCREMENT_ALLOCATION, park_id)
                    if status == "UPDATE 0":
                        logger.warning("The car park {} did not exist or had too many allocations "
                                       "when allocating it to user : '{}'".format(park_id, user_id))
                        return False
                    else:
                        await conn.execute(c.ALLOCATIONS_INSERT, user_id, park_id)
            except asyncpg.exceptions.UniqueViolationError:
                logger.warning("Tried to allocate user : '{}' when they already had an allocation.".format(user_id))
                return False
        return True

    async def get_available_parking_lots(self, lat: float, long: float,
                                         dist_meters: int, exclusions: List[int]) -> List[Record]:
        async with self.pool.acquire() as conn:
            if exclusions:
                print(exclusions)
                records = await conn.fetch(c.PARKINGLOTS_SELECT_WITHIN_DISTANCE_WITH_EXCLUSIONS,
                                           lat, long, dist_meters, exclusions)
            else:
                records = await conn.fetch(c.PARKINGLOTS_SELECT_WITHIN_DISTANCE, lat, long, dist_meters)
        return records
