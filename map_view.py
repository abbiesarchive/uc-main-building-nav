"""Draw one floor on a matplotlib axes. Units are meters."""
from matplotlib.patches import Polygon as MplPolygon

from floors import get_floor
from map_data import LINK_TYPES, building, voids

COLORS = {
    "Lift": "#f4a261", "Stairs": "#e76f51", "Toilet": "#8ecae6",
    "Pantry": "#b7e4c7", "Storage": "#ced4da", "Library": "#ffe8a3",
    "Lounge": "#d8c3f0", "Lab": "#a8dadc", "MeetingRoom": "#ffc8dd",
    "Office": "#cde7b0", "Utility": "#dddddd",
}


def link_label(room, links):
    """Text for a stair or lift: where it goes, e.g. "Stairs\n▲ Lt. 2A"."""
    kind = "Lift" if room["type"] == "Lift" else "Stairs"
    lines = [kind]
    if "up" in links:
        lines.append(f"▲ Lt. {links['up']}")
    if "down" in links:
        lines.append(f"▼ Lt. {links['down']}")
    return "\n".join(lines)


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

    # Corridors and lobbies stay white (the floor). Only open patches that belong
    # to an L-shaped room are drawn, in that room's colour.
    room_type = {r["room_id"]: r["type"] for r in rooms}
    for area in walkable:
        owner = area["part_of"]
        if owner:
            add_polygon(ax, area["polygon"], facecolor=COLORS.get(room_type.get(owner), "#eeeeee"),
                        edgecolor="#555555", linewidth=0.8, zorder=2)

    patches = {}
    for room in rooms:
        poly = room["polygon"]
        is_link = room["type"] in LINK_TYPES
        patches[room["room_id"]] = add_polygon(
            ax, poly, facecolor=COLORS.get(room["type"], "#eeeeee"),
            edgecolor="#555555", linewidth=0.8, zorder=2,
            hatch="///" if room["type"] == "Stairs" else None)
        links = get_floor(floor).LINKS.get(room["room_id"])
        if is_link and links:
            label, style = link_label(room, links), dict(fontweight="bold", fontsize=6.5)
        else:
            label = room["room_id"]
            if poly.area >= 40:
                label += "\n" + room["name"].split(" (")[0]
            style = dict(fontsize=6.5)
        ax.text(poly.centroid.x, poly.centroid.y, label, ha="center", va="center", zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8) if is_link else None,
                **style)

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
