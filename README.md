# AV Road Risk Index
**Menlo Park, CA** &nbsp;|&nbsp; Street View CV &nbsp;×&nbsp; OSM Complexity &nbsp;×&nbsp; SWITRS Crashes &nbsp;×&nbsp; Getis-Ord Gi*

---

## What This Is

Every drivable street in Menlo Park — all **2,480 segments** — scored and ranked by navigational risk for an autonomous vehicle.

Three independent data sources. One composite score per segment. A statistically validated map of where AV operations face the highest combined risk — and what kind of risk it is.

---

## Map Preview

<img width="1914" height="1068" alt="AV_Risk_Map png" src="https://github.com/user-attachments/assets/5e04d26a-df04-46f0-8d6c-9d58945d87d5" />
<!-- Replace this comment block with: ![AV Road Risk Index — Menlo Park CA](outputs/maps/av_risk_index_preview.png) -->

> **To view the full interactive map:** download `outputs/maps/av_risk_index_map.html` and open in Chrome or Edge. Click any segment to see the Street View photo, risk score breakdown, and hotspot classification.

---
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>

## Pipeline

Three data sources flow through eight processing stages into one interactive map.

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  STREET VIEW API    │  │  OPENSTREETMAP      │  │  SWITRS CRASHES     │
│  640×480 images     │  │  Road network       │  │  2018–2023          │
│  pitch –45°         │  │  Highway attributes │  │  San Mateo County   │
└──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
           │                        │                        │
           ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  02a SAMPLE POINTS  │  │  03 OSM COMPLEXITY  │  │  00 PREPROCESS      │
│  GPS point every    │  │  Score each segment │  │  Filter coords      │
│  50 m per segment   │  │  by highway type,   │  │  Apply severity     │
│  + heading calc     │  │  lanes, speed,      │  │  weights: fatal ×3  │
│  5,690 points total │  │  directionality     │  │  severe ×2  inj ×1  │
└──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘
           │                        │                        │
           ▼                        │                        │
┌─────────────────────┐             │                        │
│  02b STREET VIEW    │             │                        │
│  DISTRESS SCORING   │             │                        │
│  Crop bottom 40%    │             │                        │
│  Edge density ×0.40 │             │                        │
│  Texture var  ×0.35 │             │                        │
│  Dark patch   ×0.25 │             │                        │
│  → distress_score   │             │                        │
└──────────┬──────────┘             │                        │
           │                        │                        │
           ▼                        │                        │
┌─────────────────────┐             │                        │
│  02c AGGREGATE      │             │                        │
│  Group by osmid     │             │                        │
│  avg/max/std        │             │                        │
│  reliable ≥2 samples│             │                        │
│  974 segments scored│             │                        │
└──────────┬──────────┘             │                        │
           │                        │                        │
           └────────────┬───────────┘────────────────────────┘
                        │
                        ▼
          ┌─────────────────────────────┐
          │       04 SPATIAL JOIN       │
          │  JOIN 1 distress → osmid    │
          │  JOIN 2 complexity 100 m    │
          │  JOIN 3 accidents 30 m      │
          │  2,480 segments — all 3     │
          │  features attached          │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │      05 RISK SCORING        │
          │  Cap outliers at p95        │
          │  MinMaxScaler → 0 to 1      │
          │  Weighted composite score   │
          │  Percentile risk tiers      │
          └──────────────┬──────────────┘
                         │
                         ▼
          ┌─────────────────────────────┐
          │  06 GETIS-ORD Gi* HOTSPOT   │
          │  Centroids → UTM            │
          │  300 m distance band        │
          │  999 permutations           │
          │  z-score + p-value per seg  │
          └──────────────┬──────────────┘
                         │
               ┌─────────┴─────────┐
               ▼                   ▼
  ┌────────────────────┐ ┌────────────────────┐
  │   07 WEB MAP       │ │  08 SUMMARY STATS  │
  │   Folium HTML      │ │  4-panel chart     │
  │   Gi* colour coded │ │  Risk distribution │
  │   SV photo popups  │ │  Component means   │
  │   Interactive      │ │  summary_stats.csv │
  └────────────────────┘ └────────────────────┘
