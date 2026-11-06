"""Thin web API around the existing navigation code. No algorithm lives here.
Run: python server.py   then open http://127.0.0.1:5055
"""
import math
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from shapely.geometry import LineString

from floors import load_all
from gis_ops import rooms_along_route
from map_data import is_walkable
from movement import Navigator
from pathfinding import get_all_rooms, get_room_center, going_up, link_cells, plan, _search

WEB = Path(__file__).parent / "web"
app = Flask(__name__, static_folder=None)
nav = Navigator()          # shared; every request sets its position first
lock = threading.Lock()
WALK_SPEED = 1.3           # m/s


def bbox(poly):
    return [round(v, 2) for v in poly.bounds]


def place(data):
    """Put the shared Navigator where the browser says the user is."""
    floor = str(data.get("floor", nav.start[0]))
    if floor not in nav.floors:
        floor = nav.start[0]
    nav.floor, nav.x, nav.y = floor, float(data.get("x", 0)), float(data.get("y", 0))
    nav.radius = max(1, min(15, int(data.get("radius", nav.radius))))
    nav.step = max(1, min(20, int(data.get("step", nav.step))))


def state(message=""):
    room = nav.here()
    link, _ = nav.link()
    links = nav.settings[nav.floor].LINKS.get(link["room_id"], {}) if link else {}
    return {
        "floor": nav.floor, "x": nav.x, "y": nav.y, "message": message,
        "here": {"room_id": room["room_id"], "name": room["name"], "type": room["type"]} if room else None,
        "can_up": bool(link and links.get("up")), "can_down": bool(link and links.get("down")),
        "hint": nav.link_hint(),
        "nearby": [{"room_id": r["room_id"], "dist": round(d, 1)} for r, d in nav.nearby()],
    }


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/web/<path:name>")
def static_files(name):
    return send_from_directory(WEB, name)


@app.get("/api/map")
def api_map():
    floors = []
    for name, cfg in load_all().items():
        rooms = nav.floors[name]["rooms"]
        types = {r["room_id"]: r["type"] for r in rooms}
        patches = [{"bbox": bbox(a["polygon"]), "type": types.get(a["part_of"])}
                   for a in nav.floors[name]["walkable"] if a["part_of"]]
        floors.append({
            "floor": name, "level": cfg.LEVEL, "start": list(cfg.START),
            "outline_rects": [list(r) for r in cfg.OUTLINE],
            "voids": [list(v) for v in cfg.VOIDS],
            "patches": patches,
            "rooms": [{"id": r["room_id"], "name": r["name"], "type": r["type"], "bbox": bbox(r["polygon"]),
                       "links": {k: v for k, v in cfg.LINKS.get(r["room_id"], {}).items() if k in ("up", "down") and v}}
                      for r in rooms],
        })
    return jsonify(floors)


@app.get("/api/rooms")
def api_rooms():
    return jsonify([{"key": f"{r['floor']}:{r['room_id']}", "id": r["room_id"], "name": r["name"], "type": r["type"], "floor": r["floor"],
                     "center": get_room_center(r)} for r in get_all_rooms()])


@app.post("/api/nearby")
def api_nearby():
    with lock:
        place(request.json)
        return jsonify(state())


@app.post("/api/move")
def api_move():
    d = request.json
    with lock:
        place(d)
        msg = nav.move(int(d["dx"]), int(d["dy"]))
        return jsonify(state(msg))


@app.post("/api/goto")
def api_goto():
    d = request.json
    with lock:
        place(d)
        x, y = round(float(d["tx"])), round(float(d["ty"]))
        if not is_walkable(nav.floor, x, y):
            return jsonify(state("That point is not walkable (closed room, void or outside)."))
        nav.x, nav.y = x, y
        return jsonify(state())


@app.post("/api/change_floor")
def api_change_floor():
    d = request.json
    with lock:
        place(d)
        msg = nav.change_floor(up=bool(d["up"]))
        return jsonify(state(msg))


@app.post("/api/teleport")
def api_teleport():
    d = request.json
    with lock:
        place(d)
        room = next((r for r in get_all_rooms() if f"{r['floor']}:{r['room_id']}" == d["key"]), None)
        if room is None:
            return jsonify(state("Unknown room.")), 404
        msg = nav.teleport_to_room(room)
        return jsonify(state(msg))


def compass(dx, dy):
    return ("east", "north", "west", "south")[round(math.atan2(dy, dx) / (math.pi / 2)) % 4]


