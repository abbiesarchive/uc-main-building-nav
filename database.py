"""SQLite access for room data stored in campus.db."""
import math
import sqlite3
from contextlib import closing

from floors import ROOT

DB_PATH = ROOT / "campus.db"
ROOM_COLUMNS = ("floor", "room_id", "name", "type", "xmin", "ymin", "xmax", "ymax")


def revision():
    """Return a lightweight cache key that changes when SQLite is updated."""
    try:
        stat = DB_PATH.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size


def connect():
    """Open the initialized database or raise an actionable setup error."""
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Database tidak ditemukan: {DB_PATH}. Jalankan `python load_db.py` terlebih dahulu."
        )
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def fetch_rooms(floor, shared_rooms=None):
    """Return rooms stored for a floor, plus explicitly shared room IDs."""
    shared_rooms = shared_rooms or {}
    clauses = ["floor = ?"]
    params = [str(floor)]
    for shared_floor, room_ids in shared_rooms.items():
        room_ids = tuple(room_ids)
        if room_ids:
            clauses.append(
                f"(floor = ? AND room_id IN ({','.join('?' for _ in room_ids)}))"
            )
            params.extend((str(shared_floor), *room_ids))
    query = (
        "SELECT floor, room_id, name, type, xmin, ymin, xmax, ymax "
        "FROM rooms WHERE " + " OR ".join(clauses) + " ORDER BY room_id"
    )
    try:
        with closing(connect()) as db:
            return [dict(row) for row in db.execute(query, params)]
    except sqlite3.OperationalError as exc:
        raise RuntimeError(
            "Tabel rooms belum tersedia di campus.db. Jalankan `python load_db.py` untuk "
            "membuat atau memperbarui database."
        ) from exc


def replace_floor_rooms(floor, rows):
    """Validate and atomically replace all database rooms owned by one floor."""
    normalized = []
    seen_ids = set()
    for index, row in enumerate(rows, start=1):
        record = {column: row.get(column) for column in ROOM_COLUMNS}
        record["floor"] = str(record["floor"] or "").strip()
        for column in ("room_id", "name", "type"):
            record[column] = str(record[column] or "").strip()
        if record["floor"] != str(floor):
            raise ValueError(f"Baris {index}: nilai lantai harus {floor}.")
        if not record["room_id"] or not record["name"] or not record["type"]:
            raise ValueError(f"Baris {index}: ID, nama, dan tipe ruangan wajib diisi.")
        if record["room_id"] in seen_ids:
            raise ValueError(f"ID ruangan duplikat: {record['room_id']}.")
        seen_ids.add(record["room_id"])

        for column in ("xmin", "ymin", "xmax", "ymax"):
            try:
                record[column] = float(record[column])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Baris {index}: koordinat {column} harus berupa angka.") from exc
            if not math.isfinite(record[column]):
                raise ValueError(f"Baris {index}: koordinat {column} harus berupa angka finite.")
        if record["xmin"] >= record["xmax"] or record["ymin"] >= record["ymax"]:
            raise ValueError(f"Baris {index}: koordinat minimum harus lebih kecil dari maksimum.")
        normalized.append(tuple(record[column] for column in ROOM_COLUMNS))

    insert_sql = (
        "INSERT INTO rooms (floor, room_id, name, type, xmin, ymin, xmax, ymax) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with closing(connect()) as db:
        try:
            db.execute("BEGIN")
            db.execute("DELETE FROM rooms WHERE floor = ?", (str(floor),))
            db.executemany(insert_sql, normalized)
            db.commit()
        except sqlite3.Error:
            db.rollback()
            raise