```

---

## Data Sources

Three datasets. All free. All public. Each one answers a different question about the same street.

---

### 1 — Google Street View Static API

**What it provides:** 640×480 photographs taken from a car-mounted camera at street level. Used to visually assess pavement condition on every road segment.

**Where to get it:**

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with a Google account
2. Click **Select a project** at the top → **New Project** → name it `av-risk-index` → Create
3. In the left menu go to **APIs & Services → Library**
4. Search for **Street View Static API** → click it → click **Enable**
5. Go to **APIs & Services → Credentials**
6. Click **+ Create Credentials → API Key**
7. Copy the key that appears

**How to configure it:**

Open `.env` in your project root and paste your key:
```
STREETVIEW_API_KEY=your_actual_key_here
```
No spaces. No quotes. Save the file.

**Cost:** Google provides $200 free monthly credit. Each Street View image costs $0.007. Menlo Park requires approximately 5,690 images — total cost around $40, covered by the free tier with credit to spare. Set a budget alert in the Google Cloud console to avoid surprise charges.

**What gets downloaded:** One JPEG per sample point, cached locally in `data/streetview_images/`. If the pipeline is interrupted and restarted, already-downloaded images are skipped automatically.

---

### 2 — OpenStreetMap via OSMnx

**What it provides:** The complete drivable road network for Menlo Park — every segment with attributes including highway classification, lane count, speed limit, and directionality. No download required. The pipeline fetches it automatically.

**Where to get it:** Script `01_download_road_network.py` handles this entirely. Run it once:

```bash
python scripts/01_download_road_network.py
```

This queries the OpenStreetMap API via the OSMnx Python library and saves the road network to `data/raw/road_network/menlo_park_streets.gpkg`. Requires an internet connection. Takes about 30 seconds.

**What gets saved:** 2,480 road segments as a GeoPackage with full OSM attribute columns. This file is the spatial backbone that every downstream script joins against.

**Note:** OSMnx is maintained by Geoff Boeing at USC. The library handles coordinate system conversion, graph simplification, and edge attribute extraction automatically. Documentation at [osmnx.readthedocs.io](https://osmnx.readthedocs.io).

---

### 3 — SWITRS Crash Records

**What it provides:** Every recorded collision in San Mateo County from 2018 to 2023 — three linked tables covering crash details, party information, and victim injuries. Used to score historical accident risk per road segment.

**Where to get it:**

1. Go to [tims.berkeley.edu](https://tims.berkeley.edu)
2. Click **SWITRS Query** in the top navigation
3. Create a free account and verify your email
4. Log in and click **New Query**
5. Set the following filters:
   - **County:** San Mateo
   - **Date range:** January 1 2018 to December 31 2023
   - **Collision type:** All (leave unchecked to include everything)
6. Click **Submit Query** and wait — large queries take 2–5 minutes to process
7. When complete, click **Download** and select **CSV format**
8. You will receive three separate CSV files: `Crashes`, `Parties`, `Victims`

**Where to place the files:**

Rename and move them to match these exact paths:
```
data/raw/supplemental/crashes.csv
data/raw/supplemental/parties.csv
data/raw/supplemental/victims.csv
```

**How to process them:**

Run the preprocessing script:
```bash
python scripts/00_preprocess_accidents.py
```

This merges the three tables, filters to valid coordinates within San Mateo County bounds, calculates a severity weight per crash, and saves the cleaned output to `data/raw/supplemental/accidents.csv`. That file is what all downstream scripts consume.

**Expected output:**
```
Crashes: ~971 rows
After coordinate filter: 957 crashes
Fatal crashes: 10
Cyclist involved: 141
Pedestrian involved: 61
```

**Why SWITRS:** It is the most comprehensive publicly available crash dataset for California. Maintained by CHP and distributed by UC Berkeley's SafeTREC. Unlike aggregated datasets, SWITRS provides GPS coordinates per crash, enabling direct spatial joins to the road network.

---

### Run Order After Data Collection

Once all three sources are in place, run the full pipeline in this order:

```bash
python scripts/01_download_road_network.py   # OSM road network (automatic)
python scripts/02a_prepare_sample_points.py  # Generate Street View sample coordinates
python scripts/02b_streetview_distress.py    # Fetch images + score distress (takes 30–60 min)
python scripts/02c_aggregate_distress.py     # Average scores to segment level
python scripts/03_osm_complexity.py          # Score behavioral complexity from OSM attributes
python scripts/00_preprocess_accidents.py    # Clean and weight SWITRS crash data
python scripts/04_spatial_join.py            # Attach all three layers to road network
python scripts/05_risk_scoring.py            # Normalize, weight, and score each segment
python scripts/06_hotspot_analysis.py        # Getis-Ord Gi* spatial statistics
python scripts/07_build_webmap.py            # Build interactive HTML map
python scripts/08_summary_stats.py           # Charts and summary report
```

Scripts 02b is the only one that takes significant time — it makes one API call per sample point. All other scripts complete in under 2 minutes each.

---

## Why Each Stage Was Built This Way

### Raw Data — Three Independent Signals

The index uses three data sources that were not built for this purpose. That is deliberate. When three independent signals — one visual, one structural, one historical — all flag the same street, that convergence is the finding.

**Street View** answers: what does this road look like right now?
**OpenStreetMap** answers: what kind of driving environment is this?
**SWITRS** answers: what has already gone wrong here?

No single source is reliable on its own. A road can look clean, be structurally complex, and have a fatal crash history. The composite sees all three.

---

### 02a — Sample Points

A road segment is a line. A camera needs a GPS coordinate and a direction.

Every segment is divided into stops — one every 50 metres. At each stop the script calculates two things: where the camera sits, and which direction it faces along the road. That heading calculation is what keeps the camera looking at the road surface instead of perpendicular to it.

5,690 sample points generated across 974 unique segments. 99.9% Street View coverage.

---

### 02b — Street View Distress Scoring

The image is cropped to the bottom 40% — that is where the road surface appears when the camera is angled down at –45°. Three metrics are measured independently and combined:

| Metric | Weight | What it detects |
|---|---|---|
| Edge density | 0.40 | Cracks — distress lines create edges a healthy surface does not |
| Texture variance | 0.35 | Roughness — deteriorated surfaces have higher pixel variance |
| Dark patch ratio | 0.25 | Crack shadows — cracks appear as dark linear features |

No single metric is reliable alone. Edge detection fires on shadows. Texture variance fires on painted markings. The three-metric combination filters false positives that any individual signal would produce.

Output: one `distress_score` from 0 (pristine) to 1 (failed) per image.

---

### 02c — Aggregate to Segment

One photo is an observation. Five photos of the same street is a measurement.

Each sample point is scored individually, then aggregated to segment level: mean, max, and standard deviation. Segments with fewer than two samples are flagged as less reliable — a high score on a single image is a candidate; a consistent high score across six images is a finding.

---

### 03 — OSM Behavioral Complexity

Behavioral complexity is a measure of how many different kinds of agents an AV will encounter — vehicles, pedestrians, cyclists, turning movements.

OSM road attributes are the structural predictors of that agent density. Highway classification, lane count, speed limits, and directionality each contribute to a base complexity score. The hierarchy is built into the data: a pedestrian street scores 0.80 (maximum unpredictability), a residential street scores 0.30 (low speed, mostly cars).

| Highway type | Base score | Why |
|---|---|---|
| Pedestrian / living street | 0.80 | Maximum mixed-agent environment |
| Primary | 0.70 | High traffic, signals, turning movements |
| Secondary | 0.65 | Mixed traffic, transitional environment |
| Residential | 0.30 | Low speed, mostly cars, predictable |

Lane factor, oneway factor, and speed factor apply as multipliers. A four-lane primary road scores higher than a two-lane primary road — correctly, because the agent interaction space is wider.

---

### 00 — Preprocess Accidents

Raw SWITRS data contains three tables: Crashes, Parties, and Victims. The preprocessing step cleans, filters to valid San Mateo County coordinates, and calculates a severity weight per crash.

**The key design decision:** a fatal crash is not the same risk signal as a fender bender.

| Severity | Weight |
|---|---|
| Fatal | 3.0 |
| Severe injury | 2.0 |
| Other injury | 1.0 |
| Property damage only | 1.0 |

Raw accident counts are misleading. A busy intersection accumulates minor incidents. A quiet residential street can have one fatal crash. Severity weighting preserves the distinction that matters for AV risk assessment.

957 crashes processed. 10 fatal. 141 cyclist involved. 61 pedestrian involved.

---

### 04 — Spatial Join

Three datasets. Three different shapes. Three different scales. Script 04 attaches all of them to the same road segment using the right join method for each data type.

**JOIN 1 — distress:** direct merge on `osmid`. Distress is already at segment level — no geometry needed. 99.9% coverage.

**JOIN 2 — complexity:** `sjoin_nearest` with a 100-metre search radius. OSM centroids sit at the middle of long segments — 100 m provides enough slack to match correctly without pulling from the wrong street. 99.1% coverage.

**JOIN 3 — accidents:** `sjoin_nearest` with a 30-metre search radius. Tight attribution matters here — a crash at one intersection should not inflate the score of a parallel street two blocks over.

Missing distress values are imputed to the city median, not zero. Zero imputation would artificially pull risk scores down for segments without Street View coverage.

---

### 05 — Risk Scoring

Three numbers on different scales measuring different things. The scoring stage normalises, weights, and combines them into one comparable risk score per segment.

**Outlier cap:** accident counts are capped at the 95th percentile before normalisation. Without this, a single segment with 75 accidents causes MinMaxScaler to divide all other values by 75 — a segment with 5 accidents scores 0.067 instead of reflecting its actual risk level. Capping preserves the signal.

**Weights:**

| Component | Weight | Rationale |
|---|---|---|
| Behavioral complexity | **40%** | AV research consistently identifies prediction failure in dense multi-agent environments as the leading incident cause. This is the most AV-specific signal in the index. |
| Pavement distress | **35%** | Real risk factor, but Menlo Park is a well-funded city with well-maintained roads. Low variance in this layer. |
| Accident history | **25%** | Retrospective data. Undercounts near-misses. A road can be genuinely dangerous without a recorded crash yet. Still essential — historical pattern is a real signal. |

**Risk tiers:** percentile-based, not fixed bins.

| Tier | Percentile range | Segments |
|---|---|---|
| Low | 0 – 40th | 992 |
| Moderate | 40th – 70th | 744 |
| High | 70th – 90th | 511 |
| Critical | Top 10% | 233 |

Fixed bins cluster poorly when scores compress. Percentile tiers guarantee all four categories are meaningfully populated regardless of distribution shape.

Each segment also receives a `dominant_factor` tag — Surface Condition, Behavioral Complexity, or Accident History — identifying which component is driving that segment's score. This is what tells a decision-maker whether a high-risk street is a resurfacing problem, a routing problem, or a crash history problem.

---

### 06 — Getis-Ord Gi* Hotspot Analysis

A high-scoring segment could be a data anomaly. Gi* answers a different question: is this segment's score higher than you would expect by chance, given what its neighbours score?

A single bad street could be noise. A cluster of bad streets is a systemic problem. Gi* is the statistical tool that tells the difference.

**Spatial weights:** 300-metre distance band — roughly one city block in Menlo Park's road grid. Each segment has an average of 51.1 neighbours. Row-standardised so all neighbours within 300 m contribute equally regardless of exact distance.

**Permutation testing:** 999 random permutations per segment. Each segment receives a z-score and a p-value. At 99% confidence there is a 1-in-100 chance the cluster happened by accident.

**This is what separates a risk map from a hotspot map.** A risk map shows you scores. A hotspot map shows you where elevated scores are spatially correlated — where the problem is systemic, not isolated.

| Classification | Segments |
|---|---|
| Hot Spot (99%) | 158 |
| Hot Spot (95%) | 78 |
| Hot Spot (90%) | 120 |
| Not Significant | 1,652 |
| Cold Spot | 472 |

---

## Results

**Highest risk corridor:** Willow Road — risk score 0.68, Behavioral Complexity dominant. Major connector to Highway 101, high throughput, mixed traffic. Not a pavement problem. A routing problem.

**Confirmed hotspot corridor:** Santa Cruz Avenue — risk score 0.66, Hot Spot 99% confirmed. Downtown Menlo Park. Angled parking on both sides. Cyclists from the trail. Pedestrians mid-block. Three independent signals converged on the same street without any manual input.

**Dominant driver across the city:** Behavioral Complexity drives 1,897 of 2,480 segments. Menlo Park's roads are well-maintained. The risk is environmental, not structural.

---

## Stack

| Tool | Role |
|---|---|
| Python 3.10 | Pipeline orchestration |
| GeoPandas | Spatial data processing |
| OSMnx | Road network download |
| OpenCV | Computer vision distress scoring |
| scikit-learn | MinMaxScaler normalisation |
| esda / libpysal | Getis-Ord Gi* hotspot analysis |
| Folium | Interactive web map |
| SWITRS | Historical crash records |

---

## Project Structure

```
av_risk_index/
├── scripts/
│   ├── config.py
│   ├── 00_preprocess_accidents.py
│   ├── 01_download_road_network.py
│   ├── 02a_prepare_sample_points.py
│   ├── 02b_streetview_distress.py
│   ├── 02c_aggregate_distress.py
│   ├── 03_osm_complexity.py
│   ├── 04_spatial_join.py
│   ├── 05_risk_scoring.py
│   ├── 06_hotspot_analysis.py
│   ├── 07_build_webmap.py
│   └── 08_summary_stats.py
├── outputs/
│   ├── maps/
│   │   └── av_risk_index_map.html   ← final deliverable
│   └── charts/
│       └── summary_charts.png
└── run_pipeline.py
```

---


## Summary Charts
<img width="2085" height="1475" alt="summary_charts" src="https://github.com/user-attachments/assets/11fac44c-fb48-4baf-8bff-503bb5548ac8" />

