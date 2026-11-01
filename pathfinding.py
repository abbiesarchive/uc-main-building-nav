"""A* route search for the indoor map: ONE search over all floors.

Graph:
  node  = (floor, x, y) on a 1 m grid (x, y are whole meters)
  edge  = one step W / A / S / D (4 directions), cost 1 m, only onto walkable cells
        + standing in a stair or lift, move to the same (x, y) on the floor in LINKS
          ("up" / "down"), cost = the "cost" in LINKS (a team assumption, not measured)

Heuristic (never overestimates, and consistent): the larger of
  - Manhattan distance to the target room, minus 1.5 m (stairs keep x, y, so only walking closes this gap)
  - the cheapest total stair/lift cost from this floor to the target floor
"""
import heapq
import math

import numpy as np
import shapely
from functools import lru_cache
from shapely.geometry import LineString, Point

from floors import get_floor, load_all
from map_data import LINK_TYPES, load_rooms, walkable_area

MOVES = [(0, 1), (0, -1), (1, 0), (-1, 0)]    # W, S, D, A
LINK_ROOM_STEP_COST = 3     # stepping into a stair/lift you do not use costs more, so routes do not cut through them
GOAL_REACH = 1.0            # a closed room is reached when you stand within 1 m of its wall (doors are not modeled)


def get_all_rooms():
    """Every room of every mapped floor, each with its floor."""
    all_rooms = []
    for f in load_all():
        for r in load_rooms(f):
            all_rooms.append({**r, "floor": f})
    return all_rooms


def get_room_center(room):
    c = room["polygon"].centroid
    return (round(c.x, 1), round(c.y, 1))


def going_up(current_floor, target_floor):
    """True if the target floor is above the current floor (uses LEVEL, so 2A is between 2 and 3)."""
    return get_floor(target_floor).LEVEL > get_floor(current_floor).LEVEL


# ---------------------------------------------------------------- the grid

def _cells_in(geometry):
    """Whole-meter cells (x, y) covered by a shapely geometry."""
    xmin, ymin, xmax, ymax = geometry.bounds
    xs, ys = np.meshgrid(np.arange(math.floor(xmin), math.ceil(xmax) + 1),
                         np.arange(math.floor(ymin), math.ceil(ymax) + 1))
    xs, ys = xs.ravel(), ys.ravel()
    inside = shapely.covers(geometry, shapely.points(xs, ys))
    return {(int(x), int(y)) for x, y in zip(xs[inside], ys[inside])}


@lru_cache
def walkable_cells(floor):
    """Cells where the dot can stand (the same rule as map_data.walkable_area)."""
    return frozenset(_cells_in(walkable_area(floor)))


@lru_cache
def link_cells(floor):
    """{cell: [stair/lift room, ...]} for every stair and lift on the floor."""
    cells = {}
    for room in load_rooms(floor):
        if room["type"] in LINK_TYPES:
            for cell in _cells_in(room["polygon"]):
                cells.setdefault(cell, []).append(room)
    return cells


@lru_cache
def floor_cost(start_floor, target_floor):
    """Cheapest stair/lift cost between two floors, ignoring walking. None if there is no way."""
    best = {start_floor: 0.0}
    queue = [(0.0, start_floor)]
    while queue:
        cost, floor = heapq.heappop(queue)
        if floor == target_floor:
            return cost
        if cost > best.get(floor, float("inf")):
            continue
        for links in get_floor(floor).LINKS.values():
            for direction in ("up", "down"):
                nxt = links.get(direction)
                if nxt is None or nxt not in load_all():
                    continue
                new_cost = cost + links.get("cost", 0)
                if new_cost < best.get(nxt, float("inf")):
                    best[nxt] = new_cost
                    heapq.heappush(queue, (new_cost, nxt))
    return None


# ---------------------------------------------------------------- A*

def astar(start_floor, start, target_room):
    """Cheapest list of nodes [(floor, x, y), ...] from start to the target room, or None."""
    target_floor = target_room["floor"]
    poly = target_room["polygon"]
    txmin, tymin, txmax, tymax = poly.bounds
    goal_cells = {c for c in walkable_cells(target_floor) if poly.distance(Point(c)) <= GOAL_REACH}
    if not goal_cells:
        return None

    def heuristic(node):
        floor, x, y = node
        dx = max(txmin - x, 0, x - txmax)
        dy = max(tymin - y, 0, y - tymax)
        walk = max(dx + dy - 1.5, 0)                # x, y only change by walking, on any floor
        return max(walk, floor_cost(floor, target_floor))   # never None: such moves are not pushed

    start_node = (start_floor, round(start[0]), round(start[1]))
    if floor_cost(start_floor, target_floor) is None:
        return None

    g_score = {start_node: 0.0}
    came_from = {}
    counter = 0
    queue = [(heuristic(start_node), 0, start_node)]
    closed = set()
    while queue:
        _, _, node = heapq.heappop(queue)
        if node in closed:
            continue
        closed.add(node)
        floor, x, y = node

        if floor == target_floor and (x, y) in goal_cells:
            path = [node]
            while node in came_from:
                node = came_from[node]
                path.append(node)
            return path[::-1]

        neighbours = []
        here_walkable = walkable_cells(floor)
        links_here = link_cells(floor)
        for dx, dy in MOVES:                          # W / A / S / D
            cell = (x + dx, y + dy)
            if cell in here_walkable:
                cost = 1
                if cell in links_here and not (floor == target_floor and cell in goal_cells):
                    cost += LINK_ROOM_STEP_COST
                neighbours.append(((floor, cell[0], cell[1]), cost))
        for room in links_here.get((x, y), []):       # stair / lift: change floor
            links = get_floor(floor).LINKS.get(room["room_id"], {})
            for direction in ("up", "down"):
                nxt = links.get(direction)
                if nxt is None or nxt not in load_all() or (x, y) not in walkable_cells(nxt):
                    continue
                if floor_cost(nxt, target_floor) is None:
                    continue
                neighbours.append(((nxt, x, y), links.get("cost", 0)))

        for neighbour, cost in neighbours:
            new_g = g_score[node] + cost
            if neighbour not in closed and new_g < g_score.get(neighbour, float("inf")):
                g_score[neighbour] = new_g
                came_from[neighbour] = node
                counter += 1
                heapq.heappush(queue, (new_g + heuristic(neighbour), counter, neighbour))
    return None


