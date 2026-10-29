"""Draw one floor on a matplotlib axes. Units are meters."""
from matplotlib.patches import Polygon as MplPolygon

from map_data import building, voids

COLORS = {
    "Lift": "#f4a261", "Stairs": "#e76f51", "Toilet": "#8ecae6",
    "Pantry": "#b7e4c7", "Storage": "#ced4da", "Library": "#ffe8a3",
    "Lounge": "#d8c3f0", "Lab": "#a8dadc", "MeetingRoom": "#ffc8dd",
    "Office": "#cde7b0", "Utility": "#dddddd",
}
CORRIDOR = "#fff3c4"


def add_polygon(ax, polygon, **style):
    patch = MplPolygon(list(polygon.exterior.coords), closed=True, **style)
    ax.add_patch(patch)
    return patch


def draw_floor(ax, floor, rooms, walkable):
    """Draw the fixed part of the map. Returns {room_id: patch} so the app
    can highlight rooms later."""
    ax.clear()
    outline = building(floor)
    add_polygon(ax, outline, facecolor="white", edgecolor="black", linewidth=2, zorder=1)

    room_type = {r["room_id"]: r["type"] for r in rooms}
    for area in walkable:
        owner = area["part_of"]          # open patch of an L-shaped room
        add_polygon(ax, area["polygon"],
                    facecolor=COLORS.get(room_type.get(owner), CORRIDOR),
                    edgecolor="#555555" if owner else "#e0c870",
                    linewidth=0.8 if owner else 0.5, zorder=2)
        if not owner and area["polygon"].area >= 10:
            ax.text(area["polygon"].centroid.x, area["polygon"].centroid.y,
                    "lobi / koridor", ha="center", va="center", fontsize=6,
                    style="italic", color="#8a6d00", zorder=5)

    patches = {}
    for room in rooms:
        poly = room["polygon"]
        patches[room["room_id"]] = add_polygon(
            ax, poly, facecolor=COLORS.get(room["type"], "#eeeeee"),
            edgecolor="#555555", linewidth=0.8, zorder=2)
        label = room["room_id"]
        if poly.area >= 40:
            label += "\n" + room["name"].split(" (")[0]
        ax.text(poly.centroid.x, poly.centroid.y, label, ha="center",
                va="center", fontsize=6.5, zorder=5)

    for void in voids(floor):
        add_polygon(ax, void, facecolor="#bbbbbb", edgecolor="black",
                    hatch="xx", linewidth=1, zorder=2)
        ax.text(void.centroid.x, void.centroid.y, "VOID", ha="center",
                va="center", fontsize=8, zorder=5)

    xmin, ymin, xmax, ymax = outline.bounds
    ax.set_xlim(xmin - 2, xmax + 2)
    ax.set_ylim(ymin - 2, ymax + 2)
    ax.set_aspect("equal")
    ax.set_xticks(range(int(xmin), int(xmax) + 1, 10))
    ax.set_yticks(range(int(ymin), int(ymax) + 1, 5))
    ax.grid(True, linewidth=0.3, zorder=0)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    return patches
