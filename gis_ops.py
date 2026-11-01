"""The two GIS operations. Units are meters.

Buffer        a circle of radius r around the user (Point -> Polygon)
Spatial Join  which rooms (Polygon layer) touch the buffer / the route
"""
from shapely.geometry import Point

# untuk buat buffer di sekitar titik user dengan radius 
def buffer_around(x, y, radius):
    return Point(x, y).buffer(radius)

# function untuk bantu liat ruangan yang ada di dalam titik buffer user
def spatial_join(rooms, shape):
    """Rooms that intersect the given shape (a buffer or a route line)."""
    return [room for room in rooms if room["polygon"].intersects(shape)]

# intinya dia panggil spatial join dan buffer biar bsa liat ruangan yang ada di dalam buffer user, nanti dipake di movement.py
def rooms_in_buffer(rooms, x, y, radius):
    return spatial_join(rooms, buffer_around(x, y, radius))

# cari dan urutkan ruangan yang dilewati rute user, nanti dipake di movement.py
def rooms_along_route(rooms, route_line, width=1.0):
    """Rooms the route passes through, in order from the start.
    A small buffer around the line stands for the width of a person."""
    hits = spatial_join(rooms, route_line.buffer(width / 2))
    return sorted(hits, key=lambda r: route_line.project(r["polygon"].centroid))
