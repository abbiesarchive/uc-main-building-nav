"""Build campus.db (SQLite) from the room CSVs in csv/.
Run:  python load_db.py            rebuild the tables from scratch
      python load_db.py --keep     skip tables that already exist (keeps edits made in the app)

Tables:
    rooms     floor, room_id, name, type, xmin, ymin, xmax, ymax     (the csv rows)
    walkable  floor, area_id, name, type, part_of, xmin, ymin, xmax, ymax
              (corridors, lobbies and open patches: the floor that is not a room and not a void)
`floor` and `room_id` are text ("2A", "02001"), so compare with floor = '2A'.
Units are meters.
"""
import sqlite3
import sys

import pandas as pd

from floors import ROOT, load_all
from map_data import build_walkable, load_rooms, read_csv

DB = ROOT / "campus.db"
RECT = "xmin REAL, ymin REAL, xmax REAL, ymax REAL"
SCHEMAS = {
    "rooms": f"floor TEXT, room_id TEXT PRIMARY KEY, name TEXT, type TEXT, {RECT}",
    "walkable": f"floor TEXT, area_id TEXT PRIMARY KEY, name TEXT, type TEXT, part_of TEXT, {RECT}",
}


def room_rows():
    """Every csv row once (the shared Lt. 2 / 2A core is stored under floor 2)."""
    csv_files = sorted({settings.ROOMS_CSV for settings in load_all().values()})
    frames = [read_csv(ROOT / path) for path in csv_files]
    return pd.concat(frames).drop_duplicates("room_id")


def walkable_rows():
    rows = []
    for floor in load_all():
        for area in build_walkable(floor, load_rooms(floor)):
            x0, y0, x1, y1 = area["polygon"].bounds
            rows.append((floor, area["area_id"], area["name"], "Corridor", area["part_of"],
                         round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)))
    return rows


def main(keep):
    db = sqlite3.connect(DB)
    existing = {name for (name,) in db.execute("select name from sqlite_master where type='table'")}
    for table, schema in SCHEMAS.items():
        if keep and table in existing:
            print(f"{table}: kept (already exists)")
            continue
        db.execute(f"drop table if exists {table}")
        db.execute(f"create table {table} ({schema})")
        if table == "rooms":
            rows = [tuple(r) for r in room_rows()[["floor", "room_id", "name", "type",
                                                   "xmin", "ymin", "xmax", "ymax"]].itertuples(index=False)]
        else:
            rows = walkable_rows()
        db.executemany(f"insert into {table} values ({','.join('?' * len(rows[0]))})", rows)
        print(f"{table}: {len(rows)} rows")
    db.commit()
    db.close()


if __name__ == "__main__":
    main("--keep" in sys.argv)
