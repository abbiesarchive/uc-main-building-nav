"""Folium mapping module for UC Main Building indoor navigation.
Renders clean indoor floor plan (matching campus navigation style) with:
- Plain clean canvas background (no distracting street map tiles)
- Stylized room polygons with sharp borders and hover tooltips
- Permanent room labels (room_id & room_name) centered in each room box
- Red user location marker (matching original app)
- Interactive buffer polygon around user
- NO history trail line (clean map view)
"""
import folium
from folium import plugins
from shapely.geometry import Point

from map_data import building, voids, LINK_TYPES

# Coordinates anchor: Universitas Ciputra Main Building, Surabaya
REF_LAT = -7.285800
REF_LON = 112.631300
METERS_PER_DEG_LAT = 111139.0
METERS_PER_DEG_LON = 110245.0  # ~ 111139 * cos(-7.2858 deg)

# Primary color palette matching the sleek campus indoor theme
COLOR_ROOM_FILL = "#8294ea"      # Periwinkle blue
COLOR_ROOM_BORDER = "#1e3a8a"    # Deep blue
COLOR_ROOM_HIGHLIGHT = "#f59e0b" # Golden amber for searched/highlighted rooms
COLOR_ROOM_NEARBY = "#93c5fd"    # Light blue accent for rooms inside buffer
COLOR_LINK_ROOM = "#fed7aa"      # Orange accent for Stairs and Lifts


def xy_to_latlon(x, y):
    """Convert local Cartesian meters (x: east, y: north) to (lat, lon)."""
    lat = REF_LAT + (y / METERS_PER_DEG_LAT)
    lon = REF_LON + (x / METERS_PER_DEG_LON)
    return lat, lon


def latlon_to_xy(lat, lon):
    """Convert (lat, lon) back to local Cartesian meters (x, y)."""
    y = (lat - REF_LAT) * METERS_PER_DEG_LAT
    x = (lon - REF_LON) * METERS_PER_DEG_LON
    return round(x, 2), round(y, 2)


