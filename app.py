"""ReguLens: local-first regulatory impact, remediation and verification workbench."""
import io
import json
from datetime import datetime
import pandas as pd
import streamlit as st
from engine import (
    SAMPLE_REGULATION, SAMPLE_REGULATION_OLD, SAMPLE_CONTROL_POLICY,
    DEFAULT_CONTROLS, run_pipeline, compare_versions, compare_regulatory_sources,
    export_json, sha, remediate_task,
)
from service_layer import (init_db, save_state, load_state, save_run, update_latest_run, latest_run, list_runs, append_audit, list_audit, verify_audit_chain, enqueue_notification, list_outbox, service_health)

st.set_page_config(page_title="ReguLens | Regulatory Impact Lab", page_icon="🧭", layout="wide")
st.markdown("""
<style>
.block-container {padding-top:1.1rem;padding-bottom:2rem;max-width:1550px}
.hero {padding:1.15rem 1.45rem;border-radius:15px;background:linear-gradient(120deg,#0b2345,#165b72);color:white;margin-bottom:1rem}
.hero h1 {color:white;margin:0 0 .3rem 0}.hero p {color:#dbeafe;margin:0}
.step {border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:12px;min-height:100px}
.small {font-size:.86rem;opacity:.82}
</style>
<div class="hero"><h1>🧭 ReguLens</h1><p>Regulatory Impact & Evidence Lab · Regulation → Obligation → Applicability → Control → Evidence → Test → Gap → Remediation → Verification</p></div>
""", unsafe_allow_html=True)
st.caption("Regulatory operations workbench · persistent local database · auditable workflow · synthetic banking data · external production connectors not configured")
with st.expander("Operating boundary and evidence policy", expanded=False):
    st.write("This is a synthetic demonstration, not legal advice or production compliance assurance. The local engine uses inspectable rules and visible mapping terms; it does not claim an LLM has read or interpreted law. A task cannot close merely because a plan was created: the demo workflow requires a sandbox remediation, evidence attachment, owner attestation and successful retest. Ambiguous or unmapped links remain for human review.")

