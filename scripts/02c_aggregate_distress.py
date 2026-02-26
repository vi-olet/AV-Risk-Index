# scripts/02c_aggregate_distress.py
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading raw distress scores...")
raw = pd.read_csv(SV_DISTRESS_RAW)
print(f"Raw records: {len(raw)} across {raw['osmid'].nunique()} segments")

seg = raw.groupby("osmid").agg(
    avg_distress  = ("distress_score", "mean"),
    max_distress  = ("distress_score", "max"),
    std_distress  = ("distress_score", "std"),
    sample_count  = ("distress_score", "count")
).reset_index()

# Flag segments with fewer than 2 samples as less reliable
seg["reliable"] = seg["sample_count"] >= 2

# Classify distress level for easy reading
seg["distress_class"] = pd.cut(
    seg["avg_distress"],
    bins=[0, 0.03, 0.07, 0.12, 0.20, 1.0],
    labels=["Excellent", "Good", "Fair", "Poor", "Critical"],
    include_lowest=True
)

seg.to_csv(SV_DISTRESS_SEG, index=False)

print(f"\nAggregated {len(seg)} road segments")
print(f"\nDistress class distribution:")
print(seg["distress_class"].value_counts())
print(f"\nReliable segments (2+ samples): {seg['reliable'].sum()}")