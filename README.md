# OpenInference Lab
### AI-assisted building, independent verification, traceable inference, and human decisions

**An educational open-source prototype. No proprietary code or design from Dragon/Sentience is used.**

**Question:** If generative AI can build an inference system, how does a technically educated engineer establish whether the system's inputs, reasoning, decisions, and conclusions deserve trust?

## Quick start (Python 3.10+, no pip dependencies)

```bash
python -m openinference.demo
python -m unittest discover -s tests -v
```

Open `reports/index.html` in your browser. Select **Baseline** and **Adversarial**. Click events, provenance graphs, and integrity exceptions. The dashboard runs locally from a static file; no server or online dependencies. Optional model interface is described below.

The repo includes a frozen **15-event** genuine USGS sample drawn from the public magnitude 4.5+ weekly GeoJSON feed observed October 29, 2026. The source feed had **186 records** at capture. This is a **convenience selection, not a representative sample**. All original event fields, identifiers, and source timestamps used in this exercise can be traced to USGS public records; the manifest freezes selected field values. The independent-check scenario then **deliberately corrupts three existing source records and fabricates one report** (which also causes a near-duplicate flag on the original), labeling these edits as lab fixtures.

Source & schema: [USGS feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson), [GeoJSON summary documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php), [USGS licensing guidance](https://www.usgs.gov/data-management/data-licensing).

## What the application actually does

1. **Ingest and fingerprint.** A frozen selected record set has a baseline SHA-256 checksum manifest over fixed fields. Checksums detect changes *relative to this frozen reference*, not whether the reference was ever true or signed by USGS.
2. **Check data.** Test coordinate ranges, magnitude, timestamps, update ordering, candidate duplicates, and comparison against the manifest. Suspect records are quarantined, not used as inputs for spatial inference.
3. **Construct relationships.** Two events are connected when within **100 km and 24 hours**. Connected components are exploratory groups, *not* evidence of physical causation or aftershock status.
4. **Recommend actions.** Only queue a human for `CHECK_DATA`, `INVESTIGATE_PATTERN`, or `VERIFY_LARGE_RECORD`; otherwise `MONITOR`. The 6.0 threshold is purely a demonstration rule, not a hazard score.
5. **Audit independently.** `openinference/verify.py` recomputes geometry using a different formula, detects missing/fabricated edges, checks referential integrity and source-result hashes, and confirms decision-rule consistency.
6. **Visualize the work.** A standalone dashboard provides a coordinate plot, observation timeline, selected record facts, provenance graph, decision explanations, and audit summaries.
7. **Challenge with an LLM (optional).** An independent Claude reviewer can propose a structured criticism; factual claims are then checked against source records. No AI answer is accepted as its own proof.

```
USGS public events ──> schema + frozen hash verification ──> validated evidence
                                │                         │
                                └─> quarantine           v
                                        spatiotemporal rules
                                                 │
                                  candidate relationship graph
                                                 │
                                     human-review decisions
                                                 │
                             independent mathematical verifier
                                                 │
                              interactive investigation console
```

### Local optional model review

Create an evidence-only prompt packet **offline**:

```bash
python -m openinference.llm --id us7000ttw3
```

Explicitly call Claude when you have an account and select an available model:

```bash
export ANTHROPIC_API_KEY='YOUR_KEY'    # never commit this value
export ANTHROPIC_MODEL='A_MODEL_YOU_HAVE_ACCESS_TO'
python -m openinference.llm --id us7000ttw3 --call-claude
```

This call may incur provider charges. The model must return structured JSON (`event_id`, `proposed_decision`, `cited_event_ids`, `factual_claims`, `explanation`, `limitations`). The independent structured verifier checks IDs, values and decision agreement, then saves the results. It **cannot verify arbitrary natural-language reasoning**; such claims need further human scrutiny or independent experiments.

Optional live ingestion (requires network):

```bash
python -m openinference.demo --fetch-live
```

Downloads up to 60 current USGS events into `reports/live_download.json`, **without replacing or claiming equivalence to the frozen benchmark**. The live dataset is intentionally not validated against the frozen hashes. A production system would need its own snapshot versioning, source authentication and update policy.

## Intended learning outcomes

- Distinguish observation, inference, decision, and unverified hypothesis.
- Understand source integrity vs. schema validation vs. scientific truth.
- Identify missingness, duplication, changed records, identity and provenance failures.
- Explain why the verifier should not merely ask the same model whether its own answer is right.
- Model data lineage and produce readable visual explanations of model decisions.
- Use coding assistants for construction and adversarial brainstorming, with independent executable tests and controlled human review.
- Compare baseline and deliberately compromised cases without confusing synthetic failures for genuine public events.

## Limitations (read these)

- **Not a USGS product; not earthquake prediction; not a public-safety decision service.** Correlation is not causation.
- The dataset is deliberately small, biased and static; outcomes do not estimate real-world error rates or model calibration.
- The field-range checks are intentionally coarse; proper domain validation must reflect source conventions and catalog updates.
- A checksum is not a digital signature; the manifest itself can be changed. Production requires trusted signing/attestation and secure source management.
- A `PASS` means the coded invariants held; it does **not** mean seismic claims are true, complete or unbiased.
- Evidence quality numbers in the demo are **heuristic quality indicators, not calibrated probabilities**.
- The independent verifier shares some specifications with the builder. For stronger assurance, use external ground truth, separately authored test oracles, metamorphic tests, and human-domain review.
- Source locations are plotted as points on a coordinate grid, not a hazard, impact or geographic-reference map.

See `STUDENT_LAB.md` and `prompts/ai_workflow.md` for a teaching curriculum.
