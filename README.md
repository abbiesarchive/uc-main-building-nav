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

```bash
streamlit run web_app.py   # Run web app navigation
python check_floors.py     # Check all floors data integrity
```

Keys in the web app: W A S D or arrows walk 2 m, E / Q go up / down in a stair or lift,
+ / - change the buffer, R restarts.

## Adding your floor (you only add files)

Say you do Lt. 3:

1. Copy `csv/lantai2.csv` to `csv/lantai3.csv`, delete the rows, fill in your rooms.
   Columns: `floor, room_id, name, type, xmin, ymin, xmax, ymax`.
   Keep `floor` and `room_id` as **text** (`"2A"`, `02001`).
2. Copy `floors/lantai2.py` to `floors/lantai3.py` and change: `FLOOR`, `LEVEL`,
   `ROOMS_CSV`, `OUTLINE` (Lt. 3 is a T: add the stem rectangle), `VOIDS`, `START`,
   and `LINKS`.
3. `LINKS` says where each stair and lift on your floor leads, for example
   `"03003": {"up": "4", "down": "2", "cost": 8}`. The other floor's file must have the
   stair going back. `check_floors.py` tests that.
4. Run `python check_floors.py` and fix every error, then run `streamlit run web_app.py`
   and walk your floor.
5. Commit **only** your own files: `csv/lantai3.csv` and `floors/lantai3.py`. The app
   loads every file in `floors/` by itself, so nobody edits a shared list.

## Files

| File | Job |
|---|---|
| `web_app.py` | Main web navigation application (Streamlit) |
| `map_folium.py` | Leaflet / Folium interactive indoor map renderer |
| `movement.py` | Walking rules (WASD), floor changes (E/Q), buffer & GIS proximity |
| `map_data.py` | CSV to polygons, corridors, physical wall collision |
| `gis_ops.py` | Buffer and Spatial Join operations (Shapely) |
| `floors/` | One settings file per floor (outline, voids, start, stair links) |
| `csv/` | One room table per floor |
| `check_floors.py` | Data integrity checker for rooms and stair links |

Project rules, course requirements and open decisions: `CLAUDE.md`.
