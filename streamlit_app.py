"""Walk through the building in the browser.
Run:  streamlit run streamlit_app.py

Same rules as app.py (movement.py). Streamlit cannot read key presses by itself, so
the page has buttons, and a small script (KEYS_JS) presses them when you hit the
keyboard keys. Every click redraws the Point (you) and the Buffer.
"""
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.patches import Polygon as MplPolygon

from map_view import draw_floor
from movement import Navigator

MAX_LINES = 10

# keyboard key -> label of the button to press
KEYS_JS = """
<script>
const doc = window.parent.document;
if (!window.parent.__ucKeys) {
  window.parent.__ucKeys = true;
  const keys = {w: "W", a: "A", s: "S", d: "D", e: "E", q: "Q",
                ArrowUp: "W", ArrowLeft: "A", ArrowDown: "S", ArrowRight: "D"};
  doc.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
    const label = keys[event.key] || keys[event.key.toLowerCase()];
    if (!label) return;
    for (const button of doc.querySelectorAll("button")) {
      const text = button.innerText.trim();
      if (text === label || (label === "E" || label === "Q") && text.startsWith(label + " ")) {
        event.preventDefault();
        button.click();
        return;
      }
    }
  });
}
</script>
"""


def get_nav():
    """One Navigator per browser session."""
    if "nav" not in st.session_state:
        st.session_state.nav = Navigator()
        st.session_state.message = ""
    return st.session_state.nav


def press(action, *args):
    nav = st.session_state.nav
    if action == "move":
        st.session_state.message = nav.move(*args)
    elif action == "floor":
        st.session_state.message = nav.change_floor(up=args[0])
    elif action == "radius":
        nav.set_radius(args[0])
        st.session_state.message = ""
    elif action == "reset":
        nav.reset()
        st.session_state.message = ""


def draw(nav, near):
    data = nav.floors[nav.floor]
    fig, ax = plt.subplots(figsize=(14, 4.6))
    patches = draw_floor(ax, nav.floor, data["rooms"], data["walkable"])
    for room, _ in near:
        patches[room["room_id"]].set_edgecolor("#d00000")
        patches[room["room_id"]].set_linewidth(2.2)
    ax.add_patch(MplPolygon(list(nav.buffer().exterior.coords), closed=True, facecolor="#1565c0",
                            alpha=0.15, edgecolor="#1565c0", linewidth=1.5, zorder=3))
    ax.plot([nav.x], [nav.y], "o", color="#d00000", markersize=11, markeredgecolor="white", zorder=7)
    ax.set_title(f"Lt. {nav.floor}   you are at ({nav.x:g}, {nav.y:g}) m   "
                 f"(sizes are estimates, about +/- 0.5 m)", fontsize=10)
    return fig


st.set_page_config(page_title="UC Main Building - navigation", layout="wide")
nav = get_nav()
near = nav.nearby()

st.pyplot(draw(nav, near))
plt.close("all")
st.iframe(KEYS_JS, height=1)
st.caption("Keyboard works too: W A S D or arrows walk, E up, Q down (click the page first).")

controls, info = st.columns([1, 2])
with controls:
    st.write("**Walk (1 m per click)**")
    _, up, _ = st.columns(3)
    left, down, right = st.columns(3)
    up.button("W", on_click=press, args=("move", 0, 1), use_container_width=True)
    left.button("A", on_click=press, args=("move", -1, 0), use_container_width=True)
    down.button("S", on_click=press, args=("move", 0, -1), use_container_width=True)
    right.button("D", on_click=press, args=("move", 1, 0), use_container_width=True)

    st.write("**Stair / lift**")
    e, q = st.columns(2)
    e.button("E  up", on_click=press, args=("floor", True), use_container_width=True)
    q.button("Q  down", on_click=press, args=("floor", False), use_container_width=True)

    st.write(f"**Buffer radius: {nav.radius} m**")
    minus, plus, reset = st.columns(3)
    minus.button("-", on_click=press, args=("radius", -1), use_container_width=True)
    plus.button("+", on_click=press, args=("radius", +1), use_container_width=True)
    reset.button("Restart", on_click=press, args=("reset",), use_container_width=True)

with info:
    here = nav.here()
    st.write(f"**You are in:** {here['name'] + ' (' + here['type'] + ')' if here else 'corridor / lobby'}")
    if nav.link_hint():
        st.info(nav.link_hint())
    if st.session_state.message:
        st.warning(st.session_state.message)

    st.write(f"**Rooms in the buffer ({len(near)}):**")
    st.text("\n".join(
        f"{'inside' if dist == 0 else f'{dist:.1f} m':>7}  {room['room_id']}  {room['name']}"
        for room, dist in near[:MAX_LINES]) + (f"\n... and {len(near) - MAX_LINES} more" if len(near) > MAX_LINES else ""))

    passed = [room["room_id"] for room in nav.visited()]
    st.write(f"**Rooms your trail passed ({len(passed)}):** " + ", ".join(passed))
