"""
Derive per-pod aspect and elevation from public terrain data.

Why this exists: aspect and elevation are two of the four terrain-profile fields the domain model
leaves `unsourced`, and they are the inputs to most of the scoring physics. The retired catalog
guessed them. This computes them instead, from two free sources with no key and no account:

  * run geometry — OpenStreetMap `piste:type=downhill` ways over the Snowmass bounding box
  * elevation    — AWS Terrain Tiles (terrarium-encoded PNG), the Mapzen/AWS open elevation set

The join to pods is Aspen's own: an OSM run is matched by name to a run in the recorded grooming
feed, and the feed already says which pod that run belongs to. No new pod-name mapping is created.

Aspect is taken from the fall line, not from a DEM gradient. A ski run's polyline *is* a descent
path, so the bearing from the upper end of a segment to its lower end is the direction that slope
faces. Each segment contributes to the pod's aspect histogram weighted by its vertical drop, so the
steep pitches that decide how a pod skis count for more than flat runouts.

Offline, run once a season. Python rather than TypeScript because it decodes PNGs and does tile
math; the output is JSON that the TypeScript catalog consumes.

    python3 domain/derive/terrain.py            # uses cached fixtures + tile cache
    python3 domain/derive/terrain.py --refresh  # re-fetch OSM and re-download tiles
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent.parent
FIXTURES = REPO / "domain" / "fixtures"
TILE_CACHE = FIXTURES / "terrain-tiles"
OSM_FIXTURE = FIXTURES / "osm-pistes.json"
FOREST_FIXTURE = FIXTURES / "osm-forest.json"
GROOMING_FIXTURE = FIXTURES / "grooming-feed.2026-08-22.json"
OUT = FIXTURES / "terrain-derived.json"

# Snowmass ski area, generous enough to catch every piste including Burnt Mountain.
BBOX = (39.17, -107.00, 39.27, -106.90)  # south, west, north, east
ZOOM = 14  # ~9.5 m/px at this latitude — finer than the pod-level question needs
FLANK_M = 40.0  # how far off the centreline to look for trees
TPI_RADIUS_M = 300.0  # ridge-vs-gully scale: wide enough to see the landform, not the pitch
FEET_PER_METRE = 3.280839895

NON_SKI_GROUPS = {"Uphill Routes", "Hike/XC Bike Trails", "Lost Forest"}
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

OVERPASS = "https://overpass-api.de/api/interpreter"
TERRARIUM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


# --------------------------------------------------------------------------- sources


def fetch_osm(refresh: bool) -> dict:
    if OSM_FIXTURE.exists() and not refresh:
        return json.loads(OSM_FIXTURE.read_text())
    south, west, north, east = BBOX
    query = f"""[out:json][timeout:90];
(
  way["piste:type"="downhill"]({south},{west},{north},{east});
  way["aerialway"]({south},{west},{north},{east});
);
out tags geom;"""
    req = urllib.request.Request(OVERPASS, data=query.encode(), method="POST")
    payload = json.loads(urllib.request.urlopen(req, timeout=120).read())
    OSM_FIXTURE.write_text(json.dumps(payload, indent=1, sort_keys=True))
    return payload


def fetch_forest(refresh: bool) -> dict:
    if FOREST_FIXTURE.exists() and not refresh:
        return json.loads(FOREST_FIXTURE.read_text())
    south, west, north, east = BBOX
    query = f"""[out:json][timeout:120];