# Initialize state before widgets are created.
def init(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_db()
init("regulens_result", latest_run())
init("control_table", pd.DataFrame(load_state("control_table", DEFAULT_CONTROLS)))
init("current_reg_editor", load_state("current_reg_editor", SAMPLE_REGULATION))
init("old_reg_editor", load_state("old_reg_editor", SAMPLE_REGULATION_OLD))
init("secondary_reg_editor", load_state("secondary_reg_editor", ""))
init("last_run_time", (st.session_state.regulens_result or {}).get("_persistence", {}).get("created_at", "Restored from local database"))
init("remove_evidence", False)
init("disable_control", False)
init("owner_unavailable", False)
init("transient_failure", False)


def read_upload(upload):
    if upload is None:
        return None
    data = upload.getvalue()
    ext = upload.name.lower().rsplit(".", 1)[-1]
    try:
        if ext in ("txt", "md", "csv", "json"):
            return data.decode("utf-8-sig")
        if ext == "pdf":
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        if ext == "docx":
            from docx import Document
            return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    except Exception as exc:
        st.error(f"Could not read {upload.name}: {exc}")
    return None

with st.sidebar:
    st.header("Assessment scope")
    jurisdiction = st.selectbox("Jurisdiction / scope", ["India", "United Kingdom", "European Union", "Singapore", "United States"], index=0)
    entity = st.selectbox("Legal entity", ["Retail Bank", "Digital Bank", "Payments Subsidiary", "Group Shared Services"])
    product = st.selectbox("Product / service", ["Digital banking", "Core banking", "Payments", "Lending", "All banking products"])
    st.divider()
    st.subheader("Failure injection / what-if")
    st.caption("These switches alter a copy of the demo controls before processing; no production system is touched.")
    preset = st.selectbox("Scenario preset", ["Custom", "Baseline evidence gap", "Control regression", "Resilience / retry test", "Clean synthetic run"])
    if st.button("Load scenario preset", use_container_width=True):
        preset_values = {
            "Baseline evidence gap": (True, False, False, False),
            "Control regression": (False, True, False, False),
            "Resilience / retry test": (True, False, True, True),
            "Clean synthetic run": (False, False, False, False),
            "Custom": (st.session_state.remove_evidence, st.session_state.disable_control, st.session_state.owner_unavailable, st.session_state.transient_failure),
        }
        (st.session_state.remove_evidence, st.session_state.disable_control,
         st.session_state.owner_unavailable, st.session_state.transient_failure) = preset_values[preset]
        st.rerun()
    remove_evidence = st.toggle("Remove evidence from evidence-retention control", key="remove_evidence")
    disable_control = st.toggle("Disable first control (regression)", key="disable_control")
    owner_unavailable = st.toggle("Primary owner unavailable (fallback owner)", key="owner_unavailable")
    transient_failure = st.toggle("Inject transient task-execution failure", key="transient_failure")
    st.divider()
    st.caption("All actions are synthetic/local. No real regulatory filing, bank ticket, account, or control is changed.")

tabs = st.tabs(["① Source intake & change", "② Control framework", "③ Run agent pipeline", "④ Findings & audit", "⑤ Remediation workbench", "⑥ Operations & services"])

with tabs[0]:
    st.subheader("Regulatory documents")
    left, right = st.columns(2)
    with left:
        st.markdown("**Primary / current regulation**")
        current_upload = st.file_uploader("Upload current regulation (TXT, MD, CSV, JSON, PDF, DOCX)", type=["txt", "md", "csv", "json", "pdf", "docx"], key="current_upload")
        current_upload_text = read_upload(current_upload)
        if current_upload_text is not None and st.button("Load uploaded current document", key="load_current"):
            st.session_state.current_reg_editor = current_upload_text
        current_text = st.text_area("Current regulatory text (editable)", key="current_reg_editor", height=250)
        source_name = current_upload.name if current_upload else "Synthetic sample regulation"
        st.caption(f"Current source SHA-256: `{sha(current_text)[:24]}…`")
    with right:
        st.markdown("**Previous version / change intelligence**")
        old_upload = st.file_uploader("Upload previous version (optional)", type=["txt", "md", "csv", "json", "pdf", "docx"], key="old_upload")
        old_upload_text = read_upload(old_upload)
        if old_upload_text is not None and st.button("Load uploaded previous document", key="load_old"):
            st.session_state.old_reg_editor = old_upload_text
        old_text = st.text_area("Previous regulatory text (editable)", key="old_reg_editor", height=250)
        st.caption(f"Previous source SHA-256: `{sha(old_text)[:24]}…`")
    with st.expander("Optional second regulation / cross-source intelligence"):
        secondary_upload = st.file_uploader("Upload a second source (optional)", type=["txt", "md", "csv", "json", "pdf", "docx"], key="secondary_upload")
        secondary_upload_text = read_upload(secondary_upload)
        if secondary_upload_text is not None and st.button("Load uploaded second source", key="load_secondary"):
            st.session_state.secondary_reg_editor = secondary_upload_text
        secondary_text = st.text_area("Second regulatory source (editable; optional)", key="secondary_reg_editor", height=180)
        secondary_name = secondary_upload.name if secondary_upload else "Secondary regulation (user supplied)"
        st.caption("Cross-source comparisons flag related topics and differing periods for review. They do not determine legal hierarchy or applicability.")
    if st.button("Save source documents to local workspace", key="save_sources"):
        save_state("current_reg_editor", st.session_state.current_reg_editor)
        save_state("old_reg_editor", st.session_state.old_reg_editor)
        save_state("secondary_reg_editor", st.session_state.secondary_reg_editor)
        append_audit("demo_operator", "SOURCE_DOCUMENTS_SAVED", "source", "workspace", {"current_hash": sha(st.session_state.current_reg_editor), "previous_hash": sha(st.session_state.old_reg_editor)})
        st.success("Source text saved to the local SQLite workspace and audit log.")
    c1, c2 = st.columns([1, 2])
    with c1:
        if st.button("Compare previous vs current", use_container_width=True):
            st.session_state.version_diff = compare_versions(old_text, current_text)
    with c2:
        st.caption("Change comparison is a triage aid. Review the actual source clauses before concluding that a legal requirement changed.")
    if "version_diff" in st.session_state:
        st.dataframe(pd.DataFrame(st.session_state.version_diff), use_container_width=True, hide_index=True)
        st.download_button("Download version diff CSV", pd.DataFrame(st.session_state.version_diff).to_csv(index=False), "regulatory_version_diff.csv", "text/csv")
    with st.expander("Synthetic control policy input example"):
        st.code(SAMPLE_CONTROL_POLICY)
    st.info("PDF and DOCX text extraction is local. Scanned PDFs require OCR and are not claimed as supported in this version.")

with tabs[1]:
    st.subheader("Editable bank control framework")
    st.write("Edit the records the engine actually uses. Keywords are editable comma-separated text (not list-valued cells), preventing Streamlit data-editor type mismatches.")
    edited = st.data_editor(
        st.session_state.control_table.copy(), key="control_editor", num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "control_id": st.column_config.TextColumn("Control ID", required=True),
            "control_name": st.column_config.TextColumn("Control name", required=True),
            "description": st.column_config.TextColumn("Control description"),
            "keywords": st.column_config.TextColumn("Mapping keywords (comma-separated)"),
            "owner": st.column_config.TextColumn("Owner"),
            "jurisdiction": st.column_config.TextColumn("Jurisdiction"),
            "products": st.column_config.TextColumn("Product scope"),
            "implemented": st.column_config.CheckboxColumn("Implemented"),
            "evidence_present": st.column_config.CheckboxColumn("Evidence available"),
            "test_passed": st.column_config.CheckboxColumn("Latest test passed"),
            "evidence_age_days": st.column_config.NumberColumn("Evidence age (days)", min_value=0, step=1),
            "review_frequency_days": st.column_config.NumberColumn("Review frequency (days)", min_value=0, step=1),
            "system": st.column_config.TextColumn("System"),
            "criticality": st.column_config.SelectboxColumn("Criticality", options=["Low", "Medium", "High", "Critical"]),
        })
    st.session_state.control_table = edited
    save_state("control_table", edited.fillna("").to_dict(orient="records"))
    st.caption(f"{len(edited)} control records loaded. Applicability is a reviewable demo scope, not a legal conclusion.")

