"""Walking rules: where the user is, where they can step, how they change floor.
No drawing here, so it is easy to test. Units are meters.

The user is (floor, x, y). Each step the app asks this file:
    here()     which room am I in           (Point in Polygon)
    nearby()   rooms inside the Buffer      (GIS operation 1: Buffer + Spatial Join)
    visited()  rooms my trail passed        (GIS operation 2: Spatial Join with a LineString)

Floors come from the files in floors/, so nothing here is specific to one floor.
"""
from shapely.geometry import LineString, Point

from floors import load_all
from gis_ops import buffer_around, rooms_along_route, spatial_join
from map_data import LINK_TYPES, build_walkable, is_walkable, load_rooms, room_at

STEP = 1                 # one key press = 1 m
MIN_RADIUS, MAX_RADIUS = 1, 15


class Navigator:
    def __init__(self, floor=None, radius=5):
        self.settings = load_all()
        self.floors = {}
        for name in self.settings:
            rooms = load_rooms(name)
            self.floors[name] = {"rooms": rooms, "walkable": build_walkable(name, rooms)}
        floor = floor or next(iter(self.settings))      # lowest floor by default
        self.start = (floor, *self.settings[floor].START)
        self.radius = radius
        self.reset()

    def reset(self):
        self.floor, self.x, self.y = self.start
        self.trail = [(self.x, self.y)]

    @property
    def rooms(self):
        return self.floors[self.floor]["rooms"]

    # ---- moving -----------------------------------------------------------
    def move(self, dx, dy):
        """Step one meter. Returns a message, or "" when the step worked."""
        nx, ny = self.x + dx * STEP, self.y + dy * STEP
        if not is_walkable(self.floor, nx, ny):
            return "Blocked: that is the void or outside the building."
        self.x, self.y = nx, ny
        self.trail.append((nx, ny))
        return ""

    def link(self):
        """The stair or lift the user stands in: (room, links dict), or (None, None)."""
        room = self.here()
        if room is None or room["type"] not in LINK_TYPES:
            return None, None
        return room, self.settings[self.floor].LINKS.get(room["room_id"])

    def change_floor(self, up):
        """Use the stair or lift the user stands in. up=True goes up one level."""
        room, links = self.link()
        if room is None:
            return "Stand inside a stair or lift first, then press E (up) or Q (down)."
        if links is None:
            return f"{room['name']} has no floor link yet (add it to LINKS in the floor file)."
        target = links.get("up" if up else "down")
        if target is None:
            return f"{room['name']} does not go {'up' if up else 'down'} from Lt. {self.floor}."
        if target not in self.floors:
            return f"Lt. {target} is not mapped yet (no file for it in floors/)."
        self.floor = target
        self.trail = [(self.x, self.y)]
        return f"You took {room['name']} to Lt. {target}."

    def link_hint(self):
        """Text that tells the user where the stair or lift they stand in goes."""
        room, links = self.link()
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
