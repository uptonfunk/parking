import pytest 
from simulation.simulation import ParkingLot
import json

def test_AddNew():
    lot = ParkingLot(1.0,0.5,500,"my_parking_lot",1.5,500)
    assert lot.data_to_send == json.dumps({"data": {"capacity": 500, "location": {"latitude": 1.0,
                    "longitude": 0.5
                    },
                    "name": "my_parking_lot",
                    "price": 1.5}
            })

def test_AddZeroSpaces():
    with pytest.raises(ValueError):
        ParkingLot(1.0,0.5,0,"my_parking_lot",1.5,0)

def test_AddNegativeSpaces():
    with pytest.raises(ValueError):
        ParkingLot(1.0,0.5,-10,"my_parking_lot",1.5,-10)
        
def test_AddDecimalSpaces():
    with pytest.raises(TypeError):
        ParkingLot(1.0,0.5,3.5,"my_parking_lot",1.5,3.5)
        
def test_AddBigAvailability():
    with pytest.raises(ValueError):
        ParkingLot(1.0,0.5,10,"my_parking_lot",1.5,20)
        
def test_AddTwoSpaces():
    lot = ParkingLot(1.0,0.5,500,"my_parking_lot",1.5,500)
    with pytest.raises(RuntimeError):
        ParkingLot(1.0,0.5,10,"my_parking_lot",1.5,10)
        
def test_ChangingAvailability():
    lot = ParkingLot(1.0,0.5,500,"my_parking_lot",1.5,500)
    lot.change_availability(250)
    assert lot.available == 250