def floor_steps(floor, nodes, final, target_name):
    """Turn one floor's grid path into steps: direction, distance, rooms passed."""
    pts = [(x, y) for _, x, y in nodes]
    if len(pts) < 2:
        return []
    keep = [0]
    simple = list(LineString(pts).simplify(1.5, preserve_topology=False).coords)
    idx = 0
    for p in simple[1:]:
        while idx < len(pts) - 1 and pts[idx] != tuple(p):
            idx += 1
        keep.append(idx)
    rooms = nav.floors[floor]["rooms"]
    steps = []
    prev_heading = None
    for a, b in zip(keep, keep[1:]):
        if b <= a:
            continue
        leg = pts[a:b + 1]
        dx, dy = leg[-1][0] - leg[0][0], leg[-1][1] - leg[0][1]
        dist = b - a
        heading = math.atan2(dy, dx)
        if prev_heading is None:
            verb = f"Head {compass(dx, dy)}"
        else:
            diff = (heading - prev_heading + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) < math.radians(30):
                verb = "Continue straight"
            else:
                verb = "Turn left" if diff > 0 else "Turn right"
        prev_heading = heading
        passed = [r["name"].split(" (")[0] for r in rooms_along_route(rooms, LineString(leg), width=3.0)
                  if r["type"] not in ("Lift", "Stairs")][:3]
        steps.append({"type": "walk", "floor": floor, "text": f"{verb} for {dist} m", "dist": dist,
                      "rooms": passed, "point": list(leg[0])})
    if steps:
        steps[-1]["text"] += f" to {target_name}" if final else ""
    return steps


@app.post("/api/route")
def api_route():
    d = request.json
    with lock:
        place(d)
        target = next((r for r in get_all_rooms() if f"{r['floor']}:{r['room_id']}" == d["to"]), None)
        if target is None:
            return jsonify({"found": False, "error": "Unknown destination."}), 404
        path = _search(nav.floor, (nav.x, nav.y), target)
        goal = get_room_center(target)
        dest = {"id": target["room_id"], "name": target["name"], "floor": target["floor"], "point": list(goal)}
        if path is None:
            line, _, _, _ = plan(nav.floor, (nav.x, nav.y), target)
            return jsonify({"found": False, "dest": dest, "fallback": [list(c) for c in line.coords],
                            "floor": nav.floor, "error": "No walkable route found."})

        # split the node list into one run per floor
        runs = []
        for node in path:
            if not runs or runs[-1][0][0] != node[0]:
                runs.append([node])
            else:
                runs[-1].append(node)

        segments, steps, total, changes = [], [], 0, 0
        name = target["name"].split(" (")[0]
        for i, run in enumerate(runs):
            floor = run[0][0]
            last = i == len(runs) - 1
            pts = [[x, y] for _, x, y in run]
            if last and is_walkable(floor, round(goal[0]), round(goal[1])):
                pts.append(list(goal))          # open room: end at its centre; closed room: end at the wall
            if last:
                dest["point"] = pts[-1]
            segments.append({"floor": floor, "points": pts})
            walked = floor_steps(floor, run, last, name)
            steps += walked
            total += sum(s["dist"] for s in walked)
            if not last:
                nxt = runs[i + 1][0][0]
                x, y = run[-1][1], run[-1][2]
                cfg = nav.settings[floor]
                link = next((r for r in link_cells(floor).get((x, y), [])
                             if cfg.LINKS.get(r["room_id"], {}).get("up") == nxt
                             or cfg.LINKS.get(r["room_id"], {}).get("down") == nxt), None)
                word = "up" if going_up(floor, nxt) else "down"
                steps.append({"type": "floor", "floor": floor, "to_floor": nxt, "dist": 0, "rooms": [],
                              "text": f"Take {link['name'].rsplit(' Lt', 1)[0] if link else 'stairs/lift'} {word} to Lt {nxt}",
                              "via": link["name"].rsplit(" Lt", 1)[0] if link else "", "word": word,
                              "point": [x, y]})
                changes += 1
        merged = []                      # lift Lt1->2->3 in a row becomes one step
        for st in steps:
            prev = merged[-1] if merged else None
            if prev and st["type"] == "floor" and prev["type"] == "floor" and prev.get("via") == st.get("via") \
                    and prev["word"] == st["word"]:
                prev["to_floor"] = st["to_floor"]
                prev["text"] = f"Take {st['via']} {st['word']} to Lt {st['to_floor']}"
            else:
                merged.append(st)
        steps = merged
        steps.append({"type": "arrive", "floor": target["floor"], "dist": 0, "rooms": [],
                      "text": f"Arrive at {target['name']}", "point": list(goal)})
        seconds = total / WALK_SPEED + changes * 25
        return jsonify({"found": True, "dest": dest, "total_m": total, "minutes": max(1, round(seconds / 60)),
                        "segments": segments, "steps": steps})


if __name__ == "__main__":
    app.run(debug=False, port=5055, threaded=True)
