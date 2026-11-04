"""Lt. 2A settings (split level, half a floor above Lt. 2). Units are meters.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "2A"
LEVEL = 2.5                       # between Lt. 2 and Lt. 3
ROOMS_CSV = "csv/lantai2A.csv"

OUTLINE = [(0, 40, 99.45, 60)]
# The two lift shafts are blocked too: the lifts do not stop on Lt. 2A (use them on Lt. 2).
VOIDS = [(43.5, 40, 56.7, 45.9), (46.1, 52.2, 49.1, 57.8), (54.1, 49.6, 57.1, 57.8)]
START = (50, 55)

# The core is shared with Lt. 2, so its rows live once in csv/lantai2.csv.
# Listed here, they are loaded on this floor too (Tangga Utara 02004 is Lt. 2 only).
SHARED = {"2": ["02003", "02005", "02006", "02007", "02008",
                "002001", "002002", "0002001"]}

# No lifts on this floor: they stop on Lt. 2 only. The stairs below are half flights
# down to Lt. 2 (unconfirmed for the end stairs 02003 / 02005). Each one matches the
# "up" entry in lantai2.py.
LINKS = {
    "02003": {"up": "3", "down": "2", "cost": 10},   # Tangga Barat goes on to Lt. 3
    "02005": {"up": "3", "down": "2", "cost": 10},   # Tangga Timur goes on to Lt. 3
    "02006": {"down": "2", "cost": 10},
    "02007": {"down": "2", "cost": 10},
    "02008": {"down": "2", "cost": 10},
}

# Rooms are closed: you can only stand in corridors, open lobbies, stairs and lifts.
# (Doors are not modeled yet, so you cannot go inside a room.)
ROOMS_WALKABLE = False
OPEN_ROOMS = ["LOBBY2A"]          # rooms that are really open space

IMAGE = "denah/lantai2a.jpeg"
CALIBRATION = (68, 171)
