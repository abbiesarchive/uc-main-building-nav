"""Lt. 2 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "2"                       # text, same as the floor column in the csv
LEVEL = 2                         # sort order of floors (Lt. 2A would be 2.5)
ROOMS_CSV = "csv/lantai2.csv"

# Where people can be: rectangles (xmin, ymin, xmax, ymax). Lt. 2 is the top bar only.
OUTLINE = [(0, 40, 99.45, 60)]
# Holes in the floor. Nobody can stand there.
VOIDS = [(43.6, 40, 56.8, 46.4)]
# Where the dot starts (x, y).
START = (50, 55)

# Open patches that belong to a room: room_id -> a point inside the patch.
PART_OF = {"203": (86, 59), "226": (32, 48.7), "225": (24, 42)}

# Stairs and lifts on THIS floor: room_id -> where it leads.
#   "up" / "down" = the floor you arrive on, "cost" = walking penalty for the route search.
# The other floor's file must have the matching stair going back (check_floors.py tests this).
LINKS = {
    "02001": {"up": "2A", "down": "1", "cost": 10},   # lifts: assumed to stop at every level
    "02002": {"up": "2A", "down": "1", "cost": 10},
    "02003": {"up": "2A", "cost": 8},                 # end stairs: half flight, unconfirmed
    "02005": {"up": "2A", "cost": 8},
    "02004": {"up": "3", "cost": 20},                 # Tangga Utara skips 2A
    "02006": {"up": "2A", "cost": 8},                 # open stairs by the void: half flight
    "02007": {"up": "2A", "cost": 8},
    "02008": {"up": "2A", "cost": 8},
}

# Only for the overlay check on the plan image (plot_floor.py ... overlay).
IMAGE = "denah/lantai2.jpeg"
CALIBRATION = (80, 175)           # pixel of the west column axis, pixel of the top wall
