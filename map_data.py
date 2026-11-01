"""Map layers for one floor, built from the room CSV and floors/<floor>.py.
Units are meters.

Layers:
    Polygon     rooms (one rectangle per row) and corridors
    Point       the user (made in movement.py)
    LineString  the trail / the route
"""
from functools import lru_cache

import pandas as pd
from shapely.geometry import Point, box
from shapely.ops import unary_union

from floors import ROOT, get_floor

# stairs and lifts: the dot can stand here and press E / Q to change floor
LINK_TYPES = ("Stairs", "Lift")

# untuk ambil outline bangunan lantai tertentu, return shapely polygon
# intinya dia jadikan 1 polygon dari beberapa outline suatu lantai kek misal ada 4 outline dengan 4 koordinat, nanti jadi 1 polygon saja 
@lru_cache
def building(floor):
    """Where people can be (the outline of the floor)."""
    return unary_union([box(*rect) for rect in get_floor(floor).OUTLINE])

# ambil titik voids lantai tertentu untuk bikin polygon 
@lru_cache
def voids(floor):
    """Holes in the floor (not rooms, nobody can stand there)."""
    return [box(*rect) for rect in get_floor(floor).VOIDS]

# baca file csv yg berisi data ruangan, return dataframe
def read_csv(path):
    df = pd.read_csv(path, dtype={"floor": str, "room_id": str})
    df.columns = df.columns.str.strip()
    return df

# ambil konfigurasi lantai, ambil csv, return list of dict berisi room_id, name, type, polygon
def load_rooms(floor, csv_path=None):
    """Return a list of dicts: room_id, name, type, polygon."""
    settings = get_floor(floor)
    df = read_csv(csv_path or ROOT / settings.ROOMS_CSV)
    # ambil data lantai itu sendiri saja misal kl lt 3 ya 3 saja 
    parts = [df[df["floor"] == floor]]
    # rooms shared with another floor (the Lt. 2 / 2A core) are stored once, there
    for other, ids in settings.SHARED.items():
        other_df = read_csv(ROOT / get_floor(other).ROOMS_CSV)
        parts.append(other_df[other_df["room_id"].isin(ids)])
# gabung semua data ruangan (polygon) jadi 1 lantai 
    rows = pd.concat(parts)
    return [{"room_id": r.room_id, "name": r.name, "type": r.type,
             "polygon": box(r.xmin, r.ymin, r.xmax, r.ymax)}
# itertuples untuk iterasi tiap baris dataframe, r.room_id dst untuk ambil data tiap kolom
            for r in rows.itertuples()]

# ini untuk cari ruangan kosong yang bukan ruangan atau void tapi masih dalam outline biar bsa jadi koridornya 
# ini hanya untuk cari kooridnat yg kosongnya, nanti di build_walkable baru diubah jadi area yg bisa dilewati
def free_rectangles(rooms, floor):
    """Cut the free space (outline minus rooms minus voids) into rectangles."""
# ambil outline dari lantai lalu dikurangi dari polygon ruangan yang ada dan voidnya juga, jadi ambil semua ruangan yang selain polygon ruangan dan void (difference)
    free = building(floor).difference(unary_union([r["polygon"] for r in rooms]))
    for void in voids(floor):
        free = free.difference(void)

# jadiin 1 semua polygon yg ada untuk bentuk kotak" denahnya lalu ambil semua koordinat x dan y dari polygon itu untuk bikin grid, nanti grid ini yg dipake buat bikin area yg bisa dilewati user

# buat biar ga ada duplikasi titik jadi cuman ambil titik max min yang unik saja, misal ada 4 polygon dengan 4 koordinat, nanti jadi 1 koordinat saja yang diambil untuk bikin grid
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

# ambil data dari free rectangle untuk buat area yang bsa dilewati kayak loby koridor dll (buat lift areanya kyk file di csv)
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

# ambil data dari build_walkable untuk bikin area yang bisa dilewati user, return shapely polygon
@lru_cache
def walkable_area(floor):
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
                # buffer 0.01 untuk bikin garis ruangannya jadi 1 cm biar user ga bisa jalan di garis ruangan itu
                area = area.difference(room["polygon"].buffer(0.01, join_style="mitre"))
    return area

# periksa koordinat ini tuh bisa dilewati atatu tidak 
def is_walkable(floor, x, y):
    return walkable_area(floor).covers(Point(x, y))

# cek user ada di ruangan apa 
def room_at(rooms, x, y):
    """The room that contains the point, or None (corridor / lobby)."""
    p = Point(x, y)
    for room in rooms:
        if room["polygon"].covers(p):
            return room
    return None
