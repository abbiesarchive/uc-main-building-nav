"""Import room CSV files into campus.db.

Run `python load_db.py` to rebuild from CSV or `python load_db.py --keep` to
preserve an existing rooms table while creating/updating derived walkable areas.
"""
from contextlib import closing
import sqlite3
import sys

import pandas as pd
from shapely.geometry import box

from database import DB_PATH
from floors import get_floor, load_all, ROOT
from map_data import build_walkable

ROOM_COLUMNS = ("floor", "room_id", "name", "type", "xmin", "ymin", "xmax", "ymax")
ROOM_SCHEMA = """
    floor TEXT NOT NULL,
    room_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    xmin REAL NOT NULL,
    ymin REAL NOT NULL,
    xmax REAL NOT NULL,
    ymax REAL NOT NULL,
    PRIMARY KEY (floor, room_id)
"""
WALKABLE_SCHEMA = """
    floor TEXT NOT NULL,
    area_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    part_of TEXT NOT NULL,
    xmin REAL NOT NULL,
    ymin REAL NOT NULL,
    xmax REAL NOT NULL,
    ymax REAL NOT NULL
"""


def read_csv(path):
    df = pd.read_csv(path, dtype={"floor": str, "room_id": str})
    df.columns = df.columns.str.strip()
    return df


def room_rows():
    """Every CSV row once (the shared Lt. 2 / 2A core is stored under floor 2)."""
    csv_files = sorted({settings.ROOMS_CSV for settings in load_all().values()})
    frames = [read_csv(ROOT / path) for path in csv_files]
    rows = pd.concat(frames, ignore_index=True)
    missing = set(ROOM_COLUMNS) - set(rows.columns)
    if missing:
        raise ValueError(f"Kolom CSV tidak lengkap: {', '.join(sorted(missing))}")
    rows = rows[list(ROOM_COLUMNS)].copy()
    rows["floor"] = rows["floor"].astype(str)
    rows["room_id"] = rows["room_id"].astype(str)
    duplicates = rows.loc[
        rows.duplicated(subset=("floor", "room_id"), keep=False), ["floor", "room_id"]
    ].drop_duplicates()
    if len(duplicates):
        labels = [f"{row.floor}:{row.room_id}" for row in duplicates.itertuples(index=False)]
        raise ValueError(f"room_id duplikat pada lantai yang sama: {', '.join(labels)}")
    return [tuple(row) for row in rows.itertuples(index=False, name=None)]


def walkable_rows(db):
    """Build derived walkable polygons from the rooms currently in the database."""
    stored_rooms = [dict(row) for row in db.execute(
        "SELECT floor, room_id, name, type, xmin, ymin, xmax, ymax FROM rooms"
    )]
    result = []
    for floor in load_all():
        settings = get_floor(floor)
        shared_rooms = {
            (shared_floor, room_id)
            for shared_floor, room_ids in settings.SHARED.items()
            for room_id in room_ids
        }
        floor_rooms = [
            {"room_id": row["room_id"], "name": row["name"], "type": row["type"],
             "polygon": box(row["xmin"], row["ymin"], row["xmax"], row["ymax"])}
            for row in stored_rooms
            if row["floor"] == floor or (row["floor"], row["room_id"]) in shared_rooms
        ]
        for area in build_walkable(floor, floor_rooms):
            x0, y0, x1, y1 = area["polygon"].bounds
            result.append((floor, area["area_id"], area["name"], "Corridor", area["part_of"],
                           round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    return result


def main(keep):
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN")
            existing = {
                name for (name,) in db.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if not keep or "rooms" not in existing:
                db.execute("DROP TABLE IF EXISTS rooms")
                db.execute(f"CREATE TABLE rooms ({ROOM_SCHEMA})")
                rows = room_rows()
                if rows:
                    db.executemany(
                        "INSERT INTO rooms VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
                    )
                print(f"rooms: {len(rows)} rows imported")
            else:
                count = db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
                print(f"rooms: kept ({count} rows)")

            db.execute("DROP TABLE IF EXISTS walkable")
            db.execute(f"CREATE TABLE walkable ({WALKABLE_SCHEMA})")
            rows = walkable_rows(db)
            if rows:
                db.executemany(
                    "INSERT INTO walkable VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
                )
            print(f"walkable: {len(rows)} rows generated")
            db.commit()
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main("--keep" in sys.argv)
