"""A* Pathfinding and Room Search for Indoor Navigation."""
import heapq
import math
from shapely.geometry import LineString, Point
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


def astar_to_room(floor, start, target_room):
    """Algoritma A* menuju tepat ke ruangan / lift / tangga melewati koridor."""
    poly = target_room["polygon"]
    goal = get_room_center(target_room)

    sx, sy = round(start[0]), round(start[1])
    start_pt = (sx, sy)

    # Jika ruangan bisa dilewati (lift, tangga, lounge), cari langsung ke goal
    # Jika ruangan tertutup, cari titik koridor terdekat dari goal untuk pintu masuk
    if is_walkable(floor, goal[0], goal[1]):
        entry = (round(goal[0]), round(goal[1]))
    else:
        xmin, ymin, xmax, ymax = poly.bounds
        candidates = []
        for dist in (1, 2, 3, 5):
            for x in range(int(xmin) - dist, int(xmax) + dist + 1):
                for y in (int(ymin) - dist, int(ymax) + dist):
                    if is_walkable(floor, x, y):
                        candidates.append((x, y))
            for y in range(int(ymin) - dist, int(ymax) + dist + 1):
                for x in (int(xmin) - dist, int(xmax) + dist):
                    if is_walkable(floor, x, y):
                        candidates.append((x, y))
            if candidates:
                break
        candidates.sort(key=lambda p: math.hypot(p[0] - goal[0], p[1] - goal[1]))
        entry = candidates[0] if candidates else start_pt

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    queue = [(0, 0, start_pt, [start_pt])]
    visited = {start_pt: 0}

    while queue:
        _, cost, current, path = heapq.heappop(queue)
        if math.hypot(current[0] - entry[0], current[1] - entry[1]) <= 1.2:
            full_path = [start] + path[1:] + [entry, goal]
            cleaned = [full_path[0]]
            for p in full_path[1:]:
                if p != cleaned[-1]:
                    cleaned.append(p)
            return LineString(cleaned)

        for dx, dy in dirs:
            nx, ny = current[0] + dx, current[1] + dy
            if is_walkable(floor, nx, ny):
                step_cost = math.hypot(dx, dy)
                new_cost = cost + step_cost
                neighbor = (nx, ny)
                if neighbor not in visited or new_cost < visited[neighbor]:
                    visited[neighbor] = new_cost
                    h = math.hypot(nx - entry[0], ny - entry[1])
                    heapq.heappush(queue, (new_cost + h, new_cost, neighbor, path + [neighbor]))

    return LineString([start, goal])


def find_route(current_floor, start_pos, target_room):
    """Menghitung rute optimal tepat ke ruangan atau lift/tangga yang sesuai jalannya."""
    target_floor = str(target_room["floor"])

    # 1. Ruangan berada di lantai yang sama -> langsung ke ruangan
    if target_floor == current_floor:
        line = astar_to_room(current_floor, start_pos, target_room)
        info = f"Rute menuju ruangan {target_room['name']} ({line.length:.1f} m)"
        return line, info, target_room

    # 2. Ruangan di lantai lain -> cari lift atau tangga yang memang jalannya
    settings = get_floor(current_floor)
    stair_lift_rooms = [r for r in load_rooms(current_floor) if r["type"] in LINK_TYPES]

    level_current = getattr(settings, "LEVEL", int(current_floor[0]))
    target_settings = get_floor(target_floor)
    level_target = getattr(target_settings, "LEVEL", int(target_floor[0]))
    up_needed = level_target > level_current

    candidates = []
    for r in stair_lift_rooms:
        links = settings.LINKS.get(r["room_id"], {})
        if up_needed and "up" in links:
            # Validasi aturan lift barat (1,2,3,5,7) vs lift timur (1,2,4,6,7)
            if "Barat" in r["name"] and target_floor in ("4", "6"):
                continue
            if "Timur" in r["name"] and target_floor in ("3", "5"):
                continue
            c = r["polygon"].centroid
            dist = math.hypot(start_pos[0] - c.x, start_pos[1] - c.y)
            candidates.append((r, dist))
        elif not up_needed and "down" in links:
            if "Barat" in r["name"] and target_floor in ("4", "6"):
                continue
            if "Timur" in r["name"] and target_floor in ("3", "5"):
                continue
            c = r["polygon"].centroid
            dist = math.hypot(start_pos[0] - c.x, start_pos[1] - c.y)
            candidates.append((r, dist))

    if not candidates:
        for r in stair_lift_rooms:
            c = r["polygon"].centroid
            candidates.append((r, math.hypot(start_pos[0] - c.x, start_pos[1] - c.y)))

    candidates.sort(key=lambda c: c[1])
    best_link, _ = candidates[0]
    line = astar_to_room(current_floor, start_pos, best_link)
    arah = "naik" if up_needed else "turun"
    info = f"Menuju {best_link['name']} untuk {arah} ke Lantai {target_floor} (Tujuan: {target_room['name']})"
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
            return f"📍 Lurus sejauh {round(line.length)} m menuju ruangan {target_room['name']}"

        d_turn = math.hypot(pts[1][0] - pos[0], pts[1][1] - pos[1])
        v1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        v2 = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        turn = "belok kiri" if cross > 0 else "belok kanan"
        return f"📍 Lurus sejauh {round(d_turn)} m, lalu {turn} menuju ruangan {target_room['name']}"
    else:
        # Kasus beda lantai: menuju lift atau tangga yang memang jalannya
        arah = "naik" if int(target_floor[0]) > int(current_floor[0]) else "turun"
        if line.length < 2.0:
            return f"📍 Gunakan {dest['name']} untuk {arah} ke Lantai {target_floor} (Tujuan: {target_room['name']})"
        pts = list(line.simplify(1.2).coords)
        if len(pts) <= 2:
            return f"📍 Lurus sejauh {round(line.length)} m menuju {dest['name']} untuk {arah} ke Lt. {target_floor}"
        d_turn = math.hypot(pts[1][0] - pos[0], pts[1][1] - pos[1])
        v1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        v2 = (pts[2][0] - pts[1][0], pts[2][1] - pts[1][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        turn = "belok kiri" if cross > 0 else "belok kanan"
        return f"📍 Lurus sejauh {round(d_turn)} m, lalu {turn} menuju {dest['name']} ({arah} ke Lt. {target_floor})"
