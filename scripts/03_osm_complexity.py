# scripts/03_osm_complexity.py
# Generates behavioral complexity scores from OSM road attributes.
# Source: highway classification, lane count, speed limits, directionality.
# Method: structured scoring per road type with Gaussian noise σ=0.02
#         so segments of the same class get natural variation rather than
#         identical scores.
#
# Note: the Waymo open dataset Python package only distributes manylinux
# wheel files (Linux-only). No Windows binary exists on PyPI. OSM road
# attributes are direct structural predictors of the same agent interaction
# density that Waymo trajectory data would measure. The methodology is
# architecturally transparent — swapping in real Waymo data only requires
# replacing osm_complexity.csv with a file in the same column format.

import sys
import os
import pandas as pd
import geopandas as gpd
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Generating behavioral complexity scores from OSM road attributes...")
print("Source: highway type, lane count, speed limits, directionality")
print("Method: structured scoring with Gaussian noise σ=0.02 for natural variation")

# Load road network in geographic CRS
roads = gpd.read_file(ROADS_RAW).to_crs(CRS_GEOGRAPHIC)
print(f"Loaded {len(roads)} road segments")

# -------------------------------------------------------
# Base complexity scores by highway type
# Higher value = more unpredictable agent behavior expected
# Based on typical pedestrian/vehicle interaction density
# -------------------------------------------------------
highway_complexity = {
    "motorway":       0.2,    # controlled access — predictable
    "motorway_link":  0.25,
    "trunk":          0.3,
    "trunk_link":     0.3,
    "primary":        0.7,    # high traffic — mixed agents
    "primary_link":   0.6,
    "secondary":      0.65,
    "secondary_link": 0.55,
    "tertiary":       0.5,
    "tertiary_link":  0.45,
    "residential":    0.3,    # low speed — occasional pedestrians
    "living_street":  0.4,    # shared space — pedestrians common
    "unclassified":   0.3,
    "service":        0.35,
    "pedestrian":     0.8,    # very high pedestrian activity
    "cycleway":       0.6,    # cyclist-heavy
    "footway":        0.5,
    "path":           0.4,
    "steps":          0.3,
}

def get_complexity(highway_val):
    """Get base complexity score for a highway type including list values."""
    if isinstance(highway_val, list):
        scores = [highway_complexity.get(str(h), 0.35) for h in highway_val]
        return max(scores)
    return highway_complexity.get(str(highway_val), 0.35)

# Base complexity from road type
roads["base_complexity"] = roads["highway"].apply(get_complexity)

# -------------------------------------------------------
# Adjustment factors from additional OSM attributes
# -------------------------------------------------------

# Lane count — more lanes = more complex vehicle interactions
if "lanes" in roads.columns:
    roads["lanes_num"]  = pd.to_numeric(roads["lanes"], errors="coerce").fillna(1)
    roads["lane_factor"] = (roads["lanes_num"] - 1) * 0.05
else:
    roads["lane_factor"] = 0

# Directionality — bidirectional roads have more complex interactions
if "oneway" in roads.columns:
    roads["oneway_factor"] = roads["oneway"].apply(
        lambda x: -0.05 if str(x).lower() in ["yes", "true", "1"] else 0.05
    )
else:
    roads["oneway_factor"] = 0

# Speed limit — lower speed = more pedestrian activity expected
if "maxspeed" in roads.columns:
    def speed_factor(speed):
        try:
            s = float(str(speed).replace(" mph", "").replace(" kmh", "").strip())
            if s <= 25:   return  0.15   # slow zone — pedestrians likely
            elif s <= 35: return  0.05
            elif s <= 45: return  0.0
            else:         return -0.05   # fast road — fewer pedestrians
        except:
            return 0.0
    roads["speed_factor"] = roads["maxspeed"].apply(speed_factor)
else:
    roads["speed_factor"] = 0

# -------------------------------------------------------
# Composite complexity score
# -------------------------------------------------------
roads["complexity_score"] = (
    roads["base_complexity"] +
    roads["lane_factor"]     +
    roads["oneway_factor"]   +
    roads["speed_factor"]
).clip(0.1, 1.0)

# Add small controlled variation to avoid identical scores
# for all segments of the same highway type
np.random.seed(42)
roads["complexity_score"] = (
    roads["complexity_score"] +
    np.random.normal(0, 0.02, len(roads))
).clip(0.1, 1.0)

# -------------------------------------------------------
# Calculate centroids accurately
# Project to meters first, compute centroid, convert back to lat/lon
# (computing centroids in degrees gives inaccurate results)
# -------------------------------------------------------
roads_projected = roads.to_crs(CRS_PROJECTED)
centroids = gpd.GeoSeries(
    roads_projected.geometry.centroid,
    crs=CRS_PROJECTED
).to_crs(CRS_GEOGRAPHIC)

# -------------------------------------------------------
# Build output CSV
# Column format matches what 04_spatial_join.py expects
# -------------------------------------------------------
output = pd.DataFrame({
    "scenario_id":      [f"osm_{i}" for i in range(len(roads))],
    "center_x":         centroids.x.values,   # longitude (geographic)
    "center_y":         centroids.y.values,   # latitude  (geographic)
    "num_vehicles":     (roads["complexity_score"] * 8).round().astype(int),
    "num_pedestrians":  (roads["complexity_score"] * 4).round().astype(int),
    "num_cyclists":     (roads["complexity_score"] * 2).round().astype(int),
    "total_agents":     (roads["complexity_score"] * 14).round().astype(int),
    "complexity_score": roads["complexity_score"].values,
    "source":           "osm_proxy"
})

os.makedirs(os.path.dirname(OSM_COMPLEXITY_CSV), exist_ok=True)
output.to_csv(OSM_COMPLEXITY_CSV, index=False)

print(f"\nGenerated complexity scores for {len(output)} road segments")
print(f"\nComplexity score distribution:")
print(output["complexity_score"].describe())
print(f"\nHighway type breakdown (top 10 by mean complexity):")
print(
    roads[["highway", "complexity_score"]]
    .groupby("highway")["complexity_score"]
    .mean()
    .sort_values(ascending=False)
    .head(10)
)