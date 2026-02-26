# scripts/07_build_webmap.py
import sys
import os
import base64
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

# Color scheme matches standard Gi* hotspot map convention
HOTSPOT_COLORS = {
    "Hot Spot (99%)":  "#d7191c",
    "Hot Spot (95%)":  "#f17c4a",
    "Hot Spot (90%)":  "#fec980",
    "Not Significant": "#d3d3d3",
    "Cold Spot (90%)": "#abd9e9",
    "Cold Spot (95%)": "#74add1",
    "Cold Spot (99%)": "#2c7bb6"
}

def load_thumbnail(osmid):
    """Load cached Street View image as base64 string for popup embedding"""
    path = os.path.join(SV_IMAGES_DIR, f"seg_{osmid}_s0.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def build_popup(row):
    """Build HTML popup with Street View photo and risk metrics"""
    b64 = load_thumbnail(row.get("osmid", ""))
    img_html = (
        f'<img src="data:image/jpeg;base64,{b64}" '
        f'width="400" style="border-radius:6px;margin-bottom:8px;display:block"><br>'
        if b64 else ""
    )

    tier_colors = {
        "Low": "#2ecc71", "Moderate": "#f39c12",
        "High": "#e67e22", "Critical": "#e74c3c"
    }
    tier  = str(row.get("risk_tier", "N/A"))
    color = tier_colors.get(tier, "#95a5a6")
    badge = (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:11px">{tier}</span>'
    )

    return (
        f'<div style="font-family:Arial;font-size:12px;width:420px">'
        f'{img_html}'
        f'<b>{row.get("name", "Road Segment")}</b> {badge}<br><br>'
        f'<b>Risk Score:</b> {row.get("risk_score", 0):.3f}<br>'
        f'<b>Hotspot Class:</b> {row.get("hotspot_class", "N/A")}<br>'
        f'<b>Gi* Z-Score:</b> {row.get("gi_zscore", 0):.3f}<br>'
        f'<hr style="margin:4px 0">'
        f'<b>Components:</b><br>'
        f'Pavement Distress: {row.get("avg_distress", 0):.3f}<br>'
        f'Behavioral Complexity: {row.get("avg_complexity", 0):.3f}<br>'
        f'Accident Count: {int(row.get("accident_count", 0))}<br><br>'
        f'<b>Dominant Factor:</b> {row.get("dominant_factor", "N/A")}'
        f'</div>'
    )

print("Loading hotspot data...")
roads = gpd.read_file(ROADS_HOTSPOT).to_crs(CRS_GEOGRAPHIC)

m = folium.Map(location=MAP_CENTER, zoom_start=MAP_ZOOM, tiles="CartoDB positron")
MiniMap(toggle_display=True).add_to(m)
Fullscreen().add_to(m)

print(f"Adding {len(roads)} road segments to map...")
skipped = 0

for _, row in roads.iterrows():
    if row.geometry is None or row.geometry.is_empty:
        skipped += 1
        continue

    hotspot_class = str(row.get("hotspot_class", "Not Significant"))
    color  = HOTSPOT_COLORS.get(hotspot_class, "#d3d3d3")
    weight = 6 if "Hot Spot" in hotspot_class else 2

    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x, c=color, w=weight: {
            "color": c, "weight": w, "opacity": 0.85
        },
        popup=folium.Popup(build_popup(row), max_width=430),
        tooltip=f"{row.get('name', 'Segment')} — Risk: {row.get('risk_score', 0):.2f}"
    ).add_to(m)

# Add legend
legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:15px;border-radius:8px;
     border:2px solid #ccc;font-family:Arial;font-size:12px;
     box-shadow:2px 2px 6px rgba(0,0,0,0.3)">
    <b>AV Road Risk Index</b><br>
    <i style="color:#666">Menlo Park, CA — Getis-Ord Gi*</i><br><br>
    <span style="color:#d7191c">━━━</span> Hot Spot (99%)<br>
    <span style="color:#f17c4a">━━━</span> Hot Spot (95%)<br>
    <span style="color:#fec980">━━━</span> Hot Spot (90%)<br>
    <span style="color:#d3d3d3">━━━</span> Not Significant<br>
    <span style="color:#abd9e9">━━━</span> Cold Spot (90%)<br>
    <span style="color:#74add1">━━━</span> Cold Spot (95%)<br>
    <span style="color:#2c7bb6">━━━</span> Cold Spot (99%)<br><br>
    <b>Risk Weights</b><br>
    Surface: 35% | Behavior: 40% | Accidents: 25%<br><br>
    <i style="color:#999;font-size:10px">Click any segment for Street View photo</i>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

os.makedirs(os.path.dirname(OUTPUT_MAP), exist_ok=True)
m.save(OUTPUT_MAP)
print(f"\nMap saved to {OUTPUT_MAP}")
print(f"Segments added: {len(roads) - skipped} | Skipped: {skipped}")
print("Open the .html file in Chrome or Edge to preview")