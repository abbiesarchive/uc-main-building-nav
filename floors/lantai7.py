"""Lt. 7 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "7"
LEVEL = 7
ROOMS_CSV = "csv/lantai7.csv"

# Area yang bisa dilewati 
OUTLINE = [
    (0, 47.62, 96, 50),
    (0, 40, 96, 60),      
    (40, 0, 60, 40),      
]

# Titik awal user 
START = (50, 55)

# Lift dan tangga pada Lantai 7.
LINKS = {
    "07001": {"down": "6", "cost": 10},  # Lift Barat
    "07002": {"down": "6", "cost": 10},  # Lift Timur
    "07003": {"down": "6", "cost": 20},  # Tangga Barat
    "07004": {"down": "6", "cost": 20},  # Tangga Utara
    "07005": {"down": "6", "cost": 20},  # Tangga Timur
    "07006": {"down": "6", "cost": 20},  # Tangga Selatan
}


# Gambar denah untuk overlay.
IMAGE = "denah/lantai7.jpeg"

# Kalibrasi gambar (sementara mengikuti sistem koordinat yang sama).
CALIBRATION = (80, 175)