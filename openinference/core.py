"""Illustrative inference engine. NO earthquake prediction or safety classifications.

Three layers are kept distinct:
  source observations -> spatial/temporal relationships -> analyst queue decisions.
All output reasons are reproducible and linked to source record identifiers.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict

FIELDS = (
    "id", "mag", "place", "time_ms", "updated_ms", "lon", "lat",
    "depth_km", "status", "net", "nst", "gap", "rms"
)


def canonical_record(rec):
    return {name: rec.get(name) for name in FIELDS}


def record_hash(rec):
    blob = json.dumps(canonical_record(rec), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def source_link(rec):
    # Construct exclusively from a validated USGS record ID; not from untrusted URLs.
    rid = rec["id"]
    return "https://earthquake.usgs.gov/earthquakes/eventpage/" + rid


def check_fields(rec, generated_ms):
    issues = []
    rid = rec.get("id")
    if not isinstance(rid, str) or not rid or not rid.isascii() or not rid.isalnum():
        issues.append("bad_event_id")
    for k, lo, hi in (("mag", -2, 10), ("lon", -180, 180),
                      ("lat", -90, 90), ("depth_km", -20, 750)):
        val = rec.get(k)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not lo <= val <= hi:
            issues.append("invalid_" + k)
    for k in ("time_ms", "updated_ms"):
        val = rec.get(k)
        if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not 0 < val <= generated_ms + 600000:
            issues.append("invalid_" + k)
    if isinstance(rec.get("time_ms"), (int, float)) and isinstance(rec.get("updated_ms"), (int, float)):
        if rec["updated_ms"] < rec["time_ms"]:
            issues.append("update_before_event")
    for k, lo, hi in (("gap", 0, 360), ("rms", 0, 30), ("nst", 0, 10000)):
        val = rec.get(k)
        if val is not None and (isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not lo <= val <= hi):
            issues.append("invalid_" + k)
    if rec.get("status") not in ("reviewed", "automatic", "deleted"):
        issues.append("unknown_status")
    if not isinstance(rec.get("place"), str) or not rec["place"].strip():
        issues.append("missing_place")
    return issues


def haversine_km(a, b):
    x1, y1 = math.radians(a["lon"]), math.radians(a["lat"])
    x2, y2 = math.radians(b["lon"]), math.radians(b["lat"])
    h = math.sin((y2-y1)/2)**2 + math.cos(y1)*math.cos(y2)*math.sin((x2-x1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


def evidence_quality(rec, issues):
    """Transparent heuristic score, NOT a calibrated probability."""
    if issues:
        return 0.0
    quality = 0.55 + (0.15 if rec["status"] == "reviewed" else 0)
    quality += (0.10 if (rec.get("nst") or 0) >= 25 else 0)
    quality += (0.10 if rec.get("gap") is not None and rec["gap"] <= 120 else 0)
    quality += (0.10 if rec.get("rms") is not None and rec["rms"] <= 1.2 else 0)
    return round(min(1, quality), 2)


def evaluate(dataset, baseline_hashes=None):
    generated_ms = dataset["source_generated_ms"]
    records = dataset["records"]
    issues_by_id = defaultdict(list)
    by_id = defaultdict(list)
    for idx, r in enumerate(records):
        by_id[r.get("id", f"invalid_{idx}")].append(idx)
    for r in records:
        rid = r["id"]
        issues_by_id[rid] += check_fields(r, generated_ms)
        if len(by_id[rid]) > 1:
            issues_by_id[rid].append("duplicate_event_id")
        if baseline_hashes is not None:
            if rid not in baseline_hashes:
                issues_by_id[rid].append("missing_from_frozen_manifest")
            elif record_hash(r) != baseline_hashes[rid]:
                issues_by_id[rid].append("snapshot_hash_mismatch")
    # Flag possible duplicate reports, not necessarily duplicate earthquakes.
    for i, a in enumerate(records):
        for b in records[i+1:]:
            if a["id"] == b["id"]:
                continue
            if issues_by_id[a["id"]] and "invalid_lat" in issues_by_id[a["id"]]:
                continue
            if issues_by_id[b["id"]] and "invalid_lat" in issues_by_id[b["id"]]:
                continue
            try:
                close = haversine_km(a, b) < 3 and abs(a["time_ms"]-b["time_ms"]) <= 120000 and abs(a["mag"]-b["mag"]) < 0.25
            except (TypeError, ValueError, OverflowError):
                close = False
            if close:
                issues_by_id[a["id"]].append("possible_duplicate_report")
                issues_by_id[b["id"]].append("possible_duplicate_report")

    healthy = [r for r in records if not issues_by_id[r["id"]]]
    neighbors = defaultdict(list)
    graph_edges = []
    for i, a in enumerate(healthy):
        for b in healthy[i+1:]:
            if abs(a["time_ms"] - b["time_ms"]) > 24*3600*1000:
                continue
            km = haversine_km(a, b)
            if km <= 100:
                edge = {"source": a["id"], "target": b["id"], "distance_km": round(km, 1),
                        "hours_apart": round(abs(a["time_ms"]-b["time_ms"])/3600000, 2), "rule": "NEAR_IN_SPACE_AND_TIME"}
                graph_edges.append(edge)
                neighbors[a["id"]].append(b["id"])
                neighbors[b["id"]].append(a["id"])

    # Connected components are investigative neighborhoods, never causal aftershock claims.
    parent = {r["id"]: r["id"] for r in healthy}
    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for edge in graph_edges:
        parent[root(edge["source"])] = root(edge["target"])
    components = defaultdict(list)
    for r in healthy:
        components[root(r["id"])].append(r)
    clusters = []
    cluster_by_member = {}
    for members in components.values():
        if len(members) < 2:
            continue
        ids = sorted(r["id"] for r in members)
        cluster_id = "group-" + hashlib.sha1("|".join(ids).encode()).hexdigest()[:8]
        cluster = {"id": cluster_id, "members": ids, "count": len(ids),
                   "max_magnitude": max(r["mag"] for r in members),
                   "description": "Events linked by <=100 km and <=24 hours; a screening pattern, not a causal conclusion.",
                   "rule": "NEAR_IN_SPACE_AND_TIME"}
        clusters.append(cluster)
        for rid in ids:
            cluster_by_member[rid] = cluster_id

    results = []
    for r in records:
        rid = r["id"]
        issues = sorted(set(issues_by_id[rid]))
        group_id = cluster_by_member.get(rid)
        if issues:
            decision, rule = "CHECK_DATA", "DATA_INTEGRITY_FIRST"
            reason = f"Quarantined from spatial inference: {', '.join(issues)}"
        elif group_id:
            decision, rule = "INVESTIGATE_PATTERN", "NEAR_IN_SPACE_AND_TIME"
            reason = f"Connected to {len(neighbors[rid])} nearby event(s) in a 100 km / 24 h window; no causal claim."
        elif r["mag"] >= 6:
            decision, rule = "VERIFY_LARGE_RECORD", "MAGNITUDE_REVIEW_THRESHOLD"
            reason = "Magnitude >=6: independently inspect metadata and source updates; not a hazard assessment."
        else:
            decision, rule = "MONITOR", "DEFAULT_MONITOR"
            reason = "No trigger in this educational investigative rule set."
        results.append({**canonical_record(r), "source_url": (source_link(r) if baseline_hashes is None or rid in baseline_hashes else None), "sha256": record_hash(r),
                        "issues": issues, "decision": decision, "rule": rule,
                        "reason": reason, "neighbor_ids": neighbors[rid] if not issues else [],
                        "cluster_id": group_id, "evidence_ids": sorted({rid, *neighbors[rid]}) if not issues else [rid],
                        "evidence_quality": evidence_quality(r, issues),
                        "injected_fixture": bool(r.get("injected_fixture"))})
    integrity = {"passed": sum(not r["issues"] for r in results),
                 "quarantined": sum(bool(r["issues"]) for r in results),
                 "issue_count": sum(len(r["issues"]) for r in results)}
    summary = {"records": len(results), "clusters": len(clusters),
               "review_queue": sum(r["decision"] != "MONITOR" for r in results), **integrity}
    return {"meta": {k:v for k,v in dataset.items() if k != "records"},
            "records": results, "clusters": clusters, "edges": graph_edges, "summary": summary,
            "rule_set": {"near_distance_km":100, "near_time_hours":24, "large_record_magnitude":6.0},
            "claim_policy": "Event correlations do not establish causality. Decisions queue human investigation only."}
