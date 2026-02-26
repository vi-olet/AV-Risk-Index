# scripts/02a_prepare_sample_points.py
import sys
import os
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading road network...")
roads = gpd.read_file(ROADS_RAW).to_crs(CRS_GEOGRAPHIC)
print(f"Loaded {len(roads)} road segments")

sample_points = []

for idx, row in roads.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    # Measure segment length in meters using projected CRS
    geom_proj = gpd.GeoSeries([geom], crs=CRS_GEOGRAPHIC).to_crs(CRS_PROJECTED).iloc[0]
    segment_length = geom_proj.length

    # One sample point every SV_SAMPLE_INTERVAL meters, minimum 1
    num_samples = max(1, int(segment_length / SV_SAMPLE_INTERVAL))

    for i in range(num_samples):
        position = (i + 0.5) / num_samples
        point = geom.interpolate(position, normalized=True)

        # Calculate road heading so Street View faces along the road
        p1 = geom.interpolate(max(0, position - 0.05), normalized=True)
        p2 = geom.interpolate(min(1, position + 0.05), normalized=True)
        heading = (np.degrees(np.arctan2(p2.x - p1.x, p2.y - p1.y)) + 360) % 360

        sample_points.append({
            "osmid":          row.get("osmid", idx),
            "segment_idx":    int(idx),
            "sample_num":     i,
            "latitude":       round(point.y, 7),
            "longitude":      round(point.x, 7),
            "heading":        round(heading, 1),
            "geometry":       point
        })

gdf = gpd.GeoDataFrame(sample_points, crs=CRS_GEOGRAPHIC)
os.makedirs(os.path.dirname(SAMPLE_POINTS), exist_ok=True)
gdf.to_file(SAMPLE_POINTS, driver="GPKG")

print(f"Generated {len(gdf)} sample points across {len(roads)} segments")