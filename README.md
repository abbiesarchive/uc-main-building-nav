# UC Main Building Navigation

Indoor map of the Universitas Ciputra Main Building. You pick a start, walk with
WASD or the arrow keys, and the app shows the rooms around you (Buffer) and the rooms
you walked through (Spatial Join). Route search (BFS / A*) is not built yet.

## Read this first: one coordinate system for every floor

Every floor uses the same system. If one person uses a different origin, the stairs of
two floors will not line up and routing between floors breaks.

- **Unit: meter.** 1 coordinate unit = 1 m. No longitude / latitude.
- **Origin (0, 0):** the south end of the stem, at the west wall of the top bar.
- **x grows east, y grows north.** North is the top of the plan image.
- The top bar is x 0 to 99.45 and y 40 to 60. The stem hangs below it, about x 39.5 to 60.4 and y 0 to 40.
- Rooms are rectangles: `xmin, ymin, xmax, ymax` (bottom-left and top-right corner).
- Rooms that share a wall use the **same number** on that wall. Round to 2 decimals.
- A stair or lift has the same x, y on every floor it connects.
- Numbers measured from a picture are estimates, about +/- 0.5 m. Never invent a size.

## Setup (once)

```
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```
python app.py              walk around (opens a window)
python app.py 3            start on Lt. 3
python check_floors.py     check all floors  (run this before every commit)
python plot_floor.py 2     draw floor 2 and check it (add "overlay" to lay it on the plan image)
python make_walkable.py 2  list the corridors of floor 2
python draw_map.py 2       picture with a user, buffer and route
```

Keys in the app: W A S D or arrows walk 1 m, E / Q go up / down in a stair or lift,
+ / - change the buffer, R restarts.

## Adding your floor (you only add files)

Say you do Lt. 3:

1. Copy `csv/lantai2.csv` to `csv/lantai3.csv`, delete the rows, fill in your rooms.
   Columns: `floor, room_id, name, type, xmin, ymin, xmax, ymax`.
   Keep `floor` and `room_id` as **text** (`"2A"`, `02001`). ID rules are in `CLAUDE.md`.
2. Copy `floors/lantai2.py` to `floors/lantai3.py` and change: `FLOOR`, `LEVEL`,
   `ROOMS_CSV`, `OUTLINE` (Lt. 3 is a T: add the stem rectangle), `VOIDS`, `START`,
   `LINKS`, and `IMAGE` / `CALIBRATION` if you want the overlay.
3. `LINKS` says where each stair and lift on your floor leads, for example
   `"03003": {"up": "4", "down": "2A", "cost": 8}`. The other floor's file must have the
   stair going back. `check_floors.py` tests that.
4. Run `python check_floors.py` and fix every error, then `python plot_floor.py 3 overlay`
   and look at the picture, then `python app.py 3` and walk your floor.
5. Commit **only** your own files: `csv/lantai3.csv` and `floors/lantai3.py`. The app
   loads every file in `floors/` by itself, so nobody edits a shared list.

## What goes in git

- Committed: the code, `csv/lantai*.csv`, `floors/*.py`, `CLAUDE.md`, this README.
- Not committed (see `.gitignore`): `.venv`, pictures like `floor_2_overlay.png`, and
  `csv/walkable_*.csv`. The corridors are rebuilt from the room CSV every time the app
  starts, so there is no generated file to conflict on.
- **The CSV files are the database.** `load_db.py` (not written yet) will build
  `campus.db` from them for the AI course. The `.db` file is a generated copy and is not
  committed, because git cannot merge it. The edit view will save back to the CSV.

## Files

| File | Job |
|---|---|
| `floors/` | one settings file per floor (outline, voids, start, stair links) |
| `csv/` | one room table per floor |
| `map_data.py` | CSV to polygons, corridors, "can I stand here?" |
| `gis_ops.py` | Buffer and Spatial Join |
| `movement.py` | walking rules, changing floors, what is near you |
| `map_view.py` | draws a floor |
| `app.py` | the window and the keys |
| `check_floors.py` | the checks |
| `pathfinding.py` | route search (empty, to do) |

Project rules, course requirements and open decisions: `CLAUDE.md`.
