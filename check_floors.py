"""Check every floor in floors/ and stop with an error if something is wrong.

Run:  python check_floors.py          (all floors)
      python check_floors.py 3        (one floor)

Errors (exit code 1): duplicate IDs, min bigger than max, rooms outside the outline
or inside a void, overlapping rooms, a start point that is missing or blocked,
rooms nobody can walk to, stair / lift links that do not match on both floors.
Warnings: a link to a floor that has no file yet, thin gaps between rooms.
Run this before every commit. Units are meters.
"""
import sys
from collections import Counter

import pandas as pd
from shapely.geometry import Point, box

from floors import ROOT, get_floor, load_all
from map_data import LINK_TYPES, building, is_walkable, load_rooms, voids

OPPOSITE = {"up": "down", "down": "up"}
STEP = 1


def check_rows(floor):
    """Problems you can see in the csv itself."""
    errors = []
    df = pd.read_csv(ROOT / get_floor(floor).ROOMS_CSV, dtype={"floor": str, "room_id": str})
    df.columns = df.columns.str.strip()
    df = df[df["floor"] == floor]
    if df.empty:
        return [f"no rows for floor {floor!r} in {get_floor(floor).ROOMS_CSV}"]
    for room_id, n in Counter(df["room_id"]).items():
        if n > 1:
            errors.append(f"duplicate room_id {room_id} ({n} rows)")
    for r in df.itertuples():
        if r.xmin >= r.xmax or r.ymin >= r.ymax:
            errors.append(f"{r.room_id} {r.name}: min is not smaller than max")
    return errors


def reachable_points(floor):
    """Every spot you can reach from START with 1 m steps, like the app does."""
    sx, sy = get_floor(floor).START
    seen, todo = {(sx, sy)}, [(sx, sy)]
    while todo:
        x, y = todo.pop()
        for dx, dy in ((0, STEP), (0, -STEP), (STEP, 0), (-STEP, 0)):
            nxt = (x + dx, y + dy)
            if nxt not in seen and is_walkable(floor, *nxt):
                seen.add(nxt)
                todo.append(nxt)
    return seen


def check_floor(floor):
    """Returns (errors, warnings) for one floor."""
    errors, warnings = check_rows(floor), []
    settings = get_floor(floor)
    rooms = load_rooms(floor)
    if not rooms:
        return errors, warnings
    outline = building(floor).buffer(0.01)

    for room in rooms:
        label = f"{room['room_id']} {room['name']}"
        if not outline.covers(room["polygon"]):
            errors.append(f"{label}: outside the building outline")
        for void in voids(floor):
            if room["polygon"].intersection(void).area > 0.01:
                errors.append(f"{label}: overlaps the void")

    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            area = a["polygon"].intersection(b["polygon"]).area
            if area > 0.01:
                errors.append(f"overlap {a['room_id']} {a['name']} / "
                              f"{b['room_id']} {b['name']}: {area:.2f} m2")

    # start point
    if not is_walkable(floor, *settings.START):
        errors.append(f"START {settings.START} is not walkable (outside the outline or in a void)")
    else:
        points = reachable_points(floor)
        # closed rooms: you only need to reach the wall, and the grid is 1 m
        reach = 0.5 if settings.ROOMS_WALKABLE else 1.0
        for room in rooms:
            if not any(room["polygon"].distance(Point(p)) <= reach for p in points):
                errors.append(f"{room['room_id']} {room['name']}: cannot be reached from START")

    # links on this floor
    by_id = {r["room_id"]: r for r in rooms}
    for room_id, links in settings.LINKS.items():
        room = by_id.get(room_id)
        if room is None:
            errors.append(f"LINKS: room {room_id} is not in the csv of Lt. {floor}")
        elif room["type"] not in LINK_TYPES:
            errors.append(f"LINKS: {room_id} is a {room['type']}, not Stairs or Lift")
        for direction in ("up", "down"):
            if direction in links:
                warn, err = check_link_back(floor, room_id, room, direction, links[direction])
                warnings += warn
                errors += err
        if "cost" not in links:
            warnings.append(f"LINKS: {room_id} has no cost")
    return errors, warnings


def check_link_back(floor, room_id, room, direction, target):
    """The stair on the other floor must lead back here. Returns (warnings, errors)."""
    all_floors = load_all()
    if target not in all_floors:
        return [f"Lt. {floor} {room_id} goes {direction} to Lt. {target}, which has no file yet"], []
    other = all_floors[target]
    back = OPPOSITE[direction]
    # same room_id on the other floor, or a stair / lift at the same spot
    candidates = [room_id] if room_id in other.LINKS else []
    if room is not None:
        for other_room in load_rooms(target):
            if (other_room["type"] in LINK_TYPES and other_room["room_id"] in other.LINKS
                    and other_room["polygon"].intersects(room["polygon"])):
                candidates.append(other_room["room_id"])
    for candidate in candidates:
        if other.LINKS[candidate].get(back) == floor:
            return [], []
    return [], [f"Lt. {floor} {room_id} goes {direction} to Lt. {target}, but Lt. {target} "
                f"has no stair or lift at that spot going {back} to Lt. {floor}"]


def main(wanted):
    floors = wanted or list(load_all())
    if not floors:
        print("ERROR: no floor files found in floors/ (add floors/lantai2.py and its csv)")
        return 1
    failed = False
    for floor in floors:
        errors, warnings = check_floor(floor)
        print(f"Lt. {floor}: {len(errors)} errors, {len(warnings)} warnings")
        for w in warnings:
            print("  warning:", w)
        for e in errors:
            print("  ERROR:  ", e)
        failed = failed or bool(errors)
    print("FAILED" if failed else "All floors OK.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
