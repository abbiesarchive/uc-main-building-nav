"""Walk through the building in the browser.
Run: streamlit run streamlit_app.py
"""
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import LineString, Point
import streamlit.components.v1 as components

from gis_ops import rooms_along_route, spatial_join
from database import revision
from map_view import draw_floor
from movement import Navigator
from pathfinding import get_all_rooms, find_route, get_current_instruction

MAX_LINES = 10
MAX_STEP = 5
TRAIL_WIDTH = 2.2  # Lebar 2.2m (radius 1.1m) agar langkah di grid 1m koridor menyentuh dinding ruangan

KEYS_JS = """
<script>
const doc = window.parent.document;
if (!window.parent._ucKeys) {
    window.parent._ucKeys = true;
    const keys = {
        w: "W", a: "A", s: "S", d: "D", e: "E", q: "Q",
        ArrowUp: "W", ArrowLeft: "A", ArrowDown: "S", ArrowRight: "D"
    };
    doc.addEventListener("keydown", (event) => {
        if (event.ctrlKey || event.metaKey || event.altKey) return;
        if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
        const label = keys[event.key] || keys[event.key.toLowerCase()];
        if (!label) return;
        for (const button of doc.querySelectorAll("button")) {
            const text = button.innerText.trim();
            if (text === label || ((label === "E" || label === "Q") && text.startsWith(label + " "))) {
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
    """One Navigator per browser session. Rebuilt (same position) when rooms in the database changed."""
    rev = revision()
    if "nav" not in st.session_state:
        st.session_state.nav = Navigator()
        st.session_state.message = ""
        st.session_state.nav_revision = rev
    elif st.session_state.get("nav_revision") != rev or not hasattr(st.session_state.nav, "step"):
        old = st.session_state.nav            # also catches a Navigator made by older code
        new = Navigator(floor=old.floor, radius=old.radius, step=getattr(old, "step", 1))
        new.x, new.y, new.trail = old.x, old.y, old.trail
        st.session_state.nav = new
        st.session_state.nav_revision = rev
    return st.session_state.nav


@st.cache_resource
def get_cached_all_rooms(db_revision):
    """Cache daftar seluruh ruangan; dibaca ulang hanya kalau database berubah."""
    return get_all_rooms()


def get_trail_rooms(nav):
    """Hitung ruangan yang dilewati trail dengan lancar (mendukung koridor 1 m)."""
    if len(nav.trail) < 2:
        here = nav.here()
        if here:
            return [here]
        # Jika berdiri di koridor tepat di depan ruangan (jarak <= 1.1 m)
        hits = spatial_join(nav.rooms, Point(nav.x, nav.y).buffer(TRAIL_WIDTH / 2))
        return sorted(hits, key=lambda r: r["polygon"].distance(Point(nav.x, nav.y)))
    return rooms_along_route(nav.rooms, LineString(nav.trail), width=TRAIL_WIDTH)


def get_floor_canvas(nav):
    """Simpan gambar dasar lantai (ruangan, teks, void) di memori."""
    rev = revision()
    if st.session_state.get("floor_canvas_rev") != rev:     # database changed: drop old drawings
        for old in st.session_state.get("floor_canvas_cache", {}).values():
            plt.close(old["fig"])
        st.session_state.floor_canvas_cache = {}
        st.session_state.floor_canvas_rev = rev
    cache = st.session_state.floor_canvas_cache
    floor = nav.floor

    if floor not in cache:
        data = nav.floors[floor]
        fig, ax = plt.subplots(figsize=(10, 5.2), dpi=85)
        patches = draw_floor(ax, floor, data["rooms"], data["walkable"])

        buffer_patch = MplPolygon(
            [(0, 0)],
            closed=True, facecolor="#1565c0", alpha=0.15,
            edgecolor="#1565c0", linewidth=1.5, zorder=3
        )
        ax.add_patch(buffer_patch)

        # LineString untuk jejak langkah (Trail) dan rute navigasi A*
        (route_plot,) = ax.plot([], [], color="#0077b6", linewidth=4.0, zorder=6, linestyle="-", label="Rute")
        (goal_plot,) = ax.plot([], [], "s", color="#ffb703", markersize=10, markeredgecolor="#000", zorder=7)
        (dot_plot,) = ax.plot([], [], "o", color="#d00000", markersize=11, markeredgecolor="white", zorder=8)

        plt.tight_layout()
        cache[floor] = {
            "fig": fig,
            "ax": ax,
            "patches": patches,
            "buffer_patch": buffer_patch,
            "route_plot": route_plot,
            "goal_plot": goal_plot,
            "dot_plot": dot_plot,
            "highlighted": []
        }
    return cache[floor]


def draw_fast(nav, near, route_line=None):
    """Hanya menggeser titik koordinat, garis trail, dan rute tanpa menggambar ulang ruangan."""
    canvas = get_floor_canvas(nav)
    patches = canvas["patches"]

    for room_id in canvas["highlighted"]:
        if room_id in patches:
            patches[room_id].set_edgecolor("#555555")
            patches[room_id].set_linewidth(0.8)

    new_highlighted = [room["room_id"] for room, _ in near]
    for room_id in new_highlighted:
        if room_id in patches:
            patches[room_id].set_edgecolor("#d00000")
            patches[room_id].set_linewidth(2.2)
    canvas["highlighted"] = new_highlighted

    # Update garis rute A*
    if route_line and len(route_line.coords) > 1:
        rx, ry = route_line.xy
        canvas["route_plot"].set_data(rx, ry)
        gx, gy = route_line.coords[-1]
        canvas["goal_plot"].set_data([gx], [gy])
    else:
        canvas["route_plot"].set_data([], [])
        canvas["goal_plot"].set_data([], [])

    # Update posisi buffer dan titik merah user
    canvas["buffer_patch"].set_xy(list(nav.buffer().exterior.coords))
    canvas["dot_plot"].set_data([nav.x], [nav.y])
    canvas["ax"].set_title(f"Lt. {nav.floor} — posisi: ({nav.x:g}, {nav.y:g}) m", fontsize=10)

    return canvas["fig"]


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
        clear_target()


st.set_page_config(page_title="UC Main Building navigation", layout="wide")
st.markdown(
    """
    <style>
    .block-container {padding-top: 4rem; padding-bottom: 1rem; max-width: 1500px;}
    h1 {font-size: 1.5rem !important; line-height: 1.4 !important; padding: 0 0 .25rem 0 !important;}
    div[data-testid="stVerticalBlock"] {gap: .6rem;}
    div[data-testid="stButton"] button {padding: .2rem .5rem; min-height: 2.2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Campus Indoor Navigation")
components.html(KEYS_JS, height=1)


def clear_target():
    st.session_state.target_room = None
    st.session_state.selected_room_label = None
    st.session_state.search_ver = st.session_state.get("search_ver", 0) + 1


@st.fragment
def navigation_view():
    nav = get_nav()

    here_top = nav.here()
    here_label = f"{here_top['name']} (Lt. {nav.floor})" if here_top else f"Corridor / Lobby (Lt. {nav.floor})"

    all_rooms = get_cached_all_rooms(revision())
    room_dict = {f"{r['room_id']} - {r['name']} (Lt. {r['floor']})": r for r in all_rooms}
    room_options = ["-- Search lokasi tujuan --"] + sorted(room_dict.keys())
    search_ver = st.session_state.get("search_ver", 0)

    # ---- top bar: search + clear ----
    col_search, col_btn = st.columns([5, 1], vertical_alignment="bottom")
    with col_search:
        curr_label = st.session_state.get("selected_room_label")
        selected_idx = room_options.index(curr_label) if curr_label in room_options else 0
        selected_label = st.selectbox(
            "Tujuan", options=room_options, index=selected_idx,
            key=f"search_room_select_{search_ver}", label_visibility="collapsed",
        )
        if selected_label in room_dict:
            st.session_state.target_room = room_dict[selected_label]
            st.session_state.selected_room_label = selected_label
        else:
            st.session_state.target_room = None
            st.session_state.selected_room_label = None
    with col_btn:
        if st.button("Hapus Rute", use_container_width=True):
            clear_target()
            st.rerun()

    target = st.session_state.target_room
    here_now = nav.here()
    arrived = bool(target and here_now and here_now["room_id"] == target["room_id"])

    if target and not arrived:
        target_summary = f"{target['name']} (Lt. {target['floor']})"
        col_route, col_tp = st.columns([5, 1], vertical_alignment="center")
        col_route.markdown(f"**{here_label} → {target_summary}**")
        if col_tp.button("Teleport", use_container_width=True):
            st.session_state.message = nav.teleport_to_room(target)
            st.rerun()
    else:
        st.markdown(f"**Posisi:** {here_label}")

    near = nav.nearby()
    route_line, current_instruction = None, ""
    if target:
        route_line, _, _ = find_route(nav.floor, (nav.x, nav.y), target)
        current_instruction = get_current_instruction(nav.floor, (nav.x, nav.y), target)

    col_map, col_info = st.columns([2.6, 1])

    with col_map:
        if current_instruction:
            st.info(f"**{current_instruction}**")
        st.pyplot(draw_fast(nav, near, route_line), clear_figure=False)
        st.caption("Keyboard: WASD / panah = jalan · E = naik lantai · Q = turun lantai")

    with col_info:
        if nav.link_hint():
            st.info(nav.link_hint())
        if st.session_state.message:
            st.warning(st.session_state.message)

        with st.container(border=True):
            # Fixed key and no value= : the widget owns its value. (value=nav.step changed on every
            # rerun, so Streamlit saw a "new" widget and reset it while you spammed +/-.)
            st.session_state.setdefault("step_input", min(nav.step, MAX_STEP))
            step_val = st.number_input("Langkah per klik (m)", min_value=1, max_value=MAX_STEP, step=1, key="step_input")
            nav.set_step(step_val)

            _, up, _ = st.columns(3)
            left, down, right = st.columns(3)
            up.button("W", on_click=press, args=("move", 0, 1), use_container_width=True)
            left.button("A", on_click=press, args=("move", -1, 0), use_container_width=True)
            down.button("S", on_click=press, args=("move", 0, -1), use_container_width=True)
            right.button("D", on_click=press, args=("move", 1, 0), use_container_width=True)

            e, q = st.columns(2)
            e.button("E up", on_click=press, args=("floor", True), use_container_width=True)
            q.button("Q down", on_click=press, args=("floor", False), use_container_width=True)

        with st.container(border=True):
            st.markdown(f"**Radius buffer: {nav.radius} m**")
            minus, plus, reset = st.columns(3)
            minus.button("−", on_click=press, args=("radius", -1), use_container_width=True)
            plus.button("+", on_click=press, args=("radius", +1), use_container_width=True)
            reset.button("Restart", on_click=press, args=("reset",), use_container_width=True)

            st.markdown(f"**Ruangan di sekitar ({len(near)})**")
            if near:
                st.code("\n".join(
                    f"{'inside' if dist == 0 else f'{dist:.1f} m':>7}  {room['room_id']}  {room['name']}"
                    for room, dist in near[:MAX_LINES]
                ) + (f"\n... dan {len(near) - MAX_LINES} lainnya" if len(near) > MAX_LINES else ""),
                    language=None)
            else:
                st.caption("Tidak ada.")

            passed = [room["room_id"] for room in get_trail_rooms(nav)]
            st.markdown(f"**Trail ({len(passed)}):** " + (", ".join(passed) if passed else "-"))

        with st.expander("Legenda & info lift"):
            st.markdown(
                "- **Lift Barat:** lantai 1, 2, 3, 5, 7\n"
                "- **Lift Timur:** lantai 1, 2, 4, 6, 7\n\n"
                "- Titik merah: posisi Anda\n"
                ""
                "- Lingkaran biru: radius buffer\n"
                "- Garis biru & kotak kuning: rute ke tujuan\n"
                "- Ruangan bertepi merah: dalam radius buffer"
            )


navigation_view()
