"""Lt. 4 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "4"
LEVEL = 4
ROOMS_CSV = "csv/lantai4.csv"

# Area yang bisa dilewati 
OUTLINE = [
    (0, 47.62, 96, 50),
    (0, 40, 96, 60),      
    (40, 0, 60, 40),      
]

# Titik awal user 
START = (50, 55)

# Lift dan tangga pada Lantai 4.
LINKS = {
    "04001": {"up": "5", "down": "3", "cost": 10},  # Lift Barat
    "04002": {"up": "5", "down": "3", "cost": 10},  # Lift Timur
    "04003": {"up": "5", "down": "3", "cost": 20},  # Tangga Barat
    "04004": {"up": "5", "down": "3", "cost": 20},  # Tangga Utara
    "04005": {"up": "5", "down": "3", "cost": 20},  # Tangga Timur
    "04006": {"up": "5", "down": "3", "cost": 20},  # Tangga Selatan
}

# Gambar denah untuk overlay.
IMAGE = "denah/lantai4.jpeg"

# Kalibrasi gambar (sementara mengikuti sistem koordinat yang sama).
CALIBRATION = (80, 175)