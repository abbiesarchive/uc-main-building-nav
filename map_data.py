"""Map layers for one floor, built from the SQLite room table and floors/<floor>.py.
Units are meters.

Layers:
    Polygon     rooms (one rectangle per row) and corridors
    Point       the user (made in movement.py)
    LineString  the trail / the route
"""
from functools import lru_cache

from shapely.geometry import Point, box
from shapely.ops import unary_union

from database import fetch_rooms, revision
from floors import get_floor

# stairs and lifts: the dot can stand here and press E / Q to change floor
LINK_TYPES = ("Stairs", "Lift")


@lru_cache
def building(floor):
    """Where people can be (the outline of the floor)."""
    return unary_union([box(*rect) for rect in get_floor(floor).OUTLINE])


@lru_cache
def voids(floor):
    """Holes in the floor (not rooms, nobody can stand there)."""
    return [box(*rect) for rect in get_floor(floor).VOIDS]


def load_rooms(floor):
    """Return a list of dicts: room_id, name, type, polygon."""
    settings = get_floor(floor)
    return [
        {"room_id": row["room_id"], "name": row["name"], "type": row["type"],
         "polygon": box(row["xmin"], row["ymin"], row["xmax"], row["ymax"])}
        for row in fetch_rooms(floor, settings.SHARED)
    ]


def free_rectangles(rooms, floor):
    """Cut the free space (outline minus rooms minus voids) into rectangles."""
    free = building(floor).difference(unary_union([r["polygon"] for r in rooms]))
    for void in voids(floor):
        free = free.difference(void)

    shapes = [r["polygon"] for r in rooms] + [building(floor)] + voids(floor)
    xs = sorted({round(v, 2) for s in shapes for v in (s.bounds[0], s.bounds[2])})
    ys = sorted({round(v, 2) for s in shapes for v in (s.bounds[1], s.bounds[3])})

    # one strip per row of the grid: join neighbouring free cells in x
    strips = []
    for y0, y1 in zip(ys, ys[1:]):
        run = None
        for x0, x1 in zip(xs, xs[1:]):
            inside = free.covers(Point((x0 + x1) / 2, (y0 + y1) / 2))
            if inside and run:
                run[1] = x1
            elif inside:
                run = [x0, x1]
            elif run:
                strips.append((run[0], y0, run[1], y1))
                run = None
        if run:
            strips.append((run[0], y0, run[1], y1))

    # join strips with the same x range that touch in y
    strips.sort(key=lambda s: (s[0], s[2], s[1]))
    merged = []
    for s in strips:
        last = merged[-1] if merged else None
        if last and last[0] == s[0] and last[2] == s[2] and abs(last[3] - s[1]) < 0.001:
            merged[-1] = (last[0], last[1], last[2], s[3])
        else:
            merged.append(s)
    return merged


def build_walkable(floor, rooms):
    """Corridors, lobbies and open patches: the floor that is not a room and
    not a void. Made fresh every run, so there is no generated file to commit."""
    part_of_points = get_floor(floor).PART_OF
    areas = []
    for i, (x0, y0, x1, y1) in enumerate(sorted(free_rectangles(rooms, floor)), start=1):
        owner = ""
        for room_id, (px, py) in part_of_points.items():
            if x0 <= px <= x1 and y0 <= py <= y1:
                owner = room_id
        area_id = f"W{floor}{i:02d}"
        areas.append({"area_id": area_id, "name": f"Lobi / Koridor {area_id}",
                      "part_of": owner, "polygon": box(x0, y0, x1, y1)})
    return areas


def walkable_area(floor):
    return _walkable_area(floor, revision())


@lru_cache
def _walkable_area(floor, db_revision):
    """Where the dot can stand: the outline minus the voids. Unless a floor sets
    ROOMS_WALKABLE = True, also minus every room except stairs, lifts, Lounges and
    the rooms listed in OPEN_ROOMS. Each blocked room is grown by 1 cm so its wall
    line is blocked too (otherwise the dot could walk along the wall)."""
    settings = get_floor(floor)
    area = building(floor)
    for void in voids(floor):
        area = area.difference(void)
    if not settings.ROOMS_WALKABLE:
        for room in load_rooms(floor):
            if room["type"] not in LINK_TYPES and room["type"] != "Lounge" and room["room_id"] not in settings.OPEN_ROOMS:
                area = area.difference(room["polygon"].buffer(0.01, join_style="mitre"))
    return area


def is_walkable(floor, x, y):
    return walkable_area(floor).covers(Point(x, y))


def room_at(rooms, x, y):
    """The room that contains the point, or None (corridor / lobby)."""
    p = Point(x, y)
    for room in rooms:
        if room["polygon"].covers(p):
            return room
    return None
