"""Lt. 3 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

FLOOR = "3"
LEVEL = 3
ROOMS_CSV = "csv/lantai3.csv"

# Area yang bisa dilewati 
OUTLINE = [
    (0, 47.62, 96, 50),
    (0, 40, 96, 60),      
    (40, 0, 60, 40),      
]

# Area yang tidak bisa dilewati 
VOIDS = [
    # (0, 40, 50, 47.62)
]

# Titik awal user 
START = (50, 55)

# Patch tambahan untuk ruangan yang berbentuk tidak sederhana.
# (Belum diperlukan berdasarkan data CSV saat ini.)
PART_OF = {}

# Lift dan tangga pada Lantai 3.
LINKS = {
    "3001": {"up": "4", "down": "2", "cost": 10},  # Lift Barat
    "3002": {"up": "4", "down": "2", "cost": 10},  # Lift Timur
    "3003": {"up": "4", "down": "2", "cost": 20},  # Tangga Barat
    "3004": {"up": "4", "down": "2", "cost": 20},  # Tangga Utara
    "3005": {"up": "4", "down": "2", "cost": 20},  # Tangga Timur
    "3006": {"up": "4", "down": "2", "cost": 20},  # Tangga Selatan
}

# Gambar denah untuk overlay.
IMAGE = "denah/lantai3.jpeg"

# Kalibrasi gambar (sementara mengikuti sistem koordinat yang sama).
CALIBRATION = (80, 175)