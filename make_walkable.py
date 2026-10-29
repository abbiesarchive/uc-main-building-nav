"""List the corridors, lobbies and open areas of a floor (everything that is not
a room and not a void). The app builds these itself on every start, so you do
not need this to run the app. Use it to look at the areas.

Run:  python make_walkable.py 2            print the areas
      python make_walkable.py 2 --save     also write csv/walkable_lt2.csv (not committed)
Units are meters.
"""
import sys

import pandas as pd

from floors import ROOT
from map_data import build_walkable, load_rooms

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    floor = sys.argv[1]
    areas = build_walkable(floor, load_rooms(floor))

    total = sum(a["polygon"].area for a in areas)
    print(f"{len(areas)} walkable areas, {total:.1f} m2")
    for a in areas:
        x0, y0, x1, y1 = a["polygon"].bounds
        w, h = x1 - x0, y1 - y0
        note = "  <- thin, maybe a wall gap" if min(w, h) < 0.8 else ""
        owner = f"  (part of {a['part_of']})" if a["part_of"] else ""
        print(f"  {a['area_id']}  x {x0:g}-{x1:g}  y {y0:g}-{y1:g}  ({w:.2f} x {h:.2f} m){owner}{note}")

    if "--save" in sys.argv:
        rows = [[floor, a["area_id"], a["name"], "Corridor", *[round(v, 2) for v in a["polygon"].bounds],
                 a["part_of"]] for a in areas]
        df = pd.DataFrame(rows, columns=["floor", "area_id", "name", "type",
                                         "xmin", "ymin", "xmax", "ymax", "part_of"])
        out = ROOT / "csv" / f"walkable_lt{floor}.csv"
        df.to_csv(out, index=False)
        print("saved", out)
