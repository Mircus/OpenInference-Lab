"""Run: python -m openinference.demo (works entirely offline)."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import pathlib
import urllib.request
from .core import evaluate, record_hash
from .verify import audit
from .ui import render_html

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "usgs_snapshot.json"
MANIFEST = ROOT / "data" / "source_manifest.json"
OUT = ROOT / "reports"
FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"


def load_snapshot():
    return json.loads(SOURCE.read_text(encoding="utf8"))


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf8"))["record_hashes"]


def inject_corruption(snapshot):
    data = copy.deepcopy(snapshot)
    items = data["records"]
    # All edits are LAB FIXTURES. Never presented as genuine USGS reports.
    items[0]["lat"] = 128.2                         # out-of-range location
    items[0]["injected_fixture"] = "bad_latitude"
    items[1]["mag"] = 8.8                          # plausible format, false source value
    items[1]["injected_fixture"] = "magnitude_tamper"
    items[2]["updated_ms"] = items[2]["time_ms"] - 100000
    items[2]["injected_fixture"] = "impossible_update_time"
    cloned = copy.deepcopy(items[3])
    cloned["id"] = "trainingduplicate0001"
    cloned["lon"] += 0.002
    cloned["time_ms"] += 30000
    cloned["updated_ms"] += 30000
    cloned["injected_fixture"] = "fabricated_duplicate_record"
    items.append(cloned)
    data["dataset"] = "INJECTED LAB FIXTURES — NOT A USGS FEED"
    data["sample_method"] += " Four deliberately corrupted/fabricated values for student exercise."
    return data


def run():
    OUT.mkdir(exist_ok=True)
    baseline = load_snapshot()
    hashes = load_manifest()
    results = {}
    for scenario, records in (("clean", baseline), ("adversarial", inject_corruption(baseline))):
        result = evaluate(records, hashes)
        result["audit"] = audit(result, records, hashes)
        result["scenario"] = scenario
        (OUT / f"{scenario}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf8")
        results[scenario] = result
    dashboard = render_html(results)
    (OUT / "index.html").write_text(dashboard, encoding="utf8")
    print("\nOpenInference Lab — reproducible investigation demonstration")
    for name, item in results.items():
        print(f"{name:12s} records={item['summary']['records']:2d} quarantined={item['summary']['quarantined']:2d} "
              f"clusters={item['summary']['clusters']} independent_audit={item['audit']['status']}")
    print("Dashboard: reports/index.html  (open in any browser; no server needed)")
    print("Only a teaching exercise. This software is NOT a USGS product or hazard service.\n")


def fetch_latest():
    """Optional, user-invoked fresh-data acquisition, not used for frozen demo."""
    req = urllib.request.Request(FEED_URL, headers={"User-Agent":"OpenInferenceLab/0.1 educational use"})
    with urllib.request.urlopen(req, timeout=20) as reply:
        raw = json.load(reply)
    sampled = raw["features"][:60]
    records = []
    for feat in sampled:
        pr, geo = feat["properties"], feat["geometry"]
        if geo is None or geo.get("type") != "Point" or len(geo["coordinates"]) < 3:
            continue
        lon, lat, depth = geo["coordinates"][:3]
        records.append({"id":feat["id"],"mag":pr.get("mag"),"place":pr.get("place"),
                        "time_ms":pr.get("time"),"updated_ms":pr.get("updated"),
                        "lon":lon,"lat":lat,"depth_km":depth,"status":pr.get("status"),
                        "net":pr.get("net"),"nst":pr.get("nst"),"gap":pr.get("gap"),"rms":pr.get("rms")})
    output = {"dataset":"LIVE USGS MAG 4.5+ — first 60 records", "source_url":FEED_URL,
              "source_generated_ms":raw["metadata"]["generated"], "source_total_records":raw["metadata"]["count"],
              "sample_size":len(records),"sample_method":"First 60 records, not representative sample", "records": records}
    # Fresh feed has a different baseline; do not silently redefine frozen manifest.
    out = OUT / "live_download.json"
    out.write_text(json.dumps(output, indent=2), encoding="utf8")
    print(f"Saved {len(records)} live USGS events to {out}. Not merged into frozen benchmark.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-live", action="store_true", help="Download current USGS data (requires network)")
    args = parser.parse_args()
    if args.fetch_live:
        fetch_latest()
    else:
        run()
