# scripts/05_risk_scoring.py
# Normalizes all three layers to 0-1 scale, applies weights, classifies
# into risk tiers, and identifies the dominant risk factor per segment.
#
# Key decisions:
#   - Accident count capped at 95th percentile before normalization
#     to prevent one extreme outlier from compressing all other scores
#   - Risk tiers based on score percentiles (not fixed bins) so all
#     four categories are meaningfully populated regardless of distribution

import sys
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading road features...")
roads = gpd.read_file(ROADS_FEATURES)

# -------------------------------------------------------
# Cap accident outliers before normalization
# A segment with 75 accidents vs one with 5 are both
# high-risk — the difference isn't meaningfully 15x.
# Capping at 95th percentile prevents the outlier from
# compressing all other accident scores toward zero.
# -------------------------------------------------------
acc_cap = roads["accident_count"].quantile(0.95)
print(f"Capping accident count at 95th percentile: {acc_cap:.1f}")
roads["accident_count_capped"] = roads["accident_count"].clip(upper=acc_cap)

# -------------------------------------------------------
# Normalize each component independently to 0-1
# Worst segment in each category → 1.0   Best → 0.0
# -------------------------------------------------------
scaler   = MinMaxScaler()
features = ["avg_distress", "avg_complexity", "accident_count_capped"]
norm     = scaler.fit_transform(roads[features].fillna(0))

roads["norm_surface"]   = norm[:, 0]   # Street View CV distress
roads["norm_behavior"]  = norm[:, 1]   # OSM behavioral complexity
roads["norm_accidents"] = norm[:, 2]   # SWITRS severity-weighted accidents

print(f"\nNormalized score means:")
print(f"  Surface:   {roads['norm_surface'].mean():.3f}")
print(f"  Behavior:  {roads['norm_behavior'].mean():.3f}")
print(f"  Accidents: {roads['norm_accidents'].mean():.3f}")
print(f"\nWeights: Surface={WEIGHT_SURFACE} | Behavior={WEIGHT_BEHAVIOR} | Accidents={WEIGHT_ACCIDENTS}")

# -------------------------------------------------------
# Weighted composite risk score
# -------------------------------------------------------
roads["risk_score"] = (
    roads["norm_surface"]   * WEIGHT_SURFACE   +
    roads["norm_behavior"]  * WEIGHT_BEHAVIOR  +
    roads["norm_accidents"] * WEIGHT_ACCIDENTS
)

# -------------------------------------------------------
# Risk tiers — percentile-based bins
# Fixed bins cluster poorly given the score distribution.
# Percentile bins ensure all categories are meaningfully
# populated regardless of absolute score range.
#   Low      = bottom 40%
#   Moderate = 40th–70th percentile
#   High     = 70th–90th percentile
#   Critical = top 10%
# -------------------------------------------------------
roads["risk_tier"] = pd.cut(
    roads["risk_score"],
    bins=[
        roads["risk_score"].min() - 0.001,
        roads["risk_score"].quantile(0.40),
        roads["risk_score"].quantile(0.70),
        roads["risk_score"].quantile(0.90),
        roads["risk_score"].max()
    ],
    labels=["Low", "Moderate", "High", "Critical"]
)

# -------------------------------------------------------
# Dominant risk factor per segment
# Identifies which component contributes most to each
# segment's score — useful for explaining results to
# non-technical audiences and prioritizing interventions
# -------------------------------------------------------
def dominant_factor(row):
    factors = {
        "Surface Condition":      row["norm_surface"]   * WEIGHT_SURFACE,
        "Behavioral Complexity":  row["norm_behavior"]  * WEIGHT_BEHAVIOR,
        "Accident History":       row["norm_accidents"] * WEIGHT_ACCIDENTS
    }
    return max(factors, key=factors.get)

roads["dominant_factor"] = roads.apply(dominant_factor, axis=1)

roads.to_file(ROADS_RISK, driver="GPKG")

print(f"\nRisk tier distribution:")
print(roads["risk_tier"].value_counts().reindex(["Low", "Moderate", "High", "Critical"]))
print(f"\nDominant risk factors:")
print(roads["dominant_factor"].value_counts())
print(f"\nRisk score distribution:")
print(roads["risk_score"].describe())