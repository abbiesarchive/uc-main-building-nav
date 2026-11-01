"""Lt. 1 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "1"
LEVEL = 1
ROOMS_CSV = "csv/lantai1.csv"

# Where people can be: rectangles (xmin, ymin, xmax, ymax).
OUTLINE = [
    (0.0, 40.0, 99.45, 60.0),   # Sayap atas penuh dari X=0 sampai 99.45
    (39.7, 0.0, 60.3, 40.0),    # Sayap bawah mulai dari Y=0.0 sampai 40.0
]

# Holes in the floor. Nobody can stand there.
VOIDS = [
    
]

# Where the dot starts (x, y).
START = (50.0, 45.0)

# Open patches that belong to a room: room_id -> a point inside the patch.
PART_OF = {
    # "10": (52.25, 59.0),        # UC Main Building Lobby
    # "11": (50.0, 38.0),         # UC Plaza
}

# Stairs and lifts on THIS floor: room_id -> where it leads.
# "up" / "down" = the floor you arrive on, "cost" = walking penalty for the route search.
# The other floor's file must have the matching stair going back (check_floors.py tests this).
LINKS = {
    "01001": {"up": "2", "down": None, "cost": 6},   # Lift Barat Lt 1
    "01002": {"up": "2", "down": None, "cost": 6},   # Lift Timur Lt 1
    "01003": {"up": "2", "down": None, "cost": 10},  # Tangga Barat Lt 1
    "01004": {"up": "2", "down": None, "cost": 10},  # Tangga Utara Lt 1
    "01005": {"up": "2", "down": None, "cost": 10},  # Tangga Timur Lt 1
    "01006": {},  # Tangga Selatan: no steps on the plan, Lt. 2 Selatan is not modeled
}

# Only for the overlay check on the plan image (plot_floor.py ... overlay).
IMAGE = "denah/lantai1.jpeg"
CALIBRATION = (0, 0)