_last = {"key": None, "path": None}


def _search(current_floor, start_pos, target_room):
    """astar() with a one-entry cache (the app asks twice per redraw)."""
    key = (current_floor, round(start_pos[0]), round(start_pos[1]), target_room["floor"], target_room["room_id"])
    if _last["key"] != key:
        _last["key"] = key
        _last["path"] = astar(current_floor, start_pos, target_room)
    return _last["path"]


# ---------------------------------------------------------------- results for the app

def plan(current_floor, start_pos, target_room):
    """The part of the route on the current floor.
    Returns (line, link_room, next_floor, floors): link_room / next_floor are None when the
    target is on this floor; floors lists every floor of the whole route in order."""
    goal = get_room_center(target_room)
    path = _search(current_floor, start_pos, target_room)
    if path is None:
        return LineString([start_pos, goal]), None, None, [current_floor, target_room["floor"]]

    floors = [path[0][0]]
    for node in path:
        if node[0] != floors[-1]:
            floors.append(node[0])

    here = [(x, y) for floor, x, y in path[:next((i for i, n in enumerate(path) if n[0] != current_floor), len(path))]]
    if len(here) < len(path):                          # the route changes floor
        next_floor = path[len(here)][0]
        x, y = here[-1]
        link = next(r for r in link_cells(current_floor)[(x, y)]
                    if get_floor(current_floor).LINKS.get(r["room_id"], {}).get("up") == next_floor
                    or get_floor(current_floor).LINKS.get(r["room_id"], {}).get("down") == next_floor)
        points = [tuple(start_pos)] + here
        return LineString(points if len(points) > 1 else points * 2), link, next_floor, floors

    points = [tuple(start_pos)] + here + [goal]
    return LineString(points), None, None, floors


def find_route(current_floor, start_pos, target_room):
    """(line on the current floor, info text, stair/lift to use or the target room)."""
    line, link, next_floor, floors = plan(current_floor, start_pos, target_room)
    target_floor = str(target_room["floor"])
    if link is None:
        info = f"Rute menuju ruangan {target_room['name']} ({line.length:.1f} m)"
        return line, info, target_room
    arah = "naik" if going_up(current_floor, next_floor) else "turun"
    jalur = " → ".join(f"Lt. {f}" for f in floors)
    info = (f"Menuju {link['name']} untuk {arah} ke Lantai {next_floor} "
            f"(Tujuan: {target_room['name']} di Lantai {target_floor}; jalur {jalur})")
    return line, info, link


def get_current_instruction(current_floor, pos, target_room):
    """One text instruction for what to do now."""
    target_floor = str(target_room["floor"])
    line, link, next_floor, _ = plan(current_floor, pos, target_room)

    if link is None:
        if line.length < 1.5:
            return f"🎉 Anda telah sampai di ruangan {target_room['name']}!"
        goal_name = f"ruangan {target_room['name']}"
        arah_text = ""
    else:
        arah = "naik" if going_up(current_floor, next_floor) else "turun"
        goal_name = link["name"]
        arah_text = f" untuk {arah} ke Lt. {next_floor}"
        if line.length < 2.0:
            return (f"Gunakan {link['name']} untuk {arah} ke Lantai {next_floor} "
                    f"(Tujuan: {target_room['name']} di Lantai {target_floor})")

    pts = list(line.simplify(1.2).coords)
    if len(pts) <= 2:
        return f"Lurus sejauh {round(line.length)} m menuju {goal_name}{arah_text}"
    d_turn = math.hypot(pts[1][0] - pos[0], pts[1][1] - pos[1])
    v1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
    v2 = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
    turn = "belok kiri" if v1[0] * v2[1] - v1[1] * v2[0] > 0 else "belok kanan"
    return f"Lurus sejauh {round(d_turn)} m, lalu {turn} menuju {goal_name}{arah_text}"