with tabs[2]:
    st.subheader("Observable multi-stage processing")
    pipeline = [
        ("01", "Intake & source integrity", "Validate source, scope and control records"),
        ("02", "Obligation extraction", "Retain source clause and SHA-256 fingerprint"),
        ("03", "Control mapping", "Show matched terms, alternatives and review flags"),
        ("04", "Applicability & evidence", "Check scope, implementation, evidence age and test result"),
        ("05", "Change / cross-source intelligence", "Compare versions and related topics"),
        ("06", "Risk & remediation planner", "Rank gaps and assign an owner or fallback"),
        ("07", "Sandbox executor", "Create task receipts; inject and recover from a transient failure"),
        ("08", "Independent verification", "Require evidence, attestation and retest before closure"),
    ]
    cols = st.columns(4)
    for i, (num, title, detail) in enumerate(pipeline):
        with cols[i % 4]:
            st.markdown(f'<div class="step"><b>{num} · {title}</b><p class="small">{detail}</p></div>', unsafe_allow_html=True)
    st.write("")
    st.json({"jurisdiction": jurisdiction, "entity": entity, "product": product,
             "remove_evidence": remove_evidence, "disable_control": disable_control,
             "owner_unavailable": owner_unavailable, "transient_failure": transient_failure,
             "secondary_source_provided": bool(st.session_state.secondary_reg_editor.strip())})
    if st.button("▶ RUN COMPLETE REGULATORY IMPACT ASSESSMENT", type="primary", use_container_width=True):
        controls = edited.fillna("").to_dict(orient="records")
        for control in controls:
            for field in ("evidence_age_days", "review_frequency_days"):
                try: control[field] = max(0, int(control.get(field) or 0))
                except (TypeError, ValueError): control[field] = 0
            for field in ("implemented", "evidence_present", "test_passed"):
                control[field] = bool(control.get(field, False))
        scope = {"jurisdiction": jurisdiction, "entity": entity, "product": product}
        scenario = {"remove_evidence": remove_evidence, "disable_first_control": disable_control,
                    "owner_unavailable": owner_unavailable, "inject_transient_failure": transient_failure}
        with st.status("Executing the source-grounded pipeline…", expanded=True) as status:
            result = run_pipeline(current_text, controls, scope, old_text, scenario, source_name)
            if st.session_state.secondary_reg_editor.strip():
                result["cross_source"] = compare_regulatory_sources(current_text, source_name, st.session_state.secondary_reg_editor, secondary_name)
            else:
                result["cross_source"] = []
            status.update(label=f"Pipeline finished: {result['status']}", state="complete", expanded=False)
        st.session_state.regulens_result = result
        st.session_state.last_run_time = datetime.now().isoformat(timespec="seconds")
        run_id = save_run(result, result.get("status", "COMPLETED"))
        append_audit("demo_operator", "ASSESSMENT_COMPLETED", "assessment", str(run_id), {"metrics": result.get("metrics", {}), "scope": scope})
        st.success("Processing completed. Open Findings & Audit, then use the Remediation Workbench to execute, evidence, attest and retest a task.")

