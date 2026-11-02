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

# untuk reload kalo ada perubahan di file lain bisa langsung kebaca
importlib.reload(map_data)
importlib.reload(map_view)
importlib.reload(movement)
importlib.reload(pathfinding)

# ambil function dari file lain biar bsa langsung dipake 
from map_view import draw_floor
from movement import Navigator
from pathfinding import get_all_rooms, find_route, get_current_instruction

# ini untuk max brp ruangan yg ditampilkan di daftar rooms dalam buffer 
MAX_LINES = 10

# js untuk gerakin titik user pake keyboard
KEYS_JS = """
<script>
# biar js bisa akses html di streamlit 
const doc = window.parent.document;

# periksa keyboard listenernya udh kepasang apa blm 
if (!window.parent.__ucKeys) {
  window.parent.__ucKeys = true;
  
# dictionary untuk mapping tombol keyboard ke tombol di streamlit
  const keys = {w: "W", a: "A", s: "S", d: "D", e: "E", q: "Q",
                ArrowUp: "W", ArrowLeft: "A", ArrowDown: "S", ArrowRight: "D"};
                
# untuk deteksi pas user tekan tombol keyboard 
  doc.addEventListener("keydown", (event) => {

#   ini biar kalo user tekan ctrl / alt / cmd ga ke trigger 
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    
#  ini biar kalo user lagi fokus di input / textarea / select ga ke trigger bergerak titiknya
    if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) return;
    const label = keys[event.key] || keys[event.key.toLowerCase()];
    if (!label) return;
    for (const button of doc.querySelectorAll("button")) {
      const text = button.innerText.trim();
      if (text === label || (label === "E" || label === "Q") && text.startsWith(label + " ")) {
        event.preventDefault();

# ini untuk trigger klik tombol yg sesuai sama tombol keyboard yg ditekan
        button.click();
        return;
      }
    }
  });
}
</script>
"""

# panggil navigator dari file movement biar bsa siapin data lantai dan posisi user
def get_nav():
    """One Navigator per browser session."""
    # cek nav sudah pernah dijalankan dan pernah tersimpan atau tidak 
    if "nav" not in st.session_state:
        # kalo belum dia panggik dan simpan di session state 
        st.session_state.nav = Navigator()
        st.session_state.message = ""
    return st.session_state.nav

# button" di kanan untuk gerakin titik user, naik turun lantai, ubah radius buffer, reset navigator
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

# untuk bikin denah lantai, kasih warna sesuai tipe ruangan, kasih label nama ruangan, dan bikin grid
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

# untuk bikin halaman streamlit, layout 2 kolom (denah di kiri, kontrol & info di kanan), tombol untuk gerakin titik user, naik turun lantai, ubah radius buffer, reset navigator
st.set_page_config(page_title="UC Main Building - navigation", layout="wide")
nav = get_nav()
near = nav.nearby()

st.title("Campus Indoor Navigation")
# st.iframe(KEYS_JS, height=1)

# untuk bikin tombol keyboard di browser biar bisa gerakin titik user pake keyboard, tapi kalo pake st.iframe ga bisa jalan, jadi diganti pake st.components.html
components.html(KEYS_JS, height=1)

# ambil semua data lalu tampilkan di box select 
# 1 Input Gabungan: Ketik langsung untuk mencari atau pilih dari daftar ruangan
all_rooms = get_all_rooms()
room_dict = {f"{r['room_id']} - {r['name']} (Lt. {r['floor']})": r for r in all_rooms}
room_options = ["-- Cari / Pilih Ruangan Tujuan (Semua Lantai) --"] + sorted(room_dict.keys())

# buat versi search_ver biar kalo user klik tombol hapus rute, selectbox bisa reset ke default
# st session search state untuk simpan data sementara dari search user 
# .get untuk ambil data searchnya, kalo misal blm ada brrti set 0 
search_ver = st.session_state.get("search_ver", 0)

# buat 2 kolom, kiri untuk input cari ruangan, kanan untuk tombol hapus rute
# kolom untuk search dan kolom untuk hapus 
col_search, col_clear = st.columns([4, 1])
# data di bawah itu jalan untuk kolom searchnya 
with col_search:
    # ambil label ruangan yagn dipiliih user 
    curr_label = st.session_state.get("selected_room_label")
    # kalo misal label ruangan yg dipilih ada di daftar dia langsung ambil indexnya 
    selected_idx = room_options.index(curr_label) if curr_label in room_options else 0
    # yang ditampilkan di selectboxnya 
    selected_label = st.selectbox(
        "Cari Ruangan Tujuan (Semua Lantai):",
        options=room_options,
        index=selected_idx,
        # dia buat key sesuai dengan nilai search ver yang dimasukan user 
        key=f"search_room_select_{search_ver}"
    )
    # untuk periksa label yang dipilih user ini valid ada atau tidak, kalo ada dia simpan data di session state, kalo ga ada dia set ke None
    if selected_label in room_dict:
        # kalo valid dia ambil data dari room_dictnya dan simpan di target room
        st.session_state.target_room = room_dict[selected_label]
        # simpan label yang dipilih biar bs ditampilin di search pas 
        st.session_state.selected_room_label = selected_label
    # kalo misal ga valid dia set kosong
    else:
        st.session_state.target_room = None
        st.session_state.selected_room_label = None

# ini kode di bawah untuk button hapus 
with col_clear:
    # hanya untuk tambah ruang kosong bair sejajar kolomnya 
    st.write("")
    st.write("")
    # width untuk ukuran button, lalu jika ditekan maka dia lanjut
    if st.button("Hapus Rute", use_container_width=True):
        # hapus tujuan ruangan yang sblmnya tersimpan di st session state 
        st.session_state.target_room = None
        # hapus label ruangannya jg 
        st.session_state.selected_room_label = None
        # buat search ver baru biar program tau kalo user udh klik hapus rute dan reset selectbox ke default
        st.session_state.search_ver = search_ver + 1
        # jalan ulang aplikasi 
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
    # args ini untuk kirim 
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
