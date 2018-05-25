from tornado import httpclient
import parking.shared.rest_models as restmodels
from parking.shared.util import serialize_model
import json

HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}


class ParkingLotRest(object):
    def __init__(self, base_url, http_client):
        self.client = http_client
        self.rest_url = "{}/spaces".format(base_url)

    async def set_lot(self, lot: restmodels.ParkingLot):
        request = httpclient.HTTPRequest(self.rest_url, body=serialize_model(lot), headers=HEADERS, method='POST')
        response = await self.client.fetch(request)
        if restmodels.ParkingLotCreationResponse(**json.loads(response.body)).id != 1:
            raise Exception()
        return response

    async def set_available(self, pid: int, available: int):
        msgbody = serialize_model(restmodels.ParkingLotAvailableMessage(available))
        request = httpclient.HTTPRequest(self.rest_url + "/:" + str(pid) + "/available", body=msgbody, headers=HEADERS,
                                         method='POST')
        await self.client.fetch(request)

    async def set_price(self, pid: int, price: float):
        msgbody = serialize_model(restmodels.ParkingLotPriceMessage(price))
        request = httpclient.HTTPRequest(self.rest_url + "/:" + str(pid) + "/price", body=msgbody, headers=HEADERS,
                                         method='POST')
        await self.client.fetch(request)

    async def delete(self, pid: int):
        request = httpclient.HTTPRequest(self.rest_url + "/" + str(pid), method='DELETE')
        await self.client.fetch(request)
