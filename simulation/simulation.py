import asyncio
import random
import time
import tkinter as tk
from tornado import httpclient
from concurrent import futures
import logging
from geopy.distance import vincenty
from enum import Enum

from uuid import uuid4

import parking.shared.ws_models as wsmodels
import parking.shared.rest_models as restmodels
from parking.shared.clients import CarWebsocket, ParkingLotRest

logger = logging.getLogger('simulation')

SCALE = 110 * 1000  # the lat/long scaling factor


class SimManager:
    def __init__(self, no_spaces, min_spaces_per_lot, max_spaces_per_lot, no_cars,
                 no_rogues, width, height, parking_lot_seed, car_seed, max_time, app_url):
        self.random_lot = random.Random(parking_lot_seed)
        self.random_car = random.Random(car_seed)
        self.width, self.height = width, height
        self.no_cars = no_cars
        self.no_rogues = no_rogues
        self.car_tasks = []
        self.space_tasks = []
        self.rogue_tasks = []
        self.max_time = max_time
        self.cars = []
        self.rogues = []
        self.lots = []
        self.lotdict = {}
        self.stop_flag = False
        self.app_url = app_url
        self.stats = {}
        self.stats[Stats.ROGUECOUNT] = 0
        self.stats[Stats.ROGUEPARKTIMEAVG] = 0
        self.stats[Stats.FIRSTROGUESTARTTIME] = None
        self.stats[Stats.ROGUERETRY] = [0]
        self.graphs = []
        self.graphs.append(BarGraph(self, [Stats.ROGUEPARKTIMEAVG, Stats.ROGUEPARKTIMEAVG]))
        self.graphs.append(LineGraph(self, [Stats.ROGUERETRY]))
        self.retry_lock = asyncio.Lock()

        self.stop_future = asyncio.Future()


        count = 0
        name = 0

        while count < no_spaces:
            if self.stop_flag:
                break

            if False:
                p = self.point_to_location(self.random_lot.randint(0, width), self.random_lot.randint(0, height))
            else:
                p = self.point_to_location(self.random_lot.randint(1, 9) * height/10,
                                           self.random_lot.randint(1, 9) * width/10)

            max_al = min(max_spaces_per_lot, (no_spaces - count))
            if max_al < min_spaces_per_lot:
                n = max_al  # could potentially be smaller than min spaces per lot
            else:
                n = self.random_lot.randint(min_spaces_per_lot, max_al)
            price = round(self.random_lot.uniform(0, 10), 2)
            spacero = space_routine(0, p, n, str(name), price, n, self)
            self.space_tasks.append(asyncio.ensure_future(spacero))

            count += n
            name += 1

        for i in range(self.no_cars):
            start_time = 1
            p = self.point_to_location(self.random_lot.randint(0, width), self.random_lot.randint(0, height))
            coro = car_routine(start_time, p, self)
            self.car_tasks.append(asyncio.ensure_future(coro))

        rogue_start = 3
        for i in range(self.no_rogues):
            if random.randint(1, 2) == 1:
                locx = random.choice([0, width])
                locy = random.randint(0, height)
            else:
                locx = random.randint(0, width)
                locy = random.choice([0, height])
            loc = self.point_to_location(locx, locy)
            dest = self.point_to_location(self.random_lot.randint(0, width), self.random_lot.randint(0, height))
            self.rogue_tasks.append(asyncio.ensure_future(rogue_routine(rogue_start + i/10, loc, dest, self)))

        self.tasks = self.space_tasks + self.car_tasks + self.rogue_tasks
        self.run_task = None

    def point_to_location(self, x: float, y: float) -> wsmodels.Location:
        """Assuming (0, 0) x/y maps to Location(0, 0), compute the Location for an arbitrary x, y point
        """
        return wsmodels.Location(x / SCALE, y / SCALE)

    def loc_to_point(self, loc: wsmodels.Location):
        """Assuming (0, 0) x/y maps to Location(0, 0), compute the Location for an arbitrary x, y point
        """
        return (loc.longitude * (SCALE), loc.latitude * (SCALE))

    async def run_tk(self, root, interval):
        w = tk.Canvas(root, width=self.width*1.5, height=self.height)
        w.pack()
        try:
            while not self.stop_flag:
                w.delete("ani")
                now = time.time()
                for simlot in self.lots:
                    x, y = self.loc_to_point(simlot.lot.location)
                    w.create_rectangle(x, y, x + (simlot.available*4), y + (simlot.available*4), width=0, fill="green", tags="ani")

                for car in self.cars:
                    if car.drawing:
                        x, y = self.loc_to_point(wsmodels.Location(*car.get_position(now)))
                        w.create_oval(x, y, x + 5, y + 5, width=0, fill='blue', tags="ani")

                for rogue in self.rogues:
                    if rogue.drawing:
                        if now > rogue.starttime:
                            x, y = self.loc_to_point(wsmodels.Location(*rogue.get_position(now)))
                            if x <= self.width:
                                w.create_oval(x, y, x + 5, y + 5, width=0, fill='black', tags="ani")

                w.delete("graph")
                for g in range(len(self.graphs)):
                    graph = self.graphs[g]
                    graph.draw(w, self.width * 1.1, self.height * 0.1 + (g*0.5*self.height),
                               self.width * 1.4, self.height * 0.4 + (g*0.5*self.height))

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

        self.stop_future.set_result(True)

    async def stop(self, delay):
        await asyncio.sleep(delay)
        self.stop_flag = True
        await self.stop_future


