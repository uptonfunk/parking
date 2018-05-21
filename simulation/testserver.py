import asyncio
import websockets
from parking.shared.ws_models import *


async def hello(websocket, path):

    # receive a request
    request = await websocket.recv()
    # request = json.loads(request)
    # message = deserialize_ws_message(request)

    #send an allocation
    message = ParkingAllocationMessage(ParkingLot(1, "x", 1.0, Location(200.0, 300.0)))
    await websocket.send(json.dumps(attr.asdict(message)))

    while True:
        await websocket.recv()

start_server = websockets.serve(hello, 'localhost', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