def create_floor_map(floor, rooms, user_pos=None, buffer_geom=None,
                     highlighted_ids=None, near_ids=None):
    """Build a clean indoor Folium Map with permanent room labels and user marker."""
    outline_geom = building(floor)
    bounds = outline_geom.bounds  # xmin, ymin, xmax, ymax
    center_x = (bounds[0] + bounds[2]) / 2.0
    center_y = (bounds[1] + bounds[3]) / 2.0
    center_lat, center_lon = xy_to_latlon(center_x, center_y)

    highlighted_set = set(highlighted_ids or [])
    near_set = set(near_ids or [])

    # Initialize map with no external tiles for a clean indoor canvas
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=20,
        max_zoom=24,
        min_zoom=17,
        tiles=None,
        control_scale=False,
    )

    # Fit bounds tightly to the floor plan so it fills the screen comfortably
    sw_lat, sw_lon = xy_to_latlon(bounds[0] - 2, bounds[1] - 2)
    ne_lat, ne_lon = xy_to_latlon(bounds[2] + 2, bounds[3] + 2)
    m.fit_bounds([[sw_lat, sw_lon], [ne_lat, ne_lon]], padding=[15, 15])

    # Inject CSS for a soft neutral background canvas
    m.get_root().html.add_child(folium.Element("""
    <style>
        .leaflet-container {
            background-color: #e5e7eb !important;
        }
    </style>
    """))

    # 1. Building Outline (floor footprint)
    if outline_geom.geom_type == "Polygon":
        polys = [outline_geom]
    else:
        polys = list(outline_geom.geoms)

    for poly in polys:
        outline_coords = [xy_to_latlon(x, y) for x, y in poly.exterior.coords]
        folium.Polygon(
            locations=outline_coords,
            color="#94a3b8",
            weight=1.5,
            fill=True,
            fill_color="#f1f5f9",
            fill_opacity=0.5,
            tooltip=f"Outline Gedung Lt. {floor}",
        ).add_to(m)

    # 2. Voids (Holes in the floor)
    for void_poly in voids(floor):
        void_coords = [xy_to_latlon(x, y) for x, y in void_poly.exterior.coords]
        folium.Polygon(
            locations=void_coords,
            color="#64748b",
            weight=1.5,
            dash_array="4, 4",
            fill=True,
            fill_color="#cbd5e1",
            fill_opacity=0.7,
            tooltip="VOID",
        ).add_to(m)

    # 3. Rooms and Permanent Name Labels
    for r in rooms:
        poly = r["polygon"]
        coords = [xy_to_latlon(x, y) for x, y in poly.exterior.coords]
        rid = r["room_id"]
        rtype = r["type"]

        is_search_match = rid in highlighted_set
        is_in_buffer = rid in near_set
        is_link = rtype in LINK_TYPES

        if is_search_match:
            fill_color = COLOR_ROOM_HIGHLIGHT
            border_color = "#b45309"
            weight = 2.8
            fill_opacity = 0.95
        elif is_in_buffer:
            fill_color = COLOR_ROOM_NEARBY
            border_color = "#ef4444"
            weight = 2.2
            fill_opacity = 0.88
        elif is_link:
            fill_color = COLOR_LINK_ROOM
            border_color = "#ea580c"
            weight = 2.0
            fill_opacity = 0.85
        else:
            fill_color = COLOR_ROOM_FILL
            border_color = COLOR_ROOM_BORDER
            weight = 1.5
            fill_opacity = 0.85

        popup_html = f"""
        <div style="font-family: system-ui, sans-serif; font-size: 13px; line-height: 1.4; min-width: 170px;">
            <b style="font-size: 14px; color: #0f172a;">{r['name']}</b><br>
            <span style="color: #64748b;">ID:</span> <b>{rid}</b><br>
            <span style="color: #64748b;">Tipe:</span> {rtype}<br>
            <span style="color: #64748b;">Luas:</span> {poly.area:.1f} m²
        </div>
        """

        folium.Polygon(
            locations=coords,
            color=border_color,
            weight=weight,
            fill=True,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            tooltip=f"{rid} - {r['name']} ({rtype})",
            popup=folium.Popup(popup_html, max_width=280),
        ).add_to(m)

        # Permanent Centered Room Label (Name & ID)
        centroid = poly.centroid
        c_lat, c_lon = xy_to_latlon(centroid.x, centroid.y)
        clean_name = r["name"].split(" (")[0]
        # For rooms with area >= 20, show room name, otherwise show ID/abbreviation
        if poly.area >= 25:
            label_text = f"<b>{rid}</b><br>{clean_name}"
        else:
            label_text = f"<b>{rid}</b>"

        folium.Marker(
            location=[c_lat, c_lon],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    font-family: system-ui, -apple-system, sans-serif;
                    font-size: 7.5px;
                    font-weight: 700;
                    color: #0f172a;
                    text-align: center;
                    line-height: 1.15;
                    width: 70px;
                    margin-left: -35px;
                    margin-top: -8px;
                    pointer-events: none;
                    text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff,
                                 -1.5px 0 0 #fff, 1.5px 0 0 #fff, 0 -1.5px 0 #fff, 0 1.5px 0 #fff;
                ">{label_text}</div>
                """
            )
        ).add_to(m)

    # 4. Buffer Polygon around User (matching app.py buffer)
    if buffer_geom:
        buf_coords = [xy_to_latlon(bx, by) for bx, by in buffer_geom.exterior.coords]
        folium.Polygon(
            locations=buf_coords,
            color="#2563eb",
            weight=1.5,
            fill=True,
            fill_color="#3b82f6",
            fill_opacity=0.18,
            tooltip="Buffer Radius",
        ).add_to(m)

    # 5. User Dot (matching app.py self.dot: red marker with white border)
    if user_pos:
        ux, uy = user_pos
        u_lat, u_lon = xy_to_latlon(ux, uy)
        folium.CircleMarker(
            location=[u_lat, u_lon],
            radius=8,
            color="#ffffff",
            weight=2.5,
            fill=True,
            fill_color="#dc2626",
            fill_opacity=1.0,
            tooltip=f"Posisi Anda ({ux:g}, {uy:g}) m",
        ).add_to(m)

    return m
