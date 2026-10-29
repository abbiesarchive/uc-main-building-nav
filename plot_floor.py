"""Draw one floor from its csv, run the checks, optionally lay it over the plan image.

Usage:
    python plot_floor.py 2            plain drawing    -> floor_2_plain.png
    python plot_floor.py 2 overlay    on the plan      -> floor_2_overlay.png

The floor's settings (csv, image, calibration) come from floors/lantai<N>.py.
Units are meters. Sizes are estimates, about +/- 0.5 m.
"""
import sys

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from check_floors import check_floor
from floors import ROOT, get_floor
from map_data import building, load_rooms
from map_view import COLORS

PX_PER_M = 15.03


def draw(floor, rooms, overlay=False):
    settings = get_floor(floor)
    xmin, ymin, xmax, ymax = building(floor).bounds
    fig, ax = plt.subplots(figsize=(16, 10))
    if overlay:
        x0, ytop = settings.CALIBRATION
        img = mpimg.imread(ROOT / settings.IMAGE)
        h_px, w_px = img.shape[0], img.shape[1]
        # image pixel -> meters, so the boxes stay in meters
        left, right = (0 - x0) / PX_PER_M, (w_px - x0) / PX_PER_M
        top = ymax - (0 - ytop) / PX_PER_M
        bottom = ymax - (h_px - ytop) / PX_PER_M
        ax.imshow(img, extent=(left, right, bottom, top), zorder=0)
    for r in rooms:
        x0_, y0_, x1_, y1_ = r["polygon"].bounds
        ax.add_patch(Rectangle((x0_, y0_), x1_ - x0_, y1_ - y0_,
                               facecolor=COLORS.get(r["type"], "#eeeeee"),
                               edgecolor="red" if overlay else "black",
                               alpha=0.35 if overlay else 0.9, linewidth=1.2, zorder=2))
        ax.text((x0_ + x1_) / 2, (y0_ + y1_) / 2, r["room_id"],
                ha="center", va="center", fontsize=6, zorder=3)
    ax.set_xlim(xmin - 2, xmax + 2)
    ax.set_ylim(ymin - 4, ymax + 2)
    ax.set_aspect("equal")
    ax.set_xticks(range(int(xmin), int(xmax) + 1, 10))
    ax.set_yticks(range(int(ymin), int(ymax) + 1, 5))
    ax.grid(True, linewidth=0.3)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"Lt. {floor}  (sizes are estimates, about +/- 0.5 m)")
    return fig


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    floor = sys.argv[1]
    overlay = len(sys.argv) > 2 and sys.argv[2] == "overlay"
    settings = get_floor(floor)
    if overlay and not (settings.IMAGE and settings.CALIBRATION):
        sys.exit(f"floors/lantai{floor}.py needs IMAGE and CALIBRATION for the overlay.")

    rooms = load_rooms(floor)
    print(f"{len(rooms)} rooms on floor {floor}")
    errors, warnings = check_floor(floor)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    if not errors:
        print("No errors found.")

    out = f"floor_{floor}_{'overlay' if overlay else 'plain'}.png"
    draw(floor, rooms, overlay).savefig(out, dpi=110, bbox_inches="tight")
    print("saved", out)
