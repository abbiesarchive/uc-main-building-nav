"""Streamlit editor for room records stored in campus.db.

Run: streamlit run db_editor.py --server.port 8502
"""
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from database import fetch_rooms, replace_floor_rooms
from floors import load_all
from map_view import draw_floor
from movement import Navigator

ROOM_COLUMNS = ["floor", "room_id", "name", "type", "xmin", "ymin", "xmax", "ymax"]

st.set_page_config(page_title="Admin Database Denah UC", layout="wide")
st.title("Database Denah UC")
st.caption("Data ruangan dibaca dan disimpan langsung ke campus.db (SQLite).")

floors = load_all()
floor_options = sorted(floors, key=lambda floor: floors[floor].LEVEL)
floor_key = st.selectbox("Lantai:", floor_options)

try:
    rows = fetch_rooms(floor_key)
except (FileNotFoundError, RuntimeError) as exc:
    st.error(str(exc))
    st.code("python load_db.py")
    st.stop()

df = pd.DataFrame(rows, columns=ROOM_COLUMNS)
st.subheader(f"Data Ruangan: Lt. {floor_key} ({len(df)} baris)")

try:
    nav = Navigator(floor=floor_key)
    data = nav.floors[floor_key]
    fig, ax = plt.subplots(figsize=(14, 4.6))
    draw_floor(ax, floor_key, data["rooms"], data["walkable"])
    ax.set_title(f"Lt. {floor_key}", fontsize=10)
    st.pyplot(fig)
    plt.close(fig)
except (FileNotFoundError, RuntimeError, KeyError) as exc:
    st.error(f"Tidak dapat memuat visualisasi denah Lt. {floor_key}: {exc}")

edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "floor": st.column_config.TextColumn("Lantai", disabled=True),
        "room_id": st.column_config.TextColumn("ID Ruangan (Unik)"),
        "name": st.column_config.TextColumn("Nama Ruangan"),
        "type": st.column_config.SelectboxColumn(
            "Tipe",
            options=["Classroom", "MeetingRoom", "Theater", "Office", "Toilet", "Stairs",
                     "Lab", "Storage", "Clinic", "Library", "Lounge", "Pantry", "Lift",
                     "LecturerRoom", "ServerRoom"],
        ),
        "xmin": st.column_config.NumberColumn("X Min (m)", format="%.2f"),
        "ymin": st.column_config.NumberColumn("Y Min (m)", format="%.2f"),
        "xmax": st.column_config.NumberColumn("X Max (m)", format="%.2f"),
        "ymax": st.column_config.NumberColumn("Y Max (m)", format="%.2f"),
    },
)

if st.button("Simpan ke SQLite", type="primary"):
    try:
        records = edited_df.to_dict("records")
        for record in records:
            record["floor"] = floor_key
        replace_floor_rooms(floor_key, records)
    except (ValueError, sqlite3.Error, FileNotFoundError, RuntimeError) as exc:
        st.error(f"Gagal menyimpan perubahan: {exc}")
    else:
        st.success(f"Data Lt. {floor_key} berhasil disimpan ke campus.db.")
        st.rerun()

st.info("Perubahan disimpan ke SQLite setelah tombol **Simpan ke SQLite** ditekan.")
