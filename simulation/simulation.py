import asyncio
import random
import time
import tkinter as tk
import math
from tornado import httpclient
from concurrent import futures
import logging

from uuid import uuid4

import parking.shared.ws_models as wsmodels
import parking.shared.rest_models as restmodels
from parking.shared.clients import CarWebsocket, ParkingLotRest

logger = logging.getLogger('simulation')


class SimManager:
    def __init__(self, no_spaces, min_spaces_per_lot, max_spaces_per_lot, no_cars,
                 x, y, parking_lot_seed, car_seed, max_time, app_url):
        self.random_lot = random.Random(parking_lot_seed)
        self.random_car = random.Random(car_seed)
        self.x = x
        self.y = y
        self.no_cars = no_cars
        self.car_tasks = []
        self.space_tasks = []
        self.max_time = max_time
        self.cars = []
        self.lots = []
        self.stop_flag = False
        self.app_url = app_url

        count = 0
        name = 0
        while count < no_spaces:
            if self.stop_flag:
                break

            px = self.random_lot.randint(0, self.x-1)
            py = self.random_lot.randint(0, self.y-1)

            max_al = min(max_spaces_per_lot, (no_spaces - count))
            if max_al < min_spaces_per_lot:
                n = max_al  # could potentially be smaller than min spaces per lot
            else:
                n = self.random_lot.randint(min_spaces_per_lot, max_al)
            price = round(self.random_lot.uniform(0, 10), 2)
            spacero = space_routine(0, px, py, n, str(name), price, n, self)
            self.space_tasks.append(asyncio.ensure_future(spacero))

            count += n
            name += 1

        for i in range(self.no_cars):
            start_time = 5  # TODO atm, delay until after spaces created, later add handling for no spaces
            start_x = self.random_car.randint(0, self.x - 1)
            start_y = self.random_car.randint(0, self.y - 1)
            coro = car_routine(start_time, start_x, start_y, self)
            self.car_tasks.append(asyncio.ensure_future(coro))

        self.tasks = self.space_tasks + self.car_tasks
        self.run_task = None

    async def run_tk(self, root, interval):
        w = tk.Canvas(root, width=self.x, height=self.y)
        w.pack()
        try:
            while not self.stop_flag:
                w.delete("all")
                now = time.time()
                for simlot in self.lots:
                    lotlat, lotlong = simlot.lot.location.latitude, simlot.lot.location.longitude
                    w.create_rectangle(lotlat, lotlong, lotlat + 20, lotlong + 20, width=0, fill="green")

                for car in self.cars:
                    if car.drawing:
                        dotlat, dotlong = car.get_position(now)
                        w.create_oval(dotlat, dotlong, dotlat + 5, dotlong + 5, width=0, fill='blue')
                root.update()
                await asyncio.sleep(interval)
            root.destroy()
        except tk.TclError as e:
            if "application has been destroyed" not in e.args[0]:
                raise

    async def run(self):
        logger.info("simulation running")
        framerate = 1 / 60
        root = tk.Tk()
        self.run_task = self.run_tk(root, framerate)
        await asyncio.gather(self.run_task, *self.tasks)

    async def stop(self, delay):
        await asyncio.sleep(delay)
        self.stop_flag = True
        await self.run_task
        for t in self.car_tasks + self.space_tasks:
            await t


class Waypoint:
    def __init__(self, timestamp, lat, long):
        self.time = timestamp
        self.lat = lat
        self.long = long


class Car:
    def __init__(self, lat, long):
        self.lat = lat
        self.long = long
        self.destX = 0
        self.destY = 0
        self.aDestX = 0
        self.aDestY = 0
        self.drawing = False
        self.speed = 60
        self.waypoints = []
        self.waypoints.append(Waypoint(time.time(), self.lat, self.long))

    def distance_to(self, x, y):
        return math.sqrt((self.lat - x)**2 + (self.long - y)**2)

    def get_position(self, now):
        if len(self.waypoints) > 1:
            latdiff = self.waypoints[-1].lat - self.waypoints[-2].lat
            longdiff = self.waypoints[-1].long - self.waypoints[-2].long
            timediff = self.waypoints[-1].time - self.waypoints[-2].time
            progress = (now - self.waypoints[-1].time) / timediff
            poslat = self.waypoints[-2].lat + (latdiff * progress)
            poslong = self.waypoints[-2].long + (longdiff * progress)
            return poslat, poslong
        else:
            return self.lat, self.long

    def set_initial_destination(self, x, y):
        self.destX = x
        self.destY = y
        # for the moment, assuming no congestion and constant speed, we can calculate the arrival time
        # however might need to pass it in when things get more complicated
        newtime = time.time() + (self.distance_to(x, y) / self.speed)
        self.waypoints.append(Waypoint(newtime, x, y))

    def set_allocated_destination(self, x, y):
        self.aDestX = x
        self.aDestY = y
        newtime = time.time() + (self.distance_to(x, y) / self.speed)
        self.waypoints.append(Waypoint(newtime, x, y))


