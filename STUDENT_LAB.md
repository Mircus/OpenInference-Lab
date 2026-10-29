# Student lab — From AI-generated code to defensible knowledge

**Audience:** an engineering graduate comfortable with simple programming and high-school probability, not yet a professional data scientist.

**Target:** 6 sessions of 2–3 hours each. The project is intentionally small enough to inspect but complete enough to expose the hard problems.

## Session 1 — What counts as evidence?

1. Run `python -m openinference.demo` and open the console.
2. Follow an individual event from the public USGS link to the rule recommendation.
3. Explain which fields are facts supplied by the source, which are assumptions, and which are deductions.
4. Answer: Is the *selected first 15 records* sample statistically representative? Why not?
5. Deliver a 1-page source and sampling critique.

## Session 2 — The data integrity gate

1. Toggle **Baseline** vs **Adversarial**.
2. Identify all five quarantined rows and the four injected changes that created them.
3. Explain why an edited 8.8 magnitude can be in range but still be false.
4. Decide whether two close-in-time and space observations are duplicates or separate events; list evidence required to settle the question.
5. Deliver an independently written data-quality checklist and 3 more corruption tests.

## Session 3 — Build an inference graph

1. Ask a coding assistant to implement proximity graphing *without giving it our implementation*.
2. Compare the AI-generated function to the 100 km / 24 h specification using held-out fixtures.
3. Explain the difference between linked pairs and connected components (transitive chains).
4. Design a case where two ends of a connected group are separated by >100 km. Should they be called a single group?
5. Deliver two implementations and a test table.

## Session 4 — Independent verification

1. Run `python -m unittest discover -s tests -v`.
2. Inject a fake edge into `reports/clean.json`. Why does the verifier reject it?
3. Try removing one true edge. Why does detecting omissions matter as much as detecting fabricated links?
4. Debate the limits of SHA-256 manifests and the limits of a passing test suite.
5. Deliver a written failure taxonomy: data, inference, integrity, decision, governance.

## Session 5 — A model challenges the model

1. Run `python -m openinference.llm --id us7000ttw3` for a locally generated review prompt.
2. Optionally invoke Claude using `--call-claude`, or paste the prompt into a chat LLM and save the JSON response manually.
3. Run `audit_llm_review` against model output and introduce a deliberately false numeric claim.
4. See which errors the verifier catches, and which natural-language errors remain unverified.
5. Deliver an AI review and a separate human critique, including unresolved uncertainties.

## Session 6 — From analysis to a decision support product

1. Build an improved dashboard view showing the record → rule → decision chain with failures first.
2. Add an abstain/needs-more-data outcome when the evidence is insufficient.
3. Define a reference set of adjudicated labels and a plan for measuring precision/recall and calibration when applicable.
4. Design source-version update handling: if USGS revises a magnitude, don't call a legitimate update an attack.
5. Submit a short release memo: what this system does, what it does not, tests passed, unresolved risks, next experiments.

## Assessment rubric

| Dimension | Weight | How to demonstrate competence |
|---|---:|---|
| Sound statistical / scientific reasoning | 25% | Distinguishes correlation, evidence quality and causation |
| Data quality and provenance | 20% | Detects corruption, duplicates, and source changes |
| Inference and algorithm quality | 20% | Rule semantics tested; missing and invented links caught |
| AI collaboration | 15% | Uses AI for code and adversarial review without treating it as proof |
| Visualization and communication | 10% | Decision path and uncertainties transparent |
| Operational responsibility | 10% | Documented limitations, human review and update policy |

**Pass criterion:** a student must be able to explain a convincing but WRONG inference, construct a test that exposes it, and show precisely which evidence remains missing. A beautiful AI-generated dashboard is not sufficient.
