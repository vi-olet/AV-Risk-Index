# scripts/08_summary_stats.py
import sys
import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

roads = gpd.read_file(ROADS_HOTSPOT)

print("\n" + "="*50)
print("AV ROAD RISK INDEX — SUMMARY STATISTICS")
print("Menlo Park, California")
print("="*50)
print(f"\nTotal road segments analyzed: {len(roads)}")

print(f"\nRisk Tier Distribution:")
print(roads["risk_tier"].value_counts().reindex(["Low", "Moderate", "High", "Critical"]))

print(f"\nHotspot Classification:")
print(roads["hotspot_class"].value_counts())

print(f"\nDominant Risk Factors:")
print(roads["dominant_factor"].value_counts())

# -------------------------------------------------------
# Top 10 — deduplicated by street name
# Prevents the same street flooding all 10 rows
# -------------------------------------------------------
print(f"\nTop 10 Highest Risk Segments (unique streets):")
top10 = (
    roads
    .drop_duplicates(subset="name")
    .nlargest(10, "risk_score")
    [["name", "risk_score", "risk_tier", "hotspot_class", "dominant_factor"]]
)
print(top10.to_string(index=False))

# -------------------------------------------------------
# Save full CSV report
# -------------------------------------------------------
os.makedirs("outputs/reports", exist_ok=True)
roads.drop(columns="geometry").to_csv("outputs/reports/summary_stats.csv", index=False)

# -------------------------------------------------------
# 4-panel summary chart
# -------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("AV Road Risk Index — Menlo Park, CA", fontsize=15, fontweight="bold")

TIER_COLORS    = ["#2ecc71", "#f39c12", "#e67e22", "#e74c3c"]
HOTSPOT_COLORS = {
    "Hot Spot (99%)":  "#d7191c",
    "Hot Spot (95%)":  "#f17c4a",
    "Hot Spot (90%)":  "#fec980",
    "Not Significant": "#d3d3d3",
    "Cold Spot (90%)": "#abd9e9",
    "Cold Spot (95%)": "#74add1",
    "Cold Spot (99%)": "#2c7bb6",
}

# ── Chart 1: Risk score distribution ──────────────────────────────────────
ax = axes[0, 0]
ax.hist(roads["risk_score"], bins=30, color="#3b82f6", edgecolor="white", linewidth=0.5)
ax.axvline(
    roads["risk_score"].mean(), color="#ef4444", linestyle="--", linewidth=1.5,
    label=f"Mean: {roads['risk_score'].mean():.3f}"
)
ax.set_title("Composite Risk Score Distribution", fontweight="bold")
ax.set_xlabel("Risk Score (0–1)")
ax.set_ylabel("Number of Segments")
ax.legend()
ax.spines[["top", "right"]].set_visible(False)

# ── Chart 2: Risk tier bar chart ──────────────────────────────────────────
ax = axes[0, 1]
tier_counts = (
    roads["risk_tier"]
    .value_counts()
    .reindex(["Low", "Moderate", "High", "Critical"])
)
bars = ax.bar(
    tier_counts.index, tier_counts.values,
    color=TIER_COLORS, edgecolor="white", linewidth=0.5
)
ax.set_title("Segments by Risk Tier", fontweight="bold")
ax.set_xlabel("Risk Tier")
ax.set_ylabel("Number of Segments")
ax.spines[["top", "right"]].set_visible(False)
for bar, val in zip(bars, tier_counts.values):
    if not pd.isna(val):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 5,
            str(int(val)), ha="center", fontweight="bold", fontsize=9
        )

# ── Chart 3: Hotspot classification (horizontal bar) ─────────────────────
ax = axes[1, 0]
hotspot_order = [
    "Hot Spot (99%)", "Hot Spot (95%)", "Hot Spot (90%)",
    "Not Significant",
    "Cold Spot (90%)", "Cold Spot (95%)", "Cold Spot (99%)"
]
hotspot_counts = roads["hotspot_class"].value_counts().reindex(hotspot_order).fillna(0)
bar_colors     = [HOTSPOT_COLORS.get(k, "#d3d3d3") for k in hotspot_counts.index]

ax.barh(hotspot_counts.index, hotspot_counts.values,
        color=bar_colors, edgecolor="white", linewidth=0.5)
ax.set_title("Getis-Ord Gi* Hotspot Classification", fontweight="bold")
ax.set_xlabel("Number of Segments")
ax.spines[["top", "right"]].set_visible(False)
for i, val in enumerate(hotspot_counts.values):
    ax.text(val + 5, i, str(int(val)), va="center", fontsize=8)

# ── Chart 4: Average normalized component scores ──────────────────────────
ax = axes[1, 1]
components   = ["Pavement\nDistress", "Behavioral\nComplexity", "Accident\nHistory"]
comp_cols    = ["norm_surface", "norm_behavior", "norm_accidents"]
comp_colors  = ["#3b82f6", "#ef4444", "#f59e0b"]
comp_weights = [WEIGHT_SURFACE, WEIGHT_BEHAVIOR, WEIGHT_ACCIDENTS]

# Only use columns that exist (in case behavior is still 0)
means = []
for col in comp_cols:
    if col in roads.columns:
        means.append(roads[col].mean())
    else:
        means.append(0)

bars = ax.bar(components, means, color=comp_colors, edgecolor="white", linewidth=0.5)
ax.set_title("Average Normalized Component Scores", fontweight="bold")
ax.set_ylabel("Average Score (0–1)")
ax.set_ylim(0, 1)
ax.spines[["top", "right"]].set_visible(False)

# Add weight labels inside bars
for bar, weight, mean in zip(bars, comp_weights, means):
    if mean > 0.05:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            mean / 2,
            f"weight\n{int(weight*100)}%",
            ha="center", va="center",
            color="white", fontsize=8, fontweight="bold"
        )
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        mean + 0.02,
        f"{mean:.3f}",
        ha="center", fontsize=8, fontweight="bold"
    )

plt.tight_layout()
os.makedirs(os.path.dirname(OUTPUT_CHARTS), exist_ok=True)
plt.savefig(OUTPUT_CHARTS, dpi=150, bbox_inches="tight")
print(f"\nCharts saved to {OUTPUT_CHARTS}")
plt.show()






