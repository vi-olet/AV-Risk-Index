# scripts/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
STREETVIEW_API_KEY = os.getenv("STREETVIEW_API_KEY")

# Study Area
STUDY_AREA         = "Menlo Park, California, USA"
MAP_CENTER         = [37.4530, -122.1817]
MAP_ZOOM           = 14

# Coordinate Systems
CRS_GEOGRAPHIC     = "EPSG:4326"    # lat/lon for web maps
CRS_PROJECTED      = "EPSG:26910"   # UTM Zone 10N — for California distance measurements

# Street View Settings
SV_PITCH           = -45            # degrees down toward road surface
SV_FOV             = 90
SV_SAMPLE_INTERVAL = 50             # meters between sample points

# Risk Score Weights — must sum to 1.0
WEIGHT_SURFACE     = 0.35           # Street View pavement distress
WEIGHT_BEHAVIOR    = 0.40           # OSM behavioral complexity
WEIGHT_ACCIDENTS   = 0.25           # SWITRS historical accident data

# Hotspot Analysis
SPATIAL_WEIGHT_THRESHOLD = 300      # meters — roughly 1 city block

# File Paths — raw data
ROADS_RAW          = "data/raw/road_network/menlo_park_streets.gpkg"
OSM_COMPLEXITY_DIR = "data/raw/osm_complexity"
ACCIDENTS_CSV      = "data/raw/supplemental/accidents.csv"
SV_IMAGES_DIR      = "data/streetview_images"

# File Paths — processed data
SAMPLE_POINTS      = "data/processed/sample_points.gpkg"
SV_DISTRESS_RAW    = "data/processed/streetview_distress_raw.csv"
SV_DISTRESS_SEG    = "data/processed/streetview_distress_by_segment.csv"
OSM_COMPLEXITY_CSV = "data/processed/osm_complexity.csv"
ROADS_FEATURES     = "data/processed/roads_with_features.gpkg"
ROADS_RISK         = "data/processed/roads_risk_scored.gpkg"
ROADS_HOTSPOT      = "data/processed/roads_hotspot_final.gpkg"

# File Paths — outputs
OUTPUT_MAP         = "outputs/maps/av_risk_index_map.html"
OUTPUT_CHARTS      = "outputs/charts/summary_charts.png"
LOG_FILE           = "logs/pipeline.log"




