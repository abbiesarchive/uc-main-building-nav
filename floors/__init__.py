"""Loads every floor file in this folder (floors/lantai2.py, floors/lantai3.py, ...).
Adding a floor means adding a file here. Nothing else is edited.

A floor file must define: FLOOR, LEVEL, ROOMS_CSV, OUTLINE, START.
It may define: VOIDS, PART_OF, LINKS, SHARED, IMAGE, CALIBRATION. See README.md.
"""
import importlib
import pkgutil
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the project folder

REQUIRED = ["FLOOR", "LEVEL", "ROOMS_CSV", "OUTLINE", "START"]
OPTIONAL = {"VOIDS": [], "PART_OF": {}, "LINKS": {}, "SHARED": {}, "IMAGE": None, "CALIBRATION": None}


@lru_cache
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
        if module.FLOOR in found:
            raise ValueError(f"Floor {module.FLOOR!r} is defined in two files in floors/")
        found[module.FLOOR] = module
    return dict(sorted(found.items(), key=lambda item: item[1].LEVEL))


def get_floor(floor):
    return load_all()[floor]
