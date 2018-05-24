# flake8: noqa
SETUP_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS cube ;
CREATE EXTENSION IF NOT EXISTS earthdistance;
"""

PARKINGLOTS_CREATE_TABLE = """
CREATE TABLE ParkingLots (
	id              serial PRIMARY KEY,
	name            text NOT NULL,
    capacity        integer NOT NULL,
	lat             float NOT NULL,
	long            float NOT NULL,
	price           float NOT NULL,
	num_available   integer NOT NULL,
	num_allocated   integer NOT NULL
);

CREATE INDEX 
ON ParkingLots USING gist (ll_to_earth(lat, long));
"""

PARKINGLOTS_DROP_TABLE = """
DROP TABLE IF EXISTS ParkingLots;
"""

ALLOCATIONS_CREATE_TABLE = """
CREATE TABLE Allocations (
    user_id text NOT NULL,
    park_id integer NOT NULL,

    PRIMARY KEY(user_id),
    FOREIGN KEY(park_id) REFERENCES ParkingLots(id)
);
"""

ALLOCATIONS_DROP_TABLE = """
DROP TABLE IF EXISTS Allocations;
"""

PARKINGLOTS_INSERT = """
INSERT INTO ParkingLots (name, capacity, lat, long, price, num_available, num_allocated)
VALUES ($1, $2, $3, $4, $5, $6, $7)
RETURNING id;
"""

PARKINGLOTS_DELETE = """
DELETE FROM ParkingLots where id=$1
RETURNING id;
"""

PARKINGLOTS_UPDATE_AVAILABILITY = """
UPDATE ParkingLots
SET num_available = $2
WHERE id = $1
RETURNING id;
"""

PARKINGLOTS_UPDATE_PRICE = """
UPDATE ParkingLots
SET price = $2
WHERE id = $1
RETURNING id;
"""

PARKINGLOTS_INCREMENT_ALLOCATION = """
UPDATE ParkingLots
SET num_allocated = num_allocated + 1
WHERE id = $1
 AND num_allocated < num_available
"""

PARKINGLOTS_SELECT_WITHIN_DISTANCE = """
SELECT *
FROM (
    SELECT
        *, earth_distance(ll_to_earth($1, $2), ll_to_earth(lat, long)) as distance
    FROM
        ParkingLots
    WHERE
        earth_box(ll_to_earth($1, $2), $3) @> ll_to_earth(lat, long) 
        AND num_available > num_allocated
        AND earth_distance(ll_to_earth($1, $2), 
                 ll_to_earth(lat, long)) < $3
    ) as p
ORDER BY distance;
"""

PARKINGLOTS_SELECT_WITHIN_DISTANCE_WITH_EXCLUSIONS = """
SELECT *
FROM (
    SELECT
        *, earth_distance(ll_to_earth($1, $2), ll_to_earth(lat, long)) as distance
    FROM
        ParkingLots
    WHERE
        earth_box(ll_to_earth($1, $2), $3) @> ll_to_earth(lat, long) 
        AND num_available > num_allocated
        AND earth_distance(ll_to_earth($1, $2), 
                 ll_to_earth(lat, long)) < $3
    ) as p
WHERE id <> any($4::int[])
ORDER BY distance;
"""

ALLOCATIONS_INSERT = """
INSERT INTO Allocations (user_id, park_id)
VALUES ($1, $2)
"""
