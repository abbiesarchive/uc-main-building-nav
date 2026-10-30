"""Walk through the building with the keyboard.
Run:  python app.py        (or  python app.py 3  to start on Lt. 3)

W / A / S / D or the arrow keys   walk 1 m
E / Q                             stair or lift: up / down one level
+ / -                             bigger / smaller buffer
R                                 back to the start

Every step the Point (you), the Buffer around you and the trail (LineString) are
redrawn, and the Spatial Join lists the rooms near you and the rooms you passed.
"""
import sys
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon as MplPolygon

from map_view import draw_floor
from movement import Navigator

DIRECTIONS = {
    "w": (0, 1), "Up": (0, 1),
    "s": (0, -1), "Down": (0, -1),
    "a": (-1, 0), "Left": (-1, 0),
    "d": (1, 0), "Right": (1, 0),
}
HELP = "WASD / arrows walk   E up   Q down   + / - buffer   R restart"
MAX_LINES = 10


class App:
    def __init__(self):
        self.nav = Navigator(floor=sys.argv[1] if len(sys.argv) > 1 else None)
        self.message = ""
        self.drawn_floor = None
        self.highlighted = []

        self.root = tk.Tk()
        self.root.title("UC Main Building - navigation")
        self.fig = Figure(figsize=(14, 4.6), dpi=90)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.info = tk.Text(self.root, height=17, font=("Menlo", 11),
                            state="disabled", takefocus=0)
        self.info.pack(fill="x")
        self.root.bind("<Key>", self.on_key)
        self.root.focus_force()
        self.refresh()

    # ---- drawing ----------------------------------------------------------
    def draw_static(self):
        """The part of the map that does not move. Drawn once per floor."""
        floor = self.nav.floor
        data = self.nav.floors[floor]
        self.patches = draw_floor(self.ax, floor, data["rooms"], data["walkable"])
        self.buffer_patch = MplPolygon([(0, 0)], closed=True, facecolor="#1565c0",
                                       alpha=0.15, edgecolor="#1565c0", linewidth=1.5, zorder=3)
        self.ax.add_patch(self.buffer_patch)
        (self.dot,) = self.ax.plot([], [], "o", color="#d00000", markersize=11,
                                   markeredgecolor="white", zorder=7)
        self.drawn_floor = floor
        self.highlighted = []

    def refresh(self):
        nav = self.nav
        if self.drawn_floor != nav.floor:
            self.draw_static()

        # move the parts that change every step
        self.dot.set_data([nav.x], [nav.y])
        self.buffer_patch.set_xy(list(nav.buffer().exterior.coords))

        near = nav.nearby()
        for room_id in self.highlighted:
            self.patches[room_id].set_edgecolor("#555555")
            self.patches[room_id].set_linewidth(0.8)
        self.highlighted = [room["room_id"] for room, _ in near]
        for room_id in self.highlighted:
            self.patches[room_id].set_edgecolor("#d00000")
            self.patches[room_id].set_linewidth(2.2)

        self.ax.set_title(f"Lt. {nav.floor}   you are at ({nav.x:g}, {nav.y:g}) m   "
                          f"(sizes are estimates, about +/- 0.5 m)", fontsize=10)
        self.canvas.draw_idle()
        self.write_info(near)

    def write_info(self, near):
        nav = self.nav
        here = nav.here()
        lines = [f"Lt. {nav.floor}   position ({nav.x:g}, {nav.y:g}) m   buffer radius {nav.radius} m",
                 f"You are in: {here['name'] + ' (' + here['type'] + ')' if here else 'corridor / lobby'}"]
        if nav.link_hint():
            lines.append(nav.link_hint())
        lines.append("")
        lines.append(f"Rooms in the buffer ({len(near)}):")
        for room, dist in near[:MAX_LINES]:
            where = "inside" if dist == 0 else f"{dist:.1f} m"
            lines.append(f"  {where:>7}  {room['room_id']}  {room['name']}")
        if len(near) > MAX_LINES:
            lines.append(f"  ... and {len(near) - MAX_LINES} more")
        lines.append("")
        passed = [room["room_id"] for room in nav.visited()]
        lines.append(f"Rooms your trail passed ({len(passed)}): " + ", ".join(passed))
        lines.append("")
        lines.append(self.message)
        lines.append(HELP)

        self.info.config(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", "\n".join(lines))
        self.info.config(state="disabled")

    # ---- keys -------------------------------------------------------------
    def on_key(self, event):
        self.handle(event.keysym)

    def handle(self, keysym):
        key = keysym if len(keysym) > 1 else keysym.lower()
        self.message = ""
        if key in DIRECTIONS:
            self.message = self.nav.move(*DIRECTIONS[key])
        elif key == "e":
            self.message = self.nav.change_floor(up=True)
        elif key == "q":
            self.message = self.nav.change_floor(up=False)
        elif key in ("plus", "equal"):
            self.nav.set_radius(+1)
        elif key == "minus":
            self.nav.set_radius(-1)
        elif key == "r":
            self.nav.reset()
        else:
            return
        self.refresh()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
