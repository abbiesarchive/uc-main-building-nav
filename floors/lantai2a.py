"""Lt. 2A settings (split level, half a floor above Lt. 2). Units are meters.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "2A"
LEVEL = 2.5                       # between Lt. 2 and Lt. 3
ROOMS_CSV = "csv/lantai2A.csv"

OUTLINE = [(0, 40, 99.45, 60)]
VOIDS = [(43.5, 40, 56.7, 45.9)]
START = (50, 55)

# The core is shared with Lt. 2, so its rows live once in csv/lantai2.csv.
# Listed here, they are loaded on this floor too (Tangga Utara 02004 is Lt. 2 only).
SHARED = {"2": ["02001", "02002", "02003", "02005", "02006", "02007", "02008",
                "002001", "002002", "0002001"]}

# Lifts go on to Lt. 3. The other stairs are half flights down to Lt. 2 (unconfirmed
# for the end stairs 02003 / 02005). Each one matches the "up" entry in lantai2.py.
LINKS = {
    "02001": {"up": "3", "down": "2", "cost": 10},
    "02002": {"up": "3", "down": "2", "cost": 10},
    "02003": {"down": "2", "cost": 8},
    "02005": {"down": "2", "cost": 8},
    "02006": {"down": "2", "cost": 8},
    "02007": {"down": "2", "cost": 8},
    "02008": {"down": "2", "cost": 8},
}

IMAGE = "denah/lantai2a.jpeg"
CALIBRATION = (68, 171)
