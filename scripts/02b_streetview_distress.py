# scripts/02b_streetview_distress.py
import sys
import os
import time
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import cv2
from PIL import Image
import io
from tqdm import tqdm
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import *

os.makedirs(SV_IMAGES_DIR, exist_ok=True)

def fetch_image(lat, lon, heading):
    """Fetch Street View image. Returns (PIL Image, date string) or (None, None)"""
    # Check coverage first — cheaper metadata call
    meta_url = (
        f"https://maps.googleapis.com/maps/api/streetview/metadata"
        f"?location={lat},{lon}&key={STREETVIEW_API_KEY}"
    )
    meta = requests.get(meta_url, timeout=10).json()
    if meta.get("status") != "OK":
        return None, None

    image_url = (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size=640x480"
        f"&location={lat},{lon}"
        f"&heading={heading}"
        f"&pitch={SV_PITCH}"
        f"&fov={SV_FOV}"
        f"&key={STREETVIEW_API_KEY}"
    )
    r = requests.get(image_url, timeout=15)
    img = Image.open(io.BytesIO(r.content)) if r.status_code == 200 else None
    return img, meta.get("date", "unknown")


def score_distress(image):
    """Score pavement distress from Street View image. Returns 0 (perfect) to 1 (severe)"""
    arr  = np.array(image)
    # Use bottom 40% of image — that's where the road surface appears at pitch=-45
    road = arr[int(arr.shape[0] * 0.6):, :]
    gray = cv2.cvtColor(road, cv2.COLOR_RGB2GRAY)

    # Metric 1: Edge density — cracks and distress lines create edges
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    edge_density = float(edges.sum() / (edges.size * 255))

    # Metric 2: Texture variance — rough surfaces have higher variance than smooth
    texture_variance = float(np.var(gray) / 10000)

    # Metric 3: Dark patch ratio — cracks appear as dark linear features
    _, dark = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY_INV)
    dark_ratio = float(dark.sum() / (dark.size * 255))

    distress_score = min(1.0,
        edge_density     * 0.40 +
        min(texture_variance, 1.0) * 0.35 +
        dark_ratio       * 0.25
    )

    return {
        "edge_density":      edge_density,
        "texture_variance":  texture_variance,
        "dark_ratio":        dark_ratio,
        "distress_score":    distress_score
    }


# Load sample points
print("Loading sample points...")
points = gpd.read_file(SAMPLE_POINTS)
print(f"Processing {len(points)} sample points...")

results   = []
no_coverage = 0
errors    = 0

for _, row in tqdm(points.iterrows(), total=len(points), desc="Street View"):
    cache_file = os.path.join(
        SV_IMAGES_DIR,
        f"seg_{row['osmid']}_s{row['sample_num']}.jpg"
    )

    try:
        if os.path.exists(cache_file):
            image    = Image.open(cache_file)
            sv_date  = "cached"
        else:
            image, sv_date = fetch_image(
                row["latitude"], row["longitude"], row["heading"]
            )
            if image:
                image.save(cache_file)
            time.sleep(0.05)  # gentle rate limiting

        if image:
            scores = score_distress(image)
            scores.update({
                "osmid":      row["osmid"],
                "sample_num": row["sample_num"],
                "sv_date":    sv_date
            })
            results.append(scores)
        else:
            no_coverage += 1

    except Exception as e:
        errors += 1

results_df = pd.DataFrame(results)
os.makedirs(os.path.dirname(SV_DISTRESS_RAW), exist_ok=True)
results_df.to_csv(SV_DISTRESS_RAW, index=False)

print(f"\nComplete: {len(results)} scored | {no_coverage} no coverage | {errors} errors")
print(results_df["distress_score"].describe())