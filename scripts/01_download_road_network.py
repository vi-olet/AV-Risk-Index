# scripts/01_download_road_network.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

import osmnx as ox
import geopandas as gpd

print("Downloading Menlo Park road network from OpenStreetMap...")

G = ox.graph_from_place(STUDY_AREA, network_type="drive")
nodes, edges = ox.graph_to_gdfs(G)

os.makedirs(os.path.dirname(ROADS_RAW), exist_ok=True)
edges.to_file(ROADS_RAW, driver="GPKG")

print(f"Done. Saved {len(edges)} road segments to {ROADS_RAW}")
print(f"Road types found: {edges['highway'].value_counts().to_dict()}")