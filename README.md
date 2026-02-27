# AV Road Risk Index
**Menlo Park, CA** &nbsp;|&nbsp; Street View CV &nbsp;×&nbsp; OSM Complexity &nbsp;×&nbsp; SWITRS Crashes &nbsp;×&nbsp; Getis-Ord Gi*

---

## What This Is

Every drivable street in Menlo Park — all **2,480 segments** — scored and ranked by navigational risk for an autonomous vehicle.

Three independent data sources. One composite score per segment. A statistically validated map of where AV operations face the highest combined risk — and what kind of risk it is.

---

## Map Preview

<img width="1914" height="1068" alt="AV_Risk_Map png" src="https://github.com/user-attachments/assets/f660ff88-0621-4128-ae5d-d1192e7a4684" />


---

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

**Cost:** Google provides $200 free monthly credit. Each Street View image costs $0.007. Menlo Park requires approximately 5,690 images — total cost around $40, covered by the free tier with credit to spare.

**What gets downloaded:** One JPEG per sample point, cached locally in `data/streetview_images/`. If the pipeline is interrupted and restarted, already-downloaded images are skipped automatically.

---

### 2 — OpenStreetMap via OSMnx

**What it provides:** The complete drivable road network for Menlo Park — every segment with attributes including highway classification, lane count, speed limit, and directionality. No download required. The pipeline fetches it automatically.

**Where to get it:** Script `01_download_road_network.py` handles this entirely:

```bash
python scripts/01_download_road_network.py
```

This saves the road network to `data/raw/road_network/menlo_park_streets.gpkg`. Takes about 30 seconds.

---

### 3 — SWITRS Crash Records

**What it provides:** Every recorded collision in San Mateo County from 2018 to 2023 — crashes, parties, and victims. Used to score historical accident risk per road segment.

**Where to get it:**

