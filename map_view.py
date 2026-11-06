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


FONT = 6.5
MIN_FONT = 3.0


def draw_labels(ax, labels, bounds):
    """Write every room label so it fits inside its room: shrink the font (and turn the text
    90 degrees for tall narrow rooms) until it fits. Tries the full text (id + name) down to
    4.5 pt first, then just the id down to MIN_FONT. Only a room too tiny even for that stays blank."""
    fig = ax.figure
    xmin, ymin, xmax, ymax = bounds
    box_w = fig.get_figwidth() * 72 * 0.88          # axes area in points (tight_layout is about this)
    box_h = fig.get_figheight() * 72 * 0.82
    pt_per_m = min(box_w / (xmax - xmin + 4), box_h / (ymax - ymin + 4))   # aspect is equal

    def fits(text, size, w, h):
        lines = text.split("\n")
        need_w = max(map(len, lines)) * 0.62 * size / pt_per_m + 0.3
        need_h = len(lines) * 1.25 * size / pt_per_m + 0.2
        return need_w <= w and need_h <= h

    def sizes(top, low):
        size = top
        while size >= low - 1e-9:
            yield size
            size -= 0.5

    for poly, label, bold, is_link in labels:
        x0, y0, x1, y1 = poly.bounds
        w, h = x1 - x0, y1 - y0
        short = label.split("\n")[0]
        tries = [(label, s) for s in sizes(FONT, 4.5)] + [(short, s) for s in sizes(FONT, MIN_FONT)]
        found = None
        for text, size in tries:
            if fits(text, size, w, h):
                found = (text, size, 0)
                break
            if fits(text, size, h, w):
                found = (text, size, 90)
                break
        if found is None:
            continue
        text, size, rotation = found
        ax.text(poly.centroid.x, poly.centroid.y, text, ha="center", va="center", zorder=5,
                fontsize=size, fontweight="bold" if bold else "normal", rotation=rotation,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8) if is_link else None)


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
    labels = []
    for room in rooms:
        poly = room["polygon"]
        is_link = room["type"] in LINK_TYPES
        links = get_floor(floor).LINKS.get(room["room_id"])
        unavailable = is_link and not links          # e.g. a lift that does not stop on this floor
        patches[room["room_id"]] = add_polygon(
            ax, poly, facecolor="#d6d6d6" if unavailable else COLORS.get(room["type"], "#eeeeee"),
            edgecolor="#555555", linewidth=0.8, zorder=2,
            hatch="///" if room["type"] == "Stairs" else None)
        if unavailable:
            label, bold = ("✕ Lift" if room["type"] == "Lift" else "✕ Stairs") + "\nnot served", True
        elif is_link:
            label, bold = link_label(room, links), True
        else:
            label, bold = room["room_id"] + "\n" + room["name"].split(" (")[0], False
        labels.append((poly, label, bold, is_link))

    for void in voids(floor):
        add_polygon(ax, void, facecolor="#bbbbbb", edgecolor="black",
                    hatch="xx", linewidth=1, zorder=2)
        ax.text(void.centroid.x, void.centroid.y, "VOID", ha="center",
                va="center", fontsize=8, zorder=5)

    xmin, ymin, xmax, ymax = outline.bounds
    ax.set_xlim(xmin - 2, xmax + 2)
    ax.set_ylim(ymin - 2, ymax + 2)
    ax.set_aspect("equal")
    draw_labels(ax, labels, outline.bounds)
    ax.set_xticks(range(int(xmin), int(xmax) + 1, 10))
    ax.set_yticks(range(int(ymin), int(ymax) + 1, 5))
    ax.grid(True, linewidth=0.3, zorder=0)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    return patches
