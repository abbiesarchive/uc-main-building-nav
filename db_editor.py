"""Web App Sederhana untuk Mengedit Database Denah (CSV / campus.db).
Jalankan di terminal:
    streamlit run db_editor.py --server.port 8502
"""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from map_view import draw_floor
from movement import Navigator

# Setup folder CSV
CSV_DIR = Path(__file__).parent / "csv"

st.set_page_config(page_title="Admin Database Denah UC", layout="wide")

st.title("Database Denah UC")
st.caption("Pilih file lantai lalu ubah data ruangan di tabel")

# 1. Ambil daftar file CSV yang ada di folder csv/
csv_files = sorted(CSV_DIR.glob("lantai*.csv"))
if not csv_files:
    st.error("Tidak ditemukan file CSV di folder csv/")
    st.stop()

# 2. Pilihan dropdown lantai
file_options = {f.name: f for f in csv_files}
selected_filename = st.selectbox("Lantai :", list(file_options.keys()))
selected_path = file_options[selected_filename]

# 3. Baca file CSV
df = pd.read_csv(selected_path, dtype={"floor": str, "room_id": str})

st.subheader(f"Data Ruangan: `{selected_filename}` ({len(df)} baris)")

# 3. Tentukan identifier lantai
floor_key = selected_filename.replace("lantai", "").replace(".csv", "")

if floor_key.lower() == "2a":
    floor_key = "2A"
    
# 3. Visualisasi Denah (Menggunakan Navigator yang sama dengan aplikasi user)
try:
    nav = Navigator()

    # Ambil data lantai dari Navigator
    data = nav.floors[floor_key]

    rooms = data["rooms"]
    walkable = data["walkable"]

    # Gambar denah menggunakan fungsi yang sama
    fig, ax = plt.subplots(figsize=(14, 4.6))

    draw_floor(ax, floor_key, rooms, walkable)

    ax.set_title(f"Lt. {floor_key}", fontsize=10)

    st.pyplot(fig)
    plt.close(fig)

except Exception as e:
    st.warning(
        f"Tidak dapat memuat visualisasi denah "
        f"untuk lantai {floor_key}: {e}"
    )
    
# 4. Tabel Interaktif (bisa edit, tambah baris di bagian bawah, atau centang lalu hapus)
edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",  # Mengizinkan tambah / hapus baris langsung
    column_config={
        "floor": st.column_config.TextColumn("Lantai"),
        "room_id": st.column_config.TextColumn("ID Ruangan (Unik)"),
        "name": st.column_config.TextColumn("Nama Ruangan"),
        "type": st.column_config.SelectboxColumn(
            "Tipe",
            options=["Classroom", "MeetingRoom", "Theater", "Office", "Toilet", "Stairs", "Lab", "Storage", "Clinic", "Library", "Lounge", "Pantry", "Lift", "LecturerRoom", "ServerRoom"]
        ),
        "xmin": st.column_config.NumberColumn("X Min (m)", format="%.2f"),
        "ymin": st.column_config.NumberColumn("Y Min (m)", format="%.2f"),
        "xmax": st.column_config.NumberColumn("X Max (m)", format="%.2f"),
        "ymax": st.column_config.NumberColumn("Y Max (m)", format="%.2f"),
    }
)

col1, col2 = st.columns([1, 4])

with col1:
    # 5. Tombol Simpan
    if st.button("Save", type="secondary", use_container_width=True):
        # Validasi sederhana: pastikan tidak ada room_id kosong
        if edited_df["room_id"].isna().any() or (edited_df["room_id"] == "").any():
            st.error("Gagal simpan: Ada baris dengan ID Ruangan yang kosong!")
        else:
            # Simpan kembali ke file CSV
            edited_df.to_csv(selected_path, index=False)
            st.success(f"Berhasil disimpan ke `{selected_filename}`!")

with col2:
    st.info("Jangan lupa untuk menekan tombol 'Save' setelah mengedit data. Perubahan tidak akan tersimpan otomatis.")