with tabs[3]:
    result = st.session_state.regulens_result
    if not result:
        st.info("Run the assessment in tab ③ to populate obligations, mappings, risk findings, remediation tasks and execution trace.")
    else:
        metrics = result["metrics"]
        st.subheader("Latest assessment outcome")
        cards = st.columns(6)
        cards[0].metric("Obligations", metrics["obligations"])
        cards[1].metric("Proposed links", metrics["mapped"])
        cards[2].metric("Mappings for review", metrics["mapping_review"])
        cards[3].metric("Open gaps", metrics["gaps"])
        cards[4].metric("Critical gaps", metrics["critical"])
        cards[5].metric("Open actions", metrics["actions"])
        st.caption(f"Run: {st.session_state.get('last_run_time', '')} · Source hash: {result.get('source_hash', '')[:24]}… · Status: {result['status']}")
        out_tabs = st.tabs(["Obligations", "Traceability matrix", "Risk & tasks", "Change / conflicts", "Execution trace", "Export"])
        with out_tabs[0]:
            st.dataframe(pd.DataFrame(result["obligations"]), use_container_width=True, hide_index=True)
        with out_tabs[1]:
            combined = pd.DataFrame(result["obligations"]).merge(pd.DataFrame(result["mappings"]), on=["obligation_id", "domain"], how="left")
            findings = pd.DataFrame(result["findings"])
            if not findings.empty:
                combined = combined.merge(findings[["obligation_id", "applicability", "assessment", "severity", "risk_score", "gap_reasons", "required_evidence"]], on="obligation_id", how="left")
            st.dataframe(combined, use_container_width=True, hide_index=True)
        with out_tabs[2]:
            st.dataframe(pd.DataFrame(result["findings"]), use_container_width=True, hide_index=True)
            st.subheader("Remediation task register")
            st.dataframe(pd.DataFrame(result.get("executed_tasks", [])), use_container_width=True, hide_index=True)
        with out_tabs[3]:
            st.write("**Previous vs current**")
            st.dataframe(pd.DataFrame(result.get("changes", [])), use_container_width=True, hide_index=True)
            st.write("**Possible conflicts within source**")
            st.dataframe(pd.DataFrame(result.get("contradictions", [])), use_container_width=True, hide_index=True)
            st.write("**Cross-source topic comparison**")
            if result.get("cross_source"):
                st.dataframe(pd.DataFrame(result["cross_source"]), use_container_width=True, hide_index=True)
            else:
                st.caption("No second regulatory source was provided for cross-source comparison.")
        with out_tabs[4]:
            st.dataframe(pd.DataFrame(result["events"]), use_container_width=True, hide_index=True)
            st.caption("Observable operational trace only; no private model chain-of-thought is exposed.")
        with out_tabs[5]:
            st.download_button("Download complete run bundle (JSON)", export_json(result), "regulens_run_bundle.json", "application/json", use_container_width=True)
            st.download_button("Download findings (CSV)", pd.DataFrame(result["findings"]).to_csv(index=False), "regulens_findings.csv", "text/csv", use_container_width=True)
            st.download_button("Download obligations (CSV)", pd.DataFrame(result["obligations"]).to_csv(index=False), "regulens_obligations.csv", "text/csv", use_container_width=True)
            st.download_button("Download remediation tasks (CSV)", pd.DataFrame(result.get("executed_tasks", [])).to_csv(index=False), "regulens_remediation_tasks.csv", "text/csv", use_container_width=True)
            st.download_button("Download traceability matrix (CSV)", pd.DataFrame(result["mappings"]).to_csv(index=False), "regulens_traceability.csv", "text/csv", use_container_width=True)

