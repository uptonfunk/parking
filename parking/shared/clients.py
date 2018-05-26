from tornado import httpclient
import parking.shared.rest_models as rest_models
from parking.shared.util import serialize_model
import json

HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}


class ParkingLotRest(object):
    """
    An async client for the parking lot REST API
    """

    def __init__(self, base_url, http_client):
        self.client = http_client
        self.rest_url = f"{base_url}/spaces"

    async def create_lot(self, lot: rest_models.ParkingLot):
        request = httpclient.HTTPRequest(self.rest_url, body=serialize_model(lot), headers=HEADERS, method='POST')
        response = await self.client.fetch(request)
        return rest_models.ParkingLotCreationResponse(**json.loads(response.body)).id

    async def update_available(self, lot_id: int, available: int):
        msgbody = serialize_model(rest_models.ParkingLotAvailableMessage(available))
        request = httpclient.HTTPRequest(f"{self.rest_url}/{lot_id}/available", body=msgbody, headers=HEADERS,
                                         method='POST')
        await self.client.fetch(request)

    async def update_price(self, lot_id: int, price: float):
        msgbody = serialize_model(rest_models.ParkingLotPriceMessage(price))
        request = httpclient.HTTPRequest(f"{self.rest_url}/{lot_id}/price", body=msgbody, headers=HEADERS,
                                         method='POST')
        await self.client.fetch(request)

    async def delete_lot(self, lot_id: int):
        request = httpclient.HTTPRequest(f"{self.rest_url}/{lot_id}", method='DELETE')
        await self.client.fetch(request)
