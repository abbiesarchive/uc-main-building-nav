"""A* Pathfinding and Room Search for Indoor Navigation."""
import heapq
import math
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from map_data import is_walkable, load_rooms, LINK_TYPES
from floors import load_all, get_floor


def get_all_rooms():
    """Mengambil seluruh ruangan dari seluruh lantai yang terpetakan."""
    all_rooms = []
    for f in load_all():
        for r in load_rooms(f):
            all_rooms.append({**r, "floor": f})
    return all_rooms


def get_room_center(room):
    """Mendapatkan titik koordinat tepat di ruangan / lift / tangga."""
    c = room["polygon"].centroid
    return (round(c.x, 1), round(c.y, 1))


def heuristic(p1, p2):
    """Fungsi heuristik A* menggunakan jarak Euclidean (admissible dan konsisten)."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def astar_to_room(floor, start, target_room):
    """Algoritma A* menuju tepat ke ruangan / lift / tangga melewati koridor tanpa memotong lift/tangga/ruangan lain."""
    rooms = load_rooms(floor)
    poly = target_room["polygon"]
    goal = get_room_center(target_room)

    start_pt_geom = Point(*start)
    start_room = next((r for r in rooms if r["polygon"].covers(start_pt_geom)), None)

    # Ruangan/lift/tangga yang dilarang dipotong: semua ruangan KECUALI target_room, Lounge, dan start_room
    blocked = [r["polygon"] for r in rooms 
               if r["room_id"] != target_room["room_id"] 
               and r["type"] != "Lounge" 
               and (not start_room or r["room_id"] != start_room["room_id"])]
    blocked_union = unary_union(blocked) if blocked else None

    def can_pass(x, y):
        if not is_walkable(floor, x, y):
            return False
        if blocked_union and blocked_union.covers(Point(x, y)):
            return False
        return True

    if target_room["type"] == "Lounge" or target_room["type"] in LINK_TYPES:
        entry = (round(goal[0]), round(goal[1]))
    else:
        xmin, ymin, xmax, ymax = poly.bounds
        candidates = []
        for dist in (1, 2, 3, 5):
            for x in range(int(xmin) - dist, int(xmax) + dist + 1):
                for y in (int(ymin) - dist, int(ymax) + dist):
                    if can_pass(x, y):
                        candidates.append((x, y))
            for y in range(int(ymin) - dist, int(ymax) + dist + 1):
                for x in (int(xmin) - dist, int(xmax) + dist):
                    if can_pass(x, y):
                        candidates.append((x, y))
            if candidates:
                break
        candidates.sort(key=lambda p: math.hypot(p[0] - goal[0], p[1] - goal[1]))
        entry = candidates[0] if candidates else (round(start[0]), round(start[1]))

    sx, sy = round(start[0]), round(start[1])
    start_pt = (sx, sy)
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    # Inisialisasi struktur data A* standar:
    # open_set   : Priority queue menyimpan tuple (f_score, g_score, node)
    # came_from  : Map penelusuran balik (parent pointer) untuk rekonstruksi rute optimal
    # g_score    : Biaya aktual terkecil dari start ke setiap node (g(n))
    # f_score    : Estimasi total biaya f(n) = g(n) + h(n)
    # closed_set : Node yang sudah dievaluasi optimal
    open_set = []
    came_from = {}
    g_score = {start_pt: 0.0}
    f_score = {start_pt: heuristic(start_pt, entry)}
    heapq.heappush(open_set, (f_score[start_pt], 0.0, start_pt))
    closed_set = set()

    while open_set:
        current_f, current_g, current = heapq.heappop(open_set)

        if current in closed_set:
            continue
        closed_set.add(current)

        # Evaluasi apakah sudah mencapai radius target/entry (toleransi 1.2 m)
        if heuristic(current, entry) <= 1.2:
            # Rekonstruksi rute optimal dari came_from
            curr = current
            path = [curr]
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()

            full_path = [start] + path[1:] + [entry, goal]
            cleaned = [full_path[0]]
            for p in full_path[1:]:
                if p != cleaned[-1]:
                    cleaned.append(p)
            return LineString(cleaned)

        for dx, dy in dirs:
            nx, ny = current[0] + dx, current[1] + dy
            neighbor = (nx, ny)

            if neighbor in closed_set:
                continue

            if can_pass(nx, ny):
                step_cost = math.hypot(dx, dy)
                tentative_g = current_g + step_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = heuristic(neighbor, entry)
                    f = tentative_g + h
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, tentative_g, neighbor))

    return LineString([start, goal])


def going_up(current_floor, target_floor):
    """True if the target floor is above the current floor (uses LEVEL, so 2A is between 2 and 3)."""
    return get_floor(target_floor).LEVEL > get_floor(current_floor).LEVEL


def floor_cost(start_floor, target_floor):
    """Cheapest stair/lift cost to get from one floor to another, or None if there is no way.
    Dijkstra over floors; every LINKS entry is an edge (cost = its "cost")."""
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


def find_route(current_floor, start_pos, target_room):
    """Menghitung rute optimal tepat ke ruangan atau lift/tangga yang sesuai jalannya."""
    target_floor = str(target_room["floor"])

    # 1. Ruangan berada di lantai yang sama -> langsung ke ruangan
    if target_floor == current_floor:
        line = astar_to_room(current_floor, start_pos, target_room)
        info = f"Rute menuju ruangan {target_room['name']} ({line.length:.1f} m)"
        return line, info, target_room

    # 2. Ruangan di lantai lain -> pakai lift/tangga yang benar-benar menuju lantai tujuan
    #    (langsung atau lewat lantai lain). Pilih yang total biayanya paling kecil:
    #    jarak jalan + biaya lift/tangga + biaya sisa perjalanan antar lantai.
    settings = get_floor(current_floor)
    stair_lift_rooms = [r for r in load_rooms(current_floor) if r["type"] in LINK_TYPES]
    up_needed = going_up(current_floor, target_floor)

    candidates = []
    for r in stair_lift_rooms:
        links = settings.LINKS.get(r["room_id"], {})
        step = links.get("up" if up_needed else "down")
        if step is None:
            continue
        rest = floor_cost(step, target_floor)
        if rest is None:
            continue   # dari lantai itu tidak bisa sampai ke lantai tujuan
        c = r["polygon"].centroid
        dist = math.hypot(start_pos[0] - c.x, start_pos[1] - c.y)
        candidates.append((r, dist + links.get("cost", 0) + rest))

    if not candidates:
        for r in stair_lift_rooms:
            c = r["polygon"].centroid
            candidates.append((r, math.hypot(start_pos[0] - c.x, start_pos[1] - c.y)))

    candidates.sort(key=lambda c: c[1])
    best_link, _ = candidates[0]
    line = astar_to_room(current_floor, start_pos, best_link)
    arah = "naik" if up_needed else "turun"
    next_floor = settings.LINKS.get(best_link["room_id"], {}).get("up" if up_needed else "down", target_floor)
    info = f"Menuju {best_link['name']} untuk {arah} ke Lantai {next_floor} (Tujuan: {target_room['name']} di Lantai {target_floor})"
    return line, info, best_link


def get_current_instruction(current_floor, pos, target_room):
    """Menghasilkan 1 arahan langkah aktif tepat menuju ruangan atau lift/tangga jalannya."""
    target_floor = str(target_room["floor"])
    line, info, dest = find_route(current_floor, pos, target_room)

    # Kasus lantai yang sama
    if target_floor == current_floor:
        if line.length < 1.5:
            return f"🎉 Anda telah sampai di ruangan {target_room['name']}!"
        pts = list(line.simplify(1.2).coords)
        if len(pts) <= 2:
            return f"Lurus sejauh {round(line.length)} m menuju ruangan {target_room['name']}"

        d_turn = math.hypot(pts[1][0] - pos[0], pts[1][1] - pos[1])
        v1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        v2 = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        turn = "belok kiri" if cross > 0 else "belok kanan"
        return f"Lurus sejauh {round(d_turn)} m, lalu {turn} menuju ruangan {target_room['name']}"
    else:
        # Kasus beda lantai: menuju lift atau tangga yang memang jalannya
        up = going_up(current_floor, target_floor)
        arah = "naik" if up else "turun"
        next_floor = get_floor(current_floor).LINKS.get(dest["room_id"], {}).get("up" if up else "down", target_floor)
        if line.length < 2.0:
            return f"Gunakan {dest['name']} untuk {arah} ke Lantai {next_floor} (Tujuan: {target_room['name']} di Lantai {target_floor})"
        pts = list(line.simplify(1.2).coords)
        if len(pts) <= 2:
            return f"Lurus sejauh {round(line.length)} m menuju {dest['name']} untuk {arah} ke Lt. {next_floor}"
        d_turn = math.hypot(pts[1][0] - pos[0], pts[1][1] - pos[1])
        v1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        v2 = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        turn = "belok kiri" if cross > 0 else "belok kanan"
        return f"Lurus sejauh {round(d_turn)} m, lalu {turn} menuju {dest['name']} ({arah} ke Lt. {next_floor})"
