"""Draw a floor with a user, a buffer and a route (a picture, no window).
Run:  python draw_map.py 2       (saves map_lt2.png)
Change the numbers under "Try this" and run it again. Units are meters.
"""
import sys

import matplotlib.pyplot as plt
from shapely.geometry import LineString

from floors import get_floor
from gis_ops import buffer_around, rooms_along_route, rooms_in_buffer
from map_data import build_walkable, load_rooms, room_at
from map_view import add_polygon, draw_floor

FLOOR = sys.argv[1] if len(sys.argv) > 1 else "2"

# ---- Try this ------------------------------------------------------------
USER = get_floor(FLOOR).START                 # x, y of the user (m)
RADIUS = 5                                    # buffer radius (m)
ROUTE = [USER, (USER[0] + 12, USER[1]), (USER[0] + 20, USER[1] - 3)]   # points (m)
# --------------------------------------------------------------------------

rooms = load_rooms(FLOOR)
fig, ax = plt.subplots(figsize=(18, 8))
patches = draw_floor(ax, FLOOR, rooms, build_walkable(FLOOR, rooms))

near = rooms_in_buffer(rooms, *USER, RADIUS)
for room in near:                                          # Spatial Join result
    patches[room["room_id"]].set_edgecolor("#d00000")
    patches[room["room_id"]].set_linewidth(2.2)
add_polygon(ax, buffer_around(*USER, RADIUS), facecolor="#1565c0", alpha=0.15,
            edgecolor="#1565c0", linewidth=1.5, zorder=3)  # Buffer

route = LineString(ROUTE)                                  # LineString layer
ax.plot(*route.xy, color="#1565c0", linewidth=3.5, zorder=6, label=f"Route ({route.length:.1f} m)")
ax.plot(*USER, "o", color="#d00000", markersize=11, markeredgecolor="white",
        zorder=7, label=f"User, buffer {RADIUS} m")                 # Point layer

here = room_at(rooms, *USER)
passed = rooms_along_route(rooms, route)
ax.set_title(f"Lt. {FLOOR}: user at {USER} in {here['name'] if here else 'corridor / lobby'}. "
             f"Red outline = rooms in the buffer. "
             f"Route passes: {', '.join(r['room_id'] for r in passed)}", fontsize=10)
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "Sizes are estimates, about +/- 0.5 m", fontsize=8)

out = f"map_lt{FLOOR}.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
plt.show()
