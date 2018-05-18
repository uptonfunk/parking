import asyncio
import websockets
import json
import random
import numpy as np
import requests

cars = []
resturl = 'https://a6fbc847-6668-47c6-8169-2effb5444a13.mock.pstmn.io/spaces'


class Map:
    def __init__(self, lat_range: tuple, long_range: tuple,
                 no_spaces: int, min_spaces: int, max_spaces: int):
        self.lat_min = round(lat_range[0])
        self.lat_max = round(lat_range[1])
        self.long_min = round(long_range[0])
        self.long_max = round(long_range[1])
        self.x_range = self.lat_max - self.lat_min
        self.y_range = self.long_max - self.long_min
        self.grid = np.empty([self.y_range, self.x_range], dtype=object)
        # Let's make some spaces!
        count = 0
        random.seed()
        while count < no_spaces:
            for r in range(50):
                x = random.randint(0, self.x_range-1)
                y = random.randint(0, self.y_range-1)
                if self.grid[y][x] is None:
                    break
                elif self.grid[y][x] is not None & r == 49:
                    continue

            max_al = min(max_spaces, (no_spaces - count))
            if max_al < min_spaces:
                n = max_al
            else:
                n = random.randint(min_spaces, max_al)
            self.grid[y][x] = ParkingLot(x, y, n, n, 0)
            count += n

    def get_parking_lots(self):
        return self.grid[self.grid is not None].size

    def get_total_capacity(self):
        count = 0
        for ele in self.grid[self.grid is not None]:
            count += ele.get_capacity()
        return count


class Car:
    def __init__(self, lat, long):
        self.lat = lat
        self.long = long
        self.destX = 0
        self.destY = 0
        self.aDestX = 0
        self.aDestY = 0

    def get_location(self):
        return self.lat, self.long

    def set_initial_destination(self, x, y):
        self.destX = x
        self.destY = y

    def get_initial_destination(self):
        return self.destX, self.destY

    def set_allocated_destination(self, x, y):
        self.aDestX = x
        self.aDestY = y

    def get_allocated_destination(self):
        return self.aDestX, self.aDestY


class ParkingLot:
    def __init__(self, lat: float, long: float,
                 capacity: int, name: str, price: int, available: int = 0):
        self.lat: float = lat
        self.long: float = long
        self.capacity: int = capacity
        self.available: int = available
        self.cars = []
        self.name = name
        self.price = price
        self.id = None

        body = {}
        data = {"capacity": capacity}
        location = {"latitude": lat, "longitude": long}
        data["location"] = location
        data["name"] = name
        data["price"] = price
        body["data"] = data

        status = requests.post(resturl, data=json.dumps(data))
        self.id = json.loads(status.text)["id"]
        print(self.id)

    def get_location(self):
        return self.lat, self.long

    def get_capacity(self):
        return self.capacity

    def get_available(self):
        return self.available

    def allocate_space(self, car_id: int) -> bool:
        # TODO should there be less available as soon as an allocation is made?
        # TODO I think this should only be when a car parks
        if (car_id not in self.cars) & self.available > 0:
            self.cars.append(car_id)
            self.available -= 1
            return True
        else:
            return False

    def fill_space(self) -> bool:
            if self.available > 0:
                self.available -= 1
                data = {"available": self.available}
                status = requests.post(resturl + "/:" + self.id, data=json.dumps(data))
                if status.status_code != "200":
                    pass
                    # TODO server error handling
                return True
            else:
                return False

    def free_space(self) -> bool:
        if self.available < self.capacity:
            self.available += 1
            return True
        else:
            return False

    def change_price(self, new_price):
        self.price = new_price
        data = {"price": self.price}
        # TODO clean up repeated code
        status = requests.post(resturl + "/:" + self.id, data=json.dumps(data))
        if status.status_code != "200":
            pass
            # TODO server error handling

    def delete(self):
        # TODO actual deletion
        status = requests.delete(resturl + "/:" + self.id)
        if status.status_code != "200":
            pass
            # TODO server error handling


async def car_routine(startt, startx, starty):
    await asyncio.sleep(startt)

    # TODO replace json with [de]serialization functions

    async with websockets.connect('ws://localhost:8765') as websocket:
        # Create a car
        car = Car(startx, starty)
        cars.append(car)

        # Send the destination of the car to the server
        x, y = car.get_initial_destination()
        await websocket.send(json.dumps({'location': {'latitude': x, 'longitude': y}, 'preferences': {}, '_type': 2},
                                        indent=4,
                                        separators=(',', ': ')))

        # Recieve the parking allocation information
        space = await websocket.recv()
        space = json.loads(space)
        car.set_allocated_destination(space['location']['longitude'], space['location']['latitude'])
        print(car.get_allocated_destination())

        while True:
            # Send the location of the car at time intervals
            x, y = car.get_location()
            await asyncio.sleep(3)
            await websocket.send(json.dumps({'location': {'latitude': x, 'longitude': y}, '_type': 1},
                                            indent=4,
                                            separators=(',', ': ')))


async def space_routine(startt, lat, long, capacity, name, price, available):
    await asyncio.sleep(startt)
    ParkingLot(lat, long, name, capacity, price=price, available=available)

# mymap = Map((0, 1000), (0, 1000), 3000, 5, 50)
car_tasks = [asyncio.ensure_future(car_routine(0, 2, 2)),
             asyncio.ensure_future(car_routine(0, 4, 4)),
             asyncio.ensure_future(car_routine(5, 6, 6))]
# space_tasks = [asyncio.ensure_future(space_routine(0, 0, 0, 10, "space", 0, 10))]
space_tasks = []
tasks = car_tasks + space_tasks

asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
