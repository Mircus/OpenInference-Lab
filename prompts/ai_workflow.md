# Working with multiple AI roles, without making AI the judge of its own truth

## 1. Builder (Claude or another coding model)

> Implement a Python function that receives a list of time-stamped events with latitude/longitude and returns all pairs within 100 km and 24 hours. Use only the Python standard library. Before writing code, specify assumptions and edge cases. Include tests for dateline crossing, polar coordinates, identical timestamps, missing values and equality at the boundary. Do NOT look at the existing implementation in `openinference/core.py`.

Human checks: specification, input validation, omissions, reproducibility, and code execution.

## 2. Adversarial test designer (fresh model context)

> You have been hired to DISPROVE the correctness of an AI-written spatial inference system. Its intended invariant: event pairs must be no farther than 100 km and 24 hours apart. Propose at least 12 distinct counterexamples including antimeridian behavior, missingness, chaining and duplicate events. Provide exact test input and expected outcome; distinguish hard errors from ambiguous cases.

Human checks: independently verify expected outputs. AI can invent faulty expected values.

## 3. Scientific reviewer (separate evidence packet)

> Given only the supplied event facts and the candidate rule decision, return a JSON object with known evidence IDs, exactly verifiable factual claims, a proposed analyst decision, limitations and alternatives. Never assert that spatial proximity proves causality or that this analysis is an earthquake hazard assessment.

Programmatic checks: referential closure, numeric fields, allowed decision labels. Human checks: semantics, scientific assumptions, alternative hypotheses, hidden sources.

## 4. Integrity engineer (independent executable oracle)

> Write a SECOND verifier from a formal list of invariants without importing the builder's geometry or clustering functions. Validate all declared edges, find omitted valid edges, check source-to-output field conservation, verify review/quarantine gating, and produce minimal counterexamples on disagreement.

Run both implementations. The reviewer is not correct merely because it is a different model. Reconcile disagreements with mathematics, reference data and explicit decision rules.

## 5. Visual analyst

> Design an investigative display separating reported facts, derived candidate relationships, and decisions. Expose source URL, snapshot hash, local tests, input-quality failures, and unresolved uncertainty. Do not display heuristic quality scores as calibrated probabilities.

Evaluate for cognitive clarity, inspectability, accessibility and misleading visual cues. Test the actual browser, not only generated HTML.

## Suggested role allocation

AI generates draft code, hypotheses, test ideas and optional narrative critiques. Deterministic programs validate structural invariants. Humans decide whether the model's question, data and domain interpretation are justified. Independent external evidence is required for substantive scientific claims.
