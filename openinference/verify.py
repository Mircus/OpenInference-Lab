"""Independent checks on an inference RESULT, not reusing core's rule implementation.

This is an intentionally smaller, separate oracle. It verifies provenance closure,
spatio-temporal edges, rule-consistent decisions, source hashes, and audit integrity.
It cannot establish geophysical truth; external ground truth is still required.
"""
from __future__ import annotations
import hashlib
import json
import math


def independent_distance(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    v = math.sin(p1)*math.sin(p2) + math.cos(p1)*math.cos(p2)*math.cos(dl)
    return 6371.0088 * math.acos(max(-1, min(1, v)))


def audit(report, original, manifest):
    failures, checks = [], 0
    records = report["records"]
    originals = {r["id"]: r for r in original["records"]}
    record_by_id = {r["id"]: r for r in records}
    if len(record_by_id) != len(records):
        failures.append("Duplicate result identifiers")
    if len(originals) != len(original["records"]):
        failures.append("Duplicate source identifiers")
    links = set()
    for e in report["edges"]:
        a, b = record_by_id.get(e["source"]), record_by_id.get(e["target"])
        checks += 1
        if not a or not b:
            failures.append("Spatial edge has unknown endpoint")
            continue
        try:
            if independent_distance(a, b) > 100.01 or abs(a["time_ms"]-b["time_ms"]) > 24*3600*1000:
                failures.append(f"Unsupported spatial edge {a['id']} <-> {b['id']}")
        except (ValueError, TypeError):
            failures.append("Unverifiable edge geometry")
        links.add(frozenset((a["id"], b["id"])))
    groups = {g["id"]: set(g["members"]) for g in report["clusters"]}
    for g in report["clusters"]:
        checks += 1
        if len(g["members"]) < 2 or any(rid not in record_by_id for rid in g["members"]):
            failures.append(f"Malformed cluster {g['id']}")
    for r in records:
        checks += 6
        rid = r["id"]
        original_rec = originals.get(rid)
        if not original_rec:
            failures.append(f"Fabricated event in result: {rid}")
            continue
        # Independent canonical source comparison (not importing core hash).
        keys = ("id", "mag", "place", "time_ms", "updated_ms", "lon", "lat", "depth_km", "status", "net", "nst", "gap", "rms")
        canonical = {k: original_rec.get(k) for k in keys}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        if digest != r["sha256"]:
            failures.append(f"Source-to-result mismatch for {rid}")
        manifest_ok = manifest.get(rid) == digest
        if manifest_ok and "snapshot_hash_mismatch" in r["issues"]:
            failures.append(f"False hash error for {rid}")
        if not manifest_ok and not any(x in r["issues"] for x in ("snapshot_hash_mismatch", "missing_from_frozen_manifest")):
            failures.append(f"Undetected source change for {rid}")
        if not set(r["evidence_ids"]).issubset(record_by_id):
            failures.append(f"Dangling evidence reference for {rid}")
        if rid not in r["evidence_ids"]:
            failures.append(f"Missing primary evidence for {rid}")
        if r["issues"] and r["decision"] != "CHECK_DATA":
            failures.append(f"Invalid event allowed into decision logic: {rid}")
        if not r["issues"]:
            if r["cluster_id"] and rid not in groups.get(r["cluster_id"], set()):
                failures.append(f"Invalid cluster membership for {rid}")
            # Compute an expected decision independently from its evidence links.
            has_neighbor = any(rid in edge for edge in links)
            expectation = ("INVESTIGATE_PATTERN" if has_neighbor else
                           "VERIFY_LARGE_RECORD" if r["mag"] >= 6 else "MONITOR")
            if r["decision"] != expectation:
                failures.append(f"Rule/decision disagreement: {rid} expected {expectation}")
            if has_neighbor != bool(r["cluster_id"]):
                failures.append(f"Cluster completeness failure for {rid}")
    # Verify all eligible candidate pairs were discovered; prevents missing edges.
    eligible = [r for r in records if not r["issues"]]
    for i, a in enumerate(eligible):
        for b in eligible[i+1:]:
            if abs(a["time_ms"]-b["time_ms"]) > 24*3600*1000:
                continue
            checks += 1
            if independent_distance(a,b) <= 99.99 and frozenset((a["id"],b["id"])) not in links:
                failures.append(f"Missing expected edge: {a['id']} <-> {b['id']}")
    return {"status": "PASS" if not failures else "FAIL", "checks": checks,
            "failures": failures, "method": "Independent geometry + result consistency + snapshot hashes"}


def audit_llm_review(review, report):
    """Verify structured factual assertions. Free text cannot be proven by this check."""
    records = {r["id"]:r for r in report["records"]}
    failures = []
    rid = review.get("event_id")
    if rid not in records:
        failures.append("Unknown primary event")
    if review.get("proposed_decision") not in {"CHECK_DATA", "INVESTIGATE_PATTERN", "VERIFY_LARGE_RECORD", "MONITOR", "ESCALATE_HUMAN"}:
        failures.append("Decision outside approved vocabulary")
    cited = review.get("cited_event_ids")
    if not isinstance(cited, list) or not cited or any(x not in records for x in cited):
        failures.append("Unknown or missing evidence identifiers")
    factual_claims = review.get("factual_claims", [])
    if not isinstance(factual_claims, list):
        failures.append("factual_claims must be an array")
        factual_claims = []
    permitted_fields = {"mag", "place", "time_ms", "lat", "lon", "depth_km", "status", "gap", "rms", "nst"}
    for claim in factual_claims:
        if not isinstance(claim, dict):
            failures.append("Malformed factual claim")
            continue
        event_id, field = claim.get("event_id"), claim.get("field")
        if event_id not in records or field not in permitted_fields:
            failures.append("Unverifiable factual claim")
        elif records[event_id][field] != claim.get("value"):
            failures.append(f"Contradicted factual claim: {event_id}.{field}")
    if rid in records and review.get("proposed_decision") not in (records[rid]["decision"], "ESCALATE_HUMAN"):
        failures.append("Disagrees with rule engine; requires independent adjudication")
    return {"status": "PASS" if not failures else "REVIEW_REQUIRED", "failures":failures,
            "limitation": "Only typed claims and links checked. Natural-language explanation and causality NOT verified."}
