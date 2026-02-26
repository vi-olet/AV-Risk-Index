# scripts/00_preprocess_accidents.py
import sys
import os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

print("Loading SWITRS tables...")
crashes = pd.read_csv("data/raw/supplemental/crashes.csv", low_memory=False)
print(f"Crashes: {len(crashes)} rows")

# Load parties and victims if available
try:
    parties = pd.read_csv("data/raw/supplemental/parties.csv", low_memory=False)
    print(f"Parties: {len(parties)} rows")
    has_parties = True
except FileNotFoundError:
    print("parties.csv not found — skipping party details")
    has_parties = False

try:
    victims = pd.read_csv("data/raw/supplemental/victims.csv", low_memory=False)
    print(f"Victims: {len(victims)} rows")
    has_victims = True
except FileNotFoundError:
    print("victims.csv not found — skipping victim details")
    has_victims = False

# -------------------------------------------------------
# Rename columns to lowercase for consistency
# -------------------------------------------------------
crashes.columns = crashes.columns.str.lower()

# -------------------------------------------------------
# Use LATITUDE/LONGITUDE columns — already present
# -------------------------------------------------------
accidents = crashes.copy()

# Drop rows with missing coordinates
accidents = accidents.dropna(subset=["latitude", "longitude"])

# Filter to valid Menlo Park / San Mateo County coordinates
accidents = accidents[
    (accidents["latitude"]  > 37.0) & (accidents["latitude"]  < 38.5) &
    (accidents["longitude"] > -123.0) & (accidents["longitude"] < -121.0)
]

print(f"\nAfter coordinate filter: {len(accidents)} crashes")

# -------------------------------------------------------
# Severity weighting using available columns
# Fatal crashes weighted more heavily than injury crashes
# -------------------------------------------------------
accidents["severity_weight"] = (
    accidents["number_killed"].fillna(0)   * 3.0 +
    accidents["number_injured"].fillna(0)  * 1.0 +
    accidents["count_severe_inj"].fillna(0) * 2.0
).clip(lower=1.0)

# -------------------------------------------------------
# Useful flag columns already in crashes file
# -------------------------------------------------------
accidents["involved_cyclist"]  = accidents["bicycle_accident"].fillna("N").eq("Y").astype(int)
accidents["involved_ped"]      = accidents["pedestrian_accident"].fillna("N").eq("Y").astype(int)
accidents["involved_moto"]     = accidents["motorcycle_accident"].fillna("N").eq("Y").astype(int)
accidents["alcohol"]           = accidents["alcohol_involved"].fillna("N").eq("Y").astype(int)

# -------------------------------------------------------
# Merge parties summary if available
# -------------------------------------------------------
if has_parties:
    parties.columns = parties.columns.str.lower()
    if "case_id" in parties.columns:
        party_summary = parties.groupby("case_id").agg(
            num_parties = ("case_id", "count")
        ).reset_index()
        accidents = accidents.merge(party_summary, on="case_id", how="left")

# -------------------------------------------------------
# Merge victim summary if available
# -------------------------------------------------------
if has_victims:
    victims.columns = victims.columns.str.lower()
    if "case_id" in victims.columns:
        victim_summary = victims.groupby("case_id").agg(
            total_victims = ("case_id", "count")
        ).reset_index()
        accidents = accidents.merge(victim_summary, on="case_id", how="left")

# -------------------------------------------------------
# Save final output
# -------------------------------------------------------
os.makedirs(os.path.dirname(ACCIDENTS_CSV), exist_ok=True)
accidents.to_csv(ACCIDENTS_CSV, index=False)

print(f"\nSaved {len(accidents)} accidents to {ACCIDENTS_CSV}")
print(f"\nDate range: {accidents['collision_date'].min()} to {accidents['collision_date'].max()}")
print(f"Fatal crashes:      {accidents['number_killed'].fillna(0).gt(0).sum()}")
print(f"Cyclist involved:   {accidents['involved_cyclist'].sum()}")
print(f"Pedestrian involved:{accidents['involved_ped'].sum()}")
print(f"Alcohol involved:   {accidents['alcohol'].sum()}")
print(f"\nSeverity weight distribution:")
print(accidents["severity_weight"].describe())