# test_simulation.py

import json
import asyncio

from parking.shared.location import Location
from parking.shared.rest_models import ParkingLot, ParkingLotCreationResponse
from parking.shared.util import serialize_model

from simulation.simulation import SimManager

import pytest

HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}

"""
@pytest.mark.gen_test(run_sync=False)
async def test_create_parking_lot(http_client, base_url):
    lot = ParkingLot(100, 'test', 1.0, Location(0.0, 1.0))
    response = await http_client.fetch(base_url + '/spaces', method='POST', headers=HEADERS, body=serialize_model(lot))
    assert ParkingLotCreationResponse(**json.loads(response.body)).id == 1
"""

@pytest.mark.gen_test(run_sync=False)
async def test_integrate_sim(http_client, base_url):
    sim = SimManager(2000, 20, 70, 50, 1000, 1000, 2, 4, 100, base_url)
    asyncio.ensure_future(sim.stop(30))
    await sim.run()
