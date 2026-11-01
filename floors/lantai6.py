"""Lt. 6 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "6"
LEVEL = 6
ROOMS_CSV = "csv/lantai6.csv"

# Where people can be: rectangles (xmin, ymin, xmax, ymax).
OUTLINE = [
    (0.0, 40.0, 99.45, 60.0),   # Sayap atas penuh dari X=0 sampai 99.45
    (39.7, 0.0, 60.3, 40.0),    # Sayap bawah mulai dari Y=0.0 sampai 40.0
]

# Holes in the floor. Nobody can stand there. (Dikosongkan agar bersih dan konsisten dengan Lt. 4 & 5)
VOIDS = []

# Where the dot starts (x, y).
START = (51.8, 48.5)

# Open patches that belong to a room: room_id -> a point inside the patch.
PART_OF = {}

# Stairs and lifts on THIS floor: room_id -> where it leads.
# "up" / "down" = the floor you arrive on, "cost" = walking penalty for the route search.
# Terhubung ke Lantai 7 (atas) dan Lantai 5 (bawah)
LINKS = {
    "06001": {},  # Lift Barat
    "06002": {"up": "7", "down": "4", "cost": 10},  # Lift Timur
    "06003": {"up": "7", "down": "5", "cost": 8},   # Tangga Barat
    "06004": {"up": "7", "down": "5", "cost": 8},   # Tangga Utara
    "06005": {"up": "7", "down": "5", "cost": 8},   # Tangga Timur
    "06006": {"up": "7", "down": "5", "cost": 8},   # Tangga Selatan
}

# Only for the overlay check on the plan image (plot_floor.py ... overlay).
IMAGE = "denah/lantai6.jpeg"
CALIBRATION = (66, 210)