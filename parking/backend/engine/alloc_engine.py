import logging
from typing import Optional
from geopy.distance import distance
from parking.backend.db.dbaccess import DbAccess
from parking.shared.rest_models import ParkingLot
from parking.shared.location import Location
from parking.shared.ws_models import ParkingRequestMessage

logger = logging.getLogger('backend')


class AllocationEngine():
    def __init__(self, dba: DbAccess, user_sessions: 'UserSessions') -> None:
        self.dba = dba
        self.user_sessions = user_sessions

    async def handle_allocation_request(self, user_id: str, request: ParkingRequestMessage) -> Optional[ParkingLot]:
        rejections = self.user_sessions.get_user(user_id).rejections
        lots = await self.dba.get_available_parking_lots(request.location, 100, rejections)

        # Just take the first lot for now...
        if lots:
            lot = lots[0]
            return ParkingLot(lot['capacity'], lot['name'], lot['price'],
                              Location(lot['lat'], lot['long']), id=lot['id'])
        else:
            return None

    async def commit_allocation(self, user_id: str, park_id: int) -> bool:
        success = await self.dba.allocate_parking_lot(user_id, park_id)
        if not success:
            logger.warning('Failed to allocate parking lot {} to user {}'.format(park_id, user_id))
        return success

    async def remove_allocation(self, user_id: str) -> None:
        self.user_sessions.deallocate(user_id)
        await self.dba.delete_allocation(user_id)
        logger.info('Removed allocation for {}'.format(user_id))

    async def delete_allocation(self, user_id: str) -> None:
        await self.dba.delete_allocation(user_id)
        logger.info('Deleted allocation for {}'.format(user_id))

    async def recalculate_allocations(self, park_id: int) -> None:
        # Deallocate users if parking spaces are taken
        # Calculate the allocated users and find the furthest away
        lot = await self.dba.get_parking_lot(park_id)
        user_sessions = self.user_sessions
        overflow = lot['num_allocated'] - lot['num_available']

        def sort_func(elem):
            user_loc = user_sessions.get_user(elem['user_id']).location
            return distance((lot['lat'], lot['long']), (user_loc.latitude, user_loc.longitude))

        if overflow > 0:
            allocations = await self.dba.get_parking_lot_allocations(park_id)
            allocations.sort(key=sort_func, reverse=True)
            for alloc in allocations[:overflow]:
                await self.remove_allocation(alloc['user_id'])
