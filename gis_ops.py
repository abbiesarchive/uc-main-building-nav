"""The two GIS operations. Units are meters.

Buffer        a circle of radius r around the user (Point -> Polygon)
Spatial Join  which rooms (Polygon layer) touch the buffer / the route
"""
from shapely.geometry import Point


def buffer_around(x, y, radius):
    return Point(x, y).buffer(radius)


def spatial_join(rooms, shape):
    """Rooms that intersect the given shape (a buffer or a route line)."""
    return [room for room in rooms if room["polygon"].intersects(shape)]


def rooms_in_buffer(rooms, x, y, radius):
    return spatial_join(rooms, buffer_around(x, y, radius))


def rooms_along_route(rooms, route_line, width=2.2):
    """Rooms the route passes through, in order from the start.
    width=2.2 m (radius 1.1 m) so walking on the 1 m corridor grid touches adjacent room walls."""
    hits = spatial_join(rooms, route_line.buffer(width / 2))
    return sorted(hits, key=lambda r: route_line.project(r["polygon"].centroid))