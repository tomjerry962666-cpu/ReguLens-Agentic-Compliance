# ReguLens technical architecture

## End-to-end chain

`Regulatory sources → source fingerprints → obligation candidates → applicability → control mapping → evidence/effectiveness checks → gap/risk scoring → remediation plan → sandbox execution → evidence attachment → owner attestation → independent retest → closure gate → exportable audit trace`

## Stages and responsibilities

1. **Intake** — accepts editable text or supported text documents; records source name and SHA-256 fingerprints. Empty input blocks safely.
2. **Obligation extraction** — uses transparent normative-language patterns to retain candidate obligations and original source clauses. Candidates are not legal conclusions.
3. **Change intelligence** — compares old/current clauses using exact matching and text similarity; reports added, modified, removed and unchanged candidates.
4. **Control mapping** — ranks controls by visible keyword/domain evidence, returns matched terms and alternatives, and marks weak/tied mappings for review.
5. **Applicability/effectiveness** — checks the selected jurisdiction/product against configured control scope, plus implementation, evidence presence, evidence freshness and latest test result.
6. **Consistency intelligence** — flags possible numeric-period conflicts within a source and compares related topics across two optional regulatory sources. Human review is required.
7. **Risk planner** — ranks gaps using an inspectable heuristic and creates task records with owners, required evidence and closure gates.
8. **Executor** — simulates task creation and optional transient failure/retry; emits task receipts. No external system is modified.
9. **Remediation workbench** — requires four explicit steps: execute synthetic remediation, attach synthetic evidence, record owner attestation, and run a retest.
10. **Verification gate** — closes only if the control is mapped, the mapping is not marked for review, applicability is within configured scope, implementation/evidence/test checks pass, and workflow gates are complete. Otherwise it remains open or requires review.
11. **Observability/export** — ordered event records plus JSON and CSV downloads.

## Decision boundaries

- The engine is deterministic and inspectable. It does not use a paid API or claim an LLM has interpreted a regulation.
- Matching scores and risk scores are heuristics, not calibrated probabilities.
- No automatic legal applicability decision is made from a jurisdiction label alone.
- The sandbox's evidence receipt is synthetic. A task being created is not equivalent to compliance.
- Unmapped or ambiguous requirements cannot be automatically closed.
- All state mutations occur in the local Streamlit session; restart the app to reset the demo.

## Why this is agentic rather than a static dashboard

The pipeline invokes specialised processing stages, changes state from configurable inputs, selects and assigns actions, retries a deliberately failed operation, applies sandbox remediation, and verifies the outcome against explicit gates. Each stage records its observable action/status/detail. This is bounded local workflow automation; it is not autonomous production banking execution.

## Runtime

- Python 3.10–3.13
- Streamlit UI
- Pandas for editable tables/exports
- pypdf and python-docx for text extraction from supported documents
- Python standard library for the engine, hashing, matching and tests
