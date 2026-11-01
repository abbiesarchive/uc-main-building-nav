"""Loads every floor file in this folder (floors/lantai2.py, floors/lantai3.py, ...).
Adding a floor means adding a file here. Nothing else is edited.

A floor file must define: FLOOR, LEVEL, ROOMS_CSV, OUTLINE, START.
It may define: VOIDS, PART_OF, LINKS, SHARED, ROOMS_WALKABLE, OPEN_ROOMS, IMAGE, CALIBRATION. See README.md.
"""
import importlib
import pkgutil
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the project folder

REQUIRED = ["FLOOR", "LEVEL", "ROOMS_CSV", "OUTLINE", "START"]
OPTIONAL = {"VOIDS": [], "PART_OF": {}, "LINKS": {}, "SHARED": {}, "ROOMS_WALKABLE": False, "OPEN_ROOMS": [], "IMAGE": None, "CALIBRATION": None}

# ini untuk simpan data dari function load_all biar ga perlu load ulang tiap kali dipanggil
@lru_cache
# ini untuk load semua konfigurasi lantai yg ada di folder floors, biar bisa dipake di file lain
def load_all():
    """{floor: settings module}, lowest LEVEL first."""
    found = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        missing = [name for name in REQUIRED if not hasattr(module, name)]
        if missing:
            raise ValueError(f"floors/{info.name}.py is missing: {', '.join(missing)}")
        for name, default in OPTIONAL.items():
            if not hasattr(module, name):
                setattr(module, name, default.copy() if hasattr(default, "copy") else default)
# kalo ada lantai yg sama di file lain, error
        if module.FLOOR in found:
            raise ValueError(f"Floor {module.FLOOR!r} is defined in two files in floors/")
# modul dimasukin ke dictionary agar bisa diakses dari luar, key = lantai, value = module
        found[module.FLOOR] = module
# untuk urutkan semua lantai berdasarkan level 
    return dict(sorted(found.items(), key=lambda item: item[1].LEVEL))

# untuk ambil konfigurasi 1 lantai 
def get_floor(floor):
    return load_all()[floor]
