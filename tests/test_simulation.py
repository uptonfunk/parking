# test_simulation.py

import asyncio
import logging
from uuid import uuid4

from parking.shared.location import Location
from parking.shared.rest_models import ParkingLot
import parking.shared.ws_models as wsmodels
from parking.shared.clients import CarWebsocket

from simulation.simulation import SimManager, ParkingLotRest, ParkingLot as SimPL

import pytest

HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}

logger = logging.getLogger('simulation_tests')
logger.setLevel(logging.DEBUG)


@pytest.mark.gen_test(run_sync=False)
async def test_create_parking_lot(http_client, base_url):
    cli = ParkingLotRest(base_url, http_client)
    lot = ParkingLot(10, 'a', 1.0, Location(0.0, 1.0))

    response = await cli.create_lot(lot)
    lot.id = response
    logger.debug(f'[test_create_parking_lot] created lot {response}')
    simlot = SimPL(lot, cli, 10)

    logger.debug(f'[test_create_parking_lot] sleeping for 10 ...')
    await asyncio.sleep(1)
    logger.debug(f'[test_create_parking_lot] slept, changing price')
    await simlot.change_price(1.0)
    logger.debug(f'[test_create_parking_lot] done')

    car_id = str(uuid4())
    car_cli = await CarWebsocket.create(base_url=base_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.debug("car websocket client connected")
    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    allocated = await car_cli.receive(wsmodels.ParkingAllocationMessage)
    logger.debug(f'allocation recieved: {allocated}')

    assert allocated.lot.id == lot.id


@pytest.mark.gen_test(run_sync=False)
async def test_create_multiple_parking_lot(http_client, base_url):
    cli = ParkingLotRest(base_url, http_client)

    lot = ParkingLot(10, 'a', 1.0, Location(0.0, 1.0))
    response = await cli.create_lot(lot)
    lot.id = response
    logger.debug(f'[test_create_parking_lot] created lot {lot.id}')

    lot2 = ParkingLot(10, 'b', 1.0, Location(2.0, 2.0))
    response = await cli.create_lot(lot2)
    lot2.id = response
    logger.debug(f'[test_create_parking_lot] created lot2 {lot2.id}')

    car_id = str(uuid4())
    car_cli = await CarWebsocket.create(base_url=base_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.debug("car websocket client connected")
    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    allocated = await car_cli.receive(wsmodels.ParkingAllocationMessage)
    logger.debug(f'allocation recieved: {allocated}')

    assert allocated.lot.id == lot.id


@pytest.mark.gen_test(run_sync=False)
async def test_no_parking_lots_retry(http_client, base_url):
    car_id = str(uuid4())
    car_cli = await CarWebsocket.create(base_url=base_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.debug("car websocket client connected")
    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    allocated = await car_cli.receive(wsmodels.ErrorMessage)
    logger.debug(f'allocation failed: {allocated}')

    assert allocated.error.msg == 'No parking lot available.'

    cli = ParkingLotRest(base_url, http_client)
    lot = ParkingLot(10, 'a', 1.0, Location(0.0, 1.0))

    response = await cli.create_lot(lot)
    lot.id = response
    logger.debug(f'created lot {response}')
    simlot = SimPL(lot, cli, 10)

    logger.debug(f'sleeping for 10 ...')
    await asyncio.sleep(1)
    logger.debug(f'slept, changing price')
    await simlot.change_price(1.0)
    logger.debug(f'done')

    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    allocated = await car_cli.receive(wsmodels.ParkingAllocationMessage)
    logger.debug(f'allocation recieved: {allocated}')

    assert allocated.lot.id == lot.id


@pytest.mark.gen_test(run_sync=False)
async def test_no_parking_lots(http_client, base_url):
    car_id = str(uuid4())
    car_cli = await CarWebsocket.create(base_url=base_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.debug("car websocket client connected")
    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    allocated = await car_cli.receive(wsmodels.ErrorMessage)
    logger.debug(f'allocation failed: {allocated}')

    assert allocated.error.msg == 'No parking lot available.'


@pytest.mark.gen_test(run_sync=False)
async def test_no_parking_lots_retry_waiting(http_client, base_url):
    car_id = str(uuid4())
    car_cli = await CarWebsocket.create(base_url=base_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.debug("car websocket client connected")
    response = await car_cli.send_parking_request(Location(0.0, 1.0), {})
    logger.debug(f'requested allocation: {response}')
    futs = [car_cli.receive(wsmodels.ParkingAllocationMessage), car_cli.receive(wsmodels.ErrorMessage)]
    (fut,), *_ = await asyncio.wait(futs, return_when=asyncio.FIRST_COMPLETED)
    space = fut.result()

    assert isinstance(space, wsmodels.ErrorMessage)
    assert space.error.msg == 'No parking lot available.'


@pytest.mark.gen_test(run_sync=False, timeout=100)
async def test_integrate_sim(caplog, http_client, base_url):
    caplog.set_level(logging.DEBUG)
    sim = SimManager(50, 5, 5, 25, 155, 900, 600, 2, 4, 100, base_url)
    asyncio.ensure_future(sim.stop(180))
    await sim.run()
