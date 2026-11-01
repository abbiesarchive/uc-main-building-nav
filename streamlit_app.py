"""Walk through the building in the browser.
Run:  streamlit run streamlit_app.py
"""
import importlib
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.patches import Polygon as MplPolygon
import streamlit.components.v1 as components

import map_data
import map_view
import movement
import pathfinding

importlib.reload(map_data)
importlib.reload(map_view)
importlib.reload(movement)
importlib.reload(pathfinding)

from map_view import draw_floor
from movement import Navigator
from pathfinding import get_all_rooms, find_route, get_current_instruction

MAX_LINES = 10

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
        st.session_state.nav = Navigator()
        st.session_state.message = ""
        st.session_state.target_room = None
        st.session_state.selected_room_label = None
        st.session_state.search_ver = st.session_state.get("search_ver", 0) + 1


def draw(nav, near, route_line=None):
    data = nav.floors[nav.floor]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    patches = draw_floor(ax, nav.floor, data["rooms"], data["walkable"])
    for room, _ in near:
        patches[room["room_id"]].set_edgecolor("#d00000")
        patches[room["room_id"]].set_linewidth(2.2)

    # Gambar rute AI LineString jika ada tujuan aktif
    if route_line and len(route_line.coords) > 1:
        rx, ry = route_line.xy
        ax.plot(rx, ry, color="#0077b6", linewidth=4.0, zorder=6, linestyle="-", label="Rute")
        gx, gy = route_line.coords[-1]
        ax.plot([gx], [gy], "s", color="#ffb703", markersize=10, markeredgecolor="#000", zorder=7)

    ax.add_patch(MplPolygon(list(nav.buffer().exterior.coords), closed=True, facecolor="#1565c0",
                            alpha=0.15, edgecolor="#1565c0", linewidth=1.5, zorder=3))
    ax.plot([nav.x], [nav.y], "o", color="#d00000", markersize=11, markeredgecolor="white", zorder=8)
    ax.set_title(f"Lt. {nav.floor}   posisi: ({nav.x:g}, {nav.y:g}) m", fontsize=10)
    plt.tight_layout()
    return fig


st.set_page_config(page_title="UC Main Building - navigation", layout="wide")
nav = get_nav()
near = nav.nearby()

st.title("Campus Indoor Navigation")
# st.iframe(KEYS_JS, height=1)

components.html(KEYS_JS, height=1)

# 1 Input Gabungan: Ketik langsung untuk mencari atau pilih dari daftar ruangan
all_rooms = get_all_rooms()
room_dict = {f"{r['room_id']} - {r['name']} (Lt. {r['floor']})": r for r in all_rooms}
room_options = ["-- Cari / Pilih Ruangan Tujuan (Semua Lantai) --"] + sorted(room_dict.keys())

search_ver = st.session_state.get("search_ver", 0)

col_search, col_clear = st.columns([4, 1])
with col_search:
    curr_label = st.session_state.get("selected_room_label")
    selected_idx = room_options.index(curr_label) if curr_label in room_options else 0
    selected_label = st.selectbox(
        "Cari Ruangan Tujuan (Semua Lantai):",
        options=room_options,
        index=selected_idx,
        key=f"search_room_select_{search_ver}"
    )
    if selected_label in room_dict:
        st.session_state.target_room = room_dict[selected_label]
        st.session_state.selected_room_label = selected_label
    else:
        st.session_state.target_room = None
        st.session_state.selected_room_label = None

with col_clear:
    st.write("")
    st.write("")
    if st.button("Hapus Rute", use_container_width=True):
        st.session_state.target_room = None
        st.session_state.selected_room_label = None
        st.session_state.search_ver = search_ver + 1
        st.rerun()

# Hitung rute navigasi dan 1 arahan langkah aktif saat ini
route_line, current_instruction = None, ""
if st.session_state.target_room:
    route_line, _, _ = find_route(nav.floor, (nav.x, nav.y), st.session_state.target_room)
    current_instruction = get_current_instruction(nav.floor, (nav.x, nav.y), st.session_state.target_room)

# Layout 2 Kolom (Denah di kiri, Kontrol & Info di kanan)
col_map, col_info = st.columns([2.3, 1])

with col_map:
    st.subheader(f"Denah Lantai {nav.floor}")
    if current_instruction:
        st.info(f"**{current_instruction}**")
    st.pyplot(draw(nav, near, route_line))
    plt.close("all")
    st.caption("Keyboard: W A S D / panah untuk jalan, E naik lantai, Q turun lantai.")

with col_info:
    here = nav.here()
    st.write(f"**You are in:** {here['name'] + ' (' + here['type'] + ')' if here else 'corridor / lobby'}")
    if nav.link_hint():
        st.info(nav.link_hint())
    if st.session_state.message:
        st.warning(st.session_state.message)

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

    st.markdown("---")
    st.markdown("**Informasi & Aturan Lift**")
    st.markdown("- **Lift Barat:** Hanya melayani lantai 1, 2, 3, 5, 7")
    st.markdown("- **Lift Timur:** Hanya melayani lantai 1, 2, 4, 6, 7")
            
    st.markdown("**Tanda pada Peta**")
    st.markdown("- **Titik Merah (di dalam):** Posisi Anda saat ini")
    st.markdown("- **Lingkaran Biru (Transparan):** Radius *buffer* / jangkauan deteksi ruangan di sekitar Anda")
    st.markdown("- **Garis Biru & Kotak Kuning:** Jalur rute navigasi menuju titik tujuan aktif")
    st.markdown("- **Ruangan Bergaris Tepi Merah:** Ruangan yang berada di dalam jangkauan radius *buffer* Anda saat ini")
    st.markdown("---")

    st.write(f"**Buffer radius: {nav.radius} m**")
    minus, plus, reset = st.columns(3)
    minus.button("Kurangi (-)", on_click=press, args=("radius", -1), use_container_width=True)
    plus.button("Tambah (+)", on_click=press, args=("radius", +1), use_container_width=True)
    reset.button("Restart", on_click=press, args=("reset",), use_container_width=True)

    st.write(f"**Rooms in buffer ({len(near)}):**")
    st.text("\n".join(
        f"{'inside' if dist == 0 else f'{dist:.1f} m':>7}  {room['room_id']}  {room['name']}"
        for room, dist in near[:MAX_LINES]) + (f"\n... and {len(near) - MAX_LINES} more" if len(near) > MAX_LINES else ""))

    passed = [room["room_id"] for room in nav.visited()]
    st.write(f"**Trail passed ({len(passed)}):** " + ", ".join(passed))