class Stats(Enum):
    ROGUECOUNT = 1
    ROGUEPARKTIMEAVG = 2
    USERCOUNT = 3
    USERPARKTIMEAVG = 4
    ROGUERETRY = 5
    USERRETRY = 6
    FIRSTROGUESTARTTIME = 7


class Graph:
    def __init__(self, manager, stats):
        self.manager = manager
        self.stats = stats

    def draw(self, canvas: tk.Canvas, top_left_x, top_left_y, bottom_right_x, bottom_right_y):
        pass


class BarGraph(Graph):
    def __init__(self, manager, stats):
        super().__init__(manager, stats)

    def draw(self, w: tk.Canvas, top_left_x, top_left_y, bottom_right_x, bottom_right_y):
        width = bottom_right_x - top_left_x
        height = bottom_right_y - top_left_y
        w.create_line(top_left_x, bottom_right_y, bottom_right_x, bottom_right_y, fill="black")
        w.create_line(bottom_right_x, top_left_y, bottom_right_x, bottom_right_y, fill="black")

        bar_ratio = 0.6  # how much of the screen is taken up by bars vs empty space
        segment = width / len(self.stats)
        bar_gap = ((1 - bar_ratio) * 0.5) * segment

        values = []
        for s in range(len(self.stats)):
            if isinstance(self.stats[s], list):
                values += self.stats[s]
            else:
                values.append(self.stats[s])

        for v in range(len(values)):
            value = self.manager.stats[values[v]]
            w.create_rectangle(v * segment + bar_gap + top_left_x,
                               bottom_right_y - (value * 5),
                               (v+1) * segment - bar_gap + top_left_x,
                               bottom_right_y, tags="graph")


class LineGraph(Graph):
    def __init__(self, manager, stats):
        super().__init__(manager, stats)

    def draw(self, w: tk.Canvas, top_left_x, top_left_y, bottom_right_x, bottom_right_y):
        width = bottom_right_x - top_left_x
        height = bottom_right_y - top_left_y
        w.create_line(top_left_x, bottom_right_y, bottom_right_x, bottom_right_y, fill="black")
        w.create_line(bottom_right_x, top_left_y, bottom_right_x, bottom_right_y, fill="black")

        max_lines = int(width / 10)

        values = self.manager.stats[self.stats[0]]
        # for s in range(len(self.stats)):
        #     if isinstance(self.stats[s], list):
        #         values += self.stats[s]
        #     else:
        #         values.append(self.stats[s])

        if len(values) > max_lines:
            values = values[-max_lines:]

        length = width/(len(values))
        for v in range(len(values) - 1):
            w.create_line(top_left_x + (v+1) * length, bottom_right_y - values[v] * 8,
                          top_left_x + (v+2) * length, bottom_right_y - values[v+1] * 8,
                          tags = "graph")

