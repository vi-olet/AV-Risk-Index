# scripts/04_spatial_join.py
# Attaches all three risk layers to the road network:
#   Join 1 — Street View distress:    direct merge on osmid (already at segment level)
#   Join 2 — OSM behavioral complexity: sjoin_nearest 100m radius
#   Join 3 — SWITRS accident history:   sjoin_nearest 30m radius

import sys
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading road network...")
roads = gpd.read_file(ROADS_RAW).to_crs(CRS_PROJECTED)

# Force osmid to string throughout — prevents silent merge failures
# when one side is int64 and the other is object
roads["osmid"] = roads["osmid"].astype(str)
print(f"Loaded {len(roads)} road segments")

# -------------------------------------------------------
# Join 1: Street View distress — direct merge on osmid
# Scores already aggregated to segment level by 02c
# -------------------------------------------------------
print("\nJoining Street View distress scores...")
distress = pd.read_csv(SV_DISTRESS_SEG)
distress["osmid"] = distress["osmid"].astype(str)

roads = roads.merge(
    distress[["osmid", "avg_distress", "max_distress", "sample_count", "reliable"]],
    on="osmid",
    how="left"
)

sv_coverage = roads["avg_distress"].notna().sum()
print(f"Street View coverage: {sv_coverage}/{len(roads)} segments ({sv_coverage/len(roads)*100:.1f}%)")

# Impute missing with city median rather than 0
# so unsampled segments don't artificially lower their risk score
sv_median = roads["avg_distress"].median()
roads["avg_distress"] = roads["avg_distress"].fillna(sv_median)
roads["sv_imputed"]   = roads["sample_count"].isna()

# -------------------------------------------------------
# Join 2: OSM behavioral complexity
# Each complexity point spatially joined to nearest road within 100m
# Drop osmid from complexity data before joining to avoid column conflict
# -------------------------------------------------------
print("\nJoining OSM behavioral complexity scores...")
try:
    complexity_df = pd.read_csv(OSM_COMPLEXITY_CSV)
    print(f"Loaded {len(complexity_df)} complexity records")

    # Remove osmid column if present — prevents sjoin_nearest column conflict
    if "osmid" in complexity_df.columns:
        complexity_df = complexity_df.drop(columns=["osmid"])

    complexity_gdf = gpd.GeoDataFrame(
        complexity_df,
        geometry=[
            Point(x, y) for x, y in
            zip(complexity_df.center_x, complexity_df.center_y)
        ],
        crs=CRS_GEOGRAPHIC   # center_x/y are in lat/lon (geographic)
    ).to_crs(CRS_PROJECTED)  # reproject to meters for distance join

    # Spatial join — each complexity point joins to nearest road segment
    complexity_joined = gpd.sjoin_nearest(
        complexity_gdf,
        roads[["osmid", "geometry"]],
        max_distance=100   # 100 meter search radius
    )

    # Force osmid to string after join
    complexity_joined["osmid"] = complexity_joined["osmid"].astype(str)
    print(f"Matched {len(complexity_joined)} complexity records to road segments")

    complexity_per_road = complexity_joined.groupby("osmid").agg(
        avg_complexity = ("complexity_score", "mean"),
        max_complexity = ("complexity_score", "max"),
        scenario_count = ("scenario_id", "count")
    ).reset_index()

    complexity_per_road["osmid"] = complexity_per_road["osmid"].astype(str)

    roads = roads.merge(complexity_per_road, on="osmid", how="left")

    complexity_coverage = roads["avg_complexity"].notna().sum()
    print(f"Complexity coverage: {complexity_coverage}/{len(roads)} segments ({complexity_coverage/len(roads)*100:.1f}%)")

except FileNotFoundError:
    print(f"Complexity data not found at {OSM_COMPLEXITY_CSV} — setting to 0")
    print("Run scripts/03_osm_complexity.py first")
    roads["avg_complexity"] = 0
    roads["scenario_count"] = 0

# -------------------------------------------------------
# Join 3: Accident history — sjoin_nearest 30m radius
# Count / weight accidents within 30 metres of each segment
# Zero is valid — quiet streets genuinely have no accidents
# -------------------------------------------------------
print("\nJoining SWITRS accident data...")
try:
    accidents = pd.read_csv(ACCIDENTS_CSV)
    print(f"Loaded {len(accidents)} accident records")

    # Confirm coordinate columns exist
    if "latitude" not in accidents.columns or "longitude" not in accidents.columns:
        print("Accident CSV missing latitude/longitude columns — setting count to 0")
        roads["accident_count"]  = 0
        roads["severity_score"]  = 0
    else:
        accidents = accidents.dropna(subset=["latitude", "longitude"])

        accidents_gdf = gpd.GeoDataFrame(
            accidents,
            geometry=[
                Point(lon, lat) for lon, lat in
                zip(accidents.longitude, accidents.latitude)
            ],
            crs=CRS_GEOGRAPHIC
        ).to_crs(CRS_PROJECTED)

        acc_joined = gpd.sjoin_nearest(
            accidents_gdf,
            roads[["osmid", "geometry"]],
            max_distance=30   # 30 metre radius — tight to avoid cross-street attribution
        )

        acc_joined["osmid"] = acc_joined["osmid"].astype(str)

        # Aggregate — count and severity score per segment
        agg_dict = {"osmid": "count"}
        if "severity_weight" in acc_joined.columns:
            agg_dict["severity_weight"] = "sum"

        acc_per_road = acc_joined.groupby("osmid").agg(
            accident_count  = ("osmid", "count"),
            **( {"severity_score": ("severity_weight", "sum")}
                if "severity_weight" in acc_joined.columns else {} )
        ).reset_index()

        acc_per_road["osmid"] = acc_per_road["osmid"].astype(str)

        roads = roads.merge(acc_per_road, on="osmid", how="left")
        acc_coverage = roads["accident_count"].notna().sum()
        print(f"Accident coverage: {acc_coverage}/{len(roads)} segments ({acc_coverage/len(roads)*100:.1f}%)")

except FileNotFoundError:
    print(f"Accident data not found at {ACCIDENTS_CSV}")
    print("Run scripts/00_preprocess_accidents.py first, or continue without accident data")
    print("If continuing without: set WEIGHT_ACCIDENTS=0 in config.py")
    roads["accident_count"] = 0
    roads["severity_score"] = 0

# -------------------------------------------------------
# Fill remaining NaN values with 0
# -------------------------------------------------------
fill_cols = [
    "avg_distress", "avg_complexity", "accident_count", "severity_score",
    "max_distress", "max_complexity", "scenario_count"
]
for col in fill_cols:
    if col in roads.columns:
        roads[col] = roads[col].fillna(0)

# -------------------------------------------------------
# Save
# -------------------------------------------------------
os.makedirs(os.path.dirname(ROADS_FEATURES), exist_ok=True)
roads.to_file(ROADS_FEATURES, driver="GPKG")

print(f"\nSaved {len(roads)} segments to {ROADS_FEATURES}")
print(f"\nFeature summary:")
print(roads[["avg_distress", "avg_complexity", "accident_count"]].describe())




