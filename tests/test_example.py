from . import example as ex1
from parking import example as m

def test_example_load_from_tests_package():
    assert ex1()

def test_example_load_from_parking():
    assert m.example()