class ParkingLot:
    def __init__(self, lot: restmodels.ParkingLot, client: ParkingLotRest, available: int = 0):

        self.lot = lot

        if (self.lot.capacity < 1) | (available < 1):
            raise ValueError("Parking capacity/availability must be positive")

        if (not(isinstance(self.lot.capacity, int))) | (not(isinstance(available, int))):
            raise TypeError("Capacity/availability must be an integer")

        if available > self.lot.capacity:
            raise ValueError("Capacity has to be greater than available spaces")

        self.available: int = available
        self.cars = []
        self.client = client

    async def fill_space(self) -> bool:
        if self.available > 0:
            response = await self.client.update_available(self.lot.id, self.available - 1)
            if response.error:
                pass
            self.available -= 1
            return True
        else:
            return False

    def free_space(self) -> bool:
        if self.available < self.lot.capacity:
            self.available += 1
            return True
        else:
            return False

    async def change_price(self, new_price):
        self.lot.price = new_price
        response = await self.client.update_price(self.lot.id, new_price)
        # TODO error handling
        # if response.error:
        #     pass

    async def delete(self):
        response = await self.client.delete_lot(self.lot.id)
        # if response.error:
        #     pass

    async def change_availability(self, value):
        if value > self.lot.capacity | value < 0:
            raise ValueError("Availability must be positive and no greater than the capacity")

        if not(isinstance(value, int)):
            raise TypeError("Availability must be an integer")

        response = await self.client.update_available(self.lot.id, value)

        # if response.error == "200":
        #     self.available = value
        #     return True
        # else:
        #     return False


async def car_routine(startt, startx, starty, manager):
    await asyncio.sleep(startt)

    car = Car(startx, starty)
    manager.cars.append(car)

    x, y = car.aDestX, car.aDestY
    logger.info("car routine started")
    car_id = str(uuid4())
    cli = await CarWebsocket.create(base_url=manager.app_url.replace('http', 'ws') + "/ws", user_id=car_id)
    logger.info("car websocket client connected")
    # request a parking space

    waiting = True
    while waiting and not manager.stop_flag:
        response = await cli.send_parking_request(wsmodels.Location(float(x), float(y)), {})
        logger.info("allocation requested...")
        car.drawing = True

        futs = [cli.receive(wsmodels.ParkingAllocationMessage), cli.receive(wsmodels.ErrorMessage)]
        (fut,), *_ = await asyncio.wait(futs, return_when=asyncio.FIRST_COMPLETED)
        logger.debug('got future: {}'.format(fut))
        space = fut.result()
        logger.debug('got result: {}'.format(space))
        if isinstance(space, wsmodels.ErrorMessage):
            logger.info("retrying initial request...")
            await asyncio.sleep(1)

    if not manager.stop_flag:

        logger.info("allocation recieved: '{}'".format(space.lot.id))
        car.set_allocated_destination(space.lot.location.longitude, space.lot.location.latitude)

        await cli.send_parking_acceptance(space.lot.id)

    if not manager.stop_flag:

        await cli.receive(wsmodels.WebSocketMessageType.CONFIRMATION)

    while not manager.stop_flag:
        # Send the location of the car at time intervals, while listening for deallocation
        try:
            deallocation = await asyncio.shield(asyncio.wait_for(cli.receive(wsmodels.ParkingCancellationMessage), 3))
        except futures.TimeoutError:
            deallocation = None
        x, y = car.get_position(time.time())
        await cli.send_location(wsmodels.Location(float(x), float(y)))


async def space_routine(startt, lat, long, capacity, name, price, available, manager):
    await asyncio.sleep(startt)

    cli = ParkingLotRest(manager.app_url, httpclient.AsyncHTTPClient())
    lot = restmodels.ParkingLot(capacity, name, price, restmodels.Location(float(lat), float(long)))
    response = await cli.create_lot(lot)
    lot.id = response

    simlot = ParkingLot(lot, cli, capacity)
    manager.lots.append(simlot)

    await asyncio.sleep(10)

    await simlot.change_price(1.0)

if __name__ == '__main__':
    sim = SimManager(2000, 20, 70, 50, 1000, 1000, 2, 4, 100)
    asyncio.ensure_future(sim.run())
    #stop simulation after 10 seconds
    asyncio.ensure_future(sim.stop(10))
    asyncio.get_event_loop().run_forever()
    #can access sim variables here for tests

