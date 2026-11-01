"""Lt. 3 settings. Units are meters. Coordinate system: see README.md.
Sizes are estimates, about +/- 0.5 m."""

# identitas no lt 
FLOOR = "3"
# urutan tinggi lantai 
LEVEL = 3
ROOMS_CSV = "csv/lantai3.csv"

# Area yang bisa dilewati/batas luar bangunan
OUTLINE = [
    (0, 47.62, 96, 50),
    (0, 40, 96, 60),      
    (96, 50, 99.45, 60),   # Tangga Timur at the east end
    (40, 0, 60, 40),      
]

# Titik awal user pas di lt itu 
START = (50, 55)

# Lift dan tangga pada Lantai 3.
LINKS = {
    "03001": {"up": "5", "down": "2", "cost": 10},  # Lift Barat -> Lt. 5 / Lt. 2
    "03002": {},  # Lift Timur tidak akses Lt. 3
    "03003": {"up": "4", "down": "2A", "cost": 20},  # Tangga Barat
    "03004": {"up": "4", "down": "2", "cost": 20},  # Tangga Utara
    "03005": {"up": "4", "down": "2A", "cost": 20},  # Tangga Timur
    "03006": {"up": "4", "cost": 20},  # Tangga Selatan (Lt. 2 Selatan is not modeled)
}

# Gambar denah untuk overlay.
IMAGE = "denah/lantai3.jpeg"

# Kalibrasi gambar (sementara mengikuti sistem koordinat yang sama).
CALIBRATION = (80, 175)