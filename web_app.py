"""Campus Indoor Navigation - Web Version
Built with Streamlit and Folium, faithfully matching the desktop navigation logic:
- 100% direct physical keyboard control (WASD, Arrow Keys, E, Q, R, +/-)
- Clean indoor floor plan with permanent room name labels
- No trail line history
- Exact GIS information display (Point, Buffer, Spatial Join)
"""
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

import importlib
from floors import load_all
import movement
importlib.reload(movement)
from movement import Navigator, STEP
import map_folium
importlib.reload(map_folium)
from map_folium import create_floor_map

DIRECTIONS = {
    "w": (0, 1),
    "s": (0, -1),
    "a": (-1, 0),
    "d": (1, 0),
}

# 1. Page Configuration & Dark Theme Styling
st.set_page_config(
    page_title="Campus Indoor Navigation",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Dark Theme & Typography */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    h1, h2, h3, h4, p, span, label {
        color: #ffffff !important;
    }
    .footnote-text {
        color: #8b949e !important;
        font-size: 12px;
        margin-top: 6px;
    }
    /* Info Box matching the classic desktop app */
    .terminal-box {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 13px;
        line-height: 1.5;
        color: #c9d1d9;
        margin-top: 14px;
        white-space: pre-wrap;
    }
    /* Completely hide navigation trigger buttons from UI */
    .st-key-key_w, .st-key-key_s, .st-key-key_a, .st-key-key_d,
    .st-key-key_e, .st-key-key_q, .st-key-key_plus, .st-key-key_minus, .st-key-key_r {
        display: none !important;
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        width: 0 !important;
        height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)


# 2. State Initialization with movement.Navigator
all_floors = list(load_all().keys())
default_floor = "7" if "7" in all_floors else all_floors[0]

if "nav" not in st.session_state:
    st.session_state.nav = Navigator(floor=default_floor)

if "message" not in st.session_state:
    st.session_state.message = ""

nav = st.session_state.nav


# 3. Top Bar (Header, Search Room, Select Floor)
st.title("Campus Indoor Navigation")

top_col_search, top_col_floor = st.columns([3, 1])

with top_col_search:
    search_query = st.text_input("Cari ruangan", placeholder="Contoh: Ruang Dosen")

with top_col_floor:
    current_floor_idx = all_floors.index(nav.floor) if nav.floor in all_floors else 0
    selected_floor = st.selectbox("Pilih lantai", all_floors, index=current_floor_idx)

# If user switched floor dropdown
if selected_floor != nav.floor:
    nav.floor = selected_floor
    nav.start = (selected_floor, *nav.settings[selected_floor].START)
    nav.reset()
    st.session_state.message = f"Berpindah ke Lantai {selected_floor}."
    st.rerun()


# 4. Search Filter Processing
search_matches = []
if search_query.strip():
    q = search_query.strip().lower()
    for room in nav.rooms:
        if q in room["name"].lower() or q in room["room_id"].lower() or q in room["type"].lower():
            search_matches.append(room)

highlighted_ids = [r["room_id"] for r in search_matches]


# 5. Main Body Layout (Left: Map, Right: Search & GIS Info)
left_col, right_col = st.columns([7, 4])


with left_col:
    st.subheader(f"Denah Lantai {nav.floor}")

    # Gather data from Navigator for GIS visualization
    near = nav.nearby()
    near_ids = [room["room_id"] for room, _ in near]

    # Create Folium Map with clean indoor canvas & permanent labels
    folium_map = create_floor_map(
        floor=nav.floor,
        rooms=nav.rooms,
        user_pos=(nav.x, nav.y),
        buffer_geom=nav.buffer(),
        highlighted_ids=highlighted_ids,
        near_ids=near_ids
    )

    # Render Folium (returned_objects=[] ensures clicking on the map is ignored for walking)
    st_folium(
        folium_map,
        width=850,
        height=540,
        key=f"floor_map_{nav.floor}_{nav.x}_{nav.y}_{nav.radius}",
        returned_objects=[]
    )

    st.markdown(
        '<p class="footnote-text">Peta menampilkan ruangan berdasarkan koordinat lokal CSV. Fitur pencarian belum menghitung rute.</p>',
        unsafe_allow_html=True
    )


with right_col:
    st.subheader("Hasil pencarian")
    st.write(f"Jumlah ruangan: {len(nav.rooms)}")

    if not search_query.strip():
        st.write("Ketik nama ruangan untuk mencari.")
    else:
        if search_matches:
            st.markdown(f"Ditemukan **{len(search_matches)}** ruangan:")
            for m_room in search_matches[:5]:
                st.markdown(f"- **{m_room['name']}** (`{m_room['room_id']}`) — *{m_room['type']}*")
        else:
            st.warning("Tidak ditemukan ruangan yang cocok.")

    # Complete GIS Navigation Info Box (faithfully matching app.py write_info)
    here = nav.here()
    passed = [room["room_id"] for room in nav.visited()]

    info_lines = []
    info_lines.append(f"Lt. {nav.floor}   position ({nav.x:g}, {nav.y:g}) m   buffer radius {nav.radius} m")
    info_lines.append(f"You are in: {here['name'] + ' (' + here['type'] + ')' if here else 'corridor / lobby'}")

    hint = nav.link_hint()
    if hint:
        info_lines.append(hint)

    info_lines.append("")
    info_lines.append(f"Rooms in the buffer ({len(near)}):")
    for room, dist in near[:10]:
        where = "inside" if dist == 0 else f"{dist:.1f} m"
        info_lines.append(f"  {where:>7}  {room['room_id']}  {room['name']}")
    if len(near) > 10:
        info_lines.append(f"  ... and {len(near) - 10} more")

    info_lines.append("")
    info_lines.append(f"Rooms your trail passed ({len(passed)}): " + (", ".join(passed) if passed else "-"))

    if st.session_state.message:
        info_lines.append("")
        info_lines.append(f">> {st.session_state.message}")

    info_lines.append("")
    info_lines.append("HELP: WASD / arrows walk   E up   Q down   + / - buffer   R restart")

    st.markdown(f'<div class="terminal-box">{"\n".join(info_lines)}</div>', unsafe_allow_html=True)


# 7. Global Keyboard Event Listener
# Directly captures physical keyboard keystrokes across document and all iframes
components.html("""
<script>
(function() {
    const pDoc = window.parent.document;
    const pWin = window.parent;

    function triggerAction(actionKey) {
        const btn = pDoc.querySelector('.st-key-key_' + actionKey + ' button');
        if (btn) {
            btn.click();
            return true;
        }
        return false;
    }


    function handleGlobalKeyDown(e) {
        // Do not intercept if user is typing in search input or any text field
        const targetTag = (e.target && e.target.tagName) ? e.target.tagName.toUpperCase() : "";
        if (targetTag === "INPUT" || targetTag === "TEXTAREA" || (e.target && e.target.isContentEditable)) {
            return;
        }

        const key = e.key.toLowerCase();
        let action = null;

        if (key === "w" || key === "arrowup") action = "w";
        else if (key === "s" || key === "arrowdown") action = "s";
        else if (key === "a" || key === "arrowleft") action = "a";
        else if (key === "d" || key === "arrowright") action = "d";
        else if (key === "e") action = "e";
        else if (key === "q") action = "q";
        else if (key === "r") action = "r";
        else if (key === "+" || key === "=") action = "plus";
        else if (key === "-") action = "minus";

        if (action) {
            e.preventDefault();
            e.stopPropagation();
            triggerAction(action);
        }
    }

    // Attach to parent document & window (capture phase ensures it is processed first)
    if (pWin._activeNavKeyDown) {
        pDoc.removeEventListener("keydown", pWin._activeNavKeyDown, true);
        pWin.removeEventListener("keydown", pWin._activeNavKeyDown, true);
    }
    pWin._activeNavKeyDown = handleGlobalKeyDown;
    pDoc.addEventListener("keydown", handleGlobalKeyDown, true);
    pWin.addEventListener("keydown", handleGlobalKeyDown, true);

    // Also attach to all iframes (such as Leaflet map) so clicking the map does not lose key focus
    function attachToIframes() {
        pDoc.querySelectorAll("iframe").forEach(function(frame) {
            try {
                if (frame.contentDocument) {
                    frame.contentDocument.removeEventListener("keydown", handleGlobalKeyDown, true);
                    frame.contentDocument.addEventListener("keydown", handleGlobalKeyDown, true);
                }
            } catch (err) {}
        });
    }

    attachToIframes();
    setTimeout(attachToIframes, 500);
    setTimeout(attachToIframes, 1500);
})();
</script>
""", height=0)

# Hidden keyboard bridge triggers (placed cleanly at end of page)
with st.container():
    if st.button("w", key="key_w"):
        st.session_state.message = nav.move(0, 1)
        st.rerun()
    if st.button("s", key="key_s"):
        st.session_state.message = nav.move(0, -1)
        st.rerun()
    if st.button("a", key="key_a"):
        st.session_state.message = nav.move(-1, 0)
        st.rerun()
    if st.button("d", key="key_d"):
        st.session_state.message = nav.move(1, 0)
        st.rerun()
    if st.button("e", key="key_e"):
        st.session_state.message = nav.change_floor(up=True)
        st.rerun()
    if st.button("q", key="key_q"):
        st.session_state.message = nav.change_floor(up=False)
        st.rerun()
    if st.button("plus", key="key_plus"):
        nav.set_radius(+1)
        st.rerun()
    if st.button("minus", key="key_minus"):
        nav.set_radius(-1)
        st.rerun()
    if st.button("r", key="key_r"):
        nav.reset()
        st.session_state.message = "Posisi direset ke awal."
        st.rerun()

