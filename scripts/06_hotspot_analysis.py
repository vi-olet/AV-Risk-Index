# scripts/06_hotspot_analysis.py
import sys
import os
import numpy as np
import geopandas as gpd
from libpysal.weights import DistanceBand
from esda.getisord import G_Local
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading risk-scored roads...")
roads = gpd.read_file(ROADS_RISK).to_crs(CRS_PROJECTED)

# Use segment centroids to build the spatial weight matrix
centroids = roads.geometry.centroid
coords    = np.column_stack([centroids.x, centroids.y])

print(f"Building spatial weights matrix (threshold={SPATIAL_WEIGHT_THRESHOLD}m)...")
w = DistanceBand(
    coords,
    threshold=SPATIAL_WEIGHT_THRESHOLD,
    binary=False,
    silence_warnings=True
)
w.transform = "r"  # row-standardize
print(f"Mean neighbors per segment: {w.mean_neighbors:.1f}")

print("Running Getis-Ord Gi* (this takes a few minutes)...")
gi = G_Local(
    roads["risk_score"].fillna(0).values,
    w,
    star=True,
    transform="r",
    permutations=999  # 999 random simulations for reliable p-values
)

roads["gi_zscore"] = gi.Zs
roads["gi_pvalue"] = gi.p_sim

def classify_hotspot(z, p):
    if   p <= 0.01 and z > 0: return "Hot Spot (99%)"
    elif p <= 0.05 and z > 0: return "Hot Spot (95%)"
    elif p <= 0.10 and z > 0: return "Hot Spot (90%)"
    elif p <= 0.01 and z < 0: return "Cold Spot (99%)"
    elif p <= 0.05 and z < 0: return "Cold Spot (95%)"
    elif p <= 0.10 and z < 0: return "Cold Spot (90%)"
    else:                      return "Not Significant"

roads["hotspot_class"] = roads.apply(
    lambda r: classify_hotspot(r["gi_zscore"], r["gi_pvalue"]),
    axis=1
)

roads.to_file(ROADS_HOTSPOT, driver="GPKG")

print(f"\nHotspot classification results:")
print(roads["hotspot_class"].value_counts())
print(f"\nTop 10 highest-risk hotspot segments:")
hot = roads[roads["hotspot_class"].str.contains("Hot", na=False)]
print(hot.nlargest(10, "gi_zscore")[["name", "risk_score", "hotspot_class", "dominant_factor"]])