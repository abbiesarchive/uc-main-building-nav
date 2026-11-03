# UC Main Building Navigation

Indoor map of the Universitas Ciputra Main Building. You pick a start, walk with
WASD or the arrow keys, and the app shows the rooms around you (Buffer) and the rooms
you walked through (Spatial Join). Route search uses the A* algorithm with Euclidean heuristic.

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

Import the room data into SQLite once before starting the apps (or after changing
the source CSV files):

```
python load_db.py
```

The navigation app and room editor then read and write `campus.db`. CSV files are
used only as the import source; `python load_db.py` rebuilds the database from them,
while `python load_db.py --keep` preserves an existing `rooms` table.

```
python app.py              walk around (opens a window)
streamlit run streamlit_app.py   walk around in the browser (buttons)
streamlit run db_editor.py --server.port 8502   edit SQLite room data
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
4. Run `python load_db.py` to import the new floor's CSV, then run
   `python check_floors.py` and fix every error. Next run `python plot_floor.py 3 overlay`
   and look at the picture, then `python app.py 3` and walk your floor.
5. Commit **only** your own files: `csv/lantai3.csv` and `floors/lantai3.py`. The app
   loads every file in `floors/` by itself, so nobody edits a shared list.

## Data storage

- `campus.db` is the runtime source of room data. It contains `rooms` and generated
  `walkable` tables; the application computes walkable geometry from room records and
  floor settings when needed.
- `load_db.py` imports `csv/lantai*.csv` into SQLite. CSVs are retained as source data
  and for rebuilding the database; edits made in `db_editor.py` are saved to SQLite.
- `campus.db` is excluded from git, so initialize it with `python load_db.py` after
  cloning or whenever you want to rebuild from the CSV source.
- Floor shape, voids, start positions and stair/lift connections remain in
  `floors/*.py`.

## What goes in git

- Committed: the code, `csv/lantai*.csv`, `floors/*.py`, `CLAUDE.md`, this README.
- Not committed (see `.gitignore`): `.venv`, `campus.db`, pictures like
  `floor_2_overlay.png`, and `csv/walkable_*.csv`.

## Files

| File | Job |
|---|---|
| `floors/` | one settings file per floor (outline, voids, start, stair links) |
| `csv/` | room data source for SQLite import |
| `campus.db` | runtime SQLite database for room records |
| `database.py` | SQLite reads, writes, and validation |
| `load_db.py` | imports CSV room data into SQLite |
| `map_data.py` | database records to polygons, corridors, "can I stand here?" |
| `gis_ops.py` | Buffer and Spatial Join |
| `movement.py` | walking rules, changing floors, what is near you |
| `map_view.py` | draws a floor |
| `app.py` | the window and the keys |
| `check_floors.py` | the checks |
| `pathfinding.py` | route search (A* pathfinding and multi-floor routing) |

Project rules, course requirements and open decisions: `CLAUDE.md`.
