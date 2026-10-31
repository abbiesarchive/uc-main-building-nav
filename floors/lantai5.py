"""Lt. 5 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "5"
LEVEL = 5
ROOMS_CSV = "csv/lantai5.csv"

# Where people can be: rectangles (xmin, ymin, xmax, ymax).
OUTLINE = [
    (-1.5, 39.5, 39.7, 47.0),
    (0.0, 47.0, 99.45, 60.0),
    (39.7, 1.7, 60.3, 47.0),
    (60.3, 40.4, 78.9, 47.0),
    (78.9, 39.5, 99.45, 47.0),
    (38.2, 1.7, 39.7, 39.5),
    (60.3, 4.6, 62.0, 40.4),
]

# Holes in the floor. Nobody can stand there.
VOIDS = [
    (38.2, 1.7, 39.7, 39.5),
    (60.3, 4.6, 62.0, 40.4),
]

# Where the dot starts (x, y).
START = (51.8, 48.5)

# Open patches that belong to a room: room_id -> a point inside the patch.
PART_OF = {
    "513": (64.5, 47.5),
    "510": (89.0, 47.5),
}

# Stairs and lifts on THIS floor: room_id -> where it leads.
# "up" / "down" = the floor you arrive on, "cost" = walking penalty for the route search.
# The other floor's file must have the matching stair going back (check_floors.py tests this).
LINKS = {
    "05001": {"up": "6", "down": "4", "cost": 10},  # Lift Barat
    "05002": {"up": "6", "down": "4", "cost": 10},  # Lift Timur
    "05003": {"up": "6", "down": "4", "cost": 8},   # Tangga Barat
    "05004": {"up": "6", "down": "4", "cost": 8},   # Tangga Utara
    "05005": {"up": "6", "down": "4", "cost": 8},   # Tangga Timur
    "05006": {"up": "6", "down": "4", "cost": 8},   # Tangga Selatan
}

# Only for the overlay check on the plan image (plot_floor.py ... overlay).
IMAGE = "denah/lantai5.jpeg"
CALIBRATION = (70, 188)