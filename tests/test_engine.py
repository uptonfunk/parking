from uuid import uuid4
import pytest
from parking.backend.engine.alloc_engine import AllocationEngine
from parking.backend.db.dbaccess import DbAccess
from parking.backend.user_server.session import UserSessions
from parking.shared.location import Location
from parking.shared.ws_models import ParkingRequestMessage


@pytest.mark.asyncio
async def test_handle_allocation_request():
    async def fake_get_available_parking_lot(loc, dist, rej):
        lots = [{'id': 1, 'name': 'test_lot_1', 'capacity': 10, 'lat': 0.0, 'long': 0.0001,
                 'price': 2, 'num_available': 10, 'num_allocated': 0},
                {'id': 2, 'name': 'test_lot_2', 'capacity': 10, 'lat': 0.0, 'long': 0.0001,
                 'price': 2, 'num_available': 10, 'num_allocated': 0}]
        return lots

    db = DbAccess()
    db.get_available_parking_lots = fake_get_available_parking_lot
    us = UserSessions()
    user_id = uuid4()
    us.add_user(user_id, None)
    engine = AllocationEngine(db, us)
    req = ParkingRequestMessage(location=Location(0.0, 0.0001), preferences={})

    lot = await engine.handle_allocation_request(user_id, req)
    assert lot.id == 1


@pytest.mark.asyncio
async def test_recalculate_allocations():
    user_ids = [uuid4(), uuid4(), uuid4()]
    locations = [Location(0.0, 0.0), Location(0.0001, 0.0002), Location(0.2, 0.0)]
    PARK_ID = 1
    removed = []

    async def fake_get_parking_lot(park_id):
        return {'id': PARK_ID, 'name': 'test_lot_1', 'capacity': 10, 'lat': 0.0, 'long': 0.0001,
                'price': 2, 'num_available': 1, 'num_allocated': 3}

    async def fake_get_parking_lot_allocations(park_id):
        return [{'user_id': user_ids[0], 'park_id': PARK_ID},
                {'user_id': user_ids[1], 'park_id': PARK_ID},
                {'user_id': user_ids[2], 'park_id': PARK_ID}]

    async def fake_delete_allocation(user_id):
        removed.append(user_id)

    db = DbAccess()
    db.get_parking_lot = fake_get_parking_lot
    db.get_parking_lot_allocations = fake_get_parking_lot_allocations
    db.delete_allocation = fake_delete_allocation

    us = UserSessions()
    us.deallocate = lambda user_id: print(user_id)
    for user_id, loc in zip(user_ids, locations):
        us.add_user(user_id, None)
        us.update_user_location(user_id, loc)

    engine = AllocationEngine(db, us)

    await engine.recalculate_allocations(PARK_ID)
    assert len(removed) == 2