with tabs[4]:
    result = st.session_state.regulens_result
    st.subheader("Sandbox remediation → evidence → attestation → independent retest")
    st.write("This is the part that changes application state. Execute the synthetic task, attach a generated demo evidence receipt, record owner attestation, then run retest. No external banking system is connected.")
    if not result or not result.get("executed_tasks"):
        st.info("Run an assessment first. Gaps will generate remediation tasks here.")
    else:
        tasks = result["executed_tasks"]
        task_ids = [t["task_id"] for t in tasks if t.get("status") != "CLOSED"]
        if not task_ids:
            st.success("All eligible demo tasks are closed. Review the updated findings and event trace.")
        else:
            selected_id = st.selectbox("Select an open remediation task", task_ids)
            task = next(t for t in tasks if t["task_id"] == selected_id)
            st.json({k: task.get(k) for k in ["task_id", "obligation_id", "control_id", "priority", "risk_score", "task", "owner", "status", "required_evidence", "closure_gate"]})
            progress = st.columns(4)
            progress[0].write(("✅" if task.get("remediation_executed") else "⬜") + " Execute sandbox fix")
            progress[1].write(("✅" if task.get("evidence_uploaded") else "⬜") + " Attach synthetic evidence")
            progress[2].write(("✅" if task.get("owner_attested") else "⬜") + " Owner attestation")
            progress[3].write(("✅" if task.get("retest_passed") else "⬜") + " Independent retest")
            buttons = st.columns(4)
            actions = [
                ("Execute remediation", "execute"),
                ("Attach evidence", "attach_evidence"),
                ("Record owner attestation", "attest"),
                ("Run independent retest", "retest"),
            ]
            for i, (label, action) in enumerate(actions):
                with buttons[i]:
                    if st.button(label, key=f"{selected_id}_{action}", use_container_width=True, disabled=task.get("status") == "CLOSED"):
                        try:
                            st.session_state.regulens_result = remediate_task(result, selected_id, action)
                            append_audit("demo_operator", "REMEDIATION_" + action.upper(), "remediation_task", selected_id, {"status": next((t.get("status") for t in st.session_state.regulens_result.get("executed_tasks", []) if t.get("task_id") == selected_id), "UNKNOWN")})
                            update_latest_run(st.session_state.regulens_result)
                            st.success(f"Action completed: {label}")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
            st.divider()
            st.markdown("**Current task states**")
            st.dataframe(pd.DataFrame(tasks), use_container_width=True, hide_index=True)
            st.caption("Unmapped or ambiguous obligations are deliberately kept for human control-design/mapping review; the app will not fabricate a control or silently close them.")


