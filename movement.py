"""Walking rules: where the user is, where they can step, how they change floor.
No drawing here, so it is easy to test. Units are meters.

The user is (floor, x, y). Each step the app asks this file:
    here()     which room am I in           (Point in Polygon)
    nearby()   rooms inside the Buffer      (GIS operation 1: Buffer + Spatial Join)
    visited()  rooms my trail passed        (GIS operation 2: Spatial Join with a LineString)

Floors come from the files in floors/, so nothing here is specific to one floor.
"""
import math
from shapely.geometry import LineString, Point

from floors import load_all
from gis_ops import buffer_around, rooms_along_route, spatial_join
from map_data import LINK_TYPES, build_walkable, is_walkable, load_rooms, room_at

STEP = 1                 # one key press = 1 m
MIN_RADIUS, MAX_RADIUS = 1, 15


class Navigator:
    def __init__(self, floor=None, radius=5, step=STEP):
        self.settings = load_all()
        self.floors = {}
        for name in self.settings:
            rooms = load_rooms(name)
            self.floors[name] = {"rooms": rooms, "walkable": build_walkable(name, rooms)}
        floor = floor or next(iter(self.settings))      # lowest floor by default
        self.start = (floor, *self.settings[floor].START)
        self.radius = radius
        self.step = step
        self.reset()

    def reset(self):
        self.floor, self.x, self.y = self.start
        self.trail = [(self.x, self.y)]

    @property
    def rooms(self):
        return self.floors[self.floor]["rooms"]

    # ---- moving -----------------------------------------------------------
    def set_step(self, step):
        """Set how many meters one click walks."""
        self.step = max(1, int(step))

    def move(self, dx, dy):
        """Walk self.step meters, checking every 1 m so the dot cannot jump through a wall.
        Returns a message, or "" when the whole step worked."""
        moved = 0
        for _ in range(self.step):
            nx, ny = self.x + dx, self.y + dy
            if not is_walkable(self.floor, nx, ny):
                if moved == 0:
                    return "Blocked: that is a closed room, the void or outside the building."
                return f"Blocked after {moved} m (stopped before the obstacle)."
            self.x, self.y = nx, ny
            self.trail.append((nx, ny))
            moved += 1
        return ""

    def link(self):
        """The stair or lift the user stands in: (room, links dict), or (None, None)."""
        room = self.here()
        if room is None or room["type"] not in LINK_TYPES:
            return None, None
        return room, self.settings[self.floor].LINKS.get(room["room_id"], {})

    def change_floor(self, up):
        """Use the stair or lift the user stands in. up=True goes up one level."""
        room, links = self.link()
        if room is None:
            return "Stand inside a stair or lift first, then press E (up) or Q (down)."

        # Validasi khusus Lift Barat vs Lift Timur
        if room["type"] == "Lift":
            is_barat = "Barat" in room["name"] or room["room_id"].endswith("001")
            is_timur = "Timur" in room["name"] or room["room_id"].endswith("002")
            if is_barat and self.floor in ("4", "6"):
                return "Gunakan lift timur untuk mengakses lantai 4 dan 6"
            if is_timur and self.floor in ("3", "5"):
                return "Gunakan lift barat untuk mengakses lantai 3 dan 5"

        if not links:
            if room["type"] == "Lift":
                is_barat = "Barat" in room["name"] or room["room_id"].endswith("001")
                return "Gunakan lift timur untuk mengakses lantai 4 dan 6" if is_barat else "Gunakan lift barat untuk mengakses lantai 3 dan 5"
            return f"{room['name']} has no floor link yet."

        target = links.get("up" if up else "down")
        if target is None:
            if room["type"] == "Lift":
                is_barat = "Barat" in room["name"] or room["room_id"].endswith("001")
                if is_barat and self.floor not in ("7", "1"):
                    return "Gunakan lift timur untuk mengakses lantai 4 dan 6"
                if not is_barat and self.floor not in ("7", "1"):
                    return "Gunakan lift barat untuk mengakses lantai 3 dan 5"
            return f"{room['name']} does not go {'up' if up else 'down'} from Lt. {self.floor}."

        if target not in self.floors:
            return f"Lt. {target} is not mapped yet (no file for it in floors/)."
        self.floor = target
        self.trail = [(self.x, self.y)]
        return f"You took {room['name']} to Lt. {target}."

    def teleport_to_room(self, target_room):
        """Teleport user to target room (or nearest walkable spot next to it)."""
        target_floor = str(target_room["floor"])
        if target_floor not in self.floors:
            return f"Lt. {target_floor} belum dipetakan."

        poly = target_room["polygon"]
        cx, cy = round(poly.centroid.x), round(poly.centroid.y)

        if is_walkable(target_floor, cx, cy):
            tx, ty = cx, cy
        else:
            # Cari titik walkable terdekat pada grid 1 m agar tidak terjebak di ruang tertutup
            from pathfinding import walkable_cells
            cells = walkable_cells(target_floor)
            if not cells:
                return f"Tidak ada area walkable di Lt. {target_floor}."
            tx, ty = min(
                cells,
                key=lambda c: (poly.distance(Point(c)), math.hypot(c[0] - cx, c[1] - cy))
            )

        self.floor = target_floor
        self.x, self.y = tx, ty
        self.trail = [(self.x, self.y)]
        return f"Teleport berhasil ke {target_room['name']} (Lt. {target_floor})."
    
    def link_hint(self):
        """Text that tells the user where the stair or lift they stand in goes."""
        room, links = self.link()
        if not room:
            return ""
        if room["type"] == "Lift":
            is_barat = "Barat" in room["name"] or room["room_id"].endswith("001")
            is_timur = "Timur" in room["name"] or room["room_id"].endswith("002")
            if is_barat and self.floor in ("4", "6"):
                return f"{room['name']}: Gunakan lift timur untuk mengakses lantai 4 dan 6"
            if is_timur and self.floor in ("3", "5"):
                return f"{room['name']}: Gunakan lift barat untuk mengakses lantai 3 dan 5"
        if not links:
            return ""
        parts = []
        if "up" in links:
            parts.append(f"E = up to Lt. {links['up']}")
        if "down" in links:
            parts.append(f"Q = down to Lt. {links['down']}")
        return f"{room['name']}: " + ", ".join(parts)

    def set_radius(self, delta):
        self.radius = max(MIN_RADIUS, min(MAX_RADIUS, self.radius + delta))

    # ---- the layers and the two GIS operations -----------------------------
    def point(self):
        return Point(self.x, self.y)                      # Point layer

    def buffer(self):
        return buffer_around(self.x, self.y, self.radius)  # Buffer

    def here(self):
        return room_at(self.rooms, self.x, self.y)

    def nearby(self):
        """Spatial Join: rooms inside the Buffer, nearest first, with distance."""
        hits = spatial_join(self.rooms, self.buffer())
        found = [(room, room["polygon"].distance(self.point())) for room in hits]
        return sorted(found, key=lambda pair: pair[1])

    def visited(self):
        """Spatial Join: rooms the trail (LineString) went through."""
        if len(self.trail) < 2:
            here = self.here()
            return [here] if here else []
        return rooms_along_route(self.rooms, LineString(self.trail))
