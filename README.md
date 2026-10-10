# ReguLens — Regulatory Impact & Evidence Lab

A local-first working prototype for the **ET AI Hackathon — Banking/financial regulations** challenge. It is designed to demonstrate a real, observable processing and remediation loop on synthetic data—not just a dashboard.

## Local service layer added

- **Persistent SQLite workspace:** saved sources, controls, assessment history, and task states survive browser refreshes and app restarts.
- **Audit integrity:** operational events are stored in a SHA-256 hash-chained audit log, with a built-in integrity check and CSV export.
- **Notification outbox:** alerts can be queued durably and inspected. External delivery is not faked; email/Teams/webhook credentials and connector setup are required.
- **Service health:** database integrity, saved run count, audit event count, and notification queue are visible in the Operations & Services tab.
- **Run history:** reopen prior assessment results for comparison and inspection.

These are production-style prototype services, not a claim of production banking deployment. SSO, enterprise RBAC, regulator feeds, central database/backup, secret management, email/Teams, ITSM/GRC connectors, and a hosted AI service still require real integration and security configuration.

## What you can actually do

1. **Ingest sources:** edit regulatory text or upload TXT, MD, CSV, JSON, text-based PDF, or DOCX documents.
2. **Detect regulatory changes:** compare previous and current versions and inspect the changed clauses.
3. **Extract obligation candidates:** retain each candidate's original clause, source label, and SHA-256 fingerprint.
4. **Edit the bank control framework:** change control owners, scope, mapping terms, implementation, evidence, evidence age, and test status.
5. **Map obligations to controls:** see matched terms, alternatives, and mappings that need human review.
6. **Assess effectiveness and evidence:** check applicability, control implementation, evidence availability/freshness, and test status.
7. **Prioritise gaps:** compute transparent risk scores and produce an owned remediation plan.
8. **Run what-if failures:** remove evidence, regress a control, make owners unavailable, and inject a transient execution failure.
9. **Compare regulatory sources:** optionally provide a second source to surface related topics and possible numeric-period conflicts for review.
10. **Execute a remediation workflow:** execute a sandbox-only change, attach synthetic evidence, record owner attestation, and run an independent retest.
11. **Enforce closure gates:** a task closes only when the workflow steps pass and the mapping/applicability are not flagged for review. Unmapped/ambiguous items remain for human review.
12. **Inspect and export evidence:** view the ordered event trace and download the JSON run bundle and CSV registers.

## Start on Windows

1. Download and extract the ZIP into a new folder. The ZIP contains the project files at its root, so you should see `app.py` and `START_REGULENS.bat` directly inside the extracted folder (not inside another nested project folder).
2. Install Python 3.10–3.13 (64-bit) from https://www.python.org/downloads/ and enable **Add Python to PATH** during setup.
3. Double-click `START_REGULENS.bat`. It creates a local `.venv`, installs the free dependencies, and starts the Streamlit app.
4. Open the local URL shown in the terminal, normally `http://localhost:8501`.
5. Go to **③ Run agent pipeline** and click **RUN COMPLETE REGULATORY IMPACT ASSESSMENT**.
6. Inspect **④ Findings & audit**.
7. Go to **⑤ Remediation workbench**, select a task, then run these actions in order:
   - Execute remediation
   - Attach evidence
   - Record owner attestation
   - Run independent retest
8. Watch the task status, gap count, and event trace update. Ambiguous mappings should remain open for human review.

The first start needs internet access to install Python packages. No paid service, API key, or external AI account is required.

## Run automated tests

- Double-click `RUN_TESTS.bat` after the first setup, or run:

```bash
python -m unittest discover -s tests -v
```

The automated tests cover extraction, version changes, gaps, safe handling of empty inputs, scope review, unmapped obligations, audit sequencing, retry/recovery, cross-source comparisons, fallback owners, remediation closure gates, persistent state, audit hash-chain verification, and notification outbox storage.

## Demo scenario

For a compelling short demo:

1. Keep the sample current/previous regulatory text; compare them to show changed periods and a newly added monitoring requirement.
2. In the sidebar choose **Resilience / retry test** and load it.
3. Run the assessment. Show the ordered event log, open gaps, risk ranking, fallback owner, and recovered transient failure.
4. In the Remediation Workbench choose an eligible mapped task. Execute, attach synthetic evidence, attest, and retest. Show the task close and gap metrics update.
5. Add the optional second source with a different review period, rerun, and show the cross-source review flag.
6. Download the JSON run bundle to show that the result is exportable and traceable.

## Honest limits

- The current engine uses transparent deterministic NLP/rule-based processing, not an LLM. It does not claim model-generated legal interpretation. This makes the demo reproducible and inspectable, but the team should not claim a deployed generative-AI model unless one is actually integrated.
- All sample regulations, controls, evidence receipts, and remediation actions are synthetic. The workbench changes only local in-memory demo state.
- This is not legal advice, regulatory certification, or production banking assurance.
- It does not connect to regulator feeds, bank systems, ticketing systems, identity platforms, or evidence vaults.
- PDF ingestion supports text-based PDFs; scanned-image OCR is not included.
- Applicability and mappings are proposals. Unmapped or ambiguous requirements require human validation.
- Cross-source comparison surfaces related topics and possible period conflicts; it does not infer legal hierarchy or resolve jurisdictional conflicts.

## Files

- `app.py` — Streamlit UI, upload/editor controls, scenario configuration, workbench, trace and exports.
- `engine.py` — extraction, mapping, assessment, risk ranking, change comparison, scenario injection, retry handling and remediation state machine.
- `service_layer.py` — SQLite persistence, assessment history, hash-chained audit events, service health and local notification outbox.
- `tests/test_engine.py` — automated regression tests.
- `ARCHITECTURE.md` — process flow, boundaries and traceability.
- `COMPETITIVE_LANDSCAPE.md` — researched positioning and novelty caveats.
- `DEMO_SCRIPT.md` — click-by-click demonstration.
- `sample_*.txt` — editable demo regulatory inputs.