with tabs[5]:
    st.subheader("Operations, persistence and integration readiness")
    st.write("This tab provides local service operations for the hackathon prototype. It is production-style in workflow and persistence, but it is not connected to a bank's production environment.")
    health = service_health()
    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Saved assessments", health["assessment_runs"])
    h2.metric("Audit events", health["audit_events"])
    h3.metric("Queued notifications", health["queued_notifications"])
    h4.metric("SQLite integrity", health["database_integrity"])
    st.json(health)
    st.caption("The SQLite database survives browser refreshes and app restarts. Keep the data/ folder with the app to retain history.")
    op_tabs = st.tabs(["Run history", "Audit integrity", "Notification outbox", "Integration status"])
    with op_tabs[0]:
        runs = list_runs(100)
        if runs:
            flat=[]
            for run in runs:
                m=run.get("metrics", {})
                flat.append({"run_id":run["run_id"],"created_at":run["created_at"],"status":run["status"],"source_hash":run["source_hash"],**m})
            st.dataframe(pd.DataFrame(flat), use_container_width=True, hide_index=True)
            chosen_run = st.selectbox("Load a previous assessment result", [r["run_id"] for r in runs], key="load_run_id")
            if st.button("Load selected run into Findings & Audit", key="load_old_run"):
                import sqlite3, json
                from service_layer import DB_PATH
                with sqlite3.connect(DB_PATH) as con:
                    row=con.execute("SELECT result_json,created_at FROM assessment_runs WHERE run_id=?", (int(chosen_run),)).fetchone()
                if row:
                    st.session_state.regulens_result=json.loads(row[0])
                    st.session_state.last_run_time=row[1]
                    append_audit("demo_operator", "HISTORICAL_RUN_LOADED", "assessment", str(chosen_run), {})
                    st.success("Selected run loaded. Open Findings & Audit.")
        else:
            st.info("No saved runs yet. Run an assessment to create persistent history.")
    with op_tabs[1]:
        verification=verify_audit_chain()
        if verification["valid"]:
            st.success(f"Hash-chain integrity passed for {verification['checked']} audit events.")
        else:
            st.error(f"Audit chain integrity failed at event {verification['failed_event_id']}.")
        audit=list_audit(300)
        if audit:
            audit_rows=[{"event_id":e["event_id"],"created_at":e["created_at"],"actor":e["actor"],"action":e["action"],"entity_type":e["entity_type"],"entity_id":e["entity_id"],"details":json.dumps(e["details"],ensure_ascii=False),"event_hash":e["event_hash"]} for e in audit]
            st.dataframe(pd.DataFrame(audit_rows),use_container_width=True,hide_index=True)
            st.download_button("Export audit log CSV",pd.DataFrame(audit_rows).to_csv(index=False),"regulens_audit_log.csv","text/csv")
    with op_tabs[2]:
        st.write("Notifications are durably queued locally. Email/Teams/webhook delivery needs real connector credentials and is deliberately not faked.")
        if st.button("Queue a demo compliance alert", key="queue_alert"):
            result=st.session_state.regulens_result or {}
            mid=enqueue_notification("local-demo-inbox", {"subject":"ReguLens compliance assessment update","created_at":datetime.now().isoformat(timespec="seconds"),"metrics":result.get("metrics",{}),"note":"Synthetic demo alert; external delivery is not configured."})
            st.success(f"Alert queued locally with message ID {mid}.")
        outbox=list_outbox(100)
        if outbox:
            st.dataframe(pd.DataFrame([{"message_id":x["message_id"],"created_at":x["created_at"],"channel":x["channel"],"status":x["status"],"attempts":x["attempts"],"payload":json.dumps(x["payload"],ensure_ascii=False)} for x in outbox]),use_container_width=True,hide_index=True)
        else: st.info("No notifications queued yet.")
    with op_tabs[3]:
        st.markdown("**Implemented locally**")
        st.write("- SQLite persistent workspace and run history\n- Hash-chained audit events with integrity verification\n- Durable local notification outbox\n- Regulatory source/control edits and remediation workflow\n- Downloadable CSV/JSON evidence bundles")
        st.markdown("**Not connected / needs deployment configuration**")
        st.write("- Regulator feeds and authoritative legal-source subscriptions\n- Enterprise SSO / IAM and role provisioning\n- Email, Microsoft Teams and webhook delivery\n- ITSM ticketing (ServiceNow/Jira), GRC platforms, evidence vaults\n- Central database, encrypted secret management, backup/restore, monitoring and production hosting\n- LLM/RAG service with approved model, source citations and evaluation")
        st.warning("Do not claim these external integrations are live. This build is a persistent, auditable local prototype; production deployment requires security review, connector credentials, access control, resilience testing and validation by compliance/legal experts.")