class Waypoint:
    def __init__(self, timestamp, lat, long):
        self.time = timestamp
        self.lat = lat
        self.long = long


def geodistance(ax, ay, bx, by):
    # PYTHAGORAS - use for cartesian coordinates
    # return math.sqrt((ax - bx)**2 + (ay - by)**2)

    a = (ax, ay)
    b = (bx, by)
    # VINCENTY - use for lat/long, accurate and slow
    return vincenty(a, b).meters

    # GREAT CIRCLE - use for lat/long, fast and inaccurate


class RogueCar:
    @classmethod
    async def create_rogue(cls, starttime, loc, dest, manager):
        rogue = cls(starttime, loc, dest, manager)
        await rogue.tried[0].register(rogue.first_attempt)
        return rogue

    def __init__(self, starttime, loc, dest, manager):
        self.startX = loc.latitude
        self.startY = loc.longitude
        self.destX = dest.latitude
        self.destY = dest.longitude
        self.waypoints = []
        self.drawing = True
        self.drawhozpos = True
        self.drawverpos = True
        self.starttime = starttime
        self.bestLot = None
        self.tried = []
        self.manager = manager
        self.first_attempt = None

        closeness = 5
        self.speed = 60
        stupidity = 0.5

        self.waypoints.append(Waypoint(starttime, self.startX, self.startY))

        currentX = self.startX
        currentY = self.startY

        lasttime = time.time()

        while geodistance(currentX, currentY, self.destX, self.destY) > closeness:
            # pick a random place to go next, that is probably but not definitely closer to the destination
            mu = (currentX + self.destX) * 0.5
            sigma = abs(currentX - self.destX) * stupidity
            newX = random.normalvariate(mu, sigma)

            mu = (currentY + self.destY) * 0.5
            sigma = abs(currentY - self.destY) * stupidity
            newY = random.normalvariate(mu, sigma)

            # distance = math.sqrt((currentX - newX)**2 + (currentY - newY)**2)
            distance = geodistance(currentX, currentY, newX, newY)

            duration = distance / self.speed

            self.waypoints += get_route(wsmodels.Location(currentX, currentY),
                                        wsmodels.Location(newX, newY), lasttime, self.speed)

            currentX = newX
            currentY = newY

            # self.waypoints.append(Waypoint(lasttime + duration, newX, newY))

            lasttime += duration

        bestLot = None
        bestDistance = 10000000000000
        # once close enough to the destination, find the nearest parking lot
        for ilot in manager.lots:
            currentDistance = geodistance(currentX, currentY, ilot.lot.location.latitude, ilot.lot.location.longitude)
            if currentDistance < bestDistance:
                bestDistance = currentDistance
                bestLot = ilot

        # drive to the closest lot
        duration = bestDistance / self.speed
        arrival = lasttime + duration
        #self.waypoints.append(Waypoint(arrival, bestLot.lot.location.latitude, bestLot.lot.location.longitude))
        self.waypoints += get_route(wsmodels.Location(currentX, currentY), bestLot.lot.location, lasttime, self.speed)
        self.bestLot = bestLot
        attempt = Attempt(arrival, 20, self)
        self.first_attempt = attempt
        self.tried.append(bestLot)

    def get_position(self, now):
        endTime = 0
        waypointIndex = 0

        while endTime < now:
            waypointIndex += 1
            if waypointIndex > len(self.waypoints) - 1:
                self.drawing = False
                return 1.0, 1.0
            endTime = self.waypoints[waypointIndex].time

        start = self.waypoints[waypointIndex - 1]
        end = self.waypoints[waypointIndex]

        latdiff = end.lat - start.lat
        longdiff = end.long - start.long
        timediff = end.time - start.time
        progress = (now - start.time) / timediff
        poslat = start.lat + (latdiff * progress)
        poslong = start.long + (longdiff * progress)

        if latdiff > 0:
            self.drawhozpos = True
        else:
            self.drawhozpos = False

        if longdiff > 0:
            self.drawverpos = True
        else:
            self.drawverpos = False

        return float(poslat), float(poslong)

    def park(self):
        now = time.time()

        mean = self.manager.stats[Stats.ROGUEPARKTIMEAVG]
        count = self.manager.stats[Stats.ROGUECOUNT]

        newmean = ((mean * count) + (now - self.starttime)) / (count + 1)

        self.manager.stats[Stats.ROGUEPARKTIMEAVG] = newmean
        self.manager.stats[Stats.ROGUECOUNT] += 1

    async def retry(self, now, oldlot):
        now = time.time()

        time_index = int((now - self.manager.stats[Stats.FIRSTROGUESTARTTIME]) // 0.2)

        while len(self.manager.stats[Stats.ROGUERETRY]) < time_index + 1:
            self.manager.stats[Stats.ROGUERETRY].append(0)

        self.manager.stats[Stats.ROGUERETRY][time_index] += 1

        self.tried.append(oldlot)
        if len(self.tried) == len(self.manager.lots):
            self.tried = []
        bestDistance = 10000000000000
        # once close enough to the destination, find the nearest parking lot
        bestLot = None
        for ilot in self.manager.lots:
            currentDistance = geodistance(oldlot.lot.location.latitude, oldlot.lot.location.longitude,
                                          ilot.lot.location.latitude, ilot.lot.location.longitude)
            if currentDistance < bestDistance and ilot not in self.tried:
                bestDistance = currentDistance
                bestLot = ilot

        self.bestLot = bestLot
        # drive to the closest lot
        duration = bestDistance / self.speed
        arrival = now + duration
        self.drawing = True
        # self.waypoints.append(Waypoint(arrival, bestLot.lot.location.latitude, bestLot.lot.location.longitude))
        self.waypoints += get_route(oldlot.lot.location, bestLot.lot.location, now, self.speed)
        attempt = Attempt(arrival, 20, self)
        await bestLot.register(attempt)


class Car:
    def __init__(self, loc, manager, cli):
        self.lat = loc.latitude
        self.long = loc.longitude
        self.destX = 0
        self.destY = 0
        self.aDestX = 0
        self.aDestY = 0
        self.drawing = False
        self.speed = 60  # this is in ms^-1
        self.waypoints = []
        self.waypoints.append(Waypoint(time.time(), self.lat, self.long))
        self.manager = manager
        self.cli = cli

    def distance_to(self, x, y, now):
        lat, long = self.get_position(now)
        return geodistance(x, y, lat, long)

    def get_position(self, now):
        # if len(self.waypoints) > 1:
        #     latdiff = self.waypoints[-1].lat - self.waypoints[-2].lat
        #     longdiff = self.waypoints[-1].long - self.waypoints[-2].long
        #     timediff = self.waypoints[-1].time - self.waypoints[-2].time
        #     progress = (now - self.waypoints[-2].time) / timediff
        #     poslat = self.waypoints[-2].lat + (latdiff * progress)
        #     poslong = self.waypoints[-2].long + (longdiff * progress)
        #     return poslat, poslong
        # else:
        #     return self.lat, self.long

        if (len(self.waypoints)) == 1:
            return self.waypoints[0].lat, self.waypoints[0].long

        endTime = 0
        waypointIndex = 0

        while endTime < now:
            waypointIndex += 1
            if waypointIndex > len(self.waypoints) - 1:
                return 1.0, 1.0
            endTime = self.waypoints[waypointIndex].time

        self.drawing = True

        start = self.waypoints[waypointIndex - 1]
        end = self.waypoints[waypointIndex]

        latdiff = end.lat - start.lat
        longdiff = end.long - start.long
        timediff = end.time - start.time
        progress = (now - start.time) / timediff
        poslat = start.lat + (latdiff * progress)
        poslong = start.long + (longdiff * progress)
        return float(poslat), float(poslong)

    async def set_allocated_destination(self, lot):
        self.aDestX = lot.location.latitude
        self.aDestY = lot.location.longitude
        now = time.time()
        newtime = now + (self.distance_to(self.aDestX, self.aDestY, now) / self.speed)

        # cut the last waypoint short to car's current place and time
        self.waypoints[-1].time = now
        lat, long = self.get_position(now)
        self.waypoints[-1].lat = lat
        self.waypoints[-1].long = long

        # self.waypoints.append(Waypoint(newtime, self.aDestX, self.aDestY))
        self.waypoints += get_route(wsmodels.Location(lat, long), lot.location, self.waypoints[-1].time, self.speed)
        for w in self.waypoints:
            pass

        attempt = Attempt(newtime, 20, self)

        await self.manager.lotdict[lot.id].register(attempt)

    def park(self):
        logger.info("successfully parked user")
        self.drawing = False

    async def retry(self, now, oldlot):
        logger.info("too full for user")
        x, y = self.get_position(now)

        self.waypoints = []
        waiting = True
        self.drawing = False
        while waiting and not self.manager.stop_flag:
            await self.cli.send_parking_request(wsmodels.Location(float(x), float(y)), {})
            futs = [self.cli.receive(wsmodels.ParkingAllocationMessage), self.cli.receive(wsmodels.ErrorMessage)]
            (fut,), *_ = await asyncio.wait(futs, return_when=asyncio.FIRST_COMPLETED)
            newlot = fut.result()
            logger.debug('got result: {}'.format(newlot))
            if not isinstance(newlot, wsmodels.ErrorMessage):
                break
            await asyncio.sleep(1)
        logger.info("successfully reallocated to " + str(newlot.lot.id))
        self.waypoints.append(Waypoint(now, oldlot.lot.location.latitude, oldlot.lot.location.longitude))
        distance = geodistance(oldlot.lot.location.latitude, oldlot.lot.location.longitude,
                               newlot.lot.location.latitude, newlot.lot.location.longitude)
        self.waypoints.append(Waypoint(distance / self.speed,
                                       newlot.lot.location.latitude, newlot.lot.location.longitude))
        self.drawing = True
        self.set_allocated_destination(self.manager.lotdict[newlot.lot.id])


def get_route(start, end, now, speed):
    if False:
        distance = geodistance(start.latitude, start.longitude, end.latitude, end.longitude)
        newtime = distance / speed
        return [Waypoint(now + newtime, end.latitude, end.longitude)]
    else:
        hozdist = geodistance(start.latitude, start.longitude, end.latitude, start.longitude)
        verdist = geodistance(end.latitude, start.longitude, end.latitude, end.longitude)

        hoztime = hozdist / speed
        vertime = verdist / speed

        return [Waypoint(now + hoztime, end.latitude, start.longitude),
                Waypoint(now + hoztime + vertime, end.latitude, end.longitude)]


class Attempt:
    def __init__(self, arrival, duration, car):
        self.arrival = arrival
        self.duration = duration
        self.car = car


class ParkingLot:
    def __init__(self, lot: restmodels.ParkingLot, client: ParkingLotRest, available: int = 0):

        self.lot = lot
        self.attempts = []
        self.cars = {}
        self.lock = asyncio.Lock()

        if (self.lot.capacity < 1) or (available < 1):
            raise ValueError("Parking capacity/availability must be positive")

        if (not(isinstance(self.lot.capacity, int))) or (not(isinstance(available, int))):
            raise TypeError("Capacity/availability must be an integer")

        if available > self.lot.capacity:
            raise ValueError("Capacity has to be greater than available spaces")

        self.available: int = available
        self.client = client

    async def register(self, attempt: Attempt):
        now = time.time()
        asyncio.get_event_loop().create_task(attempt_routine(attempt.arrival - now,
                                                             attempt.car, self, attempt.duration))

    async def fill_space(self) -> bool:
        with (await self.lock):
            if self.available > 0:
                await self.client.update_available(self.lot.id, self.available - 1)
                self.available -= 1
                return True
            else:
                return False

    async def free_space(self) -> bool:
        with(await self.lock):
            if self.available < self.lot.capacity:
                await self.client.update_available(self.lot.id, self.available + 1)
                self.available += 1
                return True
            else:
                return False

    async def change_price(self, new_price):
        self.lot.price = new_price
        await self.client.update_price(self.lot.id, new_price)

    async def delete(self):
        await self.client.delete_lot(self.lot.id)

    async def change_availability(self, value):
        if value > self.lot.capacity | value < 0:
            raise ValueError("Availability must be positive and no greater than the capacity")

        if not(isinstance(value, int)):
            raise TypeError("Availability must be an integer")

        await self.client.update_available(self.lot.id, value)


async def car_routine(startt, start_loc, manager):
    await asyncio.sleep(startt)

    car_id = str(uuid4())
    cli = await CarWebsocket.create(base_url=manager.app_url.replace('http', 'ws') + "/ws", user_id=car_id)

    car = Car(start_loc, manager, cli)
    manager.cars.append(car)

    # x, y = car.aDestX, car.aDestY
    dest = manager.point_to_location(random.randint(0, manager.width), random.randint(0, manager.height))
    # TODO this was originally setting everything to 0 - do this properly later

    # request a parking space
    logger.info(f'requesting allocation for car {car_id}')
    waiting = True
    while waiting and not manager.stop_flag:
        await cli.send_parking_request(dest, {})
        car.drawing = True

        futs = [cli.receive(wsmodels.ParkingAllocationMessage), cli.receive(wsmodels.ErrorMessage)]
        (fut,), *_ = await asyncio.wait(futs, return_when=asyncio.FIRST_COMPLETED)
        space = fut.result()
        logger.debug('got result: {}'.format(space))
        if not isinstance(space, wsmodels.ErrorMessage):
            break
        await asyncio.sleep(1)

    if not manager.stop_flag:
        logger.info(f"allocation recieved: for car {car_id}: '{space._type}'")
        await car.set_allocated_destination(space.lot)

        await cli.send_parking_acceptance(space.lot.id)

    if not manager.stop_flag:

        await cli.receive(wsmodels.ConfirmationMessage)

    while not manager.stop_flag:
        # Send the location of the car at time intervals, while listening for deallocation
        try:
            deallocation = await asyncio.shield(asyncio.wait_for(cli.receive(wsmodels.ParkingCancellationMessage), 3))
        except futures.TimeoutError:
            deallocation = None
        if deallocation is not None:
            logger.info("Recieved deallocation")
            # TODO handle deallocation
        logger.info(f'<Car {car_id}>: heartbeat ** send location')
        x, y = car.get_position(time.time())
        await cli.send_location(wsmodels.Location(float(x), float(y)))


async def space_routine(startt, start_loc, capacity, name, price, available, manager):
    await asyncio.sleep(startt)

    cli = ParkingLotRest(manager.app_url, httpclient.AsyncHTTPClient())
    lot = restmodels.ParkingLot(capacity, name, price, start_loc)
    logger.debug("creating lot...")
    response = await cli.create_lot(lot)
    lot.id = response
    logger.info("created lot {}".format(response))

    logger.info("created lot {}".format(response))

    simlot = ParkingLot(lot, cli, capacity)
    manager.lotdict[lot.id] = simlot
    manager.lots.append(simlot)


async def rogue_routine(startt, loc, dest, manager):
    await asyncio.sleep(startt)
    now = time.time()
    if manager.stats[Stats.FIRSTROGUESTARTTIME] is None:
        manager.stats[Stats.FIRSTROGUESTARTTIME] = now
    rogue = await RogueCar.create_rogue(time.time(), loc, dest, manager)
    rogue.drawing = True
    manager.rogues.append(rogue)


async def attempt_routine(delay, car, plot: ParkingLot, duration):
    await asyncio.sleep(delay)
    success = await plot.fill_space()
    now = time.time()
    if success:
        car.park()
        await asyncio.sleep(duration)
        await plot.free_space()
    else:
        await car.retry(now, plot)

if __name__ == '__main__':
    sim = SimManager(2000, 20, 70, 50, 50, 1000, 500, 2, 4, 100, "127.0.0.1")
    asyncio.ensure_future(sim.run())
    asyncio.ensure_future(sim.stop(60))
    asyncio.get_event_loop().run_forever()