1. Go to [tims.berkeley.edu](https://tims.berkeley.edu)
2. Click **SWITRS Query** → create a free account → log in
3. Set filters: County = San Mateo | Years = 2018–2023 | All collision types
4. Click **Submit Query** → wait 2–5 minutes → **Download as CSV**
5. You will receive three files: `Crashes`, `Parties`, `Victims`

**Where to place the files:**
```
data/raw/supplemental/crashes.csv
data/raw/supplemental/parties.csv
data/raw/supplemental/victims.csv
```

Then run:
```bash
python scripts/00_preprocess_accidents.py
```

---

### Run Order After Data Collection

```bash
python scripts/01_download_road_network.py
python scripts/02a_prepare_sample_points.py
python scripts/02b_streetview_distress.py      # 30–60 min — API calls
python scripts/02c_aggregate_distress.py
python scripts/03_osm_complexity.py
python scripts/00_preprocess_accidents.py
python scripts/04_spatial_join.py
python scripts/05_risk_scoring.py
python scripts/06_hotspot_analysis.py
python scripts/07_build_webmap.py
python scripts/08_summary_stats.py
```

---

## Pipeline — Stage by Stage

---

### 01 — Download Road Network

Downloads the complete Menlo Park drivable road network from OpenStreetMap.

```bash
python scripts/01_download_road_network.py
```

**Expected output:**
```
Downloading Menlo Park road network from OpenStreetMap...
Done. Saved 2480 road segments to data/raw/road_network/menlo_park_streets.gpkg
Road types found: {'residential': 1402, 'secondary': 387, 'tertiary': 312,
                   'primary': 198, 'unclassified': 89, 'living_street': 42}
```

**Output:** `data/raw/road_network/menlo_park_streets.gpkg`

---

### 02a — Sample Points

A road segment is a line. A camera needs a GPS coordinate and a direction. Every segment is divided into stops — one every 50 metres. At each stop the script calculates where the camera sits and which direction it faces along the road.

```bash
python scripts/02a_prepare_sample_points.py
```

**Expected output:**
```
Loading road network...
Loaded 2480 road segments
Generated 5690 sample points across 974 unique segments
```

**Output:** `data/processed/sample_points.gpkg`

---

### 02b — Street View Distress Scoring

The image is cropped to the bottom 40% — that is where the road surface appears when the camera is angled down at –45°. Three metrics are measured and combined.

**Formula:**
```
distress_score = (edge_density × 0.40) + (texture_variance × 0.35) + (dark_patch_ratio × 0.25)
```

| Metric | Weight | What it detects |
|---|---|---|
| Edge density | 0.40 | Cracks — distress lines create edges a healthy surface does not |
| Texture variance | 0.35 | Roughness — deteriorated surfaces have higher pixel variance |
| Dark patch ratio | 0.25 | Crack shadows — cracks appear as dark linear features |

No single metric is reliable alone. Edge detection fires on shadows. Texture variance fires on painted markings. The three-metric combination filters false positives that any individual signal would produce.

```bash
python scripts/02b_streetview_distress.py
```

**Expected output:**
```
Processing 5690 sample points...
Complete: 5688 scored | 2 no coverage | 0 errors

count    5688.000000
mean        0.068200
std         0.044100
min         0.006200
max         0.412000
```

**Output:** `data/processed/streetview_distress_raw.csv`

> Takes 30–60 minutes. Images cached in `data/streetview_images/` — safe to interrupt and restart.

---

### 02c — Aggregate to Segment

One photo is an observation. Five photos of the same street is a measurement. Each sample point is scored individually then aggregated: mean, max, and standard deviation per segment. Segments with fewer than two samples are flagged as less reliable.

```bash
python scripts/02c_aggregate_distress.py
```

**Expected output:**
```
Raw records: 5688 across 974 segments

Distress class distribution:
Excellent    612
Good         298
Fair          52
Poor          11
Failed         1

Reliable segments (2+ samples): 786
```

**Output:** `data/processed/streetview_distress_by_segment.csv`

---

### 03 — OSM Behavioral Complexity

Behavioral complexity measures how many different kinds of agents an AV will encounter. OSM road attributes are the structural predictors of that agent density.

**Formula:**
```
complexity = base_score × lane_factor × oneway_factor × speed_factor + noise(σ=0.02)

lane_factor    = 1.0 + (lanes - 1) × 0.08
oneway_factor  = 0.85 if one-way, else 1.0
speed_factor   = 1.0 + (speed_limit / 100)
```

| Highway type | Base score | Why |
|---|---|---|
| Pedestrian / living street | 0.80 | Maximum mixed-agent environment |
| Primary | 0.70 | High traffic, signals, turning movements |
| Secondary | 0.65 | Mixed traffic, transitional environment |
| Tertiary | 0.50 | Moderate traffic, mixed agents |
| Residential | 0.30 | Low speed, mostly cars, predictable |

```bash
python scripts/03_osm_complexity.py
```

**Expected output:**
```
Loaded 2480 road segments
Computing OSM behavioral complexity scores...

Complexity score summary:
count    2480.000000
mean        0.412000
std         0.198000
min         0.089000
max         0.891000

Saved 2480 complexity scores to data/processed/osm_complexity.csv
```

**Output:** `data/processed/osm_complexity.csv`

---

### 00 — Preprocess Accidents

Raw SWITRS data contains three tables. The preprocessing step cleans, filters to valid coordinates, and calculates a severity weight per crash.

**Formula:**
```
severity_weight = fatal × 3.0 + severe_injury × 2.0 + other_injury × 1.0 + property_damage × 1.0
```

| Severity | Weight | Rationale |
|---|---|---|
| Fatal | 3.0 | Highest consequence |
| Severe injury | 2.0 | Significant bodily harm |
| Other injury | 1.0 | Minor injury |
| Property damage only | 1.0 | Minimum baseline |

Raw counts are misleading. A busy intersection accumulates minor incidents. A quiet street can have one fatal crash. Severity weighting preserves the distinction.

```bash
python scripts/00_preprocess_accidents.py
```

**Expected output:**
```
Loading SWITRS tables...
Crashes: 971 rows | Parties: 2114 rows | Victims: 1341 rows
After coordinate filter: 957 crashes

Fatal crashes:       10
Cyclist involved:   141
Pedestrian involved: 61
Alcohol involved:    69
```

**Output:** `data/raw/supplemental/accidents.csv`

---

### 04 — Spatial Join

Three datasets. Three different shapes. Three different scales. Script 04 attaches all of them to the same road segment using the right join method for each data type.

**JOIN 1 — distress:** direct merge on `osmid`. Already at segment level — no geometry needed. 99.9% coverage.

**JOIN 2 — complexity:** `sjoin_nearest` at 100-metre radius. OSM centroids sit at the middle of long segments — 100 m provides enough slack to match correctly. 99.1% coverage.

**JOIN 3 — accidents:** `sjoin_nearest` at 30-metre radius. Tight attribution matters — a crash at one intersection should not inflate the score of a parallel street two blocks over.

Missing distress values are imputed to the city median, not zero.

```bash
python scripts/04_spatial_join.py
```

**Expected output:**
```
Loaded 2480 road segments
Street View coverage:  2478/2480 (99.9%)
Complexity coverage:   2458/2480 (99.1%)
Accident coverage:      657/2480 (26.5%)

Saved 2480 segments to data/processed/roads_with_features.gpkg

Feature summary:
       avg_distress  avg_complexity  accident_count
mean       0.068793        0.412000        0.960887
max        0.248945        0.891000       75.000000
```

**Output:** `data/processed/roads_with_features.gpkg`

---

### 05 — Risk Scoring

Three numbers on different scales. The scoring stage normalises, weights, and combines them into one comparable risk score per segment.

**Step 1 — Outlier cap:**
```
accident_count_capped = min(accident_count, percentile_95)
# percentile_95 = 6.0 for Menlo Park
# Prevents one segment with 75 accidents from compressing all other scores
```

**Step 2 — Normalisation (MinMaxScaler):**
```
norm_surface   = (avg_distress   - min) / (max - min)
norm_behavior  = (avg_complexity - min) / (max - min)
norm_accidents = (accident_capped - min) / (max - min)
```

**Step 3 — Composite risk score:**
```
risk_score = (norm_surface × 0.35) + (norm_behavior × 0.40) + (norm_accidents × 0.25)
```

**Weights:**

| Component | Weight | Rationale |
|---|---|---|
| Behavioral complexity | **40%** | AV research identifies prediction failure in dense multi-agent environments as the leading incident cause |
| Pavement distress | **35%** | Real risk factor, but Menlo Park is well-maintained — low variance in this layer |
| Accident history | **25%** | Retrospective data, undercounts near-misses — still an essential historical signal |

**Risk tiers** (percentile-based, not fixed bins):

| Tier | Percentile | Segments |
|---|---|---|
| Low | 0 – 40th | 992 |
| Moderate | 40th – 70th | 744 |
| High | 70th – 90th | 511 |
| Critical | Top 10% | 233 |

```bash
python scripts/05_risk_scoring.py
```

**Expected output:**
```
Capping accident count at 95th percentile: 6.0

Normalized score means:
  Surface:   0.256
  Behavior:  0.408
  Accidents: 0.127

Risk tier distribution:
Low         992 | Moderate    744 | High        511 | Critical    233

Dominant risk factors:
Behavioral Complexity    1897
Surface Condition         460
Accident History          123
```

**Output:** `data/processed/roads_risk_scored.gpkg`

---

### 06 — Getis-Ord Gi* Hotspot Analysis

A high-scoring segment could be a data anomaly. Gi* answers a different question: is this segment's score elevated relative to its neighbours — to a degree that is statistically unlikely to be random?

**Formula:**
```
         Σ(j) w_ij × x_j  -  X̄ × Σ(j) w_ij
Gi*(d) = ──────────────────────────────────────────────────────
         S × sqrt[ (n × Σ(j) w²_ij - (Σ(j) w_ij)²) / (n-1) ]

Where:
  x_j     = risk score of neighbour j
  w_ij    = spatial weight (1 if within 300m, 0 otherwise, row-standardised)
  X̄       = mean risk score across all 2,480 segments
  S       = standard deviation of all risk scores
  n       = 2,480 total segments
```

Output is a z-score and empirical p-value per segment from 999 random permutations.

**Classification thresholds:**

| z-score | p-value | Classification |
|---|---|---|
| Positive | ≤ 0.01 | Hot Spot 99% — 1-in-100 chance this is random |
| Positive | ≤ 0.05 | Hot Spot 95% — 1-in-20 chance this is random |
| Positive | ≤ 0.10 | Hot Spot 90% — 1-in-10 chance this is random |
| — | > 0.10 | Not Significant |
| Negative | ≤ 0.10 | Cold Spot — significantly lower than surroundings |

```bash
python scripts/06_hotspot_analysis.py
```

**Expected output:**
```
Mean neighbors per segment: 51.1
Running Getis-Ord Gi* (this takes a few minutes)...

Hotspot classification results:
Not Significant    1652
Cold Spot (99%)     194
Hot Spot (99%)      158
Cold Spot (95%)     140
Cold Spot (90%)     138
Hot Spot (90%)      120
Hot Spot (95%)       78
```

**Output:** `data/processed/roads_hotspot_final.gpkg`

---

### 07 — Build Web Map

```bash
python scripts/07_build_webmap.py
```

**Expected output:**
```
Loading hotspot data...
Adding 2480 road segments to map...
Map saved to outputs/maps/av_risk_index_map.html
Segments added: 2480 | Skipped: 0
```

**Output:** `outputs/maps/av_risk_index_map.html`

---

### 08 — Summary Stats

```bash
python scripts/08_summary_stats.py
```

**Expected output:**
```
Total road segments analyzed: 2480

Risk Tier Distribution:
Low 992 | Moderate 744 | High 511 | Critical 233

Dominant Risk Factors:
Behavioral Complexity 1897 | Surface Condition 460 | Accident History 123

Top 10 Highest Risk Segments (unique streets):
          name  risk_score    hotspot_class       dominant_factor
   Willow Road    0.682946  Not Significant Behavioral Complexity
Santa Cruz Ave    0.655913   Hot Spot (99%) Behavioral Complexity
University Dr     0.422476   Hot Spot (99%)   Accident History

Charts saved to outputs/charts/summary_charts.png
```

**Output:** `outputs/charts/summary_charts.png` and `outputs/reports/summary_stats.csv`

---

## What the Gi* Results Mean for Menlo Park

The Getis-Ord Gi* analysis identified **356 statistically significant hotspot segments** at 90% confidence or higher. This is not a list of streets that scored high. It is a list of streets where elevated risk is spatially concentrated — where the problem is systemic and unlikely to be random.

---

### Score vs. Cluster — The Critical Distinction

**A high risk score** means a segment's pavement condition, behavioral complexity, and accident history are elevated relative to the city average.

**A confirmed hotspot** means that segment AND its surrounding streets within 300 metres are collectively elevated — to a degree with less than a 1–10% probability of occurring by chance.

These are different findings. They require different interventions.

| Street | Risk Score | Hotspot Class | What it means |
|---|---|---|---|
| Willow Road | 0.68 | Not Significant | Highest individual score in the city. Stands alone — surrounding streets are lower-order residential roads that pull the neighbourhood average down. One specific corridor to flag for routing. |
| Santa Cruz Avenue | 0.66 | Hot Spot 99% | Slightly lower score, but the entire downtown grid around it is elevated. The whole zone is a systemic problem. |
| University Drive | 0.42 | Hot Spot 99% | Moderate score made statistically significant by a dense cluster of accident history in the surrounding area. |

---

### The Two Primary Hotspot Zones

**Zone 1 — Downtown Menlo Park (Santa Cruz Avenue corridor)**

Santa Cruz Avenue confirmed Hot Spot at 99% confidence. The surrounding downtown grid — cross streets, parallel routes, feeder roads — all elevated. Dominant factor: Behavioral Complexity. Angled parking, cyclists from the Bay Trail, pedestrian mid-block crossings, delivery vehicles. An AV operating here faces maximum agent diversity at low speed — the hardest prediction problem in the city.

**Zone 2 — University Avenue / Sand Hill Road corridor**

University Drive and Sand Hill Circle confirmed Hot Spot at 99% confidence. Dominant factor: Accident History. This corridor has a disproportionate concentration of recorded crashes — including cyclist and pedestrian involvement above baseline. The risk here is not structural complexity. It is demonstrated history.

---

### Cold Spots — Confirmed Safe Corridors

**472 segments** returned as Cold Spots — streets where risk is significantly lower than the surrounding area. These concentrate in the residential neighbourhoods east of US-101 and the lower-density western edges of the city.

Cold spots are not just the absence of risk. They are statistically confirmed low-risk corridors. For an AV operator, these are the routes to prioritise for initial deployment before expanding into the confirmed hotspot zones.

---

### Three Action Categories

| Category | Segments | Intervention |
|---|---|---|
| Hot Spot 99% | 158 | Systemic — routing restrictions, enhanced monitoring, infrastructure review. The risk is a zone, not one street. |
| Hot Spot 90–95% | 198 | Elevated — flag for operational planning, monitor incident rates. |
| High score, not significant (Willow Rd type) | varies | Targeted — specific corridor flagged, surrounding network is manageable. |
| Cold Spot | 472 | Confirmed safe — prioritise for initial AV deployment. |

The same analytical logic applies directly to Menlo Park's Street and Sidewalk Capital Improvement Program. A ranked, statistically defensible list of where to act first — that is what this index produces.

---

## Results

**Highest risk corridor:** Willow Road — risk score 0.68, Behavioral Complexity dominant. Major connector to Highway 101, high throughput, mixed traffic. Not a pavement problem. A routing problem.

**Confirmed hotspot corridor:** Santa Cruz Avenue — risk score 0.66, Hot Spot 99% confirmed. Downtown Menlo Park. Angled parking. Cyclists from the trail. Pedestrians mid-block. Three independent signals converged on the same street without any manual input.

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

