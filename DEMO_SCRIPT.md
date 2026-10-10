# 3-minute live prototype script

## 0:00–0:20 — State the problem
"A regulatory change is not complete when a dashboard shows a gap. Teams need traceability from source clause through control, evidence, remediation and verification. ReguLens demonstrates that chain using synthetic data."

## 0:20–0:45 — Show the source change
Open Source intake. The sample previous version requires a 180-day privileged-access review; the current version uses 90 days and adds monitoring. Click Compare previous vs current. Explain that changes are triage candidates and require source review.

## 0:45–1:20 — Trigger a failure and execute the pipeline
In the sidebar choose **Resilience / retry test**, click Load scenario preset, then run the assessment. Show obligations, matched control terms, gaps, risk ranking, fallback owner and the transient failure's retry/recovery events.

## 1:20–2:20 — Demonstrate actual state transitions
Open Remediation Workbench. Select a mapped task. Click Execute remediation, Attach evidence, Record owner attestation, and Run independent retest in that order. Point out that each action changes task/control state and appends an event. Show the gap/task count updating after eligible closure.

If the selected task is ambiguous or out of scope, explain that the closure gate correctly keeps it open for human review rather than manufacturing compliance.

## 2:20–2:45 — Cross-source intelligence
Paste a second synthetic source with a different period for the same topic. Rerun and show the possible cross-source conflict flag. Explain that ReguLens asks for human review instead of assuming which rule overrides the other.

## 2:45–3:00 — Close with evidence
Open the execution trace and download the JSON run bundle. "This prototype demonstrates a repeatable source-to-action-to-verification loop, with observable decisions and bounded sandbox execution."

## Avoid overclaiming
Do not say that the prototype is connected to a live bank, automatically certifies compliance, uses an LLM, or is globally unique. It is a deterministic local prototype with synthetic data.