(
  way["natural"="wood"]({south},{west},{north},{east});
  way["landuse"="forest"]({south},{west},{north},{east});
);
out tags geom;"""
    req = urllib.request.Request(OVERPASS, data=query.encode(), method="POST")
    payload = json.loads(urllib.request.urlopen(req, timeout=180).read())
    FOREST_FIXTURE.write_text(json.dumps(payload, indent=1, sort_keys=True))
    return payload


class Forest:
    """Point-in-forest tests against OSM wood/forest polygons, bounding-box indexed.

    Ski runs are cut through the trees, so a point ON a run is usually outside every polygon
    even on a thickly wooded pod. What decides whether a pod skis well in flat light is whether
    there are trees BESIDE you, so the useful question is asked a short way off the centreline.
    """

    def __init__(self, payload: dict) -> None:
        self.polys: list[tuple[float, float, float, float, list[tuple[float, float]]]] = []
        for el in payload.get("elements", []):
            geom = el.get("geometry") or []
            if len(geom) < 4:
                continue
            pts = [(p["lat"], p["lon"]) for p in geom]
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]
            self.polys.append((min(lats), min(lons), max(lats), max(lons), pts))

    def contains(self, lat: float, lon: float) -> bool:
        for s_lat, s_lon, n_lat, n_lon, pts in self.polys:
            if not (s_lat <= lat <= n_lat and s_lon <= lon <= n_lon):
                continue
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                yi, xi = pts[i]
                yj, xj = pts[j]
                if (yi > lat) != (yj > lat):
                    if lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi:
                        inside = not inside
                j = i
            if inside:
                return True
        return False


def tpi(dem: "Elevation", lat: float, lon: float, radius: float = TPI_RADIUS_M) -> float:
    """Topographic position index, metres: this point's height above its own surroundings.

    Positive means a convex landform — a ridge or shoulder, where wind strips snow away and
    flat light has nothing to bounce off. Negative means concave — a gully or bowl that collects
    wind-drifted snow and shelters you. This is the physical thing the retired catalog was
    reaching for when it hand-labelled pods `low`, `medium`, `high` exposure.
    """
    here = dem.metres(lat, lon)
    ring = []
    for b in range(0, 360, 45):
        r_lat, r_lon = offset(lat, lon, float(b), radius)
        ring.append(dem.metres(r_lat, r_lon))
    return here - (sum(ring) / len(ring))


def offset(lat: float, lon: float, bearing_deg: float, metres: float) -> tuple[float, float]:
    r = 6371000.0
    b = math.radians(bearing_deg)
    dlat = math.degrees((metres / r) * math.cos(b))
    dlon = math.degrees((metres / (r * math.cos(math.radians(lat)))) * math.sin(b))
    return lat + dlat, lon + dlon


class Elevation:
    """Terrarium tiles, cached on disk. elevation_m = (R*256 + G + B/256) - 32768."""

    def __init__(self, zoom: int, refresh: bool) -> None:
        self.zoom = zoom
        self.refresh = refresh
        self._tiles: dict[tuple[int, int], Image.Image] = {}
        TILE_CACHE.mkdir(parents=True, exist_ok=True)

    def _tile_xy(self, lat: float, lon: float) -> tuple[float, float]:
        n = 2**self.zoom
        x = (lon + 180.0) / 360.0 * n
        lat_rad = math.radians(lat)
        y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        return x, y

    def _tile(self, tx: int, ty: int) -> Image.Image:
        key = (tx, ty)
        if key in self._tiles:
            return self._tiles[key]
        path = TILE_CACHE / f"{self.zoom}-{tx}-{ty}.png"
        if not path.exists() or self.refresh:
            url = TERRARIUM.format(z=self.zoom, x=tx, y=ty)
            path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        image = Image.open(io.BytesIO(path.read_bytes())).convert("RGB")
        self._tiles[key] = image
        return image

    def metres(self, lat: float, lon: float) -> float:
        x, y = self._tile_xy(lat, lon)
        tile = self._tile(int(x), int(y))
        px = min(int((x % 1) * 256), 255)
        py = min(int((y % 1) * 256), 255)
        r, g, b = tile.getpixel((px, py))
        return (r * 256 + g + b / 256) - 32768


# --------------------------------------------------------------------------- joining


def normalise(name: str) -> str:
    """Aspen writes `Banzai (Lower)`; OSM writes `Lower Banzai`. Collapse both to one key.

    The qualifier is CANONICALISED, never deleted. Deleting it merges `Campground (Lower)` with
    `Campground (Upper)` — and those two sit in different pods, so a single key would hand one
    pod's geometry to another. That is the same crossed-identity failure `docs/adr/0001` exists
    to remove, and the feed contains four such pairs: Campground, Green Cabin, Slot, Wildcat.
    """
    s = name.lower()
    qualifier = ""
    for token in ("lower", "upper", "middle"):
        if re.search(rf"\b{token}\b", s):
            qualifier = token
            s = re.sub(rf"\b{token}\b", " ", s)
            break
    s = re.sub(r"[^a-z0-9]+", "", s)
    return f"{s}:{qualifier}" if qualifier else s


def assert_no_cross_pod_collisions(run_to_pod: dict[str, str]) -> None:
    """A normalised key that maps to two pods would silently misassign geometry. Fail loudly."""
    buckets: dict[str, set[str]] = defaultdict(set)
    for run, pod in run_to_pod.items():
        buckets[normalise(run)].add(pod)
    crossed = {key: pods for key, pods in buckets.items() if len(pods) > 1}
    if crossed:
        detail = "; ".join(f"{key} -> {sorted(pods)}" for key, pods in sorted(crossed.items()))
        raise SystemExit(f"normalise() collides across pods, refusing to derive: {detail}")


def aspen_run_to_pod() -> dict[str, str]:
    feed = json.loads(GROOMING_FIXTURE.read_text())
    out: dict[str, str] = {}
    for area in feed["areas"]:
        if area["name"] in NON_SKI_GROUPS:
            continue
        for trail in area["trails"]:
            out[trail["name"].strip()] = area["name"]
    return out


# --------------------------------------------------------------------------- geometry


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial great-circle bearing, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def compass_of(deg: float) -> str:
    return COMPASS[int((deg + 22.5) % 360 // 45)]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-fetch OSM and re-download tiles")
    args = ap.parse_args()

    osm = fetch_osm(args.refresh)
    dem = Elevation(ZOOM, args.refresh)
    forest = Forest(fetch_forest(args.refresh))
    run_to_pod = aspen_run_to_pod()
    assert_no_cross_pod_collisions(run_to_pod)
    lookup = {normalise(k): (k, v) for k, v in run_to_pod.items()}

    # An OSM name with no Lower/Upper qualifier cannot match a qualified key directly. Accept it
    # only when every qualified variant of that base sits in ONE pod, so the assignment is
    # unambiguous; where the variants straddle two pods, leave it unmatched rather than guess.
    base_pods: dict[str, set[str]] = defaultdict(set)
    base_entry: dict[str, tuple[str, str]] = {}
    for run, pod in run_to_pod.items():
        base = normalise(run).split(":")[0]
        base_pods[base].add(pod)
        base_entry.setdefault(base, (run, pod))
    unqualified = {
        base: base_entry[base] for base, pods in base_pods.items()
        if len(pods) == 1 and base not in lookup
    }

    pods: dict[str, dict] = defaultdict(
        lambda: {
            "aspect_drop_m": defaultdict(float),
            "elev_m": [],
            "runs": [],
            "segments": 0,
            "flank_treed": 0,
            "flank_tests": 0,
            "on_run_treed": 0,
            "on_run_tests": 0,
            "tpi_len": 0.0,
            "tpi_wsum": 0.0,
            "flank_len": 0.0,
            "flank_treed_len": 0.0,
        }
    )
    unmatched: list[str] = []

    for way in osm["elements"]:
        tags = way.get("tags", {})
        if tags.get("piste:type") != "downhill":
            continue
        name = (tags.get("name") or "").strip()
        geom = way.get("geometry") or []
        if not name or len(geom) < 2:
            continue
        key = normalise(name)
        hit = lookup.get(key) or unqualified.get(key.split(":")[0])
        if hit is None:
            unmatched.append(name)
            continue
        aspen_name, pod = hit
        pod_rec = pods[pod]
        if aspen_name not in pod_rec["runs"]:
            pod_rec["runs"].append(aspen_name)

        elevs = [dem.metres(pt["lat"], pt["lon"]) for pt in geom]
        pod_rec["elev_m"].extend(elevs)

        for i in range(len(geom) - 1):
            a, b = geom[i], geom[i + 1]
            ea, eb = elevs[i], elevs[i + 1]
            drop = abs(ea - eb)
            if drop < 1.0:  # flat traverse or runout: carries no aspect signal
                continue
            if haversine_m(a["lat"], a["lon"], b["lat"], b["lon"]) < 5.0:
                continue
            # The slope faces the way it descends: order the pair high point first.
            hi, lo = (a, b) if ea > eb else (b, a)
            deg = bearing(hi["lat"], hi["lon"], lo["lat"], lo["lon"])
            pod_rec["aspect_drop_m"][compass_of(deg)] += drop
            pod_rec["segments"] += 1

            # Trees: ask beside the run, not on it. A cut run sits outside every forest
            # polygon whether or not it is bordered by timber.
            mid_lat = (a["lat"] + b["lat"]) / 2
            mid_lon = (a["lon"] + b["lon"]) / 2
            # Weight by segment length. OSM vertex density varies by a factor of five between
            # runs, so a plain mean over segments lets finely-mapped runs outvote long ones —
            # enough to flip a pod's sign on a scale that only spans about -13 to +9 m.
            seg_len = haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
            pod_rec["tpi_wsum"] += tpi(dem, mid_lat, mid_lon) * seg_len
            pod_rec["tpi_len"] += seg_len
            pod_rec["on_run_tests"] += 1
            if forest.contains(mid_lat, mid_lon):
                pod_rec["on_run_treed"] += 1
            for side in (deg - 90.0, deg + 90.0):
                f_lat, f_lon = offset(mid_lat, mid_lon, side % 360.0, FLANK_M)
                pod_rec["flank_tests"] += 1
                pod_rec["flank_len"] += seg_len
                if forest.contains(f_lat, f_lon):
                    pod_rec["flank_treed"] += 1
                    pod_rec["flank_treed_len"] += seg_len

    result = {}
    for pod, rec in sorted(pods.items()):
        drops = rec["aspect_drop_m"]
        total = sum(drops.values())
        if total <= 0 or not rec["elev_m"]:
            continue
        shares = {k: v / total for k, v in sorted(drops.items(), key=lambda kv: -kv[1])}
        dominant = next(iter(shares))
        # "Present" = an aspect holding at least a tenth of the pod's vertical. Below that it is
        # a handful of segments, not a face anyone would notice skiing it.
        present = [k for k, v in shares.items() if v >= 0.10] or [dominant]
        result[pod] = {
            "aspect": {
                "dominant": dominant,
                "present": present,
                "share_by_aspect": {k: round(v, 4) for k, v in shares.items()},
            },
            "elevation": {
                "bottom_ft": round(min(rec["elev_m"]) * FEET_PER_METRE),
                "top_ft": round(max(rec["elev_m"]) * FEET_PER_METRE),
            },
            "tree_cover": {
                "flanking": round(rec["flank_treed_len"] / rec["flank_len"], 3)
                if rec["flank_len"]
                else None,
                "on_centreline": round(rec["on_run_treed"] / rec["on_run_tests"], 3)
                if rec["on_run_tests"]
                else None,
                "samples": rec["flank_tests"],
            },
            "exposure": {
                "mean_tpi_m": round(rec["tpi_wsum"] / rec["tpi_len"], 1) if rec["tpi_len"] else None,
                "samples": rec["segments"],
            },
            "coverage": {
                "runs_matched": len(rec["runs"]),
                "segments_used": rec["segments"],
                "vertical_sampled_ft": round(total * FEET_PER_METRE),
            },
        }

    payload = {
        "generated_by": "domain/derive/terrain.py",
        "sources": {
            "geometry": {
                "name": "OpenStreetMap piste:type=downhill",
                "endpoint": OVERPASS,
                "bbox": {"south": BBOX[0], "west": BBOX[1], "north": BBOX[2], "east": BBOX[3]},
                "licence": "ODbL 1.0 — attribution required if shown to users",
            },
            "elevation": {
                "name": "AWS Terrain Tiles (terrarium)",
                "endpoint": TERRARIUM,
                "zoom": ZOOM,
                "approx_ground_resolution_m": 9.5,
            },
            "landcover": {
                "name": "OpenStreetMap natural=wood + landuse=forest",
                "endpoint": OVERPASS,
                "flank_distance_m": FLANK_M,
            },
            "pod_membership": {
                "name": "Aspen grooming feed, recorded",
                "fixture": str(GROOMING_FIXTURE.relative_to(REPO)),
            },
        },
        "method": {
            "aspect": "Bearing from the higher to the lower end of each run segment, weighted by that segment's vertical drop. Segments dropping under 1 m or shorter than 5 m are discarded as carrying no aspect signal.",
            "elevation": "Min and max sampled elevation over every matched run vertex in the pod.",
            "exposure": f"Length-weighted mean topographic position index over run segments: the point's elevation minus the mean elevation of eight points {TPI_RADIUS_M:.0f} m around it. Positive is convex terrain that sheds snow to wind; negative is concave terrain that collects it.",
            "tree_cover": f"Share of run length whose flanking points {FLANK_M:.0f} m to either side fall inside an OpenStreetMap wood or forest polygon, weighted by segment length. Measured beside the run rather than on it, because a cut run sits outside every polygon regardless of the timber around it. `on_centreline` is reported alongside as the control.",
        },
        "unmatched_osm_runs": sorted(set(unmatched)),
        "pods": result,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"{len(result)} pods derived -> {OUT.relative_to(REPO)}")
    print(f"{'POD':<16}{'elev ft':>16}  {'dom':<4}{'present':<16}{'trees':>7}{'TPI m':>8}  runs")
    for pod, r in result.items():
        e, a, c, t = r["elevation"], r["aspect"], r["coverage"], r["tree_cover"]
        print(
            f"{pod:<16}{e['bottom_ft']:>7,}-{e['top_ft']:<8,}  {a['dominant']:<4}"
            f"{','.join(a['present']):<16}{t['flanking']:>7.2f}{r['exposure']['mean_tpi_m']:>8.1f}"
            f"  {c['runs_matched']:>3}"
        )
    if unmatched:
        print(f"\n{len(set(unmatched))} OSM runs unmatched: {', '.join(sorted(set(unmatched))[:12])